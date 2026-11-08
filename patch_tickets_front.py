#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_tickets_front.py  (Point 3 - interface)
Ajoute la page "Tickets d'encaissement" : bouton de navigation, page (dossier
source + import + ajout manuel + onglets PCS/Transcash/Paysafecard + galerie),
et le module JavaScript. Sans node. Idempotent, CRLF/LF preserves.
A lancer dans le dossier du projet : python patch_tickets_front.py
"""
import os, sys

F = "web/index.html"
MARK = "initTicketsEnc"

# --- ancres mono-ligne (label, old, new) ---
NAV_OLD = '<div class="nav-item" onclick="goPage(\'factures\',this)"><span class="nav-icon">\U0001F9FE</span> Factures &amp; Bons</div>'
NAV_NEW = NAV_OLD + '\n    <div class="nav-item" onclick="goPage(\'tickets\',this)"><span class="nav-icon">\U0001F3AB</span> Tickets encaissement</div>'

TITLES_OLD = "compta:'Comptabilite',corbeille:'Corbeille'};"
TITLES_NEW = "compta:'Comptabilite',tickets:\"Tickets d'encaissement\",corbeille:'Corbeille'};"

HOOK_OLD = "if(name==='corbeille')loadCorbeille();"
HOOK_NEW = "if(name==='corbeille')loadCorbeille();if(name==='tickets'){initTicketsEnc();}"

# --- page (une seule ligne, inseree avant pg-factures) ---
_INP = "padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:13px"
PAGE = (
 '<div class="page" id="pg-tickets">'
   '<div class="card" style="margin-bottom:14px">'
     '<div class="card-title">\U0001F3AB Tickets d\'encaissement</div>'
     '<p style="font-size:13px;color:var(--text3)">Range tes tickets de paiement (PCS, Transcash, Paysafecard) dans l\'appli. Ils sont stockés <b>dans la base</b> : chiffrés à la fermeture et envoyés sur le cloud automatiquement, comme le reste. Rien ne reste en clair sur le PC.</p>'
     '<div style="display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap">'
       '<input type="text" id="tkSrcDir" readonly placeholder="Aucun dossier choisi" style="flex:1;min-width:220px;' + _INP + '">'
       '<button class="btn" onclick="pickTicketSrc()">Choisir le dossier…</button>'
       '<button class="btn primary" onclick="importTickets(this)">⬇ Importer depuis le dossier</button>'
     '</div>'
     '<div id="tkImportInfo" style="font-size:12px;color:var(--text3);margin-top:8px"></div>'
     '<div style="font-size:12px;color:var(--text3);margin-top:6px">Dans ce dossier, dépose tes tickets dans les sous-dossiers <b>PCS</b>, <b>Transcash</b> et <b>Paysafecard</b> (créés automatiquement). À l\'import, chaque image est enregistrée dans l\'appli <b>puis supprimée</b> du dossier de départ.</div>'
     '<div style="border-top:1px solid var(--border);margin:14px 0"></div>'
     '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
       '<span style="font-size:13px;color:var(--text2)">Ajout manuel :</span>'
       '<select id="tkAddType" style="' + _INP + '"><option value="pcs">PCS</option><option value="transcash">Transcash</option><option value="paysafecard">Paysafecard</option></select>'
       '<label class="btn" style="cursor:pointer">\U0001F4CE Ajouter une ou des images<input type="file" accept="image/*" multiple style="display:none" onchange="addTicketManual(this)"></label>'
     '</div>'
   '</div>'
   '<div id="tkTabs" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px"></div>'
   '<div id="tkGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px"></div>'
 '</div>'
)
PG_FACT_OLD = '<div class="page" id="pg-factures">'
PG_FACT_NEW = PAGE + PG_FACT_OLD

# --- module JS (injecte avant le dernier </body>) ---
JS = r"""
/* ===== TICKETS D'ENCAISSEMENT ===== */
var _tkFilter = 'tous';
var _TK_LABELS = {tous:'Tous', pcs:'PCS', transcash:'Transcash', paysafecard:'Paysafecard'};
var _TK_COLORS = {pcs:'#c9a84c', transcash:'#4c9bc9', paysafecard:'#6bbf59'};

function initTicketsEnc(){ _tkFilter='tous'; loadTicketsEnc(); }

async function loadTicketsEnc(){
  var r = await api('/api/tickets-enc?type=' + encodeURIComponent(_tkFilter));
  if(!r || !r.ok){ return; }
  var d = r.data || {};
  var src = document.getElementById('tkSrcDir');
  if(src) src.value = d.src || '';
  renderTkTabs(d.counts || {tous:0,pcs:0,transcash:0,paysafecard:0});
  renderTkGrid(d.items || []);
}

function renderTkTabs(counts){
  var tabs = document.getElementById('tkTabs'); if(!tabs) return;
  var order = ['tous','pcs','transcash','paysafecard'];
  tabs.innerHTML = '';
  order.forEach(function(k){
    var n = counts[k] || 0;
    var on = (_tkFilter === k);
    var b = document.createElement('button');
    b.className = 'btn' + (on ? ' primary' : '');
    b.textContent = _TK_LABELS[k] + ' (' + n + ')';
    b.onclick = function(){ _tkFilter = k; loadTicketsEnc(); };
    tabs.appendChild(b);
  });
}

function renderTkGrid(items){
  var g = document.getElementById('tkGrid'); if(!g) return;
  if(!items.length){
    g.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text3);padding:30px">Aucun ticket. Choisis un dossier et clique « Importer », ou ajoute une image à la main.</div>';
    return;
  }
  g.innerHTML = '';
  items.forEach(function(it){
    var col = _TK_COLORS[it.type] || 'var(--gold2)';
    var card = document.createElement('div');
    card.className = 'card';
    card.style.cssText = 'padding:8px;position:relative';
    card.innerHTML =
      '<div style="position:absolute;top:10px;left:10px;background:' + col + ';color:#1a1a1a;font-size:10px;font-weight:700;padding:1px 6px;border-radius:4px">' + (_TK_LABELS[it.type] || it.type) + '</div>'
    + '<div style="position:absolute;top:8px;right:8px"><button class="btn" style="padding:2px 7px;font-size:12px;background:var(--bg3);color:var(--red)" title="Supprimer" onclick="delTicketEnc(' + it.id + ')">✕</button></div>'
    + '<img id="tkimg-' + it.id + '" style="width:100%;height:120px;object-fit:cover;border-radius:6px;background:var(--bg3);cursor:pointer;margin-top:4px" onclick="viewTicketEnc(' + it.id + ')" alt="">'
    + '<div style="font-size:11px;color:var(--text3);margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + (it.nom_fichier||'') + '">' + (it.nom_fichier || ('Ticket #' + it.id)) + '</div>'
    + '<div style="font-size:11px;color:var(--text3)">' + (it.date_ajout ? it.date_ajout.replace('T',' ').slice(0,16) : '') + '</div>';
    g.appendChild(card);
    api('/api/tickets-enc/' + it.id + '/image').then(function(ri){
      if(ri && ri.ok && ri.data && ri.data.image){
        var im = document.getElementById('tkimg-' + it.id);
        if(im) im.src = ri.data.image;
      }
    });
  });
}

async function pickTicketSrc(){
  var r = await api('/api/tickets-enc/source/pick', {method:'POST'});
  if(r && r.ok && r.data && r.data.dir){
    await api('/api/tickets-enc/source', {method:'POST', body:{dir:r.data.dir}});
    var s = document.getElementById('tkSrcDir'); if(s) s.value = r.data.dir;
    if(typeof notify==='function') notify('Dossier des tickets enregistré');
  }
}

async function importTickets(btn){
  if(btn){ btn.disabled = true; var _o = btn.textContent; btn.textContent = 'Import en cours…'; }
  var info = document.getElementById('tkImportInfo');
  try{
    var r = await api('/api/tickets-enc/import', {method:'POST'});
    if(r && r.ok){
      var im = r.data.imported || {};
      var msg = r.data.total + ' ticket(s) importé(s) — PCS ' + (im.pcs||0) + ', Transcash ' + (im.transcash||0) + ', Paysafecard ' + (im.paysafecard||0) + '. ' + (r.data.deleted||0) + ' supprimé(s) du dossier.';
      if(r.data.errors && r.data.errors.length) msg += ' (' + r.data.errors.length + ' avertissement(s))';
      if(info){ info.textContent = msg; info.style.color = 'var(--green)'; }
      if(typeof notify==='function') notify(r.data.total + ' ticket(s) importé(s)');
      loadTicketsEnc();
    } else {
      var e = (r && r.error) || 'Import impossible';
      if(info){ info.textContent = e; info.style.color = 'var(--red)'; }
      if(typeof notify==='function') notify(e, 'error');
    }
  } catch(e){
    if(info){ info.textContent = 'Erreur : ' + e; info.style.color = 'var(--red)'; }
  } finally {
    if(btn){ btn.disabled = false; btn.textContent = _o; }
  }
}

function addTicketManual(input){
  var type = (document.getElementById('tkAddType')||{}).value || 'pcs';
  var files = input.files; if(!files || !files.length) return;
  var done = 0, total = files.length;
  for(var i=0;i<files.length;i++){
    (function(file){
      var reader = new FileReader();
      reader.onload = async function(e){
        await api('/api/tickets-enc', {method:'POST', body:{type:type, image:e.target.result, nom_fichier:file.name}});
        done++;
        if(done === total){
          input.value = '';
          if(typeof notify==='function') notify(total + ' ticket(s) ajouté(s)');
          loadTicketsEnc();
        }
      };
      reader.readAsDataURL(file);
    })(files[i]);
  }
}

async function delTicketEnc(id){
  if(!confirm('Supprimer ce ticket ?')) return;
  var r = await api('/api/tickets-enc/' + id, {method:'DELETE'});
  if(r && r.ok){ if(typeof notify==='function') notify('Ticket supprimé'); loadTicketsEnc(); }
}

async function viewTicketEnc(id){
  var r = await api('/api/tickets-enc/' + id + '/image');
  if(!r || !r.ok || !r.data || !r.data.image) return;
  var ov = document.getElementById('tkViewer');
  if(!ov){
    ov = document.createElement('div');
    ov.id = 'tkViewer';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;z-index:99999;cursor:zoom-out;padding:20px';
    ov.onclick = function(){ ov.style.display = 'none'; };
    ov.innerHTML = '<img id="tkViewerImg" style="max-width:95%;max-height:95%;object-fit:contain;border-radius:8px">';
    document.body.appendChild(ov);
  }
  document.getElementById('tkViewerImg').src = r.data.image;
  ov.style.display = 'flex';
}
"""

def read(p):
    with open(p, "r", encoding="utf-8", newline="") as f: return f.read()
def write(p, t):
    with open(p, "w", encoding="utf-8", newline="") as f: f.write(t)

def repl(t, old, new, label):
    n = t.count(old)
    if n != 1:
        print("  [X] %s : ancre trouvee %dx (attendu 1)" % (label, n)); sys.exit(1)
    return t.replace(old, new, 1)

def main():
    if not os.path.exists(F):
        print("ERREUR : %s introuvable" % F); sys.exit(1)
    t = read(F); eol = "\r\n" if "\r\n" in t else "\n"
    if MARK in t:
        print("  [=] deja patche, rien a faire"); sys.exit(0)

    # NAV_NEW contient un \n -> on le remplace par l'EOL reel du fichier
    nav_new = NAV_NEW.replace("\n", eol)
    t = repl(t, NAV_OLD, nav_new, "bouton navigation")
    print("  [+] bouton navigation")
    t = repl(t, TITLES_OLD, TITLES_NEW, "TITLES")
    print("  [+] titre de page")
    t = repl(t, HOOK_OLD, HOOK_NEW, "hook goPage")
    print("  [+] hook goPage")
    t = repl(t, PG_FACT_OLD, PG_FACT_NEW, "page pg-tickets")
    print("  [+] page pg-tickets")

    pos = t.rfind("</body>")
    if pos < 0:
        print("  [X] </body> introuvable"); sys.exit(1)
    block = "<script>" + eol + eol.join(JS.split("\n")) + eol + "</script>" + eol
    t = t[:pos] + block + t[pos:]
    write(F, t)
    print("  [+] module JavaScript injecte")

    if read(F).count(MARK) < 1:
        print("  [!] verification inattendue"); sys.exit(1)
    print("\nTermine (interface tickets d'encaissement).")

if __name__ == "__main__":
    main()
