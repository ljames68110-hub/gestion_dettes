function _ticketPhotos(raw){
  if(!raw)return [];
  raw=(''+raw).trim();
  if(raw.charAt(0)==='['){try{var a=JSON.parse(raw);return Array.isArray(a)?a.filter(Boolean):[];}catch(e){return [raw];}}
  return [raw];
}
function onTicketPhotoPick(input,which){
  var key='_'+which+'TicketPhotos';
  if(!Array.isArray(window[key]))window[key]=[];
  if(!input.files||!input.files.length)return;
  var files=Array.prototype.slice.call(input.files);
  var done=0;
  files.forEach(function(f){
    resizeImageFull(f,1400).then(function(b64){
      if(b64)window[key].push(b64);
      done++;
      if(done===files.length){_renderTicketPhotos(which);input.value='';}
    });
  });
}
function _renderTicketPhotos(which){
  var key='_'+which+'TicketPhotos';
  var arr=Array.isArray(window[key])?window[key]:[];
  var box=document.getElementById(which+'TicketPhotoList');
  if(!box)return;
  box.innerHTML='';
  arr.forEach(function(src,i){
    var w=document.createElement('div');
    w.style.cssText='position:relative;display:inline-block;margin:4px 6px 0 0';
    var im=document.createElement('img');
    im.src=src;
    im.style.cssText='max-height:90px;max-width:120px;border-radius:6px;border:1px solid var(--border);cursor:zoom-in';
    im.onclick=function(){openPhotoLightbox(src);};
    var bt=document.createElement('button');
    bt.type='button';bt.innerHTML='&times;';
    bt.style.cssText='position:absolute;top:-6px;right:-6px;background:var(--red);color:#fff;border:none;border-radius:50%;width:20px;height:20px;cursor:pointer;font-size:12px;line-height:1';
    bt.onclick=function(){_removeTicketPhoto(which,i);};
    w.appendChild(im);w.appendChild(bt);box.appendChild(w);
  });
}
function _removeTicketPhoto(which,idx){
  var key='_'+which+'TicketPhotos';
  if(Array.isArray(window[key])){window[key].splice(idx,1);_renderTicketPhotos(which);}
}
function _clearTicketPhoto(which){
  window['_'+which+'TicketPhotos']=[];
  var f=document.getElementById(which+'TicketPhotoFile');if(f)f.value='';
  var box=document.getElementById(which+'TicketPhotoList');if(box)box.innerHTML='';
}
function _ticketPhotoBlock(t){
  var arr=_ticketPhotos(t.photo_ticket);
  var add='<label style="display:inline-block;font-size:12px;color:var(--gold2);cursor:pointer;margin-top:6px">+ Ajouter une photo<input type="file" accept="image/*" multiple style="display:none" onchange="uploadTransPhoto(this,'+t.id+')"></label>';
  if(!arr.length){return '<div style="margin-top:6px">'+add+'</div>';}
  var imgs='';
  arr.forEach(function(src,i){
    imgs+='<div style="position:relative;display:inline-block;margin:4px 8px 0 0">'
      +'<img src="'+src+'" style="max-height:130px;max-width:150px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);cursor:zoom-in;display:block" onclick="openTransPhotoFull('+t.id+','+i+')">'
      +'<button type="button" onclick="removeTransPhoto('+t.id+','+i+')" style="position:absolute;top:-6px;right:-6px;background:var(--red);color:#fff;border:none;border-radius:50%;width:22px;height:22px;cursor:pointer;font-size:13px;line-height:1">&times;</button>'
      +'</div>';
  });
  return '<div style="padding:10px 0;text-align:center">'+imgs
    +'<div style="margin-top:8px"><button type="button" class="btn" onclick="openTransPhotoFull('+t.id+',0)" style="font-size:12px;padding:5px 12px">Voir en entier</button>'+add+'</div></div>';
}
function openTransPhotoFull(tid,idx){
  tid=parseInt(tid);idx=idx||0;
  var x=allTransactions.find(function(y){return y.id===tid;});
  if(!x&&typeof clientTransactions!=='undefined')x=clientTransactions[tid];
  if(!x)return;
  var arr=_ticketPhotos(x.photo_ticket);
  if(arr.length)openPhotoLightbox(arr[idx]||arr[0]);
}
function _saveTransPhotos(tid,arr){
  var raw=JSON.stringify(arr);
  api('/api/transactions/'+tid+'/photo-ticket',{method:'POST',body:{photo:raw}}).then(function(r){
    if(r&&r.ok){
      var x=allTransactions.find(function(y){return y.id===parseInt(tid);});
      if(x)x.photo_ticket=raw;
      if(typeof clientTransactions!=='undefined'&&clientTransactions[tid])clientTransactions[tid].photo_ticket=raw;
      notify('Photos enregistrees','success');openTransDetail(tid);
    }else notify('Erreur photo','error');
  });
}
function uploadTransPhoto(input,tid){
  if(!input.files||!input.files.length)return;
  var x=allTransactions.find(function(y){return y.id===parseInt(tid);});
  if(!x&&typeof clientTransactions!=='undefined')x=clientTransactions[tid];
  var arr=_ticketPhotos(x?x.photo_ticket:'');
  var files=Array.prototype.slice.call(input.files);var done=0;
  files.forEach(function(f){resizeImageFull(f,1400).then(function(b64){if(b64)arr.push(b64);done++;if(done===files.length)_saveTransPhotos(tid,arr);});});
}
function removeTransPhoto(tid,idx){
  var x=allTransactions.find(function(y){return y.id===parseInt(tid);});
  if(!x&&typeof clientTransactions!=='undefined')x=clientTransactions[tid];
  var arr=_ticketPhotos(x?x.photo_ticket:'');
  arr.splice(idx,1);_saveTransPhotos(tid,arr);
}
