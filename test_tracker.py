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
# tempfile makes temporary folders that are cleaned up automatically.
import tempfile
import json
# date is used to check the suggested report file names.
from datetime import date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from door import Door
from project import Project
import storage


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
        storage.PROJECTS_FILE = folder / "projects.json"
        storage.OLD_DOORS_FILE = folder / "door_list.json"
        # Start every test with no projects.
        storage.project_list.clear()

    def tearDown(self):
        # tearDown runs after EVERY test, even ones that fail.
        storage.PROJECTS_FILE = self.real_projects_file
        storage.OLD_DOORS_FILE = self.real_old_doors_file
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

    def test_damaged_projects_file_stops_the_app_and_is_not_overwritten(self):
        broken_text = '[{"name": "Westfield Mall", "doors": ['
        storage.PROJECTS_FILE.write_text(broken_text, encoding="utf-8")
        with self.assertRaises(SystemExit):
            storage.load_projects()
        self.assertEqual(storage.PROJECTS_FILE.read_text(encoding="utf-8"), broken_text)

    def test_damaged_old_doors_file_stops_the_app(self):
        storage.OLD_DOORS_FILE.write_text('[{"name": "X"}]', encoding="utf-8")
        with self.assertRaises(SystemExit):
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

    def setUp(self):
        super().setUp()
        # Put the starting project(s) in the save file before the GUI loads it.
        projects = self.SAVED_PROJECTS
        if projects is None:
            projects = [{"name": self.PROJECT_NAME, "doors": self.SAVED_DOORS}]
        self.write_save_file(json.dumps(projects))

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
    def table_rows(self):
        tree = self.gui["tree"]
        rows = []
        for door_row in tree.get_children():
            devices = [tree.item(row, "text") + "=" + tree.item(row, "values")[0]
                       for row in tree.get_children(door_row)]
            rows.append((tree.item(door_row, "text"), tree.item(door_row, "values")[0], devices))
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
# The GUI's main table and Add door window
# ---------------------------------------------------------------------------
class TestGuiAddDoor(GuiTestBase):

    # Helper: open the Add door window and find its boxes and buttons.
    def open_add_window(self):
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        widgets = add_window.winfo_children()
        # The two text boxes, in the order they were created: name, then device.
        name_entry, device_entry = [w for w in widgets if type(w) is tk.Entry]
        status_box = [w for w in widgets if isinstance(w, ttk.Combobox)][0]
        buttons = {w.cget("text"): w for w in widgets if isinstance(w, tk.Button)}
        return add_window, name_entry, device_entry, status_box, buttons

    # Helper: type a device name, pick its status, and click Add Device.
    def add_device(self, device_entry, status_box, buttons, name, status):
        device_entry.delete(0, "end")
        device_entry.insert(0, name)
        status_box.set(status)
        buttons["Add Device"].invoke()

    def test_table_shows_saved_doors(self):
        self.assertEqual(self.table_rows(), [("Joes Door", "P", ["Lock=P"])])

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
        # ...and the Add door window closed.
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
        name_entry, new_device_entry = [w for w in widgets if type(w) is tk.Entry]
        status_box, new_status_box = [w for w in widgets if isinstance(w, ttk.Combobox)]
        return {
            "window": edit_window,
            "name": name_entry,
            "new_device": new_device_entry,
            "status": status_box,
            "new_status": new_status_box,
            "devices": [w for w in widgets if isinstance(w, tk.Listbox)][0],
            "buttons": {w.cget("text"): w for w in widgets if isinstance(w, tk.Button)},
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
        self.assertEqual(self.errors, ["Click a door in the list first"])

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
        edit["buttons"]["Add device"].invoke()

        self.assertEqual(self.errors, [])
        self.assertIn("Power Supply=N", self.table_rows()[0][2])
        self.assertEqual(self.saved_file()[0]["devices"]["Power Supply"], "N")
        # The box is emptied, ready for the next device.
        self.assertEqual(edit["new_device"].get(), "")

    def test_add_duplicate_device_is_blocked(self):
        edit = self.open_edit_window("Joes Door")
        edit["new_device"].insert(0, "card reader")
        edit["buttons"]["Add device"].invoke()
        self.assertEqual(self.errors, ["card reader is already on this door"])

    def test_add_blank_device_is_blocked(self):
        edit = self.open_edit_window("Joes Door")
        edit["buttons"]["Add device"].invoke()
        self.assertEqual(self.errors, ["Type a name first."])

    def test_delete_device_yes(self):
        edit = self.open_edit_window("alex door")
        self.click_device(edit, "Sounder")
        edit["buttons"]["Delete device"].invoke()
        self.assertEqual(self.saved_file()[1]["devices"], {})
        self.assertEqual(edit["devices"].size(), 0)

    def test_delete_device_no_keeps_it(self):
        self.answer_yes = False
        edit = self.open_edit_window("alex door")
        self.click_device(edit, "Sounder")
        edit["buttons"]["Delete device"].invoke()
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
# The GUI's Remove Door button
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
        self.assertEqual(self.errors, ["Click a door in the list first"])
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

    def test_updates_after_a_change(self):
        # Change Busy Door's REX from P to C, then redraw like the app does.
        self.doors()[1].devices["REX"] = "C"
        self.gui["refresh_tree"]()
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

    def test_menu_has_both_formats(self):
        menu = self.gui["export_menu"]
        # index("end") is the number of the last item, so +1 is how many there are.
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]
        self.assertEqual(labels, ["Text file (.txt)", "PDF (.pdf)"])

    def test_cancel_saves_nothing(self):
        self.gui["export_text"]()
        self.gui["export_pdf"]()
        self.assertEqual(self.info_messages, [])
        self.assertEqual(self.errors, [])

    def test_suggested_file_names(self):
        self.gui["export_text"]()
        self.assertEqual(self.save_as_options["initialfile"], f"door_report_{date.today()}.txt")
        self.gui["export_pdf"]()
        self.assertEqual(self.save_as_options["initialfile"], f"door_report_{date.today()}.pdf")

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
        # Add a door through the real Add door window.
        self.gui["open_add_door"]()
        add_window = self.newest_window()
        name_entry = [w for w in add_window.winfo_children() if type(w) is tk.Entry][0]
        name_entry.insert(0, "Roof Hatch")
        buttons = {w.cget("text"): w for w in add_window.winfo_children() if isinstance(w, tk.Button)}
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
        entries = [w for w in widgets if type(w) is tk.Entry]
        buttons = {w.cget("text"): w for w in widgets if isinstance(w, tk.Button)}
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
        self.assertEqual(project_window.title(), "Edit project - Westfield Mall")

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


# This lets you also run the file directly: .venv/bin/python test_tracker.py
if __name__ == "__main__":
    unittest.main()
