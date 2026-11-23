# AUTOMATED TESTS FOR THE DOOR TRACKER APP
#
# Run all the tests from the ProgressApp folder with:
#   .venv/bin/python -m unittest -v test_tracker.py
#
# Each test prints "ok" if it passed, or FAIL / ERROR with details if not.
# Run this after every change to make sure nothing that used to work broke.
#
# The tests never touch your real door_list.json. Before each test, the save
# file is pointed at a temporary folder that is deleted afterward.

# unittest is Python's built-in testing tool.
import unittest
# tempfile makes temporary folders that are cleaned up automatically.
import tempfile
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from door import Door
import trackerapp_2 as data


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
# A base class that points the save file at a temporary folder.
# Every test class that saves or loads doors uses this instead of
# unittest.TestCase, so the real door_list.json is never touched.
# ---------------------------------------------------------------------------
class UsesTempSaveFile(unittest.TestCase):

    def setUp(self):
        self.temp_folder = tempfile.TemporaryDirectory()
        # Remember the real file path so it can be put back afterward.
        self.real_file_path = data.FILE_PATH
        data.FILE_PATH = Path(self.temp_folder.name) / "door_list.json"
        # Start every test with an empty door list.
        data.door_list.clear()

    def tearDown(self):
        # tearDown runs after EVERY test, even ones that fail.
        data.FILE_PATH = self.real_file_path
        data.door_list.clear()
        self.temp_folder.cleanup()

    # Helper: write some text straight into the temporary save file.
    def write_save_file(self, text):
        data.FILE_PATH.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# find_door(): finding a door by name, ignoring upper/lowercase
# ---------------------------------------------------------------------------
class TestFindDoor(UsesTempSaveFile):

    def setUp(self):
        # super().setUp() runs the setUp from UsesTempSaveFile first.
        super().setUp()
        data.door_list.append(Door("Main Entrance"))

    def test_exact_name(self):
        self.assertEqual(data.find_door("Main Entrance").name, "Main Entrance")

    def test_ignores_case_and_spaces(self):
        self.assertEqual(data.find_door("  main ENTRANCE ").name, "Main Entrance")

    def test_missing_door(self):
        self.assertIsNone(data.find_door("Server Room"))


# ---------------------------------------------------------------------------
# save_doors() and load_doors(): the JSON save file
# ---------------------------------------------------------------------------
class TestSaveAndLoad(UsesTempSaveFile):

    def test_no_save_file_starts_empty(self):
        data.load_doors()
        self.assertEqual(data.door_list, [])

    def test_save_then_load_keeps_everything(self):
        data.door_list.append(Door("Main Entrance", {"Card Reader": "C", "Lock": "P"}))
        # A comma in the name used to break the old text file.
        data.door_list.append(Door("Bldg A, Door 101", {"REX": "R"}))
        data.save_doors()

        # Empty the list, then load it back from the file.
        data.door_list.clear()
        data.load_doors()

        self.assertEqual(len(data.door_list), 2)
        self.assertEqual(data.door_list[0].name, "Main Entrance")
        self.assertEqual(data.door_list[0].devices, {"Card Reader": "C", "Lock": "P"})
        self.assertEqual(data.door_list[1].name, "Bldg A, Door 101")
        self.assertEqual(data.door_list[1].status(), "R")

    def test_damaged_file_stops_the_app_and_is_not_overwritten(self):
        broken_text = '[{"name": "X", "devices": {'
        self.write_save_file(broken_text)
        # assertRaises(SystemExit) means "the test fails unless the app
        # tries to close itself" (that's what sys.exit does).
        with self.assertRaises(SystemExit):
            data.load_doors()
        # The damaged file must still be there, unchanged, so it can be fixed.
        self.assertEqual(data.FILE_PATH.read_text(encoding="utf-8"), broken_text)

    def test_door_missing_devices_stops_the_app(self):
        self.write_save_file('[{"name": "X"}]')
        with self.assertRaises(SystemExit):
            data.load_doors()


# ---------------------------------------------------------------------------
# The GUI's Add door window
# These tests build the real window and "click" its buttons with .invoke(),
# but never call mainloop(), so nothing stays open on screen.
# ---------------------------------------------------------------------------
class TestGuiAddDoor(UsesTempSaveFile):

    def setUp(self):
        super().setUp()
        # Put one door in the save file before the GUI loads it.
        self.write_save_file(json.dumps([{"name": "Joes Door", "devices": {"Lock": "P"}}]))

        # Replace the pop-up error box with one that just records the message,
        # so the tests don't stop and wait for someone to click OK.
        self.errors = []
        self.real_showerror = messagebox.showerror
        messagebox.showerror = lambda title, message, **options: self.errors.append(message)

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
        super().tearDown()

    # Helper: open the Add door window and find its boxes and buttons.
    def open_add_window(self):
        self.gui["open_add_door"]()
        window = self.gui["window"]
        # The newest Toplevel window is the Add door window.
        add_window = [w for w in window.winfo_children() if isinstance(w, tk.Toplevel)][-1]
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

    # Helper: list every row in the main table as (name, status, [devices]).
    def table_rows(self):
        tree = self.gui["tree"]
        rows = []
        for door_row in tree.get_children():
            devices = [tree.item(row, "text") + "=" + tree.item(row, "values")[0]
                       for row in tree.get_children(door_row)]
            rows.append((tree.item(door_row, "text"), tree.item(door_row, "values")[0], devices))
        return rows

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
        saved = json.loads(data.FILE_PATH.read_text(encoding="utf-8"))
        self.assertIn({"name": "Stair 2", "devices": {"Card Reader": "C", "Lock": "R"}}, saved)
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
        self.assertEqual(len(data.door_list), 1)

    def test_cancel_saves_nothing(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        self.add_device(device_entry, status_box, buttons, "Lock", "C")
        name_entry.insert(0, "Stair 2")
        buttons["Cancel"].invoke()
        self.assertEqual(len(data.door_list), 1)
        self.assertFalse(add_window.winfo_exists())


# This lets you also run the file directly: .venv/bin/python test_tracker.py
if __name__ == "__main__":
    unittest.main()
