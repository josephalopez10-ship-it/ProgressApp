# DOOR TRACKER APP - GUI VERSION
# Tracks several projects (jobs). Each project has its own doors, and each
# door has its own devices. Pick the project from the dropdown at the top;
# the table, summary, buttons and reports all work on that project.
# Everything is saved in projects.json (see storage.py).
#
# How a GUI runs is different from the terminal version:
#   1. The code builds the window (table, buttons, menus).
#   2. window.mainloop() then waits for the user.
#   3. When a button is clicked, the function connected to it runs.
# So instead of "while True" loops with input(), each action is a function
# that runs when its button is clicked.
#
# How this file is laid out:
#   - Settings that never change (constants), like the status colors.
#   - A few stand-alone helper functions.
#   - The TrackerApp class: the whole main window. Every widget, and every
#     action (add a door, export a report...), belongs to it.
#   - main(), at the very bottom, which loads the projects and starts it.

# tkinter is Python's built-in GUI library. "tk" is a short nickname for it.
import tkinter as tk
# tkinter.font makes fonts, like the bold one used for door rows.
from tkinter import font
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
# sys lets us close the app on purpose with sys.exit().
import sys
# traceback prints the full details of an error to the terminal.
import traceback
# date gives today's date, used in the report's file name.
# datetime gives the date AND time, used for "saved at 3:42 PM" in the
# status bar.
from datetime import date, datetime
# The Door class, to create new doors, the list of allowed status letters,
# and STATUS_NAMES, which turns a letter into a word ("C" -> "Complete").
from door import Door, VALID_STATUSES, STATUS_NAMES
# The Project class, to make a project when there are none yet.
from project import Project
# Our own report.py, which builds the text and PDF reports.
import report
# Our own storage.py, which loads and saves every project.
# We write storage.project_list, storage.save_projects(), and so on.
import storage


# ---------------------------------------------------------------------------
# Constants: settings that never change while the app runs. Written in
# CAPITALS, which is how Python programmers mark "don't change this".
# ---------------------------------------------------------------------------

# The app's name and version number, shown in the window title and the
# About box. Raise the version when you release a new set of changes.
APP_NAME = "TrackerApp"
APP_VERSION = "1.0"

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

# The background shade behind each DOOR row in the table, so doors stand
# out from the device rows under them, like a heading. A soft blue-gray in
# light mode, a slightly lighter gray in dark mode.
DOOR_ROW_COLORS = {"light": "#e6ecf3", "dark": "#2c3139"}

# The choices in the "Show:" dropdown above the table, and the door status
# letter each one keeps. None means "don't filter by status".
FILTER_CHOICES = {
    "All doors": None,
    "Complete": "C",
    "Pending": "P",
    "Restrained": "R",
}

# The heading text of each table column, without the sort arrow.
COLUMN_TITLES = {"#0": "Door / Device", "devices": "Devices", "status": "Status"}

# The order doors go in when sorted by Status: problems first, so restrained
# doors are at the top, then pending, then complete.
STATUS_SORT_ORDER = {"R": 0, "P": 1, "C": 2}

# The app's icon, shown in the window's title bar and the taskbar. It's kept
# in the same folder as the code (storage.FOLDER is that folder).
ICON_FILE = storage.FOLDER / "icon.png"

# The window's size the very first time, before any size has been saved:
# width x height in pixels (wide enough for the project row).
DEFAULT_GEOMETRY = "560x680"


# ---------------------------------------------------------------------------
# Helper functions that don't need the window. They're outside the class
# because they only work on the values they're given.
# ---------------------------------------------------------------------------

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


# Check a saved window size and position before using it, and fix it up if
# needed. geometry is text like "700x800+120+40": 700 wide, 800 tall, 120
# pixels from the left of the screen and 40 from the top.
# screen_width / screen_height are the size of the screen it opens on.
# Gives back the text to pass to window.geometry().
def safe_geometry(geometry, screen_width, screen_height):
    # try/except: if the saved text isn't in the right shape (damaged
    # settings file, or a setting from an old version), int() or split()
    # fails with ValueError, and we fall back to the default size.
    try:
        # partition("+") splits at the FIRST "+":
        #   "700x800+120+40" -> "700x800", "+", "120+40"
        size, plus, position = geometry.partition("+")
        width_text, height_text = size.split("x")
        width = int(width_text)
        height = int(height_text)
        x_text, y_text = position.split("+")
        x = int(x_text)
        y = int(y_text)
    except (ValueError, AttributeError):
        return DEFAULT_GEOMETRY

    # Never bigger than the screen (say the last run was on a bigger monitor).
    # min() gives back the smaller of the two numbers.
    width = min(width, screen_width)
    height = min(height, screen_height)

    # If the window would open off the edge of the screen (say a second
    # monitor was unplugged), keep the size but let the desktop place it.
    if x < 0 or y < 0 or x > screen_width - 100 or y > screen_height - 100:
        return f"{width}x{height}"
    return f"{width}x{height}+{x}+{y}"


# Load the saved projects, before the window is built.
# The first time, this also moves the doors from the old door_list.json
# into "My First Project" (see storage.py).
# If a save file is damaged, storage raises a LoadError. Show a pop-up that
# explains what to do, then stop, WITHOUT saving anything, so the damaged
# file (and the projects in it) aren't overwritten.
def load_projects_or_stop():
    try:
        storage.load_projects()
    except storage.LoadError as error:
        # The main window isn't built yet, and a pop-up needs a window to
        # belong to. So make a plain one and hide it with withdraw(); only
        # the pop-up shows.
        error_window = tk.Tk()
        error_window.withdraw()
        messagebox.showerror(f"{APP_NAME} can't open your projects",
                             f"{error}\n\n"
                             "Nothing has been changed or saved.\n\n"
                             "To fix it: restore the file from a backup, or rename it "
                             "(for example to projects_broken.json) to start fresh, "
                             "then open the app again.",
                             parent=error_window)
        error_window.destroy()
        # Also print it, for anyone who started the app from a terminal.
        print(error)
        # sys.exit(1) stops the app here. 1 means "stopped because of a problem".
        sys.exit(1)

    # A brand-new install has no projects at all. Make an empty one, so
    # there's always a project to add doors to.
    if len(storage.project_list) == 0:
        storage.project_list.append(Project(storage.FIRST_PROJECT_NAME))
        storage.save_projects()


# ---------------------------------------------------------------------------
# The main window
# ---------------------------------------------------------------------------

# A class bundles data and the functions that work on it into one thing.
# You already know this from Door: a Door has data (name, devices) and
# functions (status(), progress()). TrackerApp is the same idea for the
# whole window: its data is the widgets (the table, the search box...) and
# the current project, and its functions ("methods") are the app's actions.
#
# "self" is how a method reaches the app's own data. Inside a method,
# self.tree is THE table and self.current_project is the project on screen.
# Every method gets self as its first parameter, but you don't pass it
# yourself: app.refresh_tree() hands app over as self automatically.
#
# Before this class, the app's data were "global" variables at the top of
# the file, and any function changing one needed a "global" line. Keeping
# them on self instead groups everything in one place, and is how most
# bigger tkinter apps are written.
class TrackerApp:

    # __init__ runs once, when the app is created with TrackerApp().
    # It builds the whole window, then shows the first project.
    def __init__(self):
        # The project picked in the dropdown at the top. Every method that
        # works on doors uses self.current_project.doors. It's changed by
        # show_project() when another project is picked.
        self.current_project = None

        # How the table is sorted. Clicking a column heading changes these:
        #   sort_column  = which column: "#0" (name), "devices", "status", or
        #                  None for "not sorted" (doors in the order added).
        #   sort_reverse = False for A to Z / lowest first, True for the
        #                  opposite.
        # Sorting only changes the order on screen; the saved order doesn't.
        self.sort_column = None
        self.sort_reverse = False

        # Create the main window.
        # className is the name the desktop knows the app by. Linux uses it
        # to group the app's windows in the taskbar, and to match it to the
        # menu launcher (see install_launcher.py).
        self.window = tk.Tk(className=APP_NAME)
        self.window.title(APP_NAME)

        # Show the app's icon in the title bar and taskbar.
        # PhotoImage loads a picture file (PNG or GIF) so tkinter can use it.
        # iconphoto(True, ...) uses it for this window AND every pop-up
        # opened later. If icon.png is missing, tkinter raises TclError; the
        # app works fine without an icon, so just carry on without one.
        try:
            self.app_icon = tk.PhotoImage(file=ICON_FILE)
            self.window.iconphoto(True, self.app_icon)
        except tk.TclError:
            self.app_icon = None

        # Open the window at the size and place it was last closed at (or
        # the default size the first time). winfo_screenwidth/height give
        # the screen size.
        saved_geometry = storage.load_setting("window_geometry", DEFAULT_GEOMETRY)
        self.window.geometry(safe_geometry(saved_geometry, self.window.winfo_screenwidth(),
                                           self.window.winfo_screenheight()))
        # The smallest the window can be dragged to, so the buttons and the
        # search row always fit.
        self.window.minsize(480, 450)
        # If a button's function crashes, show a pop-up (see
        # show_unexpected_error) instead of only printing the error to a
        # terminal nobody is looking at.
        self.window.report_callback_exception = self.show_unexpected_error
        # "WM_DELETE_WINDOW" is the message the desktop sends when the
        # window's X button is clicked. protocol() runs quit_app instead, so
        # the window size is saved.
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)

        # Build each part of the window. Each part has its own method below,
        # so __init__ reads like a table of contents.
        # The order matters: pack() stacks things in the order they're
        # packed, so the bottom bars go in first, then the top area, and the
        # table last, to fill whatever space is left.
        self.build_menu_bar()
        self.build_bottom_bars()
        self.build_project_row()
        self.build_summary()
        self.build_search_row()
        self.build_table()
        self.bind_shortcuts()

        # Turn on the theme the user picked last time (light the very first
        # time). This also colors the status rows: C green, P yellow, R red.
        self.apply_theme(storage.load_setting("theme", "light"))

        # Start on the first project. This fills the dropdown, the table and
        # the summary.
        self.show_project(storage.project_list[0])

    # -----------------------------------------------------------------------
    # Building the window
    # -----------------------------------------------------------------------

    # The menu bar along the top of the window: File, Edit, View, Help.
    # A tk.Menu given to window.config(menu=...) becomes the menu bar. Each
    # drop-down (File, Edit...) is another Menu, added with add_cascade().
    # accelerator= only SHOWS the shortcut next to the item; the keys
    # themselves are bound in bind_shortcuts().
    # tearoff=False removes the dashed "tear off" line at the top of a menu.
    def build_menu_bar(self):
        self.menu_bar = tk.Menu(self.window, tearoff=False)
        self.window.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.file_menu.add_command(label="New Project...", command=self.new_project)
        self.file_menu.add_separator()   # a thin line between groups of items
        self.file_menu.add_command(label="Export Text Report...", command=self.export_text)
        self.file_menu.add_command(label="Export PDF Report...", command=self.export_pdf)
        self.file_menu.add_separator()
        # quit_app saves the window size, then closes the window.
        self.file_menu.add_command(label="Quit", accelerator="Ctrl+Q", command=self.quit_app)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.edit_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.edit_menu.add_command(label="Add Door...", accelerator="Ctrl+N", command=self.open_add_door)
        self.edit_menu.add_command(label="Edit Door...", accelerator="Enter", command=self.open_edit_door)
        self.edit_menu.add_command(label="Delete Door", accelerator="Delete", command=self.remove_selected_door)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Edit Project...", command=self.edit_project)
        self.edit_menu.add_command(label="Delete Project", command=self.delete_project)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)

        self.view_menu = tk.Menu(self.menu_bar, tearoff=False)
        # A BooleanVar holds True or False. The checkbutton shows a tick when
        # it's True. apply_theme() keeps it matching the light/dark mode.
        self.dark_mode_on = tk.BooleanVar(value=False)
        self.view_menu.add_checkbutton(label="Dark Mode", variable=self.dark_mode_on, command=self.toggle_theme)
        self.view_menu.add_command(label="Find", accelerator="Ctrl+F", command=self.focus_search)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)

        self.help_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        self.help_menu.add_command(label=f"About {APP_NAME}", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

    # The status bar and the row of buttons along the bottom of the window.
    # The main window uses pack() (stacks things), and the pop-up windows use
    # grid() (rows and columns). Never use both in the same window, or it
    # freezes.
    def build_bottom_bars(self):
        # The status bar along the very bottom. It shows what was done last
        # and when it was saved, like "Added Stair 2 — saved at 3:42 PM".
        # It's packed side="bottom" BEFORE the buttons, so it sits below them.
        self.status_label = ttk.Label(self.window, text="Ready", anchor="w")
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
        # A thin line between the buttons and the status bar.
        ttk.Separator(self.window, orient="horizontal").pack(side="bottom", fill="x", pady=(0, 4))

        # The row of buttons. side="bottom" keeps them visible even if the
        # window is made smaller.
        button_frame = ttk.Frame(self.window)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        # style="Accent.TButton" is sv_ttk's blue button. Use it only for the
        # main action in each window, so the eye goes straight to it. Every
        # other button stays the normal gray.
        ttk.Button(button_frame, text="Add Door", command=self.open_add_door,
                   style="Accent.TButton").pack(side="left")
        # padx=(10, 0) puts 10 pixels of space on the left of the button,
        # none on the right.
        ttk.Button(button_frame, text="Edit Door", command=self.open_edit_door).pack(side="left", padx=(10, 0))
        # (Exporting a report and dark mode are in the File and View menus.)
        # side="right" puts Delete Door on the far right, away from Add and
        # Edit, so it's harder to click by accident.
        ttk.Button(button_frame, text="Delete Door", command=self.remove_selected_door).pack(side="right")

    # The project picker along the top of the window: a label, a dropdown,
    # and New / Edit / Delete project buttons.
    def build_project_row(self):
        project_frame = ttk.Frame(self.window)
        project_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))
        ttk.Label(project_frame, text="Project:").pack(side="left")
        # state="readonly" means you can only pick a project, not type one.
        self.project_box = ttk.Combobox(project_frame, state="readonly", width=25)
        self.project_box.pack(side="left", padx=(5, 0))
        ttk.Button(project_frame, text="New", command=self.new_project).pack(side="left", padx=(10, 0))
        ttk.Button(project_frame, text="Edit", command=self.edit_project).pack(side="left", padx=(5, 0))
        ttk.Button(project_frame, text="Delete", command=self.delete_project).pack(side="left", padx=(5, 0))
        # "<<ComboboxSelected>>" is the event tkinter sends when a choice is
        # picked.
        self.project_box.bind("<<ComboboxSelected>>", self.project_chosen)

    # The progress summary and progress bar, under the project row.
    def build_summary(self):
        # font=(name, size, "bold") makes it bigger and bold so it stands out.
        # justify="left" lines up both lines of text on the left, and
        # anchor="w" keeps the label itself on the left (w = west).
        self.summary_label = ttk.Label(self.window, text="", font=("TkDefaultFont", 11, "bold"), justify="left")
        self.summary_label.pack(side="top", anchor="w", padx=10, pady=(10, 0))

        # A progress bar that fills up as devices are completed, so you can
        # see how far along the project is at a glance.
        # maximum=100 means a value of 100 is a full bar, so the value is the
        # percent. It's filled in by refresh_summary().
        self.progress_bar = ttk.Progressbar(self.window, maximum=100)
        self.progress_bar.pack(side="top", fill="x", padx=10, pady=(8, 0))

    # The search row above the table: a search box and a "Show:" dropdown.
    # Typing or picking a choice hides the doors that don't match, straight
    # away.
    def build_search_row(self):
        search_frame = ttk.Frame(self.window)
        search_frame.pack(side="top", fill="x", padx=10, pady=(10, 0))

        # A StringVar is a tkinter variable that a widget is connected to.
        # Whatever is typed in the box is always in search_text, and
        # search_text.get() reads it. trace_add("write", ...) runs
        # filter_changed every time it changes, which is what makes the
        # table update while you type.
        self.search_text = tk.StringVar()
        self.search_text.trace_add("write", self.filter_changed)
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_text, width=25)
        self.search_entry.pack(side="left", padx=(5, 0))
        # Escape in the search box clears it.
        self.search_entry.bind("<Escape>", lambda event: self.search_text.set(""))

        # The "Show:" dropdown, connected to its own StringVar the same way.
        # list(FILTER_CHOICES) gives just the names: "All doors", "Complete"...
        self.status_filter = tk.StringVar(value="All doors")
        self.status_filter.trace_add("write", self.filter_changed)
        status_filter_box = ttk.Combobox(search_frame, textvariable=self.status_filter,
                                         values=list(FILTER_CHOICES), state="readonly", width=12)
        status_filter_box.pack(side="right")
        ttk.Label(search_frame, text="Show:").pack(side="right", padx=(0, 5))

        # "Showing 3 of 12 doors", under the search row. refresh_tree() fills
        # it in, and leaves it blank when every door is showing.
        self.filter_label = ttk.Label(self.window, text="")
        self.filter_label.pack(side="top", anchor="w", padx=10)

    # The table of doors and devices, filling the rest of the window.
    def build_table(self):
        # A Treeview is a table where rows can have rows inside them, like
        # folders. Column "#0" is the built-in first column (door or device
        # name). columns=("devices", "status") adds two more columns, and
        # refresh_tree() fills them in this same order.
        self.tree = ttk.Treeview(self.window, columns=("devices", "status"))
        # Clicking a heading sorts the table by that column (see
        # heading_clicked). command= needs a function that takes nothing, so
        # each lambda remembers which column it's for and passes it on.
        self.tree.heading("#0", text=COLUMN_TITLES["#0"], command=lambda: self.heading_clicked("#0"))
        self.tree.heading("devices", text=COLUMN_TITLES["devices"], command=lambda: self.heading_clicked("devices"))
        self.tree.heading("status", text=COLUMN_TITLES["status"], command=lambda: self.heading_clicked("status"))
        # How many of the door's devices are complete, like "3 / 4".
        self.tree.column("devices", width=80, anchor="center")
        # width=100 leaves room for the longest word, "Restrained".
        self.tree.column("status", width=100, anchor="center")
        # fill="both" + expand=True make the table grow with the window.
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Double-clicking a door (or one of its devices) opens the Edit
        # window. "<Double-1>" means a double-click with mouse button 1 (the
        # left button).
        self.tree.bind("<Double-1>", self.row_double_clicked)
        # A single click on the empty space below the last row unselects
        # whatever was selected. "<Button-1>" is a click with the left button.
        self.tree.bind("<Button-1>", self.table_clicked)

    # Keyboard shortcuts for the main window:
    #   Enter   -> edit the selected door (like double-clicking it)
    #   Delete  -> delete the selected door (it still asks "are you sure?")
    #   Ctrl+N  -> add a new door
    #   Ctrl+F  -> jump to the search box
    #   Ctrl+Q  -> quit
    # Enter and Delete are bound to the table, so they only work when the
    # table has the focus (after clicking a row). The Ctrl shortcuts are
    # bound to the whole main window. Pop-ups are separate windows, so they
    # don't fire while typing in one.
    # bind() hands the function an "event" with details about the key press.
    # These methods don't take one, so "lambda event: ..." makes a tiny
    # one-line function that accepts the event, ignores it, and calls them.
    def bind_shortcuts(self):
        self.tree.bind("<Return>", lambda event: self.open_edit_door())
        self.tree.bind("<Delete>", lambda event: self.remove_selected_door())
        self.window.bind("<Control-n>", lambda event: self.open_add_door())
        self.window.bind("<Control-f>", lambda event: self.focus_search())
        self.window.bind("<Control-q>", lambda event: self.quit_app())

    # -----------------------------------------------------------------------
    # Saving and the status bar
    # -----------------------------------------------------------------------

    # Show a short message in the status bar along the bottom of the window,
    # like "Added Stair 2 — saved at 3:42 PM".
    def set_status(self, message):
        self.status_label.config(text=message)

    # Save every project to projects.json, then say what was done in the
    # status bar. message describes the change, like "Added Stair 2".
    # Every change in the app saves through this one method, so the status
    # bar always shows the last save, and a failed save is always reported.
    def save_changes(self, message):
        # try/except: if the file can't be written (disk full, no
        # permission...), show a pop-up instead of crashing, and warn in the
        # status bar.
        try:
            storage.save_projects()
        except OSError as error:
            messagebox.showerror("Could not save", f"Your changes could not be saved:\n{error}",
                                 parent=self.window)
            self.set_status(f"NOT SAVED: {message}")
            return
        # strftime() turns a time into text. %I = hour (01-12), %M = minutes,
        # %p = AM or PM. lstrip("0") removes a leading zero:
        # "03:42 PM" -> "3:42 PM".
        time_text = datetime.now().strftime("%I:%M %p").lstrip("0")
        self.set_status(f"{message} — saved at {time_text}")

    # -----------------------------------------------------------------------
    # The table: filling it, sorting, searching, and the summary
    # -----------------------------------------------------------------------

    # Clear the table and fill it again from the current project's doors.
    # Call this whenever a door is added, edited, or removed, so the table
    # always matches the saved data.
    def refresh_tree(self):
        # Remember what's selected, so it can be selected again after the
        # redraw. Without this, sorting, searching or editing a door would
        # unselect it, because every row is deleted and made again.
        # selected_door / selected_device are names, or None.
        selected_door = None
        selected_device = None
        selection = self.tree.selection()
        if len(selection) > 0:
            row = selection[0]
            parent = self.tree.parent(row)
            if parent == "":
                # A door row.
                selected_door = self.tree.item(row, "text")
            else:
                # A device row: remember its door too.
                selected_door = self.tree.item(parent, "text")
                selected_device = self.tree.item(row, "text")

        # Remove every row currently in the table.
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Count the doors that pass the search and filter, for the "Showing"
        # message under the search box.
        shown = 0
        # sorted_doors() gives the doors in the order picked by clicking a
        # column heading (or the saved order, if no heading was clicked).
        for door in self.sorted_doors():
            # Skip doors that don't match what's typed in the search box or
            # picked in the Show dropdown. continue jumps to the next door.
            if not self.door_matches(door):
                continue
            shown += 1

            status = door.status()
            # The Devices column shows how many of the door's devices are
            # done, like "3 / 4". progress() gives back both numbers at once,
            # and "done, total = ..." puts them into two variables.
            done, total = door.progress()
            if total == 0:
                # No devices to count yet (or they're all N/a): show a dash
                # instead of a confusing "0 / 0".
                devices_text = "—"
            else:
                devices_text = f"{done} / {total}"

            # Add the door as a top-level row. "" means it has no parent row,
            # and "end" puts it at the bottom of the table.
            # values=(...) fills the extra columns, in the same order they
            # were made in build_table(): Devices, then Status. Status is
            # shown as a word, like "Complete", which is easier to read.
            # tags=(status, "door") gives the row two tags. The status LETTER
            # colors the text by its status, and "door" makes it bold with a
            # shaded background, so it stands out from its devices. (See
            # apply_theme() for both.) A device row only gets its status tag.
            # open=True shows the door's devices without clicking the arrow.
            door_row = self.tree.insert("", "end", text=door.name, values=(devices_text, STATUS_NAMES[status]),
                                        tags=(status, "door"), open=True)

            # Select this door again if it was selected before the redraw.
            if door.name == selected_door and selected_device is None:
                self.tree.selection_set(door_row)

            # Add each device as a row underneath its door (door_row is the
            # parent). A device row leaves the Devices column empty ("").
            for device_name, device_status in door.devices.items():
                device_row = self.tree.insert(door_row, "end", text=device_name,
                                              values=("", STATUS_NAMES[device_status]), tags=(device_status,))
                # Select this device again if it was selected before.
                if door.name == selected_door and device_name == selected_device:
                    self.tree.selection_set(device_row)

        # Tell the user when some doors are hidden, so an empty-looking table
        # isn't mistaken for missing doors. With no search or filter, blank.
        total = len(self.current_project.doors)
        if shown == total:
            self.filter_label.config(text="")
        else:
            self.filter_label.config(text=f"Showing {shown} of {total} doors")

        # Update the totals at the top. They always count the WHOLE project,
        # even when the search hides some doors.
        self.refresh_summary()

    # Give back the current project's doors in the order picked by clicking
    # a column heading. It makes a NEW sorted list; current_project.doors
    # itself is left alone, so the saved order never changes.
    def sorted_doors(self):
        if self.sort_column is None:
            return self.current_project.doors
        # sorted() needs to know WHAT to compare for each door. key=sort_key
        # hands it a function that turns a door into something comparable,
        # like its name or a number. reverse=True flips the order.
        return sorted(self.current_project.doors, key=self.sort_key, reverse=self.sort_reverse)

    # Turn a door into the value it's sorted by, for the column being
    # sorted. sorted() calls this once for each door.
    def sort_key(self, door):
        if self.sort_column == "#0":
            # .lower() so "alex door" goes between "Abbey" and "Bank", not
            # after every capitalized name.
            return door.name.lower()
        if self.sort_column == "devices":
            # Sort by how far along the door is, as a fraction: 3/4 = 0.75.
            # A door with nothing to count goes first, as -1.
            done, total = door.progress()
            if total == 0:
                return -1
            return done / total
        # Otherwise it's the Status column: restrained, pending, complete.
        return STATUS_SORT_ORDER[door.status()]

    # Runs when a column heading is clicked. Each click on the same heading
    # goes: A to Z -> Z to A -> back to unsorted. Clicking a different
    # heading starts that one at A to Z.
    def heading_clicked(self, column):
        if column != self.sort_column:
            self.sort_column = column
            self.sort_reverse = False
        elif not self.sort_reverse:
            self.sort_reverse = True
        else:
            self.sort_column = None
            self.sort_reverse = False
        self.refresh_headings()
        self.refresh_tree()

    # Put a small arrow on the sorted column's heading: ▲ for A to Z,
    # ▼ for Z to A. The other headings show just their title.
    def refresh_headings(self):
        # .items() gives each column's id and its title together.
        for column, title in COLUMN_TITLES.items():
            if column == self.sort_column and self.sort_reverse:
                self.tree.heading(column, text=f"{title}  ▼")
            elif column == self.sort_column:
                self.tree.heading(column, text=f"{title}  ▲")
            else:
                self.tree.heading(column, text=title)

    # Check one door against the search box and the Show dropdown.
    # Returns True if the door should be shown in the table, False to hide.
    def door_matches(self, door):
        # --- The Show dropdown ---
        # Look up the letter for the picked choice ("Pending" -> "P").
        wanted_status = FILTER_CHOICES[self.status_filter.get()]
        if wanted_status is not None and door.status() != wanted_status:
            return False

        # --- The search box ---
        # .lower() on both sides so "lobby" finds "Lobby".
        search = self.search_text.get().strip().lower()
        if search == "":
            return True
        # "in" checks if one piece of text is inside another:
        # "lob" in "main lobby" is True.
        if search in door.name.lower():
            return True
        # Also show the door if one of its devices matches, so searching
        # "restraint" finds every door that has a restraint.
        for device_name in door.devices:
            if search in device_name.lower():
                return True
        return False

    # Runs when the search text or the Show dropdown changes: redraw the
    # table. "*args" catches the extra details tkinter sends along (which
    # variable changed, and how). We don't need them, but have to accept them.
    def filter_changed(self, *args):
        self.refresh_tree()

    # Put the typing cursor in the search box. Runs for View > Find and
    # Ctrl+F.
    def focus_search(self):
        self.search_entry.focus_set()

    # Count the doors and devices, and show the totals in the summary.
    # Called at the end of refresh_tree(), so it updates automatically
    # whenever a door is added, edited, or removed.
    def refresh_summary(self):
        doors = self.current_project.doors
        # How many doors have each overall status. door.status() only ever
        # gives back C, P, or R, so those are the only keys needed.
        counts = {"C": 0, "P": 0, "R": 0}
        for door in doors:
            # += 1 adds one to the count for this door's status.
            counts[door.status()] += 1

        # Add up every door's devices. progress() already skips N devices.
        devices_total = 0
        devices_done = 0
        for door in doors:
            done, total = door.progress()
            devices_done += done
            devices_total += total

        # Work out the percent complete. Dividing by 0 crashes Python, so
        # check for "no devices yet" first. round() turns 77.8 into 78.
        if devices_total == 0:
            percent = 0
        else:
            percent = round(devices_done / devices_total * 100)

        # Fill the progress bar to the same percent. It was made with
        # maximum=100, so value=78 fills it 78% of the way.
        self.progress_bar.config(value=percent)

        # .config() changes a widget after it was created; here, its text.
        # "\n" puts the device totals on a second line.
        # Two f-strings next to each other inside the brackets are joined
        # into one, which is how a long line of text is split over lines.
        self.summary_label.config(text=f"{len(doors)} doors: {counts['C']} complete, "
                                       f"{counts['P']} pending, {counts['R']} restrained\n"
                                       f"Devices: {devices_done} of {devices_total} complete ({percent}%)")

    # Find the door that's selected (clicked) in the table.
    # If a device row is selected, use the door it belongs to.
    # Returns the Door object, or None if nothing is selected.
    def get_selected_door(self):
        # selection() gives the selected rows. It's empty if nothing is
        # clicked.
        selected = self.tree.selection()
        if len(selected) == 0:
            return None
        row = selected[0]

        # parent() gives the row this one sits under. Door rows have no
        # parent (""), so if there IS a parent, this is a device row: use
        # its door.
        if self.tree.parent(row) != "":
            row = self.tree.parent(row)

        # The row's text is the door name, so look the door up by name.
        return self.current_project.find_door(self.tree.item(row, "text"))

    # Runs on every single click in the table. If the click was on empty
    # space (below the last row), unselect everything, so no door is picked.
    # identify_region() says what part of the table is under the mouse:
    # "nothing" for empty space ("heading", "cell" and "tree" are the
    # headings and rows). Clicks on rows and headings are left alone, so
    # they still select a row or sort the table as normal.
    def table_clicked(self, event):
        if self.tree.identify_region(event.x, event.y) == "nothing":
            # selection_remove() unselects the rows it's given; selection()
            # is every selected row.
            self.tree.selection_remove(self.tree.selection())

    # Runs when a row in the table is double-clicked: open the Edit window
    # for it. "event" holds details about the click, like where the mouse
    # was (event.y).
    def row_double_clicked(self, event):
        # identify_row() gives the row under the mouse, or "" if the click
        # was on empty space below the last row.
        row = self.tree.identify_row(event.y)
        if row == "":
            return "break"
        # Select the clicked row, then open Edit for it like Edit Door does.
        self.tree.selection_set(row)
        self.open_edit_door()
        # "break" stops tkinter's normal double-click action, which would
        # also collapse or expand the door's device list.
        return "break"

    # -----------------------------------------------------------------------
    # Pop-up windows for doors
    # -----------------------------------------------------------------------

    # Opening a pop-up (Add Door, Edit Door, or a project window) takes two
    # steps, shared by all three:
    #   setup_popup(popup) - right after making it: hide it while its boxes
    #                        and buttons are added, and set it up.
    #   show_popup(popup)  - once everything is added: center it over the
    #                        main window and show it.
    # It's hidden in between because its size isn't known until everything
    # is in it, and the size is needed to center it.

    # Step 1: get a new pop-up ready, hidden.
    def setup_popup(self, popup):
        # withdraw() hides the window until show_popup() shows it again, so
        # it doesn't flash up in the wrong place first.
        popup.withdraw()
        # (No colors needed here: sv_ttk colors every window and list to
        # match light or dark mode by itself.)
        # transient(window) tells the desktop this window belongs to the
        # main window, so it always stays in front of it.
        popup.transient(self.window)
        # Add 10 pixels of empty space around the inside edge of the pop-up,
        # on top of each widget's own padx/pady, so nothing sits right
        # against the border. A tk.Toplevel can do this itself.
        popup.configure(padx=10, pady=10)
        # resizable(False, False) stops the window being stretched wider
        # (the first False) or taller (the second). These forms are laid out
        # to fit their contents, so stretching them only adds empty space.
        popup.resizable(False, False)
        # Pressing Escape closes the pop-up, the same as Cancel or Close.
        popup.bind("<Escape>", lambda event: popup.destroy())

    # Step 2: center the finished pop-up over the main window and show it.
    def show_popup(self, popup):
        # update_idletasks() makes tkinter work out the pop-up's size now
        # that everything is in it. winfo_reqwidth/reqheight are that size.
        popup.update_idletasks()
        popup_width = popup.winfo_reqwidth()
        popup_height = popup.winfo_reqheight()
        # The main window's position on screen (rootx/rooty = its top-left
        # corner) and its size.
        main_x = self.window.winfo_rootx()
        main_y = self.window.winfo_rooty()
        main_width = self.window.winfo_width()
        main_height = self.window.winfo_height()
        # Centered = the same amount of space on both sides. // divides and
        # drops the remainder, since pixels are whole numbers.
        x = main_x + (main_width - popup_width) // 2
        y = main_y + (main_height - popup_height) // 2
        # Never off the top or left edge of the screen. max() gives back the
        # bigger number, so a negative x or y becomes 0.
        x = max(x, 0)
        y = max(y, 0)
        # "+x+y" moves the window without changing its size.
        popup.geometry(f"+{x}+{y}")
        # deiconify() shows the window again (the opposite of withdraw()).
        popup.deiconify()
        # Wait until the window is actually on screen before grab_set().
        # A double-click opens the Edit window while the mouse is still busy
        # with the second click, so it appears a moment later than usual.
        # Without this wait, grab_set() fails with "grab failed: window not
        # viewable".
        popup.wait_visibility()
        # grab_set() stops clicks on the main window until this one closes.
        popup.grab_set()

    # Open the "Add Door" window. Runs for the Add Door button, Edit > Add
    # Door, and Ctrl+N.
    def open_add_door(self):
        # Toplevel = a second window that opens on top of the main one.
        add_window = tk.Toplevel(self.window)
        add_window.title("Add Door")
        # Hidden while it's built; stay in front, padding, Escape.
        self.setup_popup(add_window)

        # Build the door with no name yet. Devices get added to it as the
        # user clicks Add Device, and the name is filled in at Save Door.
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
        # sticky="we" stretches it from the left edge to the right edge.
        device_listbox = tk.Listbox(add_window, height=8)
        device_listbox.grid(row=3, column=0, columnspan=3, sticky="we", padx=10, pady=5)

        # Runs when Add Device is clicked.
        # This function is INSIDE open_add_door, so it can use device_entry,
        # status_box, new_door, and the other things created above. It can
        # also use self, because self belongs to open_add_door.
        def add_device():
            # .get() reads what's typed in the box. .strip() removes spaces.
            device_name = device_entry.get().strip()
            if device_name == "":
                messagebox.showerror("Missing device", "Type a device name first.", parent=add_window)
                # return leaves the function early, so nothing gets added.
                return
            # find_device ignores upper/lowercase, so "lock" matches "Lock".
            if new_door.find_device(device_name) is not None:
                messagebox.showerror("Duplicate device", f"{device_name} is already on this door.",
                                     parent=add_window)
                return

            device_status = status_box.get()
            new_door.devices[device_name] = device_status

            # Show the device in the list, then empty the box for the next.
            # .delete(0, "end") deletes from the first character to the last.
            device_listbox.insert("end", f"{device_name}   {STATUS_NAMES[device_status]}")
            device_entry.delete(0, "end")

        # --- Row 2: Add Device button ---
        # command=add_device means "run add_device when clicked". There's no
        # () after the name: we're handing over the function to run later.
        ttk.Button(add_window, text="Add Device", command=add_device).grid(row=2, column=2, padx=10, pady=5)

        # Runs when Save Door is clicked.
        def save_door():
            name = name_entry.get().strip()
            if name == "":
                messagebox.showerror("Missing name", "Door name cannot be blank.", parent=add_window)
                return
            # find_door ignores upper/lowercase: "joes door" = "Joes Door".
            if self.current_project.find_door(name) is not None:
                messagebox.showerror("Duplicate door", f"{name} already exists.", parent=add_window)
                return

            new_door.name = name
            self.current_project.doors.append(new_door)
            # Save to projects.json so the door is kept after the app closes.
            self.save_changes(f"Added {name}")
            # Redraw the main table so the new door shows up.
            self.refresh_tree()
            add_window.destroy()

        # --- Keyboard shortcuts ---
        # "<Return>" is the Enter key. Enter in the name box jumps to the
        # device box (focus_set() puts the typing cursor there). Enter in the
        # device box adds the device, so you can type a device, press Enter,
        # type the next...
        name_entry.bind("<Return>", lambda event: device_entry.focus_set())
        device_entry.bind("<Return>", lambda event: add_device())
        # Start with the typing cursor in the name box, ready to type.
        name_entry.focus_set()

        # --- Row 4: Save Door and Cancel buttons ---
        # sticky="e" lines Save Door up on the right (e = east), next to
        # Cancel. Save Door is the main action here, so it's blue (Accent).
        ttk.Button(add_window, text="Save Door", command=save_door,
                   style="Accent.TButton").grid(row=4, column=1, sticky="e", pady=10)
        # Cancel just closes the window. new_door was never added to the
        # project, so nothing is saved.
        ttk.Button(add_window, text="Cancel", command=add_window.destroy).grid(row=4, column=2, pady=10)

        # Everything's in place: center the window over the app and show it.
        self.show_popup(add_window)

    # Open the "Edit Door" window for the door selected in the table.
    # Runs for the Edit Door button, Edit > Edit Door, Enter, and a
    # double-click. In this window you can rename the door, change a
    # device's status, delete a device, or add a new one. Every change is
    # saved straight away, so there's no Save button, only Close.
    def open_edit_door(self):
        door = self.get_selected_door()
        if door is None:
            messagebox.showerror("No door selected", "Click a door in the list first.", parent=self.window)
            return

        edit_window = tk.Toplevel(self.window)
        edit_window.title(f"Edit Door - {door.name}")
        self.setup_popup(edit_window)

        # --- Row 0: door name + Rename button ---
        ttk.Label(edit_window, text="Door name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        name_entry = ttk.Entry(edit_window, width=25)
        # Put the current name in the box so the user can change it.
        # insert(0, ...) means "put this text at the start of the box".
        name_entry.insert(0, door.name)
        name_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # --- Row 1: list of this door's devices ---
        # exportselection=False keeps the clicked device selected while you
        # pick a status from the dropdown. Without it, tkinter only allows
        # one selection at a time, so picking from the dropdown would
        # unselect the device and Set Status would say "Click a device in
        # the list first."
        device_listbox = tk.Listbox(edit_window, height=8, exportselection=False)
        device_listbox.grid(row=1, column=0, columnspan=3, sticky="we", padx=10, pady=5)

        # A listbox only knows row numbers (0, 1, 2...), not device names.
        # This list keeps the device names in the same order as the listbox
        # rows, so listbox row 0 is device_names[0], and so on.
        device_names = []

        # Empty the listbox and fill it again from door.devices.
        # Runs when the window opens and after every change.
        def refresh_devices():
            device_listbox.delete(0, "end")
            device_names.clear()
            for device_name, device_status in door.devices.items():
                device_listbox.insert("end", f"{device_name}   {STATUS_NAMES[device_status]}")
                device_names.append(device_name)

        # Return the name of the device clicked in the listbox.
        # If no device is selected, show an error pop-up and return None.
        def get_selected_device():
            # curselection() gives the row numbers that are selected, like
            # (2,). It's empty if nothing is selected.
            selected = device_listbox.curselection()
            if len(selected) == 0:
                messagebox.showerror("No device selected", "Click a device in the list first.",
                                     parent=edit_window)
                return None
            return device_names[selected[0]]

        # Run after every change: save to projects.json, then redraw the
        # main table and this window's device list so both show the change.
        # message says what changed, for the status bar.
        def changes_made(message):
            self.save_changes(message)
            self.refresh_tree()
            refresh_devices()

        # Runs when Rename is clicked.
        def rename_door():
            new_name = name_entry.get().strip()
            if new_name == "":
                messagebox.showerror("Missing name", "Door name cannot be blank.", parent=edit_window)
                return
            # Block the name if a DIFFERENT door already uses it. "is not
            # door" still lets you fix the capitals on this door's own name,
            # like "lobby" to "Lobby".
            other_door = self.current_project.find_door(new_name)
            if other_door is not None and other_door is not door:
                messagebox.showerror("Duplicate door", f"{new_name} already exists.", parent=edit_window)
                return

            # Keep the old name for the status bar message.
            old_name = door.name
            door.name = new_name
            edit_window.title(f"Edit Door - {door.name}")
            changes_made(f"Renamed {old_name} to {new_name}")

        ttk.Button(edit_window, text="Rename", command=rename_door).grid(row=0, column=2, padx=10, pady=5)

        # --- Row 2: status dropdown + Set Status button (selected device) ---
        ttk.Label(edit_window, text="Status:").grid(row=2, column=0, sticky="w", padx=10)
        status_box = ttk.Combobox(edit_window, values=VALID_STATUSES, width=4, state="readonly")
        status_box.grid(row=2, column=1, sticky="w", padx=10)

        # Runs when Set Status is clicked: give the selected device the
        # status picked in the dropdown.
        def set_device_status():
            device_name = get_selected_device()
            if device_name is None:
                return
            new_status = status_box.get()
            door.devices[device_name] = new_status
            # .get(x, x) falls back to the letter if it isn't in STATUS_NAMES.
            changes_made(f"{door.name}: {device_name} set to {STATUS_NAMES.get(new_status, new_status)}")

        ttk.Button(edit_window, text="Set Status", command=set_device_status).grid(row=2, column=2, padx=10, pady=5)

        # When a device is clicked in the listbox, show its current status in
        # the dropdown, so the user can see it before changing it.
        # tkinter passes an "event" with details about the click. We don't
        # need them, but the function still has to accept it.
        def device_clicked(event):
            selected = device_listbox.curselection()
            if len(selected) > 0:
                status_box.set(door.devices[device_names[selected[0]]])

        # "<<ListboxSelect>>" is the event tkinter sends when a row in the
        # listbox is clicked.
        device_listbox.bind("<<ListboxSelect>>", device_clicked)

        # --- Row 3: Delete Device button ---
        # Asks first, since it can't be undone.
        def delete_device():
            device_name = get_selected_device()
            if device_name is None:
                return
            # askyesno shows Yes/No buttons and returns True for Yes.
            if messagebox.askyesno("Delete Device", f"Delete {device_name} from {door.name}?", parent=edit_window):
                # del removes this device and its status from the dictionary.
                del door.devices[device_name]
                changes_made(f"Deleted {device_name} from {door.name}")

        ttk.Button(edit_window, text="Delete Device", command=delete_device).grid(row=3, column=2, padx=10, pady=5)

        # --- Rows 4-5: add a new device ---
        # pady=(15, 5) adds 15 pixels of space above this row and 5 below,
        # to separate "add a new device" from the editing controls above.
        ttk.Label(edit_window, text="New device:").grid(row=4, column=0, sticky="w", padx=10, pady=(15, 5))
        new_device_entry = ttk.Entry(edit_window, width=20)
        new_device_entry.grid(row=4, column=1, sticky="w", padx=10, pady=(15, 5))
        # A second dropdown just for the new device, so it doesn't get mixed
        # up with the one used for Set Status.
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
                messagebox.showerror("Duplicate device", f"{device_name} is already on this door.",
                                     parent=edit_window)
                return
            door.devices[device_name] = new_status_box.get()
            # Empty the box, ready for the next device.
            new_device_entry.delete(0, "end")
            changes_made(f"Added {device_name} to {door.name}")

        ttk.Button(edit_window, text="Add Device", command=add_device).grid(row=5, column=2, padx=10, pady=5)

        # --- Row 6 (left side): Delete Door button ---
        # Deletes the whole door. If Yes is clicked, the door is gone, so
        # this window closes too. It's on the left, away from Close, so it's
        # harder to click by accident.
        def delete_this_door():
            if self.confirm_and_delete_door(door, edit_window):
                edit_window.destroy()

        ttk.Button(edit_window, text="Delete Door", command=delete_this_door).grid(row=6, column=0, sticky="w",
                                                                                   padx=10, pady=10)

        # --- Row 6 (right side): Close button ---
        # Changes are already saved, so Close just closes the window.
        ttk.Button(edit_window, text="Close", command=edit_window.destroy).grid(row=6, column=2, padx=10, pady=10)

        # --- Keyboard shortcuts ---
        # Enter in the name box renames the door; Enter in the new device box
        # adds the device. (Escape closes the window, set up in setup_popup.)
        name_entry.bind("<Return>", lambda event: rename_door())
        new_device_entry.bind("<Return>", lambda event: add_device())
        # Start with the typing cursor in the new device box, since adding
        # devices is the most common job in this window.
        new_device_entry.focus_set()

        # Fill the device list when the window first opens.
        refresh_devices()

        # Everything's in place: center the window over the app and show it.
        self.show_popup(edit_window)

    # Ask "are you sure?", then delete the door if Yes is clicked.
    # parent = the window the pop-up should appear on top of.
    # Returns True if the door was deleted, False if the user clicked No.
    # Used by the Delete Door button in the main window and the one in the
    # Edit window, so the confirm-and-delete steps are only written once.
    def confirm_and_delete_door(self, door, parent):
        # "\n" starts a new line inside the pop-up message.
        # icon="warning" shows a warning symbol instead of a question mark.
        if messagebox.askyesno("Delete Door", f"Delete {door.name} and all its devices?\nThis can't be undone.",
                               icon="warning", parent=parent):
            self.current_project.doors.remove(door)
            self.save_changes(f"Deleted {door.name}")
            self.refresh_tree()
            return True
        return False

    # Delete the door selected in the table. Runs for the main window's
    # Delete Door button, Edit > Delete Door, and the Delete key.
    def remove_selected_door(self):
        door = self.get_selected_door()
        if door is None:
            messagebox.showerror("No door selected", "Click a door in the list first.", parent=self.window)
            return
        self.confirm_and_delete_door(door, self.window)

    # -----------------------------------------------------------------------
    # Reports
    # -----------------------------------------------------------------------

    # Save a report of every door in the current project.
    # file_type is "txt" for a text file or "pdf" for a PDF.
    # Called by export_text() and export_pdf() below, so the "Save as" and
    # error handling steps are only written once for both formats.
    def export_report(self, file_type):
        # Start the suggested file name with the project's name, so reports
        # for different jobs don't get mixed up.
        name_start = safe_file_name(self.current_project.name)

        if file_type == "pdf":
            description = "PDF files"
        else:
            description = "Text files"

        # Open a "Save as" window. It gives back the chosen file path, or
        # nothing if the user clicks Cancel. date.today() puts today's date
        # in the suggested name, like Westfield_Mall_report_2026-11-23.txt
        file_path = filedialog.asksaveasfilename(parent=self.window, title="Save report as",
                                                 defaultextension=f".{file_type}",
                                                 filetypes=[(description, f"*.{file_type}")],
                                                 initialfile=f"{name_start}_report_{date.today()}.{file_type}")
        # "not file_path" is True when it's empty, meaning Cancel was clicked.
        if not file_path:
            return

        # try/except catches errors, like saving to a folder you're not
        # allowed to write in, and shows a pop-up instead of crashing.
        summary = self.summary_label.cget("text")
        try:
            if file_type == "pdf":
                report.make_pdf_report(self.current_project, file_path, summary)
            else:
                report.make_text_report(self.current_project, file_path, summary)
        except OSError as error:
            messagebox.showerror("Could not save", f"The report could not be saved:\n{error}", parent=self.window)
            return

        # showinfo is a pop-up with just an OK button.
        messagebox.showinfo("Report saved", f"Report saved to:\n{file_path}", parent=self.window)
        self.set_status(f"Report saved to {file_path}")

    # Runs for File > Export Text Report.
    # A menu item's command can't pass anything to the method it runs, so
    # these two small methods each call export_report() with the file type.
    def export_text(self):
        self.export_report("txt")

    # Runs for File > Export PDF Report.
    def export_pdf(self):
        self.export_report("pdf")

    # -----------------------------------------------------------------------
    # Projects
    # -----------------------------------------------------------------------

    # Fill the project dropdown with every project's name, and show the
    # current project as the one selected.
    def refresh_project_choices(self):
        names = []
        for project in storage.project_list:
            names.append(project.name)
        # values= is the list of choices in the dropdown.
        self.project_box.config(values=names)
        # .set() changes what the dropdown is showing.
        self.project_box.set(self.current_project.name)

    # Switch the whole window over to this project: the title, the dropdown,
    # the table, and the summary.
    def show_project(self, project):
        # (Before the class, this needed a "global current_project" line.
        # Now it's simply an attribute of self.)
        self.current_project = project
        self.window.title(f"{APP_NAME} - {project.name}")
        self.refresh_project_choices()
        # Clear the search and filter, so the new project starts with every
        # door showing. (Each .set() also redraws the table, through
        # filter_changed.)
        self.search_text.set("")
        self.status_filter.set("All doors")
        # refresh_tree() also updates the summary, so both show this project.
        self.refresh_tree()

    # Runs when a project is picked from the dropdown.
    # .current() gives the position of the picked choice: 0 for the first,
    # 1 for the second, and so on. The dropdown lists the projects in the
    # same order as project_list, so that position finds the right project.
    def project_chosen(self, event):
        position = self.project_box.current()
        if position >= 0:
            self.show_project(storage.project_list[position])

    # Open the project window, used for both New and Edit.
    #   project=None (the default) -> a New project: the boxes start empty.
    #   project=<a Project>        -> Edit that project: boxes start filled.
    # The form is the same either way, so one method handles both.
    def open_project_window(self, project=None):
        project_window = tk.Toplevel(self.window)
        if project is None:
            project_window.title("New Project")
        else:
            project_window.title(f"Edit Project - {project.name}")
        self.setup_popup(project_window)

        # The four boxes, one per row. Each row is a label on the left and a
        # box on the right. This list pairs each label with the Project
        # attribute it fills in, so the rows can be built with one loop.
        fields = [
            ("Project name:", "name"),
            ("Job number:", "job_number"),
            ("Address / site:", "address"),
            ("Customer / GC:", "customer"),
        ]
        # Remembers each box by its attribute name, so save_project() can
        # read them: entries["name"], entries["job_number"], and so on.
        entries = {}
        # enumerate() gives each item's position (0, 1, 2, 3) along with the
        # item, which is used as the row number.
        for row, (label_text, attribute) in enumerate(fields):
            ttk.Label(project_window, text=label_text).grid(row=row, column=0, sticky="w", padx=10, pady=5)
            entry = ttk.Entry(project_window, width=35)
            entry.grid(row=row, column=1, columnspan=2, sticky="w", padx=10, pady=5)
            # When editing, fill the box with the project's current value.
            # getattr(project, "job_number") is the same as
            # project.job_number; it's used because the name is in a variable.
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
            # project" still lets you fix the capitals on its own name.
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
            # opposite of getattr(): setattr(p, "address", "12 Main St") is
            # the same as p.address = "12 Main St".
            for attribute in ["job_number", "address", "customer"]:
                setattr(saved_project, attribute, entries[attribute].get().strip())

            if project is None:
                self.save_changes(f"Created project {name}")
            else:
                self.save_changes(f"Updated project {name}")
            # Switch to the new or edited project. This also updates the
            # title and the dropdown, so a new name shows up straight away.
            self.show_project(saved_project)
            project_window.destroy()

        # Enter in any of the four boxes saves, like clicking Save.
        for entry in entries.values():
            entry.bind("<Return>", lambda event: save_project())
        # Start with the typing cursor in the project name box.
        entries["name"].focus_set()

        # Save is the main action here, so it gets the blue Accent style.
        ttk.Button(project_window, text="Save", command=save_project,
                   style="Accent.TButton").grid(row=4, column=1, sticky="e", pady=10)
        ttk.Button(project_window, text="Cancel", command=project_window.destroy).grid(row=4, column=2,
                                                                                       padx=10, pady=10)

        # Everything's in place: center the window over the app and show it.
        self.show_popup(project_window)

    # Runs for the New button next to the dropdown, and File > New Project.
    def new_project(self):
        self.open_project_window()

    # Runs for the Edit button next to the dropdown, and Edit > Edit Project.
    def edit_project(self):
        self.open_project_window(self.current_project)

    # Runs for the Delete button next to the dropdown, and Edit > Delete
    # Project. Deletes the current project and all its doors, after asking.
    def delete_project(self):
        # Always keep at least one project, so there's somewhere to add doors.
        if len(storage.project_list) == 1:
            messagebox.showerror("Can't delete",
                                 "This is your only project. Make a new project first, then delete this one.",
                                 parent=self.window)
            return

        project = self.current_project
        if messagebox.askyesno("Delete project",
                               f"Delete the project {project.name} and all {len(project.doors)} of its doors?\n"
                               "This can't be undone.",
                               icon="warning", parent=self.window):
            storage.project_list.remove(project)
            self.save_changes(f"Deleted project {project.name}")
            # The current project is gone, so switch to the first one left.
            self.show_project(storage.project_list[0])

    # -----------------------------------------------------------------------
    # Theme, help, errors, and quitting
    # -----------------------------------------------------------------------

    # Switch the whole app to "light" or "dark" mode.
    def apply_theme(self, theme):
        # This also recolors every window and list (including pop-ups opened
        # later) as soon as tkinter gets to it, a moment after this method.
        sv_ttk.set_theme(theme)
        # Taller table rows, so the list is easier to read and tap on a touch
        # screen. set_theme() resets the table's style, so this comes after.
        ttk.Style().configure("Treeview", rowheight=28)
        # Each mode has its own status colors (see STATUS_COLORS at the top).
        for status, color in STATUS_COLORS[theme].items():
            self.tree.tag_configure(status, foreground=color)

        # Door rows: bold text on a shaded background, so each door reads
        # like a heading over its devices.
        # The bold font is a copy of the table's own font with weight="bold".
        # lookup() asks the theme which font the table uses (set_theme() can
        # change it, which is why this is done here, after set_theme()).
        table_font = ttk.Style().lookup("Treeview", "font") or "TkDefaultFont"
        # It's kept on self so it isn't thrown away while the table uses it.
        self.door_font = font.Font(font=table_font)
        self.door_font.configure(weight="bold")
        self.tree.tag_configure("door", font=self.door_font, background=DOOR_ROW_COLORS[theme])
        # Tick or untick "Dark Mode" in the View menu to match.
        self.dark_mode_on.set(theme == "dark")

    # Runs for View > Dark Mode: switch to the other mode, and remember it
    # for next time.
    def toggle_theme(self):
        if sv_ttk.get_theme() == "dark":
            new_theme = "light"
        else:
            new_theme = "dark"
        self.apply_theme(new_theme)
        storage.save_setting("theme", new_theme)

    # Runs for Help > About: a pop-up with the app's name, version, and
    # where the data is saved (handy when backing up or moving computers).
    def show_about(self):
        messagebox.showinfo(f"About {APP_NAME}",
                            f"{APP_NAME}  version {APP_VERSION}\n\n"
                            "Tracks the install progress of doors and their devices "
                            "on access control projects.\n\n"
                            f"Your projects are saved in:\n{storage.PROJECTS_FILE}",
                            parent=self.window)

    # Runs for Help > Keyboard Shortcuts: list every shortcut.
    def show_shortcuts(self):
        messagebox.showinfo("Keyboard Shortcuts",
                            "Ctrl+N\tAdd a door\n"
                            "Enter\tEdit the selected door\n"
                            "Delete\tDelete the selected door\n"
                            "Ctrl+F\tJump to the search box\n"
                            "Ctrl+Q\tQuit\n\n"
                            "In pop-up windows:\n"
                            "Enter\tAdd / save what you typed\n"
                            "Escape\tClose the window",
                            parent=self.window)

    # Show a pop-up for an error nobody planned for (a bug), instead of the
    # app silently doing nothing. tkinter calls this whenever a button's
    # function (or any other callback) crashes; see
    # report_callback_exception in __init__.
    # error_type, error, error_traceback describe the error. The full
    # details still go to the terminal, for tracking the bug down.
    def show_unexpected_error(self, error_type, error, error_traceback):
        traceback.print_exception(error_type, error, error_traceback)
        messagebox.showerror("Something went wrong",
                             f"An unexpected error happened:\n{error}\n\n"
                             "Your last saved changes are safe. If this keeps happening, "
                             "note what you clicked just before it.",
                             parent=self.window)

    # Runs when the app is closed: with the window's X button, File > Quit,
    # or Ctrl+Q. Remembers the window's size and position for next time,
    # then closes the window, which ends the app.
    def quit_app(self):
        # A setting that can't be saved isn't worth stopping the app closing
        # for, so any file error is ignored ("pass" means "do nothing").
        try:
            # geometry() with nothing passed in gives back the current size
            # and position, like "700x800+120+40".
            storage.save_setting("window_geometry", self.window.geometry())
        except OSError:
            pass
        self.window.destroy()


# ---------------------------------------------------------------------------
# Starting the app
# ---------------------------------------------------------------------------

# Load the projects, build the window, and wait for clicks.
def main():
    load_projects_or_stop()
    # TrackerApp() runs __init__, which builds the whole window.
    app = TrackerApp()
    # Start the GUI. This keeps the window open and waits for clicks.
    # Any code after this line only runs after the window is closed.
    app.window.mainloop()


# This runs main() only when this file is started directly (by the menu
# launcher, or "python trackerapp_gui.py"). When the tests import this file
# to check it, __name__ is "trackerapp_gui" instead of "__main__", so the
# app isn't started; the tests create a TrackerApp() themselves.
if __name__ == "__main__":
    main()
