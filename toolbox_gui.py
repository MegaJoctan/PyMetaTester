import tkinter as tk
from tkinter import ttk
from datetime import datetime

class SimToolboxGUI:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trade Simulator Monitor")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")

        # === ACCOUNT INFO DISPLAY ===
        self.account_label = tk.Label(
            self.root,
            text="",
            font=("Courier", 8),
            anchor="w",
            justify="left",
            bg="#f0f0f0",
            fg="#333",
        )
        self.account_label.pack(fill="x", padx=5, pady=(5, 6))

        # === POSITION TABLE ===
        position_frame = tk.LabelFrame(self.root, text="Open Positions", bg="#f0f0f0")
        position_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.position_columns = [
            "id", "symbol", "time", "type", "volume", "open_price", "sl", "tp",
            "swap", "price", "profit", "comment"
        ]

        self.position_tree = ttk.Treeview(position_frame, columns=self.position_columns, show="headings", height=10)
        for col in self.position_columns:
            self.position_tree.heading(col, text=col)
            self.position_tree.column(col, anchor="center", width=80)
        self.position_tree.pack(fill="both", expand=True, padx=5, pady=5)

        vsb1 = ttk.Scrollbar(position_frame, orient="vertical", command=self.position_tree.yview)
        self.position_tree.configure(yscrollcommand=vsb1.set)
        vsb1.pack(side="right", fill="y")

        # === ORDER TABLE ===
        order_frame = tk.LabelFrame(self.root, text="Pending Orders", bg="#f0f0f0")
        order_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.order_columns = [
            "id", "symbol", "time", "type", "volume", "open_price", "sl", "tp", "price",
            "expiry_date", "expiration_mode", "comment"
        ]

        self.order_tree = ttk.Treeview(order_frame, columns=self.order_columns, show="headings", height=10)
        for col in self.order_columns:
            self.order_tree.heading(col, text=col)
            self.order_tree.column(col, anchor="center", width=100)
        self.order_tree.pack(fill="both", expand=True, padx=5, pady=5)

        vsb2 = ttk.Scrollbar(order_frame, orient="vertical", command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right", fill="y")

    def update(self, account_info: dict, positions: list, orders: list):
        # === Update account info ===
        acc_text = (
            f"Balance: {account_info['balance']:.2f} | "
            f"Equity: {account_info['equity']:.2f} | "
            f"Profit: {account_info['profit']:.2f} | "
            f"Margin: {account_info['margin']:.2f} | "
            f"Free margin: {account_info['free_margin']:.5f} | "
            f"Margin level: {account_info['margin_level']:.2f}%"
        )
        self.account_label.config(text=acc_text)

        # === Refresh positions ===
        for row in self.position_tree.get_children():
            self.position_tree.delete(row)

        for pos in positions:
            row = [pos.get(col, "") for col in self.position_columns]
            self.position_tree.insert("", "end", values=row)

        # === Refresh orders ===
        for row in self.order_tree.get_children():
            self.order_tree.delete(row)

        for order in orders:
            row = []
            for col in self.order_columns:
                val = order.get(col, "")
                if isinstance(val, datetime):
                    val = val.strftime("%Y-%m-%d %H:%M:%S")
                row.append(val)
            self.order_tree.insert("", "end", values=row)

        self.root.update()

    def run(self):
        self.root.mainloop()
