async function lireTicketOCR(which){
  var photos=window['_'+which+'TicketPhotos'];
  if(!Array.isArray(photos)||!photos.length){notify("Prends d'abord la photo du ticket","error");return;}
  var listId=(which==='pos'?'posTicketList':'depTicketList');
  _ticketEnsure(listId);
  var box=document.getElementById(listId);
  notify('Lecture de '+photos.length+' ticket(s)...');
  var filled=0;
  for(var idx=0;idx<photos.length;idx++){
    var r;
    try{r=await api('/api/ocr-ticket',{method:'POST',body:{photo:photos[idx]}});}catch(e){continue;}
    if(!r||!r.ok)continue;
    var d=r.data||{};
    if(!d.ok||(!d.code&&!d.montant))continue;
    var rows=box?box.querySelectorAll('.tkrow'):[];
    var target=null;
    for(var rr=0;rr<rows.length;rr++){
      var cc=rows[rr].querySelector('.tkc'),aa=rows[rr].querySelector('.tka');
      if(cc&&!cc.value&&aa&&!aa.value){target=rows[rr];break;}
    }
    if(target){
      if(d.code)target.querySelector('.tkc').value=d.code;
      if(d.montant)target.querySelector('.tka').value=d.montant;
    }else{
      addTicketRow(listId,d.code||'',d.montant||'');
    }
    filled++;
  }
  if(filled)notify('Lu : '+filled+' ticket(s) rempli(s) - verifie les codes','success');
  else notify('Rien detecte, saisis manuellement','error');
}
