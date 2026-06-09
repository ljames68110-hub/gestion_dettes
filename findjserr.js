
const fs=require('fs');
const {execSync}=require('child_process');
const html=fs.readFileSync('web/index.html','utf8');
const lines=html.split('\n');
let inScript=false,start=0,buf=[],blocks=[];
for(let i=0;i<lines.length;i++){
  const L=lines[i];
  if(!inScript){
    const m=L.match(/<script(?![^>]*\bsrc=)[^>]*>/);
    if(m){inScript=true;start=i;buf=[L.slice(m.index+m[0].length)];}
  }else{
    const idx=L.indexOf('</script>');
    if(idx!==-1){buf.push(L.slice(0,idx));blocks.push({start,end:i,code:buf.join('\n')});inScript=false;}
    else buf.push(L);
  }
}
blocks.forEach((b,bi)=>{
  const padded='\n'.repeat(b.start)+b.code;
  const tmp='__chk_'+bi+'.js';
  fs.writeFileSync(tmp,padded);
  try{execSync('node --check '+tmp,{stdio:'pipe'});console.log('Bloc '+bi+' (lignes '+(b.start+1)+'-'+(b.end+1)+'): OK');}
  catch(e){console.log('Bloc '+bi+' (lignes '+(b.start+1)+'-'+(b.end+1)+'): ERREUR');console.log((e.stderr||e.message).toString().split('\n').slice(0,5).join('\n'));}
  fs.unlinkSync(tmp);
});
