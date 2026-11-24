# AUTOMATED TESTS FOR THE DOOR TRACKER APP
#
# Run all the tests from the ProgressApp folder with:
#   .venv/bin/python -m unittest -v test_tracker.py
#
# Each test prints "ok" if it passed, or FAIL / ERROR with details if not.
# Run this after every change to make sure nothing that used to work broke.
#
# The tests never touch your real projects.json or door_list.json. Before
# each test, the save files are pointed at a temporary folder that is deleted
# afterward.

# unittest is Python's built-in testing tool.
import unittest
# contextlib and io are used to hide messages printed during some tests.
import contextlib
import io
# tempfile makes temporary folders that are cleaned up automatically.
import tempfile
import json
# shutil and subprocess are used to run the pdftotext tool in one PDF test.
import shutil
import subprocess
# date is used to check the suggested report file names.
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from door import Door
from project import Project
import storage
import report
import install_launcher


# Each class below is a group of related tests.
# Each method whose name starts with "test_" is one test.
# self.assertEqual(a, b) means "the test fails unless a equals b".


# ---------------------------------------------------------------------------
# Door.status(): the overall door status worked out from its devices
# ---------------------------------------------------------------------------
class TestDoorStatus(unittest.TestCase):

    def test_no_devices_is_pending(self):
        self.assertEqual(Door("Test").status(), "P")

    def test_all_complete_is_complete(self):
        self.assertEqual(Door("Test", {"Lock": "C", "REX": "C"}).status(), "C")

    def test_na_devices_are_ignored(self):
        self.assertEqual(Door("Test", {"Lock": "C", "REX": "N"}).status(), "C")

    def test_only_na_is_complete(self):
        self.assertEqual(Door("Test", {"REX": "N"}).status(), "C")

    def test_progress_counts_complete_and_skips_na(self):
        door = Door("Test", {"Lock": "C", "REX": "P", "Sounder": "N", "Reader": "C"})
        self.assertEqual(door.progress(), (2, 3))

    def test_progress_with_no_devices(self):
        self.assertEqual(Door("Test").progress(), (0, 0))

    def test_any_pending_is_pending(self):
        self.assertEqual(Door("Test", {"Lock": "C", "REX": "P"}).status(), "P")

    def test_any_restrained_is_restrained(self):
        self.assertEqual(Door("Test", {"Lock": "C", "REX": "R"}).status(), "R")

    def test_restrained_wins_over_pending(self):
        self.assertEqual(Door("Test", {"Lock": "P", "REX": "R"}).status(), "R")

    def test_doors_do_not_share_devices(self):
        # Adding a device to one door must not add it to another door.
        door_a = Door("A")
        door_b = Door("B")
        door_a.devices["Lock"] = "C"
        self.assertEqual(door_b.devices, {})


# ---------------------------------------------------------------------------
# Door.find_device(): finding a device by name, ignoring upper/lowercase
# ---------------------------------------------------------------------------
class TestFindDevice(unittest.TestCase):

    def setUp(self):
        # setUp runs before EVERY test in this class.
        self.door = Door("Test", {"Card Reader": "C", "Lock": "P"})

    def test_exact_name(self):
        self.assertEqual(self.door.find_device("Lock"), "Lock")

    def test_ignores_case_and_spaces(self):
        # Returns the name the way it's saved, not the way it was typed.
        self.assertEqual(self.door.find_device("  card READER "), "Card Reader")

    def test_missing_device(self):
        # assertIsNone means "the test fails unless the result is None".
        self.assertIsNone(self.door.find_device("REX"))


# ---------------------------------------------------------------------------
# The Project class: a job's details and its doors
# ---------------------------------------------------------------------------
class TestProject(unittest.TestCase):

    def test_only_name_is_required(self):
        project = Project("Westfield Mall")
        self.assertEqual(project.name, "Westfield Mall")
        self.assertEqual(project.job_number, "")
        self.assertEqual(project.address, "")
        self.assertEqual(project.customer, "")
        self.assertEqual(project.doors, [])

    def test_projects_do_not_share_doors(self):
        # Adding a door to one project must not add it to another project.
        project_a = Project("A")
        project_b = Project("B")
        project_a.doors.append(Door("Main Entrance"))
        self.assertEqual(project_b.doors, [])

    def test_find_door_ignores_case_and_spaces(self):
        project = Project("Test", doors=[Door("Main Entrance"), Door("Loading Dock")])
        self.assertEqual(project.find_door("  main ENTRANCE ").name, "Main Entrance")
        self.assertIsNone(project.find_door("Roof Hatch"))

    def test_same_door_name_in_two_projects(self):
        # find_door only looks inside its own project.
        mall = Project("Mall", doors=[Door("Main Entrance", {"Lock": "C"})])
        hospital = Project("Hospital", doors=[Door("Main Entrance", {"Lock": "P"})])
        self.assertEqual(mall.find_door("Main Entrance").devices, {"Lock": "C"})
        self.assertEqual(hospital.find_door("Main Entrance").devices, {"Lock": "P"})

    def test_save_and_load_keeps_everything(self):
        project = Project("Westfield Mall", job_number="24-117", address="1200 Main St",
                          customer="Acme Builders",
                          doors=[Door("Main Entrance", {"Card Reader": "C", "Lock": "P"}),
                                 Door("Roof Hatch")])
        # Turn it into a dictionary and back, the way saving and loading will.
        copy = Project.from_dict(project.to_dict())

        self.assertEqual(copy.to_dict(), project.to_dict())
        self.assertEqual(copy.job_number, "24-117")
        self.assertEqual(copy.doors[0].devices, {"Card Reader": "C", "Lock": "P"})
        # The doors come back as real Door objects, so status() still works.
        self.assertEqual(copy.doors[0].status(), "P")

    def test_load_without_optional_details(self):
        # A saved project with only a name and doors still loads.
        copy = Project.from_dict({"name": "Old Job", "doors": []})
        self.assertEqual(copy.name, "Old Job")
        self.assertEqual(copy.job_number, "")
        self.assertEqual(copy.customer, "")


# ---------------------------------------------------------------------------
# A base class that points both save files (projects.json and the old
# door_list.json) at a temporary folder. Every test class that saves or loads
# uses this instead of unittest.TestCase, so your real files are never touched.
# ---------------------------------------------------------------------------
class UsesTempSaveFile(unittest.TestCase):

    def setUp(self):
        self.temp_folder = tempfile.TemporaryDirectory()
        folder = Path(self.temp_folder.name)
        # Remember the real paths so they can be put back afterward.
        self.real_projects_file = storage.PROJECTS_FILE
        self.real_old_doors_file = storage.OLD_DOORS_FILE
        self.real_settings_file = storage.SETTINGS_FILE
        storage.PROJECTS_FILE = folder / "projects.json"
        storage.OLD_DOORS_FILE = folder / "door_list.json"
        storage.SETTINGS_FILE = folder / "settings.json"
        # Start every test with no projects.
        storage.project_list.clear()

    def tearDown(self):
        # tearDown runs after EVERY test, even ones that fail.
        storage.PROJECTS_FILE = self.real_projects_file
        storage.OLD_DOORS_FILE = self.real_old_doors_file
        storage.SETTINGS_FILE = self.real_settings_file
        storage.project_list.clear()
        self.temp_folder.cleanup()

    # Helper: write some text straight into the temporary projects.json.
    def write_save_file(self, text):
        storage.PROJECTS_FILE.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# storage.py: saving and loading projects, and moving the old doors over.
# ---------------------------------------------------------------------------
class TestStorage(UsesTempSaveFile):

    # Helper: write an old-style door_list.json in the temporary folder.
    def write_old_doors(self, doors):
        storage.OLD_DOORS_FILE.write_text(json.dumps(doors), encoding="utf-8")

    def test_no_files_starts_empty(self):
        storage.load_projects()
        self.assertEqual(storage.project_list, [])
        # Nothing to move, so no projects.json is made.
        self.assertFalse(storage.PROJECTS_FILE.exists())

    def test_old_doors_move_into_first_project(self):
        old_doors = [{"name": "Joes Door", "devices": {"Lock": "C"}},
                     {"name": "142.1", "devices": {"Lock": "R"}}]
        self.write_old_doors(old_doors)
        storage.load_projects()

        self.assertEqual(len(storage.project_list), 1)
        project = storage.project_list[0]
        self.assertEqual(project.name, "My First Project")
        self.assertEqual([door.name for door in project.doors], ["Joes Door", "142.1"])
        self.assertEqual(project.doors[1].status(), "R")
        # projects.json was saved, and door_list.json was left alone as a backup.
        self.assertTrue(storage.PROJECTS_FILE.exists())
        self.assertEqual(json.loads(storage.OLD_DOORS_FILE.read_text(encoding="utf-8")), old_doors)

    def test_move_only_happens_once(self):
        self.write_old_doors([{"name": "Joes Door", "devices": {}}])
        storage.load_projects()
        # Rename the project and save, like a user would.
        storage.project_list[0].name = "Westfield Mall"
        storage.save_projects()

        # Start the app again: projects.json exists now, so the old doors must
        # NOT be moved a second time.
        storage.project_list.clear()
        storage.load_projects()
        self.assertEqual([p.name for p in storage.project_list], ["Westfield Mall"])

    def test_save_then_load_keeps_everything(self):
        storage.project_list.append(Project("Westfield Mall", job_number="24-117",
                                            address="1200 Main St", customer="Acme Builders",
                                            doors=[Door("Main Entrance", {"Lock": "P"})]))
        storage.project_list.append(Project("City Hospital", doors=[Door("Main Entrance")]))
        storage.save_projects()

        storage.project_list.clear()
        storage.load_projects()
        self.assertEqual([p.name for p in storage.project_list], ["Westfield Mall", "City Hospital"])
        self.assertEqual(storage.project_list[0].customer, "Acme Builders")
        self.assertEqual(storage.project_list[0].doors[0].devices, {"Lock": "P"})

    def test_find_project_ignores_case_and_spaces(self):
        storage.project_list.append(Project("Westfield Mall"))
        self.assertEqual(storage.find_project("  WESTFIELD mall ").name, "Westfield Mall")
        self.assertIsNone(storage.find_project("City Hospital"))

    def test_damaged_projects_file_raises_load_error_and_is_not_overwritten(self):
        broken_text = '[{"name": "Westfield Mall", "doors": ['
        storage.PROJECTS_FILE.write_text(broken_text, encoding="utf-8")
        with self.assertRaises(storage.LoadError):
            storage.load_projects()
        self.assertEqual(storage.PROJECTS_FILE.read_text(encoding="utf-8"), broken_text)

    def test_damaged_old_doors_file_raises_load_error(self):
        storage.OLD_DOORS_FILE.write_text('[{"name": "X"}]', encoding="utf-8")
        with self.assertRaises(storage.LoadError):
            storage.load_projects()
        # Nothing was moved, so no projects.json was made.
        self.assertFalse(storage.PROJECTS_FILE.exists())

    def test_projects_file_is_ignored_by_git(self):
        # The save file's name must match a line in .gitignore, so real job
        # data is never committed (a typo like "project.json" would break this).
        # Check the REAL file name, not the temporary one setUp swapped in.
        gitignore_lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(self.real_projects_file.name, gitignore_lines)


# ---------------------------------------------------------------------------
# A base class for the GUI tests.
# It builds the real window and lets tests "click" buttons with .invoke(),
# but never calls mainloop(), so nothing stays open on screen.
# It has no test_ methods of its own, so it doesn't run any tests itself.
# ---------------------------------------------------------------------------
class GuiTestBase(UsesTempSaveFile):

    # The doors in the save file when the GUI starts. A test class can
    # replace this with its own list.
    SAVED_DOORS = [{"name": "Joes Door", "devices": {"Lock": "P"}}]
    # The name of the project those doors are saved in.
    PROJECT_NAME = "Test Project"
    # A test class can set this to a list of whole projects instead, to start
    # with several projects (or [] for none at all).
    SAVED_PROJECTS = None
    # A test class can set this to start with saved settings, like
    # {"theme": "dark"}. None means no settings.json (the very first run).
    SAVED_SETTINGS = None

    def setUp(self):
        super().setUp()
        # Put the starting project(s) in the save file before the GUI loads it.
        projects = self.SAVED_PROJECTS
        if projects is None:
            projects = [{"name": self.PROJECT_NAME, "doors": self.SAVED_DOORS}]
        self.write_save_file(json.dumps(projects))
        if self.SAVED_SETTINGS is not None:
            storage.SETTINGS_FILE.write_text(json.dumps(self.SAVED_SETTINGS), encoding="utf-8")

        # Replace the pop-up error box with one that just records the message,
        # so the tests don't stop and wait for someone to click OK.
        self.errors = []
        self.real_showerror = messagebox.showerror
        messagebox.showerror = lambda title, message, **options: self.errors.append(message)

        # Replace the Yes/No pop-up with one that answers by itself.
        # A test sets self.answer_yes = False to "click No".
        self.answer_yes = True
        self.real_askyesno = messagebox.askyesno
        messagebox.askyesno = lambda title, message, **options: self.answer_yes

        # Run trackerapp_gui.py with mainloop() switched off, so it builds the
        # window and then returns instead of waiting for clicks.
        self.real_mainloop = tk.Tk.mainloop
        tk.Tk.mainloop = lambda self: None
        self.gui = {}
        try:
            with open("trackerapp_gui.py", encoding="utf-8") as file:
                exec(file.read(), self.gui)
        except tk.TclError:
            self.skipTest("No screen available to open a window.")

    def tearDown(self):
        if "window" in self.gui:
            self.gui["window"].destroy()
        tk.Tk.mainloop = self.real_mainloop
        messagebox.showerror = self.real_showerror
        messagebox.askyesno = self.real_askyesno
        super().tearDown()

    # Helper: list every row in the main table as (name, status, [devices]).
    # The table SHOWS words ("Complete"), but each row's tag keeps the
    # letter ("C"), so the tests can keep comparing short letters.
    def table_rows(self):
        tree = self.gui["tree"]
        rows = []
        for door_row in tree.get_children():
            devices = [tree.item(row, "text") + "=" + tree.item(row, "tags")[0]
                       for row in tree.get_children(door_row)]
            rows.append((tree.item(door_row, "text"), tree.item(door_row, "tags")[0], devices))
        return rows

    # Helper: read the save file back as a list of dictionaries.
    # It gives back the first project's list of doors, since that's the
    # project the GUI tests work on.
    def saved_file(self):
        return json.loads(storage.PROJECTS_FILE.read_text(encoding="utf-8"))[0]["doors"]

    # Helper: the doors of the project the GUI is showing.
    def doors(self):
        return self.gui["current_project"].doors

    # Helper: the newest Toplevel (pop-up) window that's open.
    def newest_window(self):
        window = self.gui["window"]
        return [w for w in window.winfo_children() if isinstance(w, tk.Toplevel)][-1]


# ---------------------------------------------------------------------------
# The GUI's main table and Add Door window
# ---------------------------------------------------------------------------
class TestGuiAddDoor(GuiTestBase):

    # Helper: open the Add Door window and find its boxes and buttons.
    def open_add_window(self):
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        widgets = add_window.winfo_children()
        # The two text boxes, in the order they were created: name, then device.
        name_entry, device_entry = [w for w in widgets if type(w) is ttk.Entry]
        status_box = [w for w in widgets if isinstance(w, ttk.Combobox)][0]
        buttons = {w.cget("text"): w for w in widgets if isinstance(w, ttk.Button)}
        return add_window, name_entry, device_entry, status_box, buttons

    # Helper: type a device name, pick its status, and click Add Device.
    def add_device(self, device_entry, status_box, buttons, name, status):
        device_entry.delete(0, "end")
        device_entry.insert(0, name)
        status_box.set(status)
        buttons["Add Device"].invoke()

    def test_table_shows_saved_doors(self):
        self.assertEqual(self.table_rows(), [("Joes Door", "P", ["Lock=P"])])

    def test_table_shows_status_as_words(self):
        tree = self.gui["tree"]
        door_row = tree.get_children()[0]
        device_row = tree.get_children(door_row)[0]
        # tree.set(row, "status") reads one column of one row.
        self.assertEqual(tree.set(door_row, "status"), "Pending")
        self.assertEqual(tree.set(device_row, "status"), "Pending")

    def test_devices_column_counts_complete_devices(self):
        tree = self.gui["tree"]
        door_row = tree.get_children()[0]
        device_row = tree.get_children(door_row)[0]
        # Joes Door has one device, Lock, which is pending.
        self.assertEqual(tree.set(door_row, "devices"), "0 / 1")
        # Device rows leave the Devices column empty.
        self.assertEqual(tree.set(device_row, "devices"), "")

    def test_devices_column_shows_dash_with_no_devices(self):
        self.doors().append(Door("Empty Door"))
        self.gui["refresh_tree"]()
        tree = self.gui["tree"]
        self.assertEqual(tree.set(tree.get_children()[1], "devices"), "—")

    def test_add_door_with_devices(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        self.add_device(device_entry, status_box, buttons, "Card Reader", "C")
        self.add_device(device_entry, status_box, buttons, "Lock", "R")
        name_entry.insert(0, "Stair 2")
        buttons["Save Door"].invoke()

        self.assertEqual(self.errors, [])
        # The new door shows in the table...
        self.assertIn(("Stair 2", "R", ["Card Reader=C", "Lock=R"]), self.table_rows())
        # ...is saved to the file...
        self.assertIn({"name": "Stair 2", "devices": {"Card Reader": "C", "Lock": "R"}}, self.saved_file())
        # ...and the Add Door window closed.
        self.assertFalse(add_window.winfo_exists())

    def test_duplicate_device_is_blocked(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        self.add_device(device_entry, status_box, buttons, "Card Reader", "C")
        self.add_device(device_entry, status_box, buttons, "card reader", "P")
        self.assertEqual(self.errors, ["card reader is already on this door."])

    def test_blank_device_is_blocked(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        self.add_device(device_entry, status_box, buttons, "   ", "C")
        self.assertEqual(self.errors, ["Type a device name first."])

    def test_blank_door_name_is_blocked(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        buttons["Save Door"].invoke()
        self.assertEqual(self.errors, ["Door name cannot be blank."])
        # Window stays open so the user can type a name.
        self.assertTrue(add_window.winfo_exists())

    def test_duplicate_door_name_is_blocked(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        name_entry.insert(0, "joes door")
        buttons["Save Door"].invoke()
        self.assertEqual(self.errors, ["joes door already exists."])
        self.assertEqual(len(self.doors()), 1)

    def test_cancel_saves_nothing(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        self.add_device(device_entry, status_box, buttons, "Lock", "C")
        name_entry.insert(0, "Stair 2")
        buttons["Cancel"].invoke()
        self.assertEqual(len(self.doors()), 1)
        self.assertFalse(add_window.winfo_exists())


# ---------------------------------------------------------------------------
# The GUI's Edit door window
# ---------------------------------------------------------------------------
class TestGuiEditDoor(GuiTestBase):

    # Start these tests with two doors.
    SAVED_DOORS = [
        {"name": "Joes Door", "devices": {"Card Reader": "C", "Lock": "P", "REX": "P"}},
        {"name": "alex door", "devices": {"Sounder": "R"}},
    ]

    # Helper: click a door's row in the main table.
    def select_door(self, name):
        tree = self.gui["tree"]
        for row in tree.get_children():
            if tree.item(row, "text") == name:
                tree.selection_set(row)
                return row

    # Helper: select a door, click Edit Door, and find the Edit window's
    # boxes and buttons. Returns them in a dictionary.
    def open_edit_window(self, door_name):
        self.select_door(door_name)
        self.gui["open_edit_door"]()
        edit_window = self.newest_window()
        widgets = edit_window.winfo_children()
        # Text boxes and dropdowns, in the order they were created.
        name_entry, new_device_entry = [w for w in widgets if type(w) is ttk.Entry]
        status_box, new_status_box = [w for w in widgets if isinstance(w, ttk.Combobox)]
        return {
            "window": edit_window,
            "name": name_entry,
            "new_device": new_device_entry,
            "status": status_box,
            "new_status": new_status_box,
            "devices": [w for w in widgets if isinstance(w, tk.Listbox)][0],
            "buttons": {w.cget("text"): w for w in widgets if isinstance(w, ttk.Button)},
        }

    # Helper: click a device in the Edit window's device list.
    def click_device(self, edit, device_name):
        listbox = edit["devices"]
        # Let the window finish appearing first. tkinter ignores click events
        # sent to a window that isn't on screen yet.
        edit["window"].update()
        for row_number in range(listbox.size()):
            if listbox.get(row_number).startswith(device_name + "   "):
                listbox.selection_clear(0, "end")
                listbox.selection_set(row_number)
                # Send the same event a real click sends, then let tkinter handle it.
                listbox.event_generate("<<ListboxSelect>>")
                edit["window"].update()
                return

    # Helper: the status of one door in the main table.
    def table_status(self, door_name):
        for name, status, devices in self.table_rows():
            if name == door_name:
                return status

    def test_nothing_selected_shows_error(self):
        self.gui["open_edit_door"]()
        self.assertEqual(self.errors, ["Click a door in the list first."])

    def test_device_row_opens_its_door(self):
        tree = self.gui["tree"]
        door_row = self.select_door("alex door")
        # Click the first device row under alex door instead of the door itself.
        tree.selection_set(tree.get_children(door_row)[0])
        self.gui["open_edit_door"]()
        self.assertEqual(self.newest_window().title(), "Edit Door - alex door")

    def test_clicking_device_shows_its_status(self):
        edit = self.open_edit_window("Joes Door")
        self.click_device(edit, "Card Reader")
        self.assertEqual(edit["status"].get(), "C")
        self.click_device(edit, "Lock")
        self.assertEqual(edit["status"].get(), "P")

    def test_set_status_updates_table_and_file(self):
        edit = self.open_edit_window("Joes Door")
        self.click_device(edit, "Lock")
        edit["status"].set("C")
        edit["buttons"]["Set Status"].invoke()
        self.click_device(edit, "REX")
        edit["status"].set("C")
        edit["buttons"]["Set Status"].invoke()

        self.assertEqual(self.errors, [])
        # All devices are C now, so the door turns C.
        self.assertEqual(self.table_status("Joes Door"), "C")
        self.assertEqual(self.saved_file()[0]["devices"], {"Card Reader": "C", "Lock": "C", "REX": "C"})

    def test_device_stays_selected_after_picking_from_dropdown(self):
        edit = self.open_edit_window("Joes Door")
        self.click_device(edit, "Lock")
        # Picking from the real dropdown also highlights its text. That used to
        # unselect the device in the list, so Set Status failed.
        edit["status"].set("C")
        edit["status"].selection_range(0, "end")
        edit["window"].update()
        edit["buttons"]["Set Status"].invoke()

        self.assertEqual(self.errors, [])
        self.assertEqual(self.doors()[0].devices["Lock"], "C")

    def test_set_status_with_no_device_selected(self):
        edit = self.open_edit_window("Joes Door")
        edit["status"].set("C")
        edit["buttons"]["Set Status"].invoke()
        self.assertEqual(self.errors, ["Click a device in the list first."])

    def test_add_device(self):
        edit = self.open_edit_window("Joes Door")
        edit["new_device"].insert(0, "Power Supply")
        edit["new_status"].set("N")
        edit["buttons"]["Add Device"].invoke()

        self.assertEqual(self.errors, [])
        self.assertIn("Power Supply=N", self.table_rows()[0][2])
        self.assertEqual(self.saved_file()[0]["devices"]["Power Supply"], "N")
        # The box is emptied, ready for the next device.
        self.assertEqual(edit["new_device"].get(), "")

    def test_add_duplicate_device_is_blocked(self):
        edit = self.open_edit_window("Joes Door")
        edit["new_device"].insert(0, "card reader")
        edit["buttons"]["Add Device"].invoke()
        self.assertEqual(self.errors, ["card reader is already on this door."])

    def test_add_blank_device_is_blocked(self):
        edit = self.open_edit_window("Joes Door")
        edit["buttons"]["Add Device"].invoke()
        self.assertEqual(self.errors, ["Type a name first."])

    def test_delete_device_yes(self):
        edit = self.open_edit_window("alex door")
        self.click_device(edit, "Sounder")
        edit["buttons"]["Delete Device"].invoke()
        self.assertEqual(self.saved_file()[1]["devices"], {})
        self.assertEqual(edit["devices"].size(), 0)

    def test_delete_device_no_keeps_it(self):
        self.answer_yes = False
        edit = self.open_edit_window("alex door")
        self.click_device(edit, "Sounder")
        edit["buttons"]["Delete Device"].invoke()
        self.assertEqual(self.doors()[1].devices, {"Sounder": "R"})

    def test_rename(self):
        edit = self.open_edit_window("Joes Door")
        edit["name"].delete(0, "end")
        edit["name"].insert(0, "Main Entrance")
        edit["buttons"]["Rename"].invoke()

        self.assertEqual(self.errors, [])
        self.assertEqual(self.table_rows()[0][0], "Main Entrance")
        self.assertEqual(self.saved_file()[0]["name"], "Main Entrance")
        self.assertEqual(edit["window"].title(), "Edit Door - Main Entrance")

    def test_rename_to_other_door_is_blocked(self):
        edit = self.open_edit_window("Joes Door")
        edit["name"].delete(0, "end")
        edit["name"].insert(0, "ALEX DOOR")
        edit["buttons"]["Rename"].invoke()
        self.assertEqual(self.errors, ["ALEX DOOR already exists."])
        self.assertEqual(self.doors()[0].name, "Joes Door")

    def test_rename_can_fix_own_capitals(self):
        edit = self.open_edit_window("Joes Door")
        edit["name"].delete(0, "end")
        edit["name"].insert(0, "JOES DOOR")
        edit["buttons"]["Rename"].invoke()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.doors()[0].name, "JOES DOOR")

    def test_rename_blank_is_blocked(self):
        edit = self.open_edit_window("Joes Door")
        edit["name"].delete(0, "end")
        edit["buttons"]["Rename"].invoke()
        self.assertEqual(self.errors, ["Door name cannot be blank."])

    def test_close(self):
        edit = self.open_edit_window("Joes Door")
        edit["buttons"]["Close"].invoke()
        self.assertFalse(edit["window"].winfo_exists())

    # Helper: double-click the table at height y, the way a real mouse does:
    # press and release the left button twice, quickly.
    def double_click_at(self, y):
        tree = self.gui["tree"]
        for click in range(2):
            tree.event_generate("<ButtonPress-1>", x=40, y=y)
            tree.event_generate("<ButtonRelease-1>", x=40, y=y)
        self.gui["window"].update()

    # Helper: double-click on a row in the table.
    def double_click_row(self, row):
        self.gui["window"].update()
        # bbox() gives the row's position on screen: x, y, width, height.
        x, y, width, height = self.gui["tree"].bbox(row)
        self.double_click_at(y + height // 2)

    # Helper: titles of the pop-up windows that are open.
    def open_window_titles(self):
        window = self.gui["window"]
        return [w.title() for w in window.winfo_children() if isinstance(w, tk.Toplevel)]

    def test_double_click_door_opens_edit(self):
        door_row = self.select_door("Joes Door")
        self.double_click_row(door_row)
        self.assertEqual(self.open_window_titles(), ["Edit Door - Joes Door"])
        # The door's device list must NOT collapse (that's what return "break" stops).
        self.assertTrue(self.gui["tree"].item(door_row, "open"))
        # The Edit window must be tied to the main window, so the desktop keeps
        # it in front instead of hiding it behind the main window.
        edit_window = self.newest_window()
        self.assertEqual(str(edit_window.transient()), str(self.gui["window"]))

    def test_double_click_device_opens_its_door(self):
        tree = self.gui["tree"]
        door_row = self.select_door("alex door")
        self.double_click_row(tree.get_children(door_row)[0])
        self.assertEqual(self.open_window_titles(), ["Edit Door - alex door"])

    def test_double_click_empty_space_does_nothing(self):
        self.gui["window"].update()
        # Far below the last row, where there's nothing to click.
        self.double_click_at(450)
        self.assertEqual(self.open_window_titles(), [])
        self.assertEqual(self.errors, [])

    def test_delete_door_button_no_keeps_it(self):
        self.answer_yes = False
        edit = self.open_edit_window("alex door")
        edit["buttons"]["Delete Door"].invoke()
        self.assertEqual(len(self.doors()), 2)
        # The Edit window stays open.
        self.assertTrue(edit["window"].winfo_exists())

    def test_delete_door_button_yes_deletes_and_closes(self):
        edit = self.open_edit_window("alex door")
        edit["buttons"]["Delete Door"].invoke()
        self.assertEqual([name for name, status, devices in self.table_rows()], ["Joes Door"])
        self.assertEqual(len(self.saved_file()), 1)
        # The door is gone, so the Edit window closes.
        self.assertFalse(edit["window"].winfo_exists())


# ---------------------------------------------------------------------------
# The GUI's Delete Door button (main window)
# ---------------------------------------------------------------------------
class TestGuiRemoveDoor(GuiTestBase):

    SAVED_DOORS = [
        {"name": "Joes Door", "devices": {"Lock": "P"}},
        {"name": "Delete Me", "devices": {"REX": "C"}},
    ]

    # Helper: click a door's row in the main table and return the row.
    def select_door(self, name):
        tree = self.gui["tree"]
        for row in tree.get_children():
            if tree.item(row, "text") == name:
                tree.selection_set(row)
                return row

    # Helper: the names of the doors in the main table.
    def table_names(self):
        return [name for name, status, devices in self.table_rows()]

    def test_nothing_selected_shows_error(self):
        self.gui["remove_selected_door"]()
        self.assertEqual(self.errors, ["Click a door in the list first."])
        self.assertEqual(len(self.doors()), 2)

    def test_no_keeps_the_door(self):
        self.answer_yes = False
        self.select_door("Delete Me")
        self.gui["remove_selected_door"]()
        self.assertEqual(self.table_names(), ["Joes Door", "Delete Me"])
        self.assertEqual(len(self.saved_file()), 2)

    def test_yes_removes_the_door(self):
        self.select_door("Delete Me")
        self.gui["remove_selected_door"]()
        # Gone from the table and the save file. The other door is untouched.
        self.assertEqual(self.table_names(), ["Joes Door"])
        self.assertEqual(self.saved_file(), [{"name": "Joes Door", "devices": {"Lock": "P"}}])

    def test_selecting_device_row_removes_its_door(self):
        tree = self.gui["tree"]
        door_row = self.select_door("Delete Me")
        # Click the device row under the door instead of the door itself.
        tree.selection_set(tree.get_children(door_row)[0])
        self.gui["remove_selected_door"]()
        self.assertEqual(self.table_names(), ["Joes Door"])


# ---------------------------------------------------------------------------
# The progress summary at the top of the window
# ---------------------------------------------------------------------------
class TestGuiSummary(GuiTestBase):

    SAVED_DOORS = [
        {"name": "Done Door", "devices": {"Lock": "C", "REX": "N"}},      # C
        {"name": "Busy Door", "devices": {"Lock": "C", "REX": "P"}},      # P
        {"name": "Stuck Door", "devices": {"Lock": "P", "Sounder": "R"}},  # R
        {"name": "Empty Door", "devices": {}},                            # P
    ]

    # Helper: the summary's text.
    def summary(self):
        return self.gui["summary_label"].cget("text")

    def test_counts_doors_and_devices(self):
        # 5 devices that aren't N, and 2 of them are C: 2 / 5 = 40%.
        self.assertEqual(self.summary(),
                         "4 doors: 1 complete, 2 pending, 1 restrained\n"
                         "Devices: 2 of 5 complete (40%)")

    def test_progress_bar_matches_percent(self):
        # float() because tkinter may hand the value back as text or a decimal.
        self.assertEqual(float(self.gui["progress_bar"].cget("value")), 40)

    def test_updates_after_a_change(self):
        # Change Busy Door's REX from P to C, then redraw like the app does.
        self.doors()[1].devices["REX"] = "C"
        self.gui["refresh_tree"]()
        self.assertEqual(float(self.gui["progress_bar"].cget("value")), 60)
        self.assertEqual(self.summary(),
                         "4 doors: 2 complete, 1 pending, 1 restrained\n"
                         "Devices: 3 of 5 complete (60%)")

    def test_updates_after_remove(self):
        tree = self.gui["tree"]
        tree.selection_set(tree.get_children()[2])   # Stuck Door
        self.gui["remove_selected_door"]()
        self.assertTrue(self.summary().startswith("3 doors: 1 complete, 2 pending, 0 restrained"))

    def test_no_doors_does_not_crash(self):
        # With no devices at all, the percent must not divide by zero.
        self.doors().clear()
        self.gui["refresh_tree"]()
        self.assertEqual(self.summary(),
                         "0 doors: 0 complete, 0 pending, 0 restrained\n"
                         "Devices: 0 of 0 complete (0%)")


# ---------------------------------------------------------------------------
# The Export menu (text file and PDF)
# ---------------------------------------------------------------------------
class TestGuiExport(GuiTestBase):

    SAVED_DOORS = [
        {"name": "Main Entrance", "devices": {"Card Reader": "C", "REX": "N"}},
        {"name": "Loading Dock", "devices": {"Restraint": "R"}},
        {"name": "Roof Hatch", "devices": {}},
    ]

    def setUp(self):
        super().setUp()
        # Replace the "Save as" window and the "Report saved" pop-up, so the
        # tests don't stop and wait for clicks. self.save_as_answer is the
        # path the fake "Save as" window gives back ("" means Cancel).
        # self.save_as_options remembers what the app asked the "Save as"
        # window to show, like the suggested file name.
        self.save_as_answer = ""
        self.save_as_options = {}
        self.real_asksaveasfilename = filedialog.asksaveasfilename

        def fake_save_as(**options):
            self.save_as_options = options
            return self.save_as_answer

        filedialog.asksaveasfilename = fake_save_as
        self.info_messages = []
        self.real_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda title, message, **options: self.info_messages.append(message)

    def tearDown(self):
        filedialog.asksaveasfilename = self.real_asksaveasfilename
        messagebox.showinfo = self.real_showinfo
        super().tearDown()

    def test_file_menu_has_both_formats(self):
        menu = self.gui["file_menu"]
        # index("end") is the number of the last item, so +1 is how many there are.
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                  if menu.type(i) == "command"]
        self.assertIn("Export Text Report...", labels)
        self.assertIn("Export PDF Report...", labels)

    def test_cancel_saves_nothing(self):
        self.gui["export_text"]()
        self.gui["export_pdf"]()
        self.assertEqual(self.info_messages, [])
        self.assertEqual(self.errors, [])

    def test_suggested_file_names(self):
        # The project is called "Test Project": the space becomes "_".
        self.gui["export_text"]()
        self.assertEqual(self.save_as_options["initialfile"], f"Test_Project_report_{date.today()}.txt")
        self.gui["export_pdf"]()
        self.assertEqual(self.save_as_options["initialfile"], f"Test_Project_report_{date.today()}.pdf")

    def test_safe_file_name(self):
        safe_file_name = self.gui["safe_file_name"]
        self.assertEqual(safe_file_name("Westfield Mall / Phase 2"), "Westfield_Mall___Phase_2")
        self.assertEqual(safe_file_name("Job-24_117"), "Job-24_117")

    def test_text_report_shows_project_name(self):
        lines = self.export_and_read()
        self.assertIn("Project:       Test Project", lines)

    # Helper: export to a file in the temporary folder and return its lines.
    def export_and_read(self):
        report_path = Path(self.temp_folder.name) / "report.txt"
        self.save_as_answer = str(report_path)
        self.gui["export_text"]()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.info_messages, [f"Report saved to:\n{report_path}"])
        # splitlines() splits the text into a list, one item per line.
        return report_path.read_text(encoding="utf-8").splitlines()

    def test_export_has_title_and_summary(self):
        lines = self.export_and_read()
        self.assertEqual(lines[0], "DOOR PROGRESS REPORT")
        self.assertTrue(lines[1].startswith("Created "))
        # The summary from the top of the window is copied in.
        self.assertIn("3 doors: 1 complete, 1 pending, 1 restrained", lines)
        self.assertIn("Devices: 1 of 2 complete (50%)", lines)

    def test_export_lists_every_door_and_device(self):
        lines = self.export_and_read()
        # Door lines: the name on the left, status in capitals at the right edge.
        self.assertIn("Main Entrance" + " " * 39 + "COMPLETE", lines)
        self.assertIn("Loading Dock" + " " * 38 + "RESTRAINED", lines)
        self.assertIn("Roof Hatch" + " " * 43 + "PENDING", lines)
        # Device lines: indented 4 spaces, status written out in full.
        self.assertIn("    Card Reader" + " " * 37 + "Complete", lines)
        self.assertIn("    REX" + " " * 50 + "N/a", lines)
        self.assertIn("    Restraint" + " " * 37 + "Restrained", lines)
        self.assertIn("    (no devices yet)", lines)

    def test_statuses_line_up(self):
        lines = self.export_and_read()
        # Every door and device line ends exactly at the right edge (60 characters).
        status_lines = [line for line in lines
                        if line.endswith(("COMPLETE", "PENDING", "RESTRAINED",
                                          "Complete", "Pending", "Restrained", "N/a"))]
        self.assertEqual(len(status_lines), 6)
        for line in status_lines:
            self.assertEqual(len(line), 60, line)

    def test_folder_that_does_not_exist_shows_error(self):
        self.save_as_answer = str(Path(self.temp_folder.name) / "no_such_folder" / "report.txt")
        self.gui["export_text"]()
        self.save_as_answer = str(Path(self.temp_folder.name) / "no_such_folder" / "report.pdf")
        self.gui["export_pdf"]()
        # One error for each format, and nothing saved.
        self.assertEqual(len(self.errors), 2)
        for error in self.errors:
            self.assertTrue(error.startswith("The report could not be saved"))
        self.assertEqual(self.info_messages, [])

    def test_export_pdf_makes_a_pdf(self):
        pdf_path = Path(self.temp_folder.name) / "report.pdf"
        self.save_as_answer = str(pdf_path)
        self.gui["export_pdf"]()

        self.assertEqual(self.errors, [])
        self.assertEqual(self.info_messages, [f"Report saved to:\n{pdf_path}"])
        # Every PDF file starts with the characters "%PDF".
        self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF"))

    def test_pdf_with_special_characters_in_details(self):
        # & and < have special meanings in PDF Paragraph text. Without escape()
        # in report.py, "<East>" silently disappears from the PDF.
        # pdftotext is a small tool that reads the text out of a PDF. If this
        # computer doesn't have it, the test is skipped instead of failing.
        if shutil.which("pdftotext") is None:
            self.skipTest("pdftotext isn't installed, so the PDF's text can't be read.")
        self.gui["current_project"].customer = "Smith & Sons <East>"
        pdf_path = Path(self.temp_folder.name) / "report.pdf"
        self.save_as_answer = str(pdf_path)
        self.gui["export_pdf"]()
        self.assertEqual(self.errors, [])

        # Run pdftotext and read its output. "-" means "print the text"
        # instead of saving it to a file.
        pdf_text = subprocess.run(["pdftotext", str(pdf_path), "-"],
                                  capture_output=True, text=True).stdout
        self.assertIn("Customer / GC: Smith & Sons <East>", pdf_text)
        self.assertIn("Project: Test Project", pdf_text)


# ---------------------------------------------------------------------------
# report.py on its own: the project details at the top of the reports
# ---------------------------------------------------------------------------
class TestReportProjectDetails(unittest.TestCase):

    def setUp(self):
        self.temp_folder = tempfile.TemporaryDirectory()
        self.report_path = Path(self.temp_folder.name) / "report.txt"

    def tearDown(self):
        self.temp_folder.cleanup()

    # Helper: make a text report for this project and return its lines.
    def text_report_lines(self, project):
        report.make_text_report(project, self.report_path, "1 doors: ...")
        return self.report_path.read_text(encoding="utf-8").splitlines()

    def test_all_details_are_shown_lined_up(self):
        project = Project("Westfield Mall", job_number="24-117", address="1200 Main St",
                          customer="Acme Builders", doors=[Door("Main Entrance")])
        lines = self.text_report_lines(project)
        # Right after the title, the "Created" line and a blank line.
        self.assertEqual(lines[3:7], ["Project:       Westfield Mall",
                                      "Job number:    24-117",
                                      "Address:       1200 Main St",
                                      "Customer / GC: Acme Builders"])

    def test_blank_details_are_skipped(self):
        lines = self.text_report_lines(Project("City Hospital", customer="Skyline GC"))
        self.assertIn("Project:       City Hospital", lines)
        self.assertIn("Customer / GC: Skyline GC", lines)
        self.assertFalse(any(line.startswith(("Job number:", "Address:")) for line in lines))

    def test_project_details_list(self):
        project = Project("Mall", job_number="", address="1 Main St")
        self.assertEqual(report.project_details(project), [("Project", "Mall"), ("Address", "1 Main St")])


# ---------------------------------------------------------------------------
# Several projects: the project dropdown at the top of the window
# ---------------------------------------------------------------------------
class TestGuiProjects(GuiTestBase):

    SAVED_PROJECTS = [
        {"name": "Westfield Mall", "job_number": "24-117",
         "doors": [{"name": "Main Entrance", "devices": {"Lock": "C"}},
                   {"name": "Loading Dock", "devices": {"REX": "R"}}]},
        {"name": "City Hospital",
         "doors": [{"name": "Main Entrance", "devices": {"Lock": "P"}}]},
    ]

    # Helper: pick a project in the dropdown, the way a user does.
    def pick_project(self, name):
        project_box = self.gui["project_box"]
        project_box.set(name)
        # Send the same event a real pick sends, then let tkinter handle it.
        project_box.event_generate("<<ComboboxSelected>>")
        self.gui["window"].update()

    def test_starts_on_first_project(self):
        self.assertEqual(self.gui["project_box"].get(), "Westfield Mall")
        self.assertEqual(self.gui["window"].title(), "TrackerApp - Westfield Mall")
        self.assertEqual([name for name, status, devices in self.table_rows()],
                         ["Main Entrance", "Loading Dock"])

    def test_dropdown_lists_every_project(self):
        self.assertEqual(list(self.gui["project_box"].cget("values")),
                         ["Westfield Mall", "City Hospital"])

    def test_picking_a_project_shows_its_doors_and_summary(self):
        self.gui["window"].update()
        self.pick_project("City Hospital")
        self.assertEqual(self.gui["current_project"].name, "City Hospital")
        self.assertEqual(self.gui["window"].title(), "TrackerApp - City Hospital")
        self.assertEqual(self.table_rows(), [("Main Entrance", "P", ["Lock=P"])])
        self.assertTrue(self.gui["summary_label"].cget("text").startswith("1 doors: 0 complete, 1 pending"))

    def test_new_door_only_goes_into_current_project(self):
        self.gui["window"].update()
        self.pick_project("City Hospital")
        # Add a door through the real Add Door window.
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        name_entry = [w for w in add_window.winfo_children() if type(w) is ttk.Entry][0]
        name_entry.insert(0, "Roof Hatch")
        buttons = {w.cget("text"): w for w in add_window.winfo_children() if isinstance(w, ttk.Button)}
        buttons["Save Door"].invoke()

        mall, hospital = storage.project_list
        self.assertEqual([d.name for d in hospital.doors], ["Main Entrance", "Roof Hatch"])
        self.assertEqual([d.name for d in mall.doors], ["Main Entrance", "Loading Dock"])
        # And it was saved inside the right project in projects.json.
        saved = json.loads(storage.PROJECTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual([d["name"] for d in saved[1]["doors"]], ["Main Entrance", "Roof Hatch"])

    def test_same_door_name_allowed_in_another_project(self):
        # Both projects already have a "Main Entrance". Editing one must not
        # change the other.
        mall, hospital = storage.project_list
        mall.find_door("Main Entrance").devices["Lock"] = "P"
        self.assertEqual(hospital.find_door("Main Entrance").devices, {"Lock": "P"})
        self.assertIsNot(mall.find_door("Main Entrance"), hospital.find_door("Main Entrance"))

    def test_project_details_are_kept_when_saving(self):
        # Saving after a change must not lose a project's job number.
        self.gui["refresh_tree"]()
        storage.save_projects()
        saved = json.loads(storage.PROJECTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["job_number"], "24-117")


# ---------------------------------------------------------------------------
# New / Edit / Delete project
# ---------------------------------------------------------------------------
class TestGuiProjectButtons(GuiTestBase):

    SAVED_PROJECTS = [
        {"name": "Westfield Mall", "job_number": "24-117", "address": "1200 Main St",
         "customer": "Acme Builders",
         "doors": [{"name": "Main Entrance", "devices": {"Lock": "C"}}]},
        {"name": "City Hospital", "doors": []},
    ]

    # Helper: open the project window (New or Edit) and find its boxes and
    # buttons. The four boxes come back in order: name, job number, address,
    # customer.
    def open_project_window(self, button_function):
        self.gui[button_function]()
        project_window = self.newest_window()
        widgets = project_window.winfo_children()
        entries = [w for w in widgets if type(w) is ttk.Entry]
        buttons = {w.cget("text"): w for w in widgets if isinstance(w, ttk.Button)}
        return project_window, entries, buttons

    # Helper: replace the text in a box.
    def type_into(self, entry, text):
        entry.delete(0, "end")
        entry.insert(0, text)

    def test_new_project(self):
        project_window, entries, buttons = self.open_project_window("new_project")
        # A new project's boxes start empty.
        self.assertEqual([e.get() for e in entries], ["", "", "", ""])
        self.type_into(entries[0], "Airport Terminal B")
        self.type_into(entries[1], "25-004")
        self.type_into(entries[3], "Skyline GC")
        buttons["Save"].invoke()

        self.assertEqual(self.errors, [])
        self.assertFalse(project_window.winfo_exists())
        # Added at the end, saved, and switched to.
        new = storage.project_list[-1]
        self.assertEqual((new.name, new.job_number, new.address, new.customer, new.doors),
                         ("Airport Terminal B", "25-004", "", "Skyline GC", []))
        self.assertIs(self.gui["current_project"], new)
        self.assertEqual(self.gui["project_box"].get(), "Airport Terminal B")
        self.assertEqual(self.table_rows(), [])
        saved = json.loads(storage.PROJECTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(saved[-1]["job_number"], "25-004")

    def test_new_project_blank_name_is_blocked(self):
        project_window, entries, buttons = self.open_project_window("new_project")
        buttons["Save"].invoke()
        self.assertEqual(self.errors, ["Project name cannot be blank."])
        self.assertEqual(len(storage.project_list), 2)
        self.assertTrue(project_window.winfo_exists())

    def test_new_project_duplicate_name_is_blocked(self):
        project_window, entries, buttons = self.open_project_window("new_project")
        self.type_into(entries[0], "city HOSPITAL")
        buttons["Save"].invoke()
        self.assertEqual(self.errors, ["city HOSPITAL already exists."])
        self.assertEqual(len(storage.project_list), 2)

    def test_new_project_cancel_adds_nothing(self):
        project_window, entries, buttons = self.open_project_window("new_project")
        self.type_into(entries[0], "Never Saved")
        buttons["Cancel"].invoke()
        self.assertEqual(len(storage.project_list), 2)
        self.assertFalse(project_window.winfo_exists())

    def test_edit_starts_filled_in(self):
        project_window, entries, buttons = self.open_project_window("edit_project")
        self.assertEqual([e.get() for e in entries],
                         ["Westfield Mall", "24-117", "1200 Main St", "Acme Builders"])
        self.assertEqual(project_window.title(), "Edit Project - Westfield Mall")

    def test_edit_project_details(self):
        project_window, entries, buttons = self.open_project_window("edit_project")
        self.type_into(entries[0], "Westfield Mall Phase 2")
        self.type_into(entries[2], "1300 Main St")
        buttons["Save"].invoke()

        self.assertEqual(self.errors, [])
        mall = storage.project_list[0]
        self.assertEqual((mall.name, mall.job_number, mall.address), ("Westfield Mall Phase 2", "24-117", "1300 Main St"))
        # The doors are still there, the title and dropdown show the new name.
        self.assertEqual([d.name for d in mall.doors], ["Main Entrance"])
        self.assertEqual(self.gui["window"].title(), "TrackerApp - Westfield Mall Phase 2")
        self.assertEqual(list(self.gui["project_box"].cget("values")), ["Westfield Mall Phase 2", "City Hospital"])

    def test_edit_to_another_projects_name_is_blocked(self):
        project_window, entries, buttons = self.open_project_window("edit_project")
        self.type_into(entries[0], "City Hospital")
        buttons["Save"].invoke()
        self.assertEqual(self.errors, ["City Hospital already exists."])
        self.assertEqual(storage.project_list[0].name, "Westfield Mall")

    def test_edit_can_fix_own_capitals(self):
        project_window, entries, buttons = self.open_project_window("edit_project")
        self.type_into(entries[0], "WESTFIELD MALL")
        buttons["Save"].invoke()
        self.assertEqual(self.errors, [])
        self.assertEqual(storage.project_list[0].name, "WESTFIELD MALL")

    def test_delete_project_no_keeps_it(self):
        self.answer_yes = False
        self.gui["delete_project"]()
        self.assertEqual(len(storage.project_list), 2)

    def test_delete_project_yes(self):
        self.gui["delete_project"]()
        self.assertEqual([p.name for p in storage.project_list], ["City Hospital"])
        # Switched to the project that's left, and saved.
        self.assertEqual(self.gui["project_box"].get(), "City Hospital")
        saved = json.loads(storage.PROJECTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual([p["name"] for p in saved], ["City Hospital"])

    def test_cannot_delete_only_project(self):
        self.gui["delete_project"]()      # deletes Westfield Mall
        self.gui["delete_project"]()      # City Hospital is the only one left
        self.assertEqual(len(self.errors), 1)
        self.assertTrue(self.errors[0].startswith("This is your only project."))
        self.assertEqual([p.name for p in storage.project_list], ["City Hospital"])


# ---------------------------------------------------------------------------
# Settings (settings.json) on their own
# ---------------------------------------------------------------------------
class TestSettings(UsesTempSaveFile):

    def test_missing_file_gives_default(self):
        self.assertEqual(storage.load_setting("theme", "light"), "light")

    def test_save_then_load(self):
        storage.save_setting("theme", "dark")
        self.assertEqual(storage.load_setting("theme", "light"), "dark")

    def test_saving_keeps_other_settings(self):
        storage.save_setting("theme", "dark")
        storage.save_setting("something_else", 5)
        self.assertEqual(json.loads(storage.SETTINGS_FILE.read_text(encoding="utf-8")),
                         {"theme": "dark", "something_else": 5})

    def test_damaged_file_gives_default_and_can_be_saved_over(self):
        # Unlike projects.json, a damaged settings file isn't worth stopping
        # the app for: it just goes back to the default.
        storage.SETTINGS_FILE.write_text("{not json", encoding="utf-8")
        self.assertEqual(storage.load_setting("theme", "light"), "light")
        storage.save_setting("theme", "dark")
        self.assertEqual(storage.load_setting("theme", "light"), "dark")

    def test_settings_file_is_ignored_by_git(self):
        gitignore_lines = Path(".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(self.real_settings_file.name, gitignore_lines)


# ---------------------------------------------------------------------------
# Light / dark mode
# ---------------------------------------------------------------------------
class TestGuiTheme(GuiTestBase):

    SAVED_DOORS = [{"name": "Joes Door", "devices": {"Lock": "C", "REX": "R"}}]

    # Helper: the text color the table uses for a status letter.
    # str() turns tkinter's color object into plain text like "#2e7d32".
    def tag_color(self, status):
        return str(self.gui["tree"].tag_configure(status, "foreground"))

    def test_first_run_is_light(self):
        self.assertEqual(self.gui["sv_ttk"].get_theme(), "light")
        self.assertFalse(self.gui["dark_mode_on"].get())
        self.assertEqual(self.tag_color("C"), "#2e7d32")

    def test_toggle_to_dark_and_back(self):
        self.gui["toggle_theme"]()
        self.assertEqual(self.gui["sv_ttk"].get_theme(), "dark")
        self.assertTrue(self.gui["dark_mode_on"].get())
        # Brighter status colors in dark mode.
        self.assertEqual(self.tag_color("C"), "#66bb6a")
        self.assertEqual(self.tag_color("R"), "#ef5350")
        # The choice is remembered.
        self.assertEqual(storage.load_setting("theme", "light"), "dark")

        self.gui["toggle_theme"]()
        self.assertEqual(self.gui["sv_ttk"].get_theme(), "light")
        self.assertEqual(self.tag_color("C"), "#2e7d32")
        self.assertEqual(storage.load_setting("theme", "light"), "light")

    def test_table_rows_stay_tall_after_toggle(self):
        # set_theme() resets the table style, so apply_theme() sets it again.
        self.gui["toggle_theme"]()
        self.assertEqual(str(ttk.Style().lookup("Treeview", "rowheight")), "28")


class TestGuiStartsDark(GuiTestBase):

    # The user picked dark mode last time.
    SAVED_SETTINGS = {"theme": "dark"}

    def test_starts_in_dark_mode(self):
        self.assertEqual(self.gui["sv_ttk"].get_theme(), "dark")
        self.assertTrue(self.gui["dark_mode_on"].get())

    def test_popup_and_device_list_are_dark(self):
        # The Edit door window: its background and its device list must be
        # dark too, not light gray / white. sv_ttk does this a moment after
        # set_theme(), so let tkinter catch up first with update().
        self.gui["window"].update()
        tree = self.gui["tree"]
        tree.selection_set(tree.get_children()[0])
        self.gui["open_edit_door"]()
        edit_window = self.newest_window()
        edit_window.update()
        self.assertEqual(edit_window.cget("background"), "#1c1c1c")
        listbox = [w for w in edit_window.winfo_children() if isinstance(w, tk.Listbox)][0]
        self.assertEqual(listbox.cget("background"), "#1c1c1c")
        self.assertEqual(listbox.cget("foreground"), "#fafafa")

    def test_switching_to_light_recolors_open_windows(self):
        self.gui["window"].update()
        self.gui["toggle_theme"]()
        self.gui["window"].update()
        self.assertEqual(self.gui["window"].cget("background"), "#fafafa")


class TestGuiNoProjects(GuiTestBase):

    # An empty projects.json: no projects at all.
    SAVED_PROJECTS = []

    def test_makes_an_empty_first_project(self):
        self.assertEqual([p.name for p in storage.project_list], ["My First Project"])
        self.assertEqual(self.gui["project_box"].get(), "My First Project")
        self.assertEqual(self.table_rows(), [])
        # It's saved straight away.
        saved = json.loads(storage.PROJECTS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["name"], "My First Project")


# ---------------------------------------------------------------------------
# The search box and "Show:" filter above the table
# ---------------------------------------------------------------------------
class TestGuiSearch(GuiTestBase):

    SAVED_DOORS = [
        {"name": "Main Lobby", "devices": {"Lock": "C", "REX": "C"}},         # C
        {"name": "Loading Dock", "devices": {"Restraint": "R"}},              # R
        {"name": "Stair 2", "devices": {"Card Reader": "P", "Lock": "C"}},    # P
    ]

    # Helper: the door names showing in the table, top to bottom.
    def shown(self):
        tree = self.gui["tree"]
        return [tree.item(row, "text") for row in tree.get_children()]

    def filter_text(self):
        return self.gui["filter_label"].cget("text")

    def test_everything_shows_at_start(self):
        self.assertEqual(self.shown(), ["Main Lobby", "Loading Dock", "Stair 2"])
        self.assertEqual(self.filter_text(), "")

    def test_search_by_door_name_ignores_case(self):
        self.gui["search_text"].set("LOBBY")
        self.assertEqual(self.shown(), ["Main Lobby"])
        self.assertEqual(self.filter_text(), "Showing 1 of 3 doors")

    def test_search_finds_doors_by_device(self):
        self.gui["search_text"].set("restraint")
        self.assertEqual(self.shown(), ["Loading Dock"])

    def test_show_dropdown_filters_by_status(self):
        self.gui["status_filter"].set("Pending")
        self.assertEqual(self.shown(), ["Stair 2"])

    def test_search_and_filter_together(self):
        # Two doors have a Lock, but only Main Lobby is complete.
        self.gui["search_text"].set("lock")
        self.gui["status_filter"].set("Complete")
        self.assertEqual(self.shown(), ["Main Lobby"])

    def test_no_matches_shows_zero(self):
        self.gui["search_text"].set("nothing like this")
        self.assertEqual(self.shown(), [])
        self.assertEqual(self.filter_text(), "Showing 0 of 3 doors")

    def test_summary_still_counts_whole_project(self):
        before = self.gui["summary_label"].cget("text")
        self.gui["search_text"].set("lobby")
        self.assertEqual(self.gui["summary_label"].cget("text"), before)

    def test_typing_in_search_box_filters(self):
        # Type into the real box, to check it's connected to search_text.
        self.gui["search_entry"].insert(0, "stair")
        self.assertEqual(self.shown(), ["Stair 2"])

    def test_escape_clears_search(self):
        entry = self.gui["search_entry"]
        entry.insert(0, "stair")
        entry.focus_force()
        entry.update()
        entry.event_generate("<Escape>")
        self.assertEqual(self.gui["search_text"].get(), "")
        self.assertEqual(len(self.shown()), 3)

    def test_switching_project_clears_search(self):
        self.gui["search_text"].set("lobby")
        self.gui["status_filter"].set("Complete")
        self.gui["show_project"](self.gui["current_project"])
        self.assertEqual(self.gui["search_text"].get(), "")
        self.assertEqual(self.gui["status_filter"].get(), "All doors")
        self.assertEqual(len(self.shown()), 3)


# ---------------------------------------------------------------------------
# Sorting by clicking a column heading
# ---------------------------------------------------------------------------
class TestGuiSort(GuiTestBase):

    SAVED_DOORS = [
        {"name": "stair 2", "devices": {"Lock": "C", "REX": "P"}},           # P, 1 / 2
        {"name": "Loading Dock", "devices": {"Restraint": "R"}},             # R, 0 / 1
        {"name": "Main Lobby", "devices": {"Lock": "C"}},                    # C, 1 / 1
        {"name": "Empty Door", "devices": {}},                               # P, —
    ]
    SAVED_ORDER = ["stair 2", "Loading Dock", "Main Lobby", "Empty Door"]

    def shown(self):
        tree = self.gui["tree"]
        return [tree.item(row, "text") for row in tree.get_children()]

    # Helper: click a column heading.
    def click(self, column):
        self.gui["heading_clicked"](column)

    def heading(self, column):
        return self.gui["tree"].heading(column, "text")

    def test_starts_in_saved_order(self):
        self.assertEqual(self.shown(), self.SAVED_ORDER)

    def test_sort_by_name_ignores_case(self):
        self.click("#0")
        self.assertEqual(self.shown(), ["Empty Door", "Loading Dock", "Main Lobby", "stair 2"])
        self.assertEqual(self.heading("#0"), "Door / Device  ▲")

    def test_second_click_reverses(self):
        self.click("#0")
        self.click("#0")
        self.assertEqual(self.shown(), ["stair 2", "Main Lobby", "Loading Dock", "Empty Door"])
        self.assertEqual(self.heading("#0"), "Door / Device  ▼")

    def test_third_click_goes_back_to_saved_order(self):
        for _ in range(3):
            self.click("#0")
        self.assertEqual(self.shown(), self.SAVED_ORDER)
        self.assertEqual(self.heading("#0"), "Door / Device")

    def test_sort_by_status_puts_problems_first(self):
        self.click("status")
        # Pending doors keep their saved order between themselves.
        self.assertEqual(self.shown(), ["Loading Dock", "stair 2", "Empty Door", "Main Lobby"])

    def test_sort_by_devices_done(self):
        self.click("devices")
        self.assertEqual(self.shown(), ["Empty Door", "Loading Dock", "stair 2", "Main Lobby"])

    def test_clicking_another_column_moves_the_arrow(self):
        self.click("#0")
        self.click("status")
        self.assertEqual(self.heading("#0"), "Door / Device")
        self.assertEqual(self.heading("status"), "Status  ▲")

    def test_sorting_does_not_change_saved_order(self):
        self.click("#0")
        names = [door.name for door in self.doors()]
        self.assertEqual(names, self.SAVED_ORDER)

    def test_heading_click_is_connected(self):
        # Run the heading's real command, to check the click is wired up.
        self.gui["tree"].tk.call(self.gui["tree"].heading("status", "command"))
        self.assertEqual(self.heading("status"), "Status  ▲")

    def test_sort_stays_after_adding_a_door(self):
        self.click("#0")
        self.doors().append(Door("Annex"))
        self.gui["refresh_tree"]()
        self.assertEqual(self.shown()[0], "Annex")


# ---------------------------------------------------------------------------
# The status bar along the bottom of the window
# ---------------------------------------------------------------------------
class TestGuiStatusBar(GuiTestBase):

    def status(self):
        return self.gui["status_label"].cget("text")

    def test_starts_as_ready(self):
        self.assertEqual(self.status(), "Ready")

    def test_save_changes_shows_message_and_time(self):
        self.gui["save_changes"]("Added Stair 2")
        # The time changes every minute, so only check the start, and that
        # it ends with AM or PM.
        self.assertTrue(self.status().startswith("Added Stair 2 — saved at "))
        self.assertTrue(self.status().endswith(("AM", "PM")))

    def test_deleting_a_door_updates_status(self):
        tree = self.gui["tree"]
        tree.selection_set(tree.get_children()[0])
        self.gui["remove_selected_door"]()
        self.assertTrue(self.status().startswith("Deleted Joes Door — saved at "))

    def test_failed_save_warns_instead_of_crashing(self):
        # Make saving fail, like a full disk would.
        def broken_save():
            raise OSError("disk full")
        real_save = storage.save_projects
        storage.save_projects = broken_save
        try:
            self.gui["save_changes"]("Added Stair 2")
        finally:
            storage.save_projects = real_save
        self.assertEqual(self.status(), "NOT SAVED: Added Stair 2")
        self.assertEqual(len(self.errors), 1)
        self.assertIn("disk full", self.errors[0])

    def test_edit_window_set_status_message(self):
        tree = self.gui["tree"]
        tree.selection_set(tree.get_children()[0])
        self.gui["open_edit_door"]()
        edit_window = self.newest_window()
        widgets = edit_window.winfo_children()
        listbox = [w for w in widgets if isinstance(w, tk.Listbox)][0]
        status_box = [w for w in widgets if isinstance(w, ttk.Combobox)][0]
        buttons = {w.cget("text"): w for w in widgets if isinstance(w, ttk.Button)}
        listbox.selection_set(0)
        status_box.set("C")
        buttons["Set Status"].invoke()
        self.assertTrue(self.status().startswith("Joes Door: Lock set to Complete — saved at "))


# ---------------------------------------------------------------------------
# The menu bar (File, Edit, View, Help) and the About box
# ---------------------------------------------------------------------------
class TestGuiMenuBar(GuiTestBase):

    def setUp(self):
        super().setUp()
        # Record showinfo pop-ups instead of waiting for someone to click OK.
        self.info = []
        self.real_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda title, message, **options: self.info.append((title, message))

    def tearDown(self):
        messagebox.showinfo = self.real_showinfo
        super().tearDown()

    # Helper: the labels in one menu, skipping the separator lines.
    def labels(self, menu):
        return [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                if menu.type(i) not in ("separator", "tearoff")]

    def test_menu_bar_has_four_menus(self):
        menu_bar = self.gui["menu_bar"]
        self.assertEqual(self.labels(menu_bar), ["File", "Edit", "View", "Help"])

    def test_edit_menu_items(self):
        self.assertEqual(self.labels(self.gui["edit_menu"]),
                         ["Add Door...", "Edit Door...", "Delete Door", "Edit Project...", "Delete Project"])

    def test_add_door_from_menu(self):
        self.gui["edit_menu"].invoke("Add Door...")
        self.assertEqual(self.newest_window().title(), "Add Door")

    def test_about_shows_version_and_save_file(self):
        self.gui["help_menu"].invoke(f"About {self.gui['APP_NAME']}")
        title, message = self.info[0]
        self.assertEqual(title, "About TrackerApp")
        self.assertIn("version " + self.gui["APP_VERSION"], message)
        self.assertIn(str(storage.PROJECTS_FILE), message)

    def test_keyboard_shortcuts_lists_ctrl_n(self):
        self.gui["help_menu"].invoke("Keyboard Shortcuts")
        title, message = self.info[0]
        self.assertEqual(title, "Keyboard Shortcuts")
        self.assertIn("Ctrl+N", message)

    def test_dark_mode_tick_follows_theme(self):
        self.assertFalse(self.gui["dark_mode_on"].get())
        self.gui["view_menu"].invoke("Dark Mode")
        self.assertTrue(self.gui["dark_mode_on"].get())
        self.assertEqual(self.gui["sv_ttk"].get_theme(), "dark")
        # Clicking it again switches back, and the tick follows.
        self.gui["view_menu"].invoke("Dark Mode")
        self.assertFalse(self.gui["dark_mode_on"].get())
        self.assertEqual(self.gui["sv_ttk"].get_theme(), "light")

    def test_window_title_uses_app_name(self):
        self.assertEqual(self.gui["window"].title(), "TrackerApp - Test Project")


# ---------------------------------------------------------------------------
# Remembering the window's size and position
# ---------------------------------------------------------------------------
class TestGuiWindowSize(GuiTestBase):

    # safe_geometry() is tested with a pretend 1920 x 1080 screen.
    def safe(self, geometry):
        return self.gui["safe_geometry"](geometry, 1920, 1080)

    def test_good_geometry_is_kept(self):
        self.assertEqual(self.safe("700x800+120+40"), "700x800+120+40")

    def test_too_big_is_shrunk_to_screen(self):
        self.assertEqual(self.safe("3000x2000+0+0"), "1920x1080+0+0")

    def test_off_screen_position_is_dropped(self):
        self.assertEqual(self.safe("700x800+2500+40"), "700x800")
        self.assertEqual(self.safe("700x800+-300+40"), "700x800")

    def test_damaged_setting_uses_default(self):
        for bad in ["", "hello", "700x800", "axb+1+2", 42, None]:
            self.assertEqual(self.safe(bad), "560x680")

    def test_quit_saves_geometry(self):
        window = self.gui["window"]
        window.update()
        expected = window.geometry()
        self.gui["quit_app"]()
        # The window is gone now, so tearDown mustn't destroy it again.
        del self.gui["window"]
        self.assertEqual(storage.load_setting("window_geometry", None), expected)

    def test_x_button_runs_quit_app(self):
        self.assertIn("quit_app", self.gui["window"].protocol("WM_DELETE_WINDOW"))


class TestGuiStartsAtSavedSize(GuiTestBase):

    SAVED_SETTINGS = {"window_geometry": "620x700+50+60"}

    def test_window_opens_at_saved_size(self):
        window = self.gui["window"]
        window.update()
        self.assertEqual(window.winfo_width(), 620)
        self.assertEqual(window.winfo_height(), 700)


# ---------------------------------------------------------------------------
# The app icon
# ---------------------------------------------------------------------------
class TestGuiIcon(GuiTestBase):

    def test_icon_file_exists(self):
        self.assertTrue(self.gui["ICON_FILE"].exists())

    def test_icon_is_loaded(self):
        icon = self.gui["app_icon"]
        self.assertEqual((icon.width(), icon.height()), (256, 256))

    def test_missing_icon_does_not_crash(self):
        # Start the app again with ICON_FILE pointing at a file that isn't
        # there. Swap the line that sets it before running the code.
        self.gui["window"].destroy()
        code = Path("trackerapp_gui.py").read_text(encoding="utf-8")
        code = code.replace('storage.FOLDER / "icon.png"', 'storage.FOLDER / "no_such_icon.png"')
        self.gui = {}
        exec(code, self.gui)
        self.assertNotIn("app_icon", self.gui)
        self.assertTrue(self.gui["window"].winfo_exists())


# ---------------------------------------------------------------------------
# Friendly error pop-ups: a damaged save file at startup, and unexpected bugs
# ---------------------------------------------------------------------------
class TestGuiErrors(GuiTestBase):

    # Helper: start the app again from the top, the way the test setup does.
    def restart_app(self):
        self.gui["window"].destroy()
        self.gui = {}
        exec(Path("trackerapp_gui.py").read_text(encoding="utf-8"), self.gui)

    def test_damaged_file_shows_pop_up_and_stops(self):
        broken_text = '[{"name": "Westfield Mall", "doors": ['
        storage.project_list.clear()
        storage.PROJECTS_FILE.write_text(broken_text, encoding="utf-8")
        # redirect_stdout hides the message the app also prints.
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.restart_app()
        self.assertEqual(len(self.errors), 1)
        self.assertIn("projects.json", self.errors[0])
        self.assertIn("Nothing has been changed", self.errors[0])
        # The damaged file was left exactly as it was.
        self.assertEqual(storage.PROJECTS_FILE.read_text(encoding="utf-8"), broken_text)

    def test_file_that_is_not_text_gives_load_error(self):
        storage.project_list.clear()
        storage.PROJECTS_FILE.write_bytes(b"\xff\xfe\x00 not text")
        with self.assertRaises(storage.LoadError):
            storage.load_projects()

    def test_crash_in_a_button_shows_pop_up(self):
        # A button whose function has a bug (dividing by zero).
        button = ttk.Button(self.gui["window"], command=lambda: 1 / 0)
        # redirect_stderr hides the error details printed to the terminal.
        with contextlib.redirect_stderr(io.StringIO()):
            button.invoke()
        self.assertEqual(len(self.errors), 1)
        self.assertIn("division by zero", self.errors[0])


# ---------------------------------------------------------------------------
# The apps-menu launcher (install_launcher.py)
# ---------------------------------------------------------------------------
class TestLauncher(unittest.TestCase):

    def entry_lines(self):
        text = install_launcher.make_desktop_entry("/home/me/My Apps/.venv/bin/python",
                                                   Path("/home/me/My Apps/ProgressApp"))
        return text.splitlines()

    def test_starts_the_gui_with_the_given_python(self):
        self.assertIn('Exec="/home/me/My Apps/.venv/bin/python" "/home/me/My Apps/ProgressApp/trackerapp_gui.py"',
                      self.entry_lines())

    def test_uses_the_app_icon_and_no_terminal(self):
        lines = self.entry_lines()
        self.assertIn("Icon=/home/me/My Apps/ProgressApp/icon.png", lines)
        self.assertIn("Terminal=false", lines)

    def test_window_class_matches_the_gui(self):
        # StartupWMClass must match className= in trackerapp_gui.py.
        gui_code = Path("trackerapp_gui.py").read_text(encoding="utf-8")
        self.assertIn('APP_NAME = "TrackerApp"', gui_code)
        self.assertIn("tk.Tk(className=APP_NAME)", gui_code)
        self.assertIn("StartupWMClass=TrackerApp", self.entry_lines())

    def test_entry_passes_the_desktop_file_checker(self):
        # desktop-file-validate is the official checker for .desktop files.
        if shutil.which("desktop-file-validate") is None:
            self.skipTest("desktop-file-validate isn't installed.")
        with tempfile.TemporaryDirectory() as folder:
            entry_file = Path(folder) / "trackerapp.desktop"
            entry_file.write_text("\n".join(self.entry_lines()) + "\n", encoding="utf-8")
            result = subprocess.run(["desktop-file-validate", str(entry_file)], capture_output=True, text=True)
        self.assertEqual(result.stdout + result.stderr, "")


# ---------------------------------------------------------------------------
# Keyboard shortcuts (Enter, Escape, Delete, Ctrl+N)
# ---------------------------------------------------------------------------
class TestGuiShortcuts(GuiTestBase):

    # Helper: press a key on a widget, the way a real key press would.
    # focus_force() gives the widget the keyboard, and update() lets tkinter
    # finish drawing first, or the key press can be ignored.
    def press(self, widget, key):
        widget.focus_force()
        widget.update()
        widget.event_generate(key)
        widget.update()

    # Helper: the text boxes in a pop-up, in the order they were created.
    def entries(self, popup):
        return [w for w in popup.winfo_children() if type(w) is ttk.Entry]

    # Helper: click Joes Door in the main table.
    def select_joes_door(self):
        tree = self.gui["tree"]
        tree.selection_set(tree.get_children()[0])
        return tree

    def test_popups_have_padding_and_fixed_size(self):
        # Check all three pop-ups: Add Door, Edit Door, and New Project.
        self.gui["open_add_door"]()
        self.select_joes_door()
        self.gui["open_edit_door"]()
        self.gui["new_project"]()
        window = self.gui["window"]
        popups = [w for w in window.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(popups), 3)
        for popup in popups:
            self.assertEqual(str(popup.cget("padx")), "10")
            self.assertEqual(str(popup.cget("pady")), "10")
            # resizable() with nothing passed in tells you the current setting.
            self.assertEqual(popup.resizable(), (False, False))

    def test_escape_closes_add_door_window(self):
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        self.press(add_window, "<Escape>")
        self.assertFalse(add_window.winfo_exists())
        self.assertEqual(len(self.doors()), 1)

    def test_add_door_window_starts_in_name_box(self):
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        add_window.update()
        name_entry = self.entries(add_window)[0]
        self.assertEqual(add_window.focus_get(), name_entry)

    def test_enter_in_device_box_adds_device(self):
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        name_entry, device_entry = self.entries(add_window)
        device_entry.insert(0, "Lock")
        self.press(device_entry, "<Return>")
        listbox = [w for w in add_window.winfo_children() if isinstance(w, tk.Listbox)][0]
        self.assertEqual(listbox.get(0, "end"), ("Lock   Pending",))
        # The device box is emptied, ready for the next device.
        self.assertEqual(device_entry.get(), "")

    def test_enter_in_edit_window_adds_device(self):
        self.select_joes_door()
        self.gui["open_edit_door"]()
        edit_window = self.newest_window()
        name_entry, new_device_entry = self.entries(edit_window)
        new_device_entry.insert(0, "REX")
        self.press(new_device_entry, "<Return>")
        self.assertEqual(self.doors()[0].devices, {"Lock": "P", "REX": "P"})

    def test_enter_in_project_window_saves(self):
        self.gui["new_project"]()
        project_window = self.newest_window()
        name_entry = self.entries(project_window)[0]
        name_entry.insert(0, "Westfield Mall")
        self.press(name_entry, "<Return>")
        self.assertFalse(project_window.winfo_exists())
        self.assertEqual(self.gui["current_project"].name, "Westfield Mall")

    def test_ctrl_n_opens_add_door_window(self):
        self.press(self.gui["tree"], "<Control-n>")
        self.assertEqual(self.newest_window().title(), "Add Door")

    def test_ctrl_f_jumps_to_search_box(self):
        self.press(self.gui["tree"], "<Control-f>")
        self.assertEqual(self.gui["window"].focus_get(), self.gui["search_entry"])

    def test_enter_on_table_opens_edit_window(self):
        tree = self.select_joes_door()
        self.press(tree, "<Return>")
        self.assertEqual(self.newest_window().title(), "Edit Door - Joes Door")

    def test_delete_key_deletes_selected_door(self):
        tree = self.select_joes_door()
        self.press(tree, "<Delete>")
        self.assertEqual(self.doors(), [])


# This lets you also run the file directly: .venv/bin/python test_tracker.py
if __name__ == "__main__":
    unittest.main()
