# DOOR TRACKER APP - GUI VERSION
# Tracks several projects (jobs). Each project has its own doors, and each
# door has its own devices. Pick the project from the dropdown at the top;
# the table, summary, buttons and reports all work on that project.
# Everything is saved in projects.json (see storage.py).
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
# sv_ttk is the "Sun Valley" theme: the modern Windows 11 look, in light and
# dark (installed with pip, and listed in requirements.txt).
import sv_ttk
# messagebox shows pop-up error and confirmation boxes.
from tkinter import messagebox
# filedialog opens the standard "Save as" window to pick where to save a file.
from tkinter import filedialog
# date gives today's date, used in the report's file name.
from datetime import date
# The Door class, to create new doors, and the list of allowed status letters.
from door import Door, VALID_STATUSES
# The Project class, to make a project when there are none yet.
from project import Project
# Our own report.py, which builds the text report.
import report
# Our own storage.py, which loads and saves every project.
# We write storage.project_list, storage.save_projects(), and so on.
import storage

# The text color for each status, in light mode and in dark mode. These are
# hex color codes (#RRGGBB). Dark mode uses brighter colors, because the
# darker ones are hard to read on a dark background.
# N isn't listed, so N rows use the normal text color.
STATUS_COLORS = {
    "light": {
        "C": "#2e7d32",   # green
        "P": "#b58900",   # yellow
        "R": "#c62828",   # red
    },
    "dark": {
        "C": "#66bb6a",   # bright green
        "P": "#ffca28",   # bright yellow
        "R": "#ef5350",   # bright red
    },
}

# The project picked in the dropdown at the top. Every function that works
# on doors uses current_project.doors. It's set when the app starts, and
# changed by show_project() when another project is picked.
current_project = None


# Clear the table and fill it again from the current project's doors.
# Call this whenever a door is added, edited, or removed, so the table always matches the saved data.
def refresh_tree():
    # Remove every row currently in the table.
    for row in tree.get_children():
        tree.delete(row)

    for door in current_project.doors:
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

    # Update the totals at the top to match the table.
    refresh_summary()


# Count the doors and devices, and show the totals in the summary at the top.
# Called at the end of refresh_tree(), so it updates automatically whenever
# a door is added, edited, or removed.
def refresh_summary():
    # How many doors have each overall status. door.status() only ever gives
    # back C, P, or R, so those are the only keys needed.
    counts = {"C": 0, "P": 0, "R": 0}
    for door in current_project.doors:
        # += 1 adds one to the count for this door's status.
        counts[door.status()] += 1

    # Count devices across every door. N devices are skipped (continue jumps to
    # the next device), the same way they're ignored for the door status.
    devices_total = 0
    devices_done = 0
    for door in current_project.doors:
        for device_status in door.devices.values():
            if device_status == "N":
                continue
            devices_total += 1
            if device_status == "C":
                devices_done += 1

    # Work out the percent complete. Dividing by 0 crashes Python, so check
    # for "no devices yet" first. round() turns 77.8 into 78.
    if devices_total == 0:
        percent = 0
    else:
        percent = round(devices_done / devices_total * 100)

    # .config() changes a widget after it was created; here, the label's text.
    # "\n" puts the device totals on a second line.
    # Two f-strings next to each other inside the brackets are joined into one,
    # which is how a long line of text is split over several lines of code.
    summary_label.config(text=f"{len(current_project.doors)} doors: {counts['C']} complete, "
                              f"{counts['P']} pending, {counts['R']} restrained\n"
                              f"Devices: {devices_done} of {devices_total} complete ({percent}%)")


# Find the door that's selected (clicked) in the table.
# If a device row is selected, use the door it belongs to.
# Returns the Door object, or None if nothing is selected.
# Used by the Edit Door button and the main window's Delete Door button.
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
    return current_project.find_door(tree.item(row, "text"))


# Runs when a row in the table is double-clicked: open the Edit window for it.
# "event" holds details about the click, like where the mouse was (event.y).
def row_double_clicked(event):
    # identify_row() gives the row under the mouse, or "" if the click was
    # on empty space below the last row.
    row = tree.identify_row(event.y)
    if row == "":
        return "break"
    # Select the clicked row, then open Edit for it like the Edit Door button.
    tree.selection_set(row)
    open_edit_door()
    # "break" stops tkinter's normal double-click action, which would also
    # collapse or expand the door's device list.
    return "break"


# Get a new pop-up window (Add Door, Edit Door, or a project window) ready.
# All three pop-ups need the same steps, so they're written once here.
def setup_popup(popup):
    # (No colors needed here: sv_ttk colors every window and list to match
    # light or dark mode by itself.)
    # transient(window) tells the desktop this window belongs to the main
    # window, so it always stays in front of it and never gets hidden behind.
    popup.transient(window)
    # Wait until the window is actually on screen before grab_set().
    # A double-click opens the Edit window while the mouse is still busy with
    # the second click, so it appears a moment later than usual. Without this
    # wait, grab_set() fails with "grab failed: window not viewable".
    popup.wait_visibility()
    # grab_set() stops clicks on the main window until this one is closed.
    popup.grab_set()


# Open the "Add Door" window. Runs when the Add Door button is clicked.
def open_add_door():
    # Toplevel = a second window that opens on top of the main one.
    add_window = tk.Toplevel(window)
    add_window.title("Add Door")
    # Theme colors, stay in front, block clicks on the main window.
    setup_popup(add_window)

    # Build the door with no name yet. Devices get added to it as the user
    # clicks Add Device, and the name is filled in when they click Save Door.
    new_door = Door("")

    # --- Row 0: door name ---
    # grid() places widgets in rows and columns, like a spreadsheet.
    # sticky="w" lines the widget up on the left (w = west).
    # padx / pady add empty space around the widget, in pixels.
    ttk.Label(add_window, text="Door name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)

    # An Entry is a one-line box the user can type in.
    name_entry = ttk.Entry(add_window, width=30)

    # columnspan=2 lets the name box stretch across columns 1 and 2.
    name_entry.grid(row=0, column=1, columnspan=2, sticky="w", padx=10, pady=5)

    # --- Row 1: device name box + status dropdown ---
    ttk.Label(add_window, text="Device:").grid(row=1, column=0, sticky="w", padx=10)
    device_entry = ttk.Entry(add_window, width=20)
    device_entry.grid(row=1, column=1, sticky="w", padx=10)

    # A Combobox is a dropdown. state="readonly" means you can only pick
    # from the list (C, P, R, N), not type something else.
    status_box = ttk.Combobox(add_window, values=VALID_STATUSES, width=4, state="readonly")

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
    ttk.Button(add_window, text="Add Device", command=add_device).grid(row=2, column=2, padx=10, pady=5)

    # Runs when Save Door is clicked.
    def save_door():
        name = name_entry.get().strip()
        if name == "":
            messagebox.showerror("Missing name", "Door name cannot be blank.", parent=add_window)
            return
        # find_door ignores upper/lowercase, so "joes door" matches "Joes Door".
        if current_project.find_door(name) is not None:
            messagebox.showerror("Duplicate door", f"{name} already exists.", parent=add_window)
            return

        new_door.name = name
        current_project.doors.append(new_door)
        # Save to projects.json so the door is kept after the app closes.
        storage.save_projects()
        # Redraw the main table so the new door shows up.
        refresh_tree()
        # Close the Add Door window.
        add_window.destroy()

    # --- Row 4: Save Door and Cancel buttons ---
    # sticky="e" lines Save Door up on the right (e = east), next to Cancel.
    # Save Door is the main action here, so it gets the blue Accent style.
    ttk.Button(add_window, text="Save Door", command=save_door, style="Accent.TButton").grid(row=4, column=1, sticky="e", pady=10)
    # Cancel just closes the window. new_door was never added to the project,
    # so nothing is saved.
    ttk.Button(add_window, text="Cancel", command=add_window.destroy).grid(row=4, column=2, pady=10)


# Open the "Edit Door" window for the door selected in the table.
# Runs when the Edit Door button is clicked.
# In this window you can rename the door, change a device's status, delete a
# device, or add a new one. Every change is saved straight away, so there's
# no Save button, only Close.
def open_edit_door():
    door = get_selected_door()
    if door is None:
        messagebox.showerror("No door selected", "Click a door in the list first.")
        return

    edit_window = tk.Toplevel(window)
    edit_window.title(f"Edit Door - {door.name}")
    # Theme colors, stay in front, block clicks on the main window.
    setup_popup(edit_window)

    # --- Row 0: door name + Rename button ---
    ttk.Label(edit_window, text="Door name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    name_entry = ttk.Entry(edit_window, width=25)

    # Put the current name in the box so the user can change it.
    # insert(0, ...) means "put this text at the start of the box".
    name_entry.insert(0, door.name)
    name_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    # --- Row 1: list of this door's devices ---
    # exportselection=False keeps the clicked device selected while you pick
    # a status from the dropdown. Without it, tkinter only allows one
    # selection at a time, so picking from the dropdown would unselect the
    # device and Set Status would say "Click a device in the list first."
    device_listbox = tk.Listbox(edit_window, height=8, exportselection=False)
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

    # Run after every change: save to projects.json, then redraw the main
    # table and this window's device list so both show the change.
    def changes_made():
        storage.save_projects()
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
        other_door = current_project.find_door(new_name)
        if other_door is not None and other_door is not door:
            messagebox.showerror("Duplicate door", f"{new_name} already exists.", parent=edit_window)
            return

        door.name = new_name
        # Update the window title to show the new name.
        edit_window.title(f"Edit Door - {door.name}")
        changes_made()

    ttk.Button(edit_window, text="Rename", command=rename_door).grid(row=0, column=2, padx=10, pady=5)

    # --- Row 2: status dropdown + Set Status button (for the selected device) ---
    ttk.Label(edit_window, text="Status:").grid(row=2, column=0, sticky="w", padx=10)
    status_box = ttk.Combobox(edit_window, values=VALID_STATUSES, width=4, state="readonly")
    status_box.grid(row=2, column=1, sticky="w", padx=10)

    # Runs when Set Status is clicked: give the selected device the status
    # picked in the dropdown.
    def set_status():
        device_name = get_selected_device()
        if device_name is None:
            return

        door.devices[device_name] = status_box.get()
        changes_made()

    ttk.Button(edit_window, text="Set Status", command=set_status).grid(row=2, column=2, padx=10, pady=5)

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
        if messagebox.askyesno("Delete Device", f"Delete {device_name} from {door.name}?", parent=edit_window):
            # del removes this device and its status from the dictionary.
            del door.devices[device_name]
            changes_made()

    ttk.Button(edit_window, text="Delete Device", command=delete_device).grid(row=3, column=2, padx=10, pady=5)

    # --- Rows 4-5: add a new device ---
    # pady=(15, 5) adds 15 pixels of space above this row and 5 below,
    # to separate "add a new device" from the editing controls above.
    ttk.Label(edit_window, text="New device:").grid(row=4, column=0, sticky="w", padx=10, pady=(15, 5))
    new_device_entry = ttk.Entry(edit_window, width=20)
    new_device_entry.grid(row=4, column=1, sticky="w", padx=10, pady=(15, 5))
    # A second dropdown just for the new device, so it doesn't get mixed up
    # with the one used for Set Status.
    new_status_box = ttk.Combobox(edit_window, values=VALID_STATUSES, width=4, state="readonly")
    new_status_box.set("P")
    new_status_box.grid(row=4, column=2, padx=10, pady=(15, 5))

    # Runs when Add Device is clicked.
    def add_device():
        device_name = new_device_entry.get().strip()
        if device_name == "":
            messagebox.showerror("Missing device", "Type a name first.", parent=edit_window)
            return

        # find_device ignores upper/lowercase, so "lock" matches "Lock".
        if door.find_device(device_name) is not None:
            messagebox.showerror("Duplicate device", f"{device_name} is already on this door.", parent=edit_window)
            return

        door.devices[device_name] = new_status_box.get()
        # Empty the box, ready for the next device.
        new_device_entry.delete(0, "end")
        changes_made()

    ttk.Button(edit_window, text="Add Device", command=add_device).grid(row=5, column=2, padx=10, pady=5)

    # --- Row 6 (left side): Delete Door button ---
    # Deletes the whole door. If Yes is clicked, the door is gone, so this
    # window closes too. It's on the left, away from Close, so it's harder to
    # click by accident.
    def delete_this_door():
        if confirm_and_delete_door(door, edit_window):
            edit_window.destroy()

    ttk.Button(edit_window, text="Delete Door", command=delete_this_door).grid(row=6, column=0, sticky="w", padx=10, pady=10)

    # --- Row 6 (right side): Close button ---
    # Changes are already saved, so Close just closes the window.
    ttk.Button(edit_window, text="Close", command=edit_window.destroy).grid(row=6, column=2, padx=10, pady=10)

    # Fill the device list when the window first opens.
    refresh_devices()


# Ask "are you sure?", then delete the door if Yes is clicked.
# parent = the window the pop-up should appear on top of.
# Returns True if the door was deleted, False if the user clicked No.
# Used by the Delete Door button in the main window and the one in the Edit window,
# so the confirm-and-delete steps are only written once.
def confirm_and_delete_door(door, parent):
    # Ask first, since a removed door can't be brought back.
    # "\n" starts a new line inside the pop-up message.
    # icon="warning" shows a warning symbol instead of a question mark.
    # The icon name must be lowercase: error, info, question, or warning.
    if messagebox.askyesno("Delete Door", f"Delete {door.name} and all its devices?\nThis can't be undone.",
                           icon="warning", parent=parent):
        current_project.doors.remove(door)
        # Save so the door is also gone from projects.json.
        storage.save_projects()
        refresh_tree()
        return True
    return False


# Remove the door selected in the table. Runs when the main window's Delete Door button is clicked.
def remove_selected_door():
    door = get_selected_door()
    if door is None:
        messagebox.showerror("No door selected", "Click a door in the list first.")
        return
    confirm_and_delete_door(door, window)


# Turn a project name into something safe to use in a file name.
# Letters, numbers, - and _ are kept; anything else (spaces, /, :, and so on)
# becomes _ , because some characters aren't allowed in file names.
# Example: "Westfield Mall / Phase 2" -> "Westfield_Mall___Phase_2"
def safe_file_name(text):
    safe = ""
    for character in text:
        # isalnum() is True for letters and numbers.
        if character.isalnum() or character in "-_":
            safe += character
        else:
            safe += "_"
    return safe


# Save a report of every door.
# file_type is "txt" for a text file or "pdf" for a PDF.
# Called by export_text() and export_pdf() below, so the "Save as" and error
# handling steps are only written once for both formats.
def export_report(file_type):
    # Start the suggested file name with the project's name, so reports for
    # different jobs don't get mixed up.
    name_start = safe_file_name(current_project.name)

    if file_type == "pdf":
        description = "PDF files"
    else:
        description = "Text files"

    # Open a "Save as" window. It gives back the chosen file path, or nothing
    # if the user clicks Cancel. date.today() puts today's date in the
    # suggested name, like Westfield_Mall_report_2026-11-23.txt
    file_path = filedialog.asksaveasfilename(parent=window, title="Save report as",
                                             defaultextension=f".{file_type}",
                                             filetypes=[(description, f"*.{file_type}")],
                                             initialfile=f"{name_start}_report_{date.today()}.{file_type}")
    # "not file_path" is True when it's empty, meaning Cancel was clicked.
    if not file_path:
        return

    # try/except catches errors, like saving to a folder you're not allowed
    # to write in, and shows a pop-up instead of crashing.
    try:
        if file_type == "pdf":
            report.make_pdf_report(current_project, file_path, summary_label.cget("text"))
        else:
            report.make_text_report(current_project, file_path, summary_label.cget("text"))
    except OSError as error:
        messagebox.showerror("Could not save", f"The report could not be saved:\n{error}")
        return

    # showinfo is a pop-up with just an OK button.
    messagebox.showinfo("Report saved", f"Report saved to:\n{file_path}")


# Run when "Text file" is picked from the Export menu.
# A menu item's command can't pass anything to the function it runs, so these
# two small functions each call export_report() with the right file type.
def export_text():
    export_report("txt")


# Run when "PDF" is picked from the Export menu.
def export_pdf():
    export_report("pdf")


# Fill the project dropdown with every project's name, and show the current
# project as the one selected.
def refresh_project_choices():
    names = []
    for project in storage.project_list:
        names.append(project.name)
    # values= is the list of choices in the dropdown.
    project_box.config(values=names)
    # .set() changes what the dropdown is showing.
    project_box.set(current_project.name)


# Switch the whole window over to this project: the title, the dropdown,
# the table, and the summary.
def show_project(project):
    # "global" lets this function change current_project, which was created
    # at the top of the file. Without it, Python would make a new variable
    # that only exists inside this function.
    global current_project
    current_project = project
    window.title(f"TrackerApp - {project.name}")
    refresh_project_choices()
    # refresh_tree() also updates the summary, so both now show this project.
    refresh_tree()


# Runs when a project is picked from the dropdown.
# .current() gives the position of the picked choice: 0 for the first, 1 for
# the second, and so on. The dropdown lists the projects in the same order as
# project_list, so that position finds the right project.
def project_chosen(event):
    position = project_box.current()
    if position >= 0:
        show_project(storage.project_list[position])


# Open the project window, used for both New and Edit.
#   project=None (the default) -> a New project: the boxes start empty.
#   project=<a Project>        -> Edit that project: the boxes start filled in.
# The form is the same either way, so one function handles both.
def open_project_window(project=None):
    project_window = tk.Toplevel(window)
    if project is None:
        project_window.title("New Project")
    else:
        project_window.title(f"Edit Project - {project.name}")
    # Theme colors, stay in front, block clicks on the main window.
    setup_popup(project_window)

    # The four boxes, one per row. Each row is a label on the left and a box
    # on the right. This list pairs each label with the Project attribute it
    # fills in, so the rows can be built with one loop instead of four copies.
    fields = [
        ("Project name:", "name"),
        ("Job number:", "job_number"),
        ("Address / site:", "address"),
        ("Customer / GC:", "customer"),
    ]
    # Remembers each box by its attribute name, so save_project() can read
    # them: entries["name"], entries["job_number"], and so on.
    entries = {}
    # enumerate() gives each item's position (0, 1, 2, 3) along with the item,
    # which is used as the row number.
    for row, (label_text, attribute) in enumerate(fields):
        ttk.Label(project_window, text=label_text).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        entry = ttk.Entry(project_window, width=35)
        entry.grid(row=row, column=1, columnspan=2, sticky="w", padx=10, pady=5)
        # When editing, fill the box with the project's current value.
        # getattr(project, "job_number") is the same as project.job_number;
        # it's used here because the attribute name is in a variable.
        if project is not None:
            entry.insert(0, getattr(project, attribute))
        entries[attribute] = entry

    # Runs when Save is clicked.
    def save_project():
        name = entries["name"].get().strip()
        if name == "":
            messagebox.showerror("Missing name", "Project name cannot be blank.", parent=project_window)
            return
        # Block the name if a DIFFERENT project already uses it. "is not
        # project" still lets you fix the capitals on this project's own name.
        other_project = storage.find_project(name)
        if other_project is not None and other_project is not project:
            messagebox.showerror("Duplicate project", f"{name} already exists.", parent=project_window)
            return

        if project is None:
            # New: make the project and add it to the list.
            saved_project = Project(name)
            storage.project_list.append(saved_project)
        else:
            # Edit: change the existing project.
            saved_project = project
            saved_project.name = name

        # Copy the other three boxes into the project. setattr() is the
        # opposite of getattr(): setattr(p, "address", "12 Main St") is the
        # same as p.address = "12 Main St".
        for attribute in ["job_number", "address", "customer"]:
            setattr(saved_project, attribute, entries[attribute].get().strip())

        storage.save_projects()
        # Switch to the new or edited project. This also updates the title and
        # the dropdown, so a new name shows up straight away.
        show_project(saved_project)
        project_window.destroy()

    # Save is the main action here, so it gets the blue Accent style.
    ttk.Button(project_window, text="Save", command=save_project, style="Accent.TButton").grid(row=4, column=1, sticky="e", pady=10)
    ttk.Button(project_window, text="Cancel", command=project_window.destroy).grid(row=4, column=2, padx=10, pady=10)


# Runs when the New button next to the dropdown is clicked.
def new_project():
    open_project_window()


# Runs when the Edit button next to the dropdown is clicked.
def edit_project():
    open_project_window(current_project)


# Runs when the Delete button next to the dropdown is clicked.
# Deletes the current project and all of its doors, after asking first.
def delete_project():
    # Always keep at least one project, so there's somewhere to add doors.
    if len(storage.project_list) == 1:
        messagebox.showerror("Can't delete", "This is your only project. Make a new project first, then delete this one.")
        return

    door_count = len(current_project.doors)
    if messagebox.askyesno("Delete project",
                           f"Delete the project {current_project.name} and all {door_count} of its doors?\nThis can't be undone.",
                           icon="warning", parent=window):
        storage.project_list.remove(current_project)
        storage.save_projects()
        # The current project is gone, so switch to the first one left.
        show_project(storage.project_list[0])


# Switch the whole app to "light" or "dark" mode.
def apply_theme(theme):
    # This also recolors every window and list (including pop-ups opened
    # later) as soon as tkinter gets to it, a moment after this function.
    sv_ttk.set_theme(theme)
    # Taller table rows, so the list is easier to read and tap on a touch
    # screen. set_theme() resets the table's style, so this comes after it.
    ttk.Style().configure("Treeview", rowheight=28)
    # Each mode has its own status colors (see STATUS_COLORS at the top).
    for status, color in STATUS_COLORS[theme].items():
        tree.tag_configure(status, foreground=color)
    # The button offers the OTHER mode.
    if theme == "dark":
        theme_button.config(text="Light mode")
    else:
        theme_button.config(text="Dark mode")


# Runs when the Light mode / Dark mode button is clicked: switch to the
# other mode, and remember it for next time.
def toggle_theme():
    if sv_ttk.get_theme() == "dark":
        new_theme = "light"
    else:
        new_theme = "dark"
    apply_theme(new_theme)
    storage.save_setting("theme", new_theme)


##########################################################################
# Build the main window. Everything below runs once, when the app starts.
##########################################################################


# Load the saved projects before building the window.
# The first time, this also moves the doors from the old door_list.json
# into "My First Project" (see storage.py).
storage.load_projects()

# A brand-new install has no projects at all. Make an empty one, so there's
# always a project to add doors to.
if len(storage.project_list) == 0:
    storage.project_list.append(Project(storage.FIRST_PROJECT_NAME))
    storage.save_projects()

# Create the main window.
window = tk.Tk()
window.title("TrackerApp")
window.geometry("560x680")   # width x height in pixels (wide enough for the project row)

# A row along the bottom of the window to hold the buttons.
# side="bottom" keeps the buttons visible even if the window is made smaller.
# The main window uses pack() (stacks things), and the Add Door and Edit Door
# windows use grid() (rows and columns). Never use both in the same window,
# or it freezes.
button_frame = ttk.Frame(window)
button_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
# style="Accent.TButton" is sv_ttk's blue button. Use it only for the main
# action in each window, so the eye goes straight to it. Every other button
# stays the normal gray.
ttk.Button(button_frame, text="Add Door", command=open_add_door, style="Accent.TButton").pack(side="left")

# padx=(10, 0) puts 10 pixels of space on the left of the button, none on the right.
ttk.Button(button_frame, text="Edit Door", command=open_edit_door).pack(side="left", padx=(10, 0))

# The Export button opens a small drop-down menu to pick the report format.
# A Menubutton is a button that shows a Menu when clicked. The theme draws
# the little arrow itself.
export_button = ttk.Menubutton(button_frame, text="Export")

# tearoff=False removes a dashed line tkinter normally puts at the top of
# menus (clicking it would pop the menu out into its own little window).
export_menu = tk.Menu(export_button, tearoff=False)
export_menu.add_command(label="Text file (.txt)", command=export_text)
export_menu.add_command(label="PDF (.pdf)", command=export_pdf)

# Connect the menu to the button.
export_button.config(menu=export_menu)
export_button.pack(side="left", padx=(10, 0))

# side="right" puts Delete Door on the far right, away from Add and Edit,
# so it's harder to click by accident.
ttk.Button(button_frame, text="Delete Door", command=remove_selected_door).pack(side="right")

# The project picker along the top of the window: a label and a dropdown.
# It's packed first, so it sits above the summary and the table.
project_frame = ttk.Frame(window)
project_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))
ttk.Label(project_frame, text="Project:").pack(side="left")
# state="readonly" means you can only pick a project, not type in the box.
project_box = ttk.Combobox(project_frame, state="readonly", width=25)
project_box.pack(side="left", padx=(5, 0))
# New / Edit / Delete project buttons, to the right of the dropdown.
ttk.Button(project_frame, text="New", command=new_project).pack(side="left", padx=(10, 0))
ttk.Button(project_frame, text="Edit", command=edit_project).pack(side="left", padx=(5, 0))
ttk.Button(project_frame, text="Delete", command=delete_project).pack(side="left", padx=(5, 0))
# "<<ComboboxSelected>>" is the event tkinter sends when a choice is picked.
project_box.bind("<<ComboboxSelected>>", project_chosen)

# The progress summary along the top of the window.
# font=(name, size, "bold") makes it bigger and bold so it stands out.
# justify="left" lines up both lines of text on the left.
# It must be packed BEFORE the table below, or it would end up under it.
# The summary and the Light/Dark mode button share one row, in a Frame:
# the summary on the left, the button on the right.
summary_frame = ttk.Frame(window)
summary_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))
summary_label = ttk.Label(summary_frame, text="", font=("TkDefaultFont", 11, "bold"), justify="left")
summary_label.pack(side="left")
# The button's text ("Dark mode" or "Light mode") is set by apply_theme().
theme_button = ttk.Button(summary_frame, command=toggle_theme)
# anchor="n" keeps it at the top of the row, level with the summary's first line.
theme_button.pack(side="right", anchor="n")

# A Treeview is a table where rows can have rows inside them, like folders.
# Column "#0" is the built-in first column (door or device name).
# columns=("status",) adds one more column, called "status".
tree = ttk.Treeview(window, columns=("status",))
tree.heading("#0", text="Door / Device")
tree.heading("status", text="Status")
tree.column("status", width=80, anchor="center")
# fill="both" + expand=True make the table grow when the window is resized.
tree.pack(fill="both", expand=True, padx=10, pady=10)

# Double-clicking a door (or one of its devices) opens the Edit window.
# "<Double-1>" means a double-click with mouse button 1 (the left button).
tree.bind("<Double-1>", row_double_clicked)

# Turn on the theme the user picked last time (light the very first time).
# This also colors the status rows: "C" green, "P" yellow, "R" red.
apply_theme(storage.load_setting("theme", "light"))

# Start on the first project. This fills the dropdown, the table and the
# summary.
show_project(storage.project_list[0])

# Start the GUI. This keeps the window open and waits for clicks.
# Any code below this line only runs after the window is closed.
window.mainloop()
