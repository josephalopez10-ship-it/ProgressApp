import tkinter as tk

from tkinter import ttk

import trackerapp_2 as data

STATUS_COLORS = {
    "C": "#2e7d32",   # green
    "P": "#b58900",   # yellow
    "R": "#c62828",   # red


}

def refresh_tree():

    for row in tree.get_children():
        tree.delete(row)

    for door in data.door_list:
        status = door.status()

        door_row = tree.insert("", "end", text=door.name, values=(status,),tags=(status,), open=True)

        for device_name, device_status in door.devices.items():
            tree.insert(door_row, "end", text=device_name, values=(device_status,),tags=(device_status,))

data.load_doors()

window = tk.Tk()
window.title("TrackerApp")
window.geometry("500x600")

tree = ttk.Treeview(window, columns=("status",))
tree.heading("#0", text="Door / Device")
tree.heading("status", text="Status")
tree.column("status", width=80, anchor="center")

tree.pack(fill="both", expand=True, padx=10, pady=10)

for status, color in STATUS_COLORS.items():
    tree.tag_configure(status, foreground=color)


refresh_tree()

window.mainloop()