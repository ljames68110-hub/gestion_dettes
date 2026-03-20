# main.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as tb
from decimal import Decimal, ROUND_HALF_UP
import db  # notre module db.py

FEE_RATES = {
    'PCS': Decimal('0.07'),
    'Paysafecard': Decimal('0.05'),
    'Liquide': Decimal('0.00'),
    'Virement': Decimal('0.00'),
    'WesternUnion': Decimal('0.00'),
}

def to_decimal(x):
    try:
        return Decimal(str(x))
    except:
        return Decimal('0')

class App:
    def __init__(self, root):
        self.root = root
        root.title("Gestion dettes - Prototype")
        root.geometry("1000x600")

        db.init_db()

        self.left = ttk.Frame(root, width=250)
        self.left.pack(side='left', fill='y', padx=10, pady=10)
        self.right = ttk.Frame(root)
        self.right.pack(side='right', fill='both', expand=True, padx=10, pady=10)

        ttk.Label(self.left, text="Clients", font=('Inter', 12, 'bold')).pack(anchor='w')
        self.lst_clients = tk.Listbox(self.left, width=30, height=25)
        self.lst_clients.pack(fill='y', expand=True)
        self.lst_clients.bind('<<ListboxSelect>>', self.on_client_select)

        btn_frame = ttk.Frame(self.left)
        btn_frame.pack(fill='x', pady=6)
        ttk.Button(btn_frame, text="Ajouter client", command=self.add_client).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="Rafraîchir", command=self.refresh_clients).pack(side='left', padx=2)

        self.header = ttk.Frame(self.right)
        self.header.pack(fill='x')
        self.lbl_name = ttk.Label(self.header, text="Sélectionne un client", font=('Inter', 16, 'bold'))
        self.lbl_name.pack(anchor='w')

        stats_frame = ttk.Frame(self.right)
        stats_frame.pack(fill='x', pady=6)
        self.lbl_nb = ttk.Label(stats_frame, text="Transactions: 0")
        self.lbl_nb.pack(side='left', padx=6)
        self.lbl_total = ttk.Label(stats_frame, text="Total encaissé: 0.00 €")
        self.lbl_total.pack(side='left', padx=6)
        self.lbl_frais = ttk.Label(stats_frame, text="Total frais: 0.00 €")
        self.lbl_frais.pack(side='left', padx=6)

        cols = ('date','type','motif','quantite','prix_unitaire','montant_brut','mode','frais','montant_net')
        self.tree = ttk.Treeview(self.right, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor='w')
        self.tree.pack(fill='both', expand=True)

        action_frame = ttk.Frame(self.right)
        action_frame.pack(fill='x', pady=6)
        ttk.Button(action_frame, text="Nouvelle transaction", command=self.open_new_transaction).pack(side='left', padx=4)
        ttk.Button(action_frame, text="Exporter CSV", command=self.export_csv).pack(side='left', padx=4)

        self.refresh_clients()

    def refresh_clients(self):
        self.lst_clients.delete(0, 'end')
        for cid, nom in db.get_clients():
            self.lst_clients.insert('end', f"{cid}|{nom}")

    def add_client(self):
        nom = simpledialog.askstring("Nouveau client", "Nom du client:")
        if nom:
            db.add_client(nom)
            self.refresh_clients()

    def on_client_select(self, event):
        sel = self.lst_clients.curselection()
        if not sel:
            return
        text = self.lst_clients.get(sel[0])
        cid = int(text.split('|',1)[0])
        self.current_client_id = cid
        client = db.get_client(cid)
        self.lbl_name.config(text=client[1])
        self.load_client_sheet(cid)

    def load_client_sheet(self, client_id):
        stats = db.get_stats(client_id)
        self.lbl_nb.config(text=f"Transactions: {stats['nb_transactions']}")
        self.lbl_total.config(text=f"Total encaissé: {stats['total_encaisse']:.2f} €")
        self.lbl_frais.config(text=f"Total frais: {stats['total_frais']:.2f} €")
        for i in self.tree.get_children():
            self.tree.delete(i)
        for tr in db.get_transactions(client_id):
            self.tree.insert('', 'end', iid=tr[0], values=(tr[1], tr[2], tr[3], tr[4], f"{tr[5]:.2f}", f"{tr[6]:.2f}", tr[7], f"{tr[8]:.2f}", f"{tr[9]:.2f}"))

    def open_new_transaction(self):
        if not hasattr(self, 'current_client_id'):
            messagebox.showwarning("Aucun client", "Sélectionne d'abord un client.")
            return
        NewTransactionDialog(self.root, self.current_client_id, self.on_transaction_saved)

    def on_transaction_saved(self, client_id):
        self.load_client_sheet(client_id)

    def export_csv(self):
        import csv
        if not hasattr(self, 'current_client_id'):
            messagebox.showwarning("Aucun client", "Sélectionne d'abord un client.")
            return
        cid = self.current_client_id
        rows = db.get_transactions(cid)
        fname = f"export_client_{cid}.csv"
        with open(fname, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id','date','type','motif','quantite','prix_unitaire','montant_brut','mode_paiement','frais','montant_net','reference','notes'])
            for r in rows:
                writer.writerow(r)
        messagebox.showinfo("Export", f"Exporté dans {fname}")

class NewTransactionDialog(tk.Toplevel):
    def __init__(self, parent, client_id, callback):
        super().__init__(parent)
        self.client_id = client_id
        self.callback = callback
        self.title("Nouvelle transaction")
        self.geometry("420x380")
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text="Type").grid(row=0, column=0, sticky='w')
        self.combo_type = ttk.Combobox(frm, values=['debit','credit'], state='readonly')
        self.combo_type.current(1)
        self.combo_type.grid(row=0, column=1, sticky='ew')

        ttk.Label(frm, text="Motif").grid(row=1, column=0, sticky='w')
        self.combo_motif = ttk.Combobox(frm, values=['Tabac','Bedo','Recharge','Pot','Cigarette','Achat'])
        self.combo_motif.grid(row=1, column=1, sticky='ew')

        ttk.Label(frm, text="Quantité").grid(row=2, column=0, sticky='w')
        self.entry_qty = ttk.Entry(frm); self.entry_qty.insert(0,"1"); self.entry_qty.grid(row=2, column=1, sticky='ew')

        ttk.Label(frm, text="Prix unitaire").grid(row=3, column=0, sticky='w')
        self.entry_unit = ttk.Entry(frm); self.entry_unit.insert(0,"0.00"); self.entry_unit.grid(row=3, column=1, sticky='ew')

        ttk.Label(frm, text="Mode paiement").grid(row=4, column=0, sticky='w')
        self.combo_mode = ttk.Combobox(frm, values=['Liquide','Virement','PCS','Paysafecard','WesternUnion'], state='readonly')
        self.combo_mode.current(0); self.combo_mode.grid(row=4, column=1, sticky='ew')

        ttk.Label(frm, text="Montant brut").grid(row=5, column=0, sticky='w')
        self.lbl_brut = ttk.Label(frm, text="0.00 €"); self.lbl_brut.grid(row=5, column=1, sticky='w')

        ttk.Label(frm, text="Frais").grid(row=6, column=0, sticky='w')
        self.lbl_frais = ttk.Label(frm, text="0.00 €"); self.lbl_frais.grid(row=6, column=1, sticky='w')

        ttk.Label(frm, text="Montant net").grid(row=7, column=0, sticky='w')
        self.lbl_net = ttk.Label(frm, text="0.00 €"); self.lbl_net.grid(row=7, column=1, sticky='w')

        ttk.Button(frm, text="Enregistrer", command=self.save).grid(row=8, column=0, columnspan=2, pady=10)

        self.combo_mode.bind('<<ComboboxSelected>>', lambda e: self.calc())
        self.entry_qty.bind('<KeyRelease>', lambda e: self.calc())
        self.entry_unit.bind('<KeyRelease>', lambda e: self.calc())
        self.calc()

    def calc(self):
        q = to_decimal(self.entry_qty.get() or '0')
        pu = to_decimal(self.entry_unit.get() or '0')
        brut = (q * pu).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        mode = self.combo_mode.get()
        rate = FEE_RATES.get(mode, Decimal('0'))
        frais = (brut * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net = (brut - frais).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.lbl_brut.config(text=f"{brut} €")
        self.lbl_frais.config(text=f"{frais} €")
        self.lbl_net.config(text=f"{net} €")
        self._calc_values = (brut, frais, net)

    def save(self):
        type_ = self.combo_type.get()
        motif = self.combo_motif.get()
        quantite = int(self.entry_qty.get() or 0)
        prix_unitaire = float(self.entry_unit.get() or 0.0)
        mode = self.combo_mode.get()
        brut, frais, net = self._calc_values
        db.add_transaction(self.client_id, type_, motif, quantite, prix_unitaire, mode, float(frais), float(brut), float(net))
        messagebox.showinfo("OK", "Transaction enregistrée.")
        self.callback(self.client_id)
        self.destroy()

if __name__ == "__main__":
    style = tb.Style(theme='flatly')
    root = style.master
    app = App(root)
    root.mainloop()
