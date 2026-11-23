import tkinter as tk

from tkinter import ttk
from tkinter import messagebox
from door import Door

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


def open_add_door():
    add_window = tk.Toplevel(window)
    add_window.title("Add door")

    add_window.grab_set()

    new_door = Door("")

    tk.Label(add_window, text="Door name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    name_entry =tk.Entry(add_window, width=30)
    name_entry.grid(row="0", column="1", sticky="w", padx=10)

    status_box = ttk.Combobox(add_window, values=data.VALID_STATUSES, width=4, state="readonly")
    status_box.set("P")
    status_box.grid(row=1, column=2, padx=10)

    device_listbox = tk.Listbox(add_window, height=8)
    device_listbox.grid(row=3, column=0, columnspan=3, sticky="we", padx=10, pady=5)

    def add_device():
        device_name = device_entry,get().strip()
        if device_name == "":
            messagebox.showerror("Missing device", "Type a device name first.", parent=add_window)
            return
        if new_door.find_device(device_name) is not None:
            messagebox.showerror("Duplaicate device", f"{device_name} is already on this door.", parent=add_window)
            return
        device_status = status_box.get()
        new_door.devices[device_name] = device_status

        device_listbox.inset("end", f"{device_name}  {device_status}")
        device_entry.delete(0,"end")
    tk.button(add_window, text="Add Device", command=add_device).grid(row=2, column=2, padx=10, pady=10)

    def save_door():
        name = name_entry.get().strip()
        if name == "":
            messagebox.showererror("Missing name", "Door name cannot be blank.", parent=add_window)
            return

        if data.find_door(name) is not None:
            messagebox.showerror("Duplicate door", f"{name} already exists", parent=add_window)
            return

        new_door.anme = name
        data.door_list.appand(new_door)
        refresh_tree()

    tk.Button(add_window, text="Save Door", command=save_door).grid(row=4, column=2, pady=10)

data.load_doors()
window = tk.Tk()
window.title("TrackerApp")
window.geometry("500x600")
button_frame = tk.Frame(window)
button_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
tk.Button(button_frame, text="Add Door", command=open_add_door).pack(side="left")
tree = ttk.Treeview(window, columns=("status",))
tree.heading("#0", text="Door / Device")
tree.heading("status", text="Status")
tree.column("status", width=80, anchor="center")

tree.pack(fill="both", expand=True, padx=10, pady=10)

for status, color in STATUS_COLORS.items():
    tree.tag_configure(status, foreground=color)


refresh_tree()

window.mainloop()