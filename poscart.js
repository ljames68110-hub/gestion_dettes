function renderPosCart(){
  var body=document.getElementById('posCartBody');if(!body)return;
  if(!posCart.length){body.innerHTML='<div class="pos-empty">Cliquez sur des articles pour les ajouter</div>';document.getElementById('posTotal').textContent='0.00 EUR';document.getElementById('posCashout').disabled=true;return;}
  body.innerHTML='';var total=0;
  posCart.forEach(function(l){
    var sub=(l.gratuit?0:l.prix)*l.qty;total+=sub;
    var row=document.createElement('div');row.className='pos-line';
    var priceHtml=l.gratuit
      ?'<span style="font-size:11px;color:var(--gold2)">Gratuit</span>'
      :'<input type="number" value="'+l.prix.toFixed(2)+'" step="0.5" min="0" onclick="event.stopPropagation()" onchange="posSetPrice('+l.id+',this.value)" style="width:74px;font-size:11px;padding:2px 5px;border-radius:5px;border:1px solid var(--border);background:var(--bg2);color:var(--text)"> <span style="font-size:10px;color:var(--text3)">EUR</span>';
    row.innerHTML='<div class="lname">'+l.nom+'<br>'+priceHtml+'</div><div class="lqty"><button onclick="posChangeQty('+l.id+',-1)">-</button><input type="number" value="'+l.qty+'" min="0" step="1" onchange="posSetQty('+l.id+',this.value)"><button onclick="posChangeQty('+l.id+',1)">+</button></div><div class="lsub">'+sub.toFixed(2)+'</div>'+'<button onclick="posToggleGratuit('+l.id+')" style="border:1px solid var(--border);border-radius:6px;padding:2px 8px;font-size:11px;cursor:pointer;margin-right:4px;background:transparent;color:'+(l.gratuit?'var(--gold2)':'var(--text3)')+'">'+(l.gratuit?'Gratuit':'Offrir')+'</button>'+'<button class="ldel" onclick="posRemove('+l.id+')">x</button>';
    body.appendChild(row);
  });
  document.getElementById('posTotal').textContent=total.toFixed(2)+' EUR';
  document.getElementById('posCashout').disabled=false;
}
function posSetPrice(id,val){
  var line=posCart.find(function(l){return l.id===id;});
  if(line){var p=parseFloat((''+val).replace(',','.'))||0;if(p<0)p=0;line.prix=p;}
  renderPosCart();
}
