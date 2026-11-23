# DOOR TRACKER APP - GUI VERSION
# A window version of trackerapp_2.py. It uses the same door_list.json,
# so doors added in either version show up in both.
#
# How a GUI runs is different from the terminal version:
#   1. The code below builds the window (table, buttons).
#   2. window.mainloop() at the very bottom then waits for the user.
#   3. When a button is clicked, the function connected to it runs.
# So instead of "while True" loops with input(), each action is a function
# that runs when its button is clicked.

# tkinter is Python's built-in GUI library. "tk" is a short nickname for it.
import tkinter as tk
# ttk has nicer-looking versions of tkinter's widgets, like the Treeview table
# and the Combobox dropdown.
from tkinter import ttk
# messagebox shows pop-up error and confirmation boxes.
from tkinter import messagebox
# The Door class, to create new doors.
from door import Door
# Reuse the door list and the load/save functions from the terminal version.
# "as data" means we write data.door_list, data.save_doors(), and so on.
import trackerapp_2 as data

# The text color for each status. These are hex color codes (#RRGGBB).
# N isn't listed, so N rows use the normal text color.
STATUS_COLORS = {
    "C": "#2e7d32",   # green
    "P": "#b58900",   # yellow
    "R": "#c62828",   # red
}


# Clear the table and fill it again from door_list.
# Call this whenever a door is added, edited, or removed, so the table always matches the saved data.
def refresh_tree():
    # Remove every row currently in the table.
    for row in tree.get_children():
        tree.delete(row)

    for door in data.door_list:
        status = door.status()
        # Add the door as a top-level row. "" means it has no parent row,
        # and "end" puts it at the bottom of the table.
        # values=(status,) fills the Status column. The comma makes it a
        # tuple (a list that can't change), which Treeview expects.
        # tags=(status,) lets us color the row by its status (see the bottom).
        # open=True shows the door's devices without having to click the arrow.
        door_row = tree.insert("", "end", text=door.name, values=(status,), tags=(status,), open=True)

        # Add each device as a row underneath its door (door_row is the parent).
        for device_name, device_status in door.devices.items():
            tree.insert(door_row, "end", text=device_name, values=(device_status,), tags=(device_status,))


# Find the door that's selected (clicked) in the table.
# If a device row is selected, use the door it belongs to.
# Returns the Door object, or None if nothing is selected.
# Used by Edit Door (and Remove Door in the next step).
def get_selected_door():
    # tree.selection() gives the selected rows. It's empty if nothing is clicked.
    selected = tree.selection()
    if len(selected) == 0:
        return None
    row = selected[0]

    # tree.parent() gives the row this one sits under. Door rows have no
    # parent (""), so if there IS a parent, this is a device row: use its door.
    if tree.parent(row) != "":
        row = tree.parent(row)

    # The row's text is the door name, so look the door up by name.
    return data.find_door(tree.item(row, "text"))


# Open the "Add Door" window. Runs when the Add Door button is clicked.
def open_add_door():
    # Toplevel = a second window that opens on top of the main one.
    add_window = tk.Toplevel(window)
    add_window.title("Add door")
    # grab_set() stops clicks on the main window until this one is closed.
    add_window.grab_set()

    # Build the door with no name yet. Devices get added to it as the user
    # clicks Add Device, and the name is filled in when they click Save Door.
    new_door = Door("")

    # --- Row 0: door name ---
    # grid() places widgets in rows and columns, like a spreadsheet.
    # sticky="w" lines the widget up on the left (w = west).
    # padx / pady add empty space around the widget, in pixels.
    tk.Label(add_window, text="Door name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)

    # An Entry is a one-line box the user can type in.
    name_entry = tk.Entry(add_window, width=30)

    # columnspan=2 lets the name box stretch across columns 1 and 2.
    name_entry.grid(row=0, column=1, columnspan=2, sticky="w", padx=10, pady=5)

    # --- Row 1: device name box + status dropdown ---
    tk.Label(add_window, text="Device:").grid(row=1, column=0, sticky="w", padx=10)
    device_entry = tk.Entry(add_window, width=20)
    device_entry.grid(row=1, column=1, sticky="w", padx=10)

    # A Combobox is a dropdown. state="readonly" means you can only pick
    # from the list (C, P, R, N), not type something else.
    status_box = ttk.Combobox(add_window, values=data.VALID_STATUSES, width=4, state="readonly")

    # Start the dropdown on P, since most devices start out pending.
    status_box.set("P")
    status_box.grid(row=1, column=2, padx=10)

    # --- Row 3: list of the devices added so far ---
    # sticky="we" stretches it from the left edge to the right edge (west to east).
    device_listbox = tk.Listbox(add_window, height=8)
    device_listbox.grid(row=3, column=0, columnspan=3, sticky="we", padx=10, pady=5)

    # Runs when Add Device is clicked.
    # This function is INSIDE open_add_door, so it can use device_entry,
    # status_box, new_door, and the other things created above.
    def add_device():
        # .get() reads what's typed in the box. .strip() removes extra spaces.
        device_name = device_entry.get().strip()
        if device_name == "":
            messagebox.showerror("Missing device", "Type a device name first.", parent=add_window)
            # return leaves the function early, so nothing gets added.
            return
        # find_device ignores upper/lowercase, so "lock" matches "Lock".
        if new_door.find_device(device_name) is not None:
            messagebox.showerror("Duplicate device", f"{device_name} is already on this door.", parent=add_window)
            return

        device_status = status_box.get()
        new_door.devices[device_name] = device_status

        # Show the device in the list, then empty the box ready for the next one.
        # .delete(0, "end") deletes from the first character (0) to the last.
        device_listbox.insert("end", f"{device_name}   {device_status}")
        device_entry.delete(0, "end")

    # --- Row 2: Add Device button ---
    # command=add_device means "run add_device when clicked".
    # There's no () after the name: we're handing over the function to run
    # later, not running it now.
    tk.Button(add_window, text="Add Device", command=add_device).grid(row=2, column=2, padx=10, pady=5)

    # Runs when Save Door is clicked.
    def save_door():
        name = name_entry.get().strip()
        if name == "":
            messagebox.showerror("Missing name", "Door name cannot be blank.", parent=add_window)
            return
        # find_door ignores upper/lowercase, so "joes door" matches "Joes Door".
        if data.find_door(name) is not None:
            messagebox.showerror("Duplicate door", f"{name} already exists.", parent=add_window)
            return

        new_door.name = name
        data.door_list.append(new_door)
        # Save to door_list.json so the door is kept after the app closes.
        data.save_doors()
        # Redraw the main table so the new door shows up.
        refresh_tree()
        # Close the Add door window.
        add_window.destroy()

    # --- Row 4: Save Door and Cancel buttons ---
    # sticky="e" lines Save Door up on the right (e = east), next to Cancel.
    tk.Button(add_window, text="Save Door", command=save_door).grid(row=4, column=1, sticky="e", pady=10)
    # Cancel just closes the window. new_door was never added to door_list,
    # so nothing is saved.
    tk.Button(add_window, text="Cancel", command=add_window.destroy).grid(row=4, column=2, pady=10)


# Open the "Edit door" window for the door selected in the table.
# Runs when the Edit Door button is clicked.
# In this window you can rename the door, change a device's status, delete a
# device, or add a new one. Every change is saved straight away, so there's
# no Save button, only Close.
def open_edit_door():
    door = get_selected_door()
    if door is None:
        messagebox.showerror("No door selected", "Click a door in the list first")
        return

    edit_window = tk.Toplevel(window)
    edit_window.title(f"Edit Door - {door.name}")
    # Stop clicks on the main window until this one is closed.
    edit_window.grab_set()

    # --- Row 0: door name + Rename button ---
    tk.Label(edit_window, text="Door name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    name_entry = tk.Entry(edit_window, width=25)

    # Put the current name in the box so the user can change it.
    # insert(0, ...) means "put this text at the start of the box".
    name_entry.insert(0, door.name)
    name_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    # --- Row 1: list of this door's devices ---
    device_listbox = tk.Listbox(edit_window, height=8)
    device_listbox.grid(row=1, column=0, columnspan=3, sticky="we", padx=10, pady=5)

    # A listbox only knows row numbers (0, 1, 2...), not device names.
    # This list keeps the device names in the same order as the listbox rows,
    # so listbox row 0 is device_names[0], row 1 is device_names[1], and so on.
    device_names = []

    # Empty the listbox and fill it again from door.devices.
    # Runs when the window opens and after every change.
    def refresh_devices():
        device_listbox.delete(0, "end")
        device_names.clear()
        for device_name, device_status in door.devices.items():
            device_listbox.insert("end", f"{device_name}   {device_status}")
            device_names.append(device_name)

    # Return the name of the device clicked in the listbox.
    # If no device is selected, show an error pop-up and return None.
    def get_selected_device():
        # curselection() gives the row numbers that are selected, like (2,).
        # It's empty if nothing is selected.
        selected = device_listbox.curselection()
        if len(selected) == 0:
            messagebox.showerror("No device selected", "Click a device in the list first.", parent=edit_window)
            return None
        return device_names[selected[0]]

    # Run after every change: save to door_list.json, then redraw the main
    # table and this window's device list so both show the change.
    def changes_made():
        data.save_doors()
        refresh_tree()
        refresh_devices()

    # Runs when Rename is clicked.
    def rename_door():
        new_name = name_entry.get().strip()
        if new_name == "":
            messagebox.showerror("Missing name", "Door name cannot be blank.", parent=edit_window)
            return

        # Block the name if a DIFFERENT door already uses it. "is not door"
        # still lets you fix the capitals on this door's own name,
        # like "lobby" to "Lobby".
        other_door = data.find_door(new_name)
        if other_door is not None and other_door is not door:
            messagebox.showerror("Duplicate door", f"{new_name} already exists.", parent=edit_window)
            return

        door.name = new_name
        # Update the window title to show the new name.
        edit_window.title(f"Edit Door - {door.name}")
        changes_made()

    tk.Button(edit_window, text="Rename", command=rename_door).grid(row=0, column=2, padx=10, pady=5)

    # --- Row 2: status dropdown + Set Status button (for the selected device) ---
    tk.Label(edit_window, text="Status:").grid(row=2, column=0, sticky="w", padx=10)
    status_box = ttk.Combobox(edit_window, values=data.VALID_STATUSES, width=4, state="readonly")
    status_box.grid(row=2, column=1, sticky="w", padx=10)

    # Runs when Set Status is clicked: give the selected device the status
    # picked in the dropdown.
    def set_status():
        device_name = get_selected_device()
        if device_name is None:
            return

        door.devices[device_name] = status_box.get()
        changes_made()

    tk.Button(edit_window, text="Set Status", command=set_status).grid(row=2, column=2, padx=10, pady=5)

    # When a device is clicked in the listbox, show its current status in the
    # dropdown, so the user can see it before changing it.
    # tkinter passes an "event" with details about the click. We don't need
    # them, but the function still has to accept it.
    def device_clicked(event):
        selected = device_listbox.curselection()
        if len(selected) > 0:
            status_box.set(door.devices[device_names[selected[0]]])

    # bind() connects an event to a function. "<<ListboxSelect>>" is the event
    # tkinter sends when a row in the listbox is clicked.
    device_listbox.bind("<<ListboxSelect>>", device_clicked)

    # --- Row 3: Delete Device button ---
    # Runs when Delete Device is clicked. Asks first, since it can't be undone.
    def delete_device():
        device_name = get_selected_device()
        if device_name is None:
            return

        # askyesno shows Yes/No buttons and returns True if Yes was clicked.
        if messagebox.askyesno("Delete device", f"Delete {device_name} from {door.name}?", parent=edit_window):
            # del removes this device and its status from the dictionary.
            del door.devices[device_name]
            changes_made()

    tk.Button(edit_window, text="Delete device", command=delete_device).grid(row=3, column=2, padx=10, pady=5)

    # --- Rows 4-5: add a new device ---
    # pady=(15, 5) adds 15 pixels of space above this row and 5 below,
    # to separate "add a new device" from the editing controls above.
    tk.Label(edit_window, text="New device:").grid(row=4, column=0, sticky="w", padx=10, pady=(15, 5))
    new_device_entry = tk.Entry(edit_window, width=20)
    new_device_entry.grid(row=4, column=1, sticky="w", padx=10, pady=(15, 5))
    # A second dropdown just for the new device, so it doesn't get mixed up
    # with the one used for Set Status.
    new_status_box = ttk.Combobox(edit_window, values=data.VALID_STATUSES, width=4, state="readonly")
    new_status_box.set("P")
    new_status_box.grid(row=4, column=2, padx=10, pady=(15, 5))

    # Runs when Add device is clicked.
    def add_device():
        device_name = new_device_entry.get().strip()
        if device_name == "":
            messagebox.showerror("Missing device", "Type a name first.", parent=edit_window)
            return

        # find_device ignores upper/lowercase, so "lock" matches "Lock".
        if door.find_device(device_name) is not None:
            messagebox.showerror("Duplicate device", f"{device_name} is already on this door", parent=edit_window)
            return

        door.devices[device_name] = new_status_box.get()
        # Empty the box, ready for the next device.
        new_device_entry.delete(0, "end")
        changes_made()

    tk.Button(edit_window, text="Add device", command=add_device).grid(row=5, column=2, padx=10, pady=5)

    # --- Row 6: Close button ---
    # Changes are already saved, so Close just closes the window.
    tk.Button(edit_window, text="Close", command=edit_window.destroy).grid(row=6, column=2, padx=10, pady=10)

    # Fill the device list when the window first opens.
    refresh_devices()


##########################################################################
# Build the main window. Everything below runs once, when the app starts.
##########################################################################


# Load the saved doors before building the window.
data.load_doors()

# Create the main window.
window = tk.Tk()
window.title("TrackerApp")
window.geometry("500x600")   # width x height in pixels

# A row along the bottom of the window to hold the buttons.
# side="bottom" keeps the buttons visible even if the window is made smaller.
# The main window uses pack() (stacks things), and the Add door and Edit door
# windows use grid() (rows and columns). Never use both in the same window,
# or it freezes.
button_frame = tk.Frame(window)
button_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
tk.Button(button_frame, text="Add Door", command=open_add_door).pack(side="left")
# padx=(10, 0) puts 10 pixels of space on the left of the button, none on the right.
tk.Button(button_frame, text="Edit Door", command=open_edit_door).pack(side="left", padx=(10, 0))

# A Treeview is a table where rows can have rows inside them, like folders.
# Column "#0" is the built-in first column (door or device name).
# columns=("status",) adds one more column, called "status".
tree = ttk.Treeview(window, columns=("status",))
tree.heading("#0", text="Door / Device")
tree.heading("status", text="Status")
tree.column("status", width=80, anchor="center")
# fill="both" + expand=True make the table grow when the window is resized.
tree.pack(fill="both", expand=True, padx=10, pady=10)

# Rows tagged "C" show in green, "P" in yellow, "R" in red.
for status, color in STATUS_COLORS.items():
    tree.tag_configure(status, foreground=color)

# Fill the table with the loaded doors.
refresh_tree()

# Start the GUI. This keeps the window open and waits for clicks.
# Any code below this line only runs after the window is closed.
window.mainloop()
