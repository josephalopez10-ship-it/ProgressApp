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
from tkinter import ttk, messagebox, filedialog

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
# A base class for the GUI tests.
# It builds the real window and lets tests "click" buttons with .invoke(),
# but never calls mainloop(), so nothing stays open on screen.
# It has no test_ methods of its own, so it doesn't run any tests itself.
# ---------------------------------------------------------------------------
class GuiTestBase(UsesTempSaveFile):

    # The doors in the save file when the GUI starts. A test class can
    # replace this with its own list.
    SAVED_DOORS = [{"name": "Joes Door", "devices": {"Lock": "P"}}]

    def setUp(self):
        super().setUp()
        # Put the starting doors in the save file before the GUI loads it.
        self.write_save_file(json.dumps(self.SAVED_DOORS))

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
    def saved_file(self):
        return json.loads(data.FILE_PATH.read_text(encoding="utf-8"))

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
        self.assertEqual(len(data.door_list), 1)

    def test_cancel_saves_nothing(self):
        add_window, name_entry, device_entry, status_box, buttons = self.open_add_window()
        self.add_device(device_entry, status_box, buttons, "Lock", "C")
        name_entry.insert(0, "Stair 2")
        buttons["Cancel"].invoke()
        self.assertEqual(len(data.door_list), 1)
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
        self.assertEqual(data.door_list[0].devices["Lock"], "C")

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
        self.assertEqual(data.door_list[1].devices, {"Sounder": "R"})

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
        self.assertEqual(data.door_list[0].name, "Joes Door")

    def test_rename_can_fix_own_capitals(self):
        edit = self.open_edit_window("Joes Door")
        edit["name"].delete(0, "end")
        edit["name"].insert(0, "JOES DOOR")
        edit["buttons"]["Rename"].invoke()
        self.assertEqual(self.errors, [])
        self.assertEqual(data.door_list[0].name, "JOES DOOR")

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
        self.assertEqual(len(data.door_list), 2)
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
        self.assertEqual(len(data.door_list), 2)

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
        data.door_list[1].devices["REX"] = "C"
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
        data.door_list.clear()
        self.gui["refresh_tree"]()
        self.assertEqual(self.summary(),
                         "0 doors: 0 complete, 0 pending, 0 restrained\n"
                         "Devices: 0 of 0 complete (0%)")


# ---------------------------------------------------------------------------
# The Export PDF button
# ---------------------------------------------------------------------------
class TestGuiExport(GuiTestBase):

    SAVED_DOORS = [
        {"name": "Main Entrance", "devices": {"Card Reader": "C", "REX": "N"}},
        {"name": "Loading Dock", "devices": {"Restraint": "R"}},
    ]

    def setUp(self):
        super().setUp()
        # Replace the "Save as" window and the "Report saved" pop-up, so the
        # tests don't stop and wait for clicks. self.save_as_answer is the
        # path the fake "Save as" window gives back ("" means Cancel).
        self.save_as_answer = ""
        self.real_asksaveasfilename = filedialog.asksaveasfilename
        filedialog.asksaveasfilename = lambda **options: self.save_as_answer
        self.info_messages = []
        self.real_showinfo = messagebox.showinfo
        messagebox.showinfo = lambda title, message, **options: self.info_messages.append(message)

    def tearDown(self):
        filedialog.asksaveasfilename = self.real_asksaveasfilename
        messagebox.showinfo = self.real_showinfo
        super().tearDown()

    def test_cancel_saves_nothing(self):
        self.gui["export_report"]()
        self.assertEqual(self.info_messages, [])
        self.assertEqual(self.errors, [])

    def test_export_makes_a_pdf(self):
        pdf_path = Path(self.temp_folder.name) / "report.pdf"
        self.save_as_answer = str(pdf_path)
        self.gui["export_report"]()

        self.assertEqual(self.errors, [])
        self.assertEqual(self.info_messages, [f"Report saved to:\n{pdf_path}"])
        # Every PDF file starts with the characters "%PDF".
        self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF"))

    def test_folder_that_does_not_exist_shows_error(self):
        self.save_as_answer = str(Path(self.temp_folder.name) / "no_such_folder" / "report.pdf")
        self.gui["export_report"]()
        self.assertEqual(len(self.errors), 1)
        self.assertTrue(self.errors[0].startswith("The report could not be saved"))
        self.assertEqual(self.info_messages, [])


# This lets you also run the file directly: .venv/bin/python test_tracker.py
if __name__ == "__main__":
    unittest.main()
