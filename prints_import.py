# PRINTS IMPORT
# Reads a set of security drawings (a PDF) and builds the doors and devices
# for a new project, so they don't have to be typed in by hand.
#
# Where the information comes from:
#   1. The riser schedules (sheets like "SECURITY RISER SCHEDULES - ACCESS
#      CONTROL" and "... - ALARM"). Every row is one device:
#        SYSTEM | BLDG | LOC | ... | DOOR # | DEVICE TYPE | DOOR TYPE | DEVICE ID | ...
#        ACCESS CONTROL | PHX53 | SER1 | ... | 162.1.2 | CARD READER | CFD16X | 050 | ...
#   2. The DOOR TYPE code in each row (like CFD16X), decoded with the legend
#      on the symbols sheet into the door's hardware (lock, REX, door
#      contact, emergency release...), which the schedules don't list.
#
# Only physical devices are kept (no software alarm points like "ATG
# Tailgating Alarm"), and plain mechanical locks are left out, since there's
# nothing for the security installer to wire. Every device starts as P.
#
# Devices from the schedules get their label in their name, the same label
# that's printed next to the device on the floor plans: building, door type
# and device ID, like "Card Reader (PHX53-CCD15B-071)". Devices that only
# come from the door type code (locks, REX...) have no label in the prints,
# so they're just named, like "REX".
#
# This understands the schedule layout and door type legend used on the
# PHX53 drawings. Other designers lay their schedules out differently, so a
# different set of prints may need this file adjusted.
#
# The text is pulled out of the PDF with "pdftotext", a free program from
# the poppler-utils package (sudo apt install poppler-utils). It only works
# on PDFs made from CAD, where the text can be selected; not on scans.

# html.unescape turns codes like "&amp;" in the bookmark list back into "&".
import html
# re is "regular expressions": patterns for matching text, like "three
# digits" (\d{3}) or "a door number". Short examples are next to each one.
import re
# subprocess runs another program (pdftotext) and collects what it prints.
import subprocess
# Door and Project are our own classes, from door.py and project.py.
from door import Door
from project import Project


# The error raised when a PDF can't be read or has no schedules in it.
# The GUI catches it and shows the message in a pop-up.
class PrintsImportError(Exception):
    pass


# The systems whose schedule rows describe door devices.
SYSTEMS = ["ACCESS CONTROL", "ALARM"]

# A door number: an optional letter, digits, optional ".digits" parts, and an
# optional letter at the end. Matches 162.1.2, 0163.1, G102 and 0260A, but
# not rack names like "DH01.02.R2 Frt" or "N/A".
DOOR_NUMBER = re.compile(r"[A-Z]?\d+(\.\d+)*[A-Z]?")

# A device ID: exactly three digits, like 050.
DEVICE_ID = re.compile(r"\d{3}")

# The schedule's DEVICE TYPE words, and the name each one gets in the app.
# Types that aren't listed here keep their own name, written in Title Case,
# unless they're a software alarm point (see is_alarm_point()).
DEVICE_NAMES = {
    "CARD READER": "Card Reader",
    "IRIS READER": "Iris Reader",
    "DOOR/GATE CONTACT": "Door Contact",
    "ALARM SOUNDER": "Alarm Sounder",
    "EMERGENCY RELEASE": "Emergency Release",
    "ANTI-TAILGATE HEAD": "Anti-Tailgate",
    "STATUS DISPLAY": "Status Display",
    "DELAYED EGRESS": "Delayed Egress",
    "PANIC ALARM BUTTON": "Panic Button",
    "KEY SWITCH": "Key Switch",
}

# The door type code, like CFD16X, is five parts (from the legend on the
# symbols sheet):
#   C  credential on the uncontrolled (entry) side: C card, F free, K key,
#      M monitored, N no entry
#   F  the same for the controlled (exit) side
#   D  door type: S single leaf, D double leaf, G gate, O overhead, ...
#   16 hardware set (see HARDWARE)
#   X  extra devices (see EXTRAS)
# The pattern below checks a code has that shape, and the ( ) groups pull
# out each part.
DOOR_TYPE_CODE = re.compile(r"([CFKMN])([CFKMN])([BDGHKORSTZ])(\d\d)([A-Z])")

# Hardware sets (the two digits), as devices to install. Mechanical locks
# (00 and 05) give nothing, since there's nothing to wire.
# 0x-4x/5x/7x for a single door, the second list for a double door.
HARDWARE = {
    # Single door
    "00": [],
    "10": ["Mortise Lock"],
    "11": ["Mortise Lock", "REX"],
    "20": ["Mortise Lock (MLR)"],
    "21": ["Mortise Lock (MLR)", "REX"],
    "22": ["Mortise Lock (MLR)", "Door Operator"],
    "23": ["Mortise Lock (MLR)", "REX", "Door Operator"],
    "30": ["Electrified Panic"],
    "31": ["Electrified Panic", "REX"],
    "32": ["Electrified Panic", "Door Operator"],
    "40": ["Electrified Panic", "Delayed Egress"],
    "41": ["Electric Strike", "Delayed Egress"],
    "50": ["Maglock"],
    "51": ["Maglock", "Door Operator"],
    "70": ["Dual Lock (Emergency Door System)"],
    "80": ["Rack Lock"],
    "90": ["Overhead Door Motor"],
    "91": ["Arm Barrier"],
    "92": ["Trash Compactor"],
    "93": ["Elevator Control"],
    # Double door. Leaf B's hardware isn't tracked separately: each device
    # counts once per door, even when the legend gives leaf B its own (a
    # REX or maglock on each leaf is still one "REX" or "Maglock").
    "05": [],
    "15": ["Mortise Lock"],
    "16": ["Mortise Lock", "REX"],
    "25": ["Mortise Lock (MLR)"],
    "26": ["Mortise Lock (MLR)", "REX"],
    "27": ["Mortise Lock (MLR)", "Door Operator"],
    "28": ["Mortise Lock (MLR)", "REX", "Door Operator"],
    "35": ["Electrified Panic"],
    "36": ["Electrified Panic", "REX"],
    "37": ["Electrified Panic", "REX"],
    "45": ["Electrified Panic", "Delayed Egress"],
    "55": ["Maglock"],
    "56": ["Maglock", "Door Operator"],
    "57": ["Maglock"],
    "71": ["Dual Lock (Emergency Door System)"],
    "85": ["Rack Lock"],
    "95": ["Vehicle Gate"],
    "96": ["Gate", "Turnstile"],
    "97": ["Trash Compactor"],
}

# The last letter of the code: extra (Division 28) devices.
EXTRAS = {
    "A": ["Alarm Sounder"],
    "B": ["Emergency Release"],
    "C": ["Anti-Tailgate"],
    "D": ["Emergency Release", "Anti-Tailgate"],
    "E": ["Biometric Reader"],
    "F": ["Biometric Reader", "Emergency Release"],
    "G": ["Biometric Reader", "Emergency Release", "Anti-Tailgate", "Alarm Sounder"],
    "H": ["Biometric Reader", "Emergency Release", "Anti-Tailgate"],
    "J": ["Anti-Tailgate", "Alarm Sounder"],
    "K": ["Status Display", "Emergency Release"],
    "L": ["Status Display"],
    "M": ["REX Push Button"],
    "N": ["REX Push Button", "Key Switch"],
    "P": ["Biometric Reader", "Emergency Release", "Key Switch"],
    "Q": ["Biometric Reader", "Emergency Release", "Anti-Tailgate", "Alarm Sounder", "Key Switch"],
    "R": ["Biometric Reader", "Emergency Release", "Anti-Tailgate", "Key Switch"],
    "S": ["Emergency Release", "Key Switch"],
    "T": ["Emergency Release", "Key Switch", "Anti-Tailgate"],
    "U": ["Biometric Reader", "Emergency Release", "Anti-Tailgate"],
    "V": ["Biometric Reader", "Alarm Sounder", "Anti-Tailgate"],
    "W": ["Biometric Reader", "Alarm Sounder"],
}


# Run a poppler program (pdftotext or pdftohtml) and give back what it
# printed. Turns its problems into a PrintsImportError with a clear message.
def run_poppler(command, pdf_path):
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        # The program itself isn't installed.
        raise PrintsImportError("Reading PDFs needs the poppler-utils programs.\n"
                                "Install them with:  sudo apt install poppler-utils")
    if result.returncode != 0:
        raise PrintsImportError(f"Could not read {pdf_path}:\n{result.stderr.strip()}")
    return result.stdout


# Find the pages that hold schedules, from the PDF's bookmarks.
# Drawing sets made with tools like Bluebeam have a bookmark per sheet, like
#   "PHX53-Z-H-03 - SECURITY RISER SCHEDULES -ACCESS CONTROL" -> page 73
# Reading only those pages takes under a second; reading all 136 sheets of
# floor plans takes about half a minute.
# Gives back a list of page numbers (empty if there are no bookmarks).
def find_schedule_pages(pdf_path):
    # pdftohtml -xml lists the bookmarks as <item page="73">name</item>.
    # -f 1 -l 1 only converts page 1, which keeps it fast.
    xml = run_poppler(["pdftohtml", "-xml", "-i", "-q", "-f", "1", "-l", "1", "-stdout", str(pdf_path)], pdf_path)
    pages = []
    # findall() gives back every (page, name) pair matching the pattern.
    for page, name in re.findall(r'<item page="(\d+)">(.*?)</item>', xml):
        name = html.unescape(name).upper()
        if "SCHEDULE" in name and ("ACCESS CONTROL" in name or "ALARM" in name):
            pages.append(int(page))
    return pages


# Run pdftotext on the PDF and give back its text, one string per page.
# pages = the page numbers to read, or None for every page.
# -layout keeps each table row on one line, with its columns spaced apart.
def read_pdf_text(pdf_path, pages=None):
    if pages is None:
        text = run_poppler(["pdftotext", "-layout", str(pdf_path), "-"], pdf_path)
        # pdftotext puts a "form feed" character (\f) between pages.
        return text.split("\f")
    texts = []
    for page in pages:
        # -f / -l = the first and last page to read.
        texts.append(run_poppler(["pdftotext", "-layout", "-f", str(page), "-l", str(page),
                                  str(pdf_path), "-"], pdf_path))
    return texts


# Find every schedule row in the pages' text.
# Gives back a list of dictionaries, one per device row, like
#   {"system": "ACCESS CONTROL", "building": "PHX53", "door": "162.1.2",
#    "type": "CARD READER", "code": "CFD16X", "id": "050"}
# Rows that appear twice in the PDF (it happens) are only kept once.
def find_schedule_rows(pages):
    rows = []
    seen = set()
    for page_text in pages:
        for line in page_text.splitlines():
            # Columns are separated by 2 or more spaces; one space can be
            # part of a value ("CARD READER"). re.split cuts the line there.
            cells = re.split(r"\s{2,}", line.strip())
            # One line can hold rows from two or three tables side by side,
            # so look for every place a row starts: a system name, followed
            # by a building code like PHX53.
            for start, cell in enumerate(cells):
                if cell not in SYSTEMS or start + 1 >= len(cells):
                    continue
                row = read_row(cells, start)
                if row is None:
                    continue
                key = (row["system"], row["door"], row["type"], row["id"])
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
    return rows


# Read one row starting at cells[start] (the system name).
# The columns before DOOR # differ between schedules (the alarm one has an
# extra BOARD# column), so the row is found from its DEVICE ID instead: the
# first three-digit cell. Counting back from there gives DOOR TYPE, DEVICE
# TYPE and DOOR #. Gives back a dictionary, or None if it isn't a row.
def read_row(cells, start):
    # range(a, b) counts a, a+1, ... up to b-1. min() keeps it inside the list.
    for position in range(start + 4, min(start + 12, len(cells))):
        if DEVICE_ID.fullmatch(cells[position]):
            # Sometimes the PDF joins DOOR # to the cell before it with a
            # single space ("DH01.01.1.R1 151.2"), so take the last word.
            door = cells[position - 3].split()[-1]
            return {
                "system": cells[start],
                # The BLDG column, right after the system name.
                "building": cells[start + 1],
                "door": door,
                "type": cells[position - 2],
                "code": cells[position - 1],
                "id": cells[position],
            }
    return None


# True for schedule entries that are alarm points in the software, not
# devices someone installs, like "ATG TAILGATING ALARM" or
# "EMERGENCY RELEASE LED".
def is_alarm_point(device_type):
    return (device_type.startswith("ATG ")
            or device_type.endswith(" LED")
            or device_type.endswith(" - ALARM"))


# Turn a door type code like CFD16X into the devices it means.
# Gives back a list of device names (empty if the code isn't a door type).
def decode_door_type(code):
    match = DOOR_TYPE_CODE.fullmatch(code)
    if match is None:
        return []
    # group(4) is the hardware digits, group(5) the extras letter.
    devices = []
    devices += HARDWARE.get(match.group(4), [])
    devices += EXTRAS.get(match.group(5), [])
    # Every controlled door gets a door contact (note 06 on the symbols
    # sheet). It's tracked as one device even on a double door, where it
    # covers both leaves.
    devices.append("Door Contact")
    return devices


# Sort door numbers the way a person would: 9.1 before 10.1, and 102.1
# before 102.10. Splitting "102.1.2" into numbers [102, 1, 2] and comparing
# those does that. Letters (like the G in G102) sort before numbers.
def door_sort_key(door_number):
    parts = re.findall(r"\d+|[A-Z]+", door_number)
    key = []
    for part in parts:
        if part.isdigit():
            key.append((1, int(part), part))
        else:
            key.append((0, 0, part))
    return key


# The device's label, as printed on the floor plans: building, door type
# code and device ID joined with dashes, like "PHX53-CCD15B-071".
def device_label(row):
    return f"{row['building']}-{row['code']}-{row['id']}"


# Build the doors from the schedule rows.
# Gives back a list of Door objects, sorted by door number, with every
# device set to P (pending).
def build_doors(rows):
    # For each door number: the schedule devices, as (name, label) pairs,
    # and the door type codes seen on its rows.
    schedule_devices = {}
    door_codes = {}
    for row in rows:
        door = row["door"]
        # Skip rows that aren't for a door: racks, panels, "N/A"...
        if not DOOR_NUMBER.fullmatch(door):
            continue
        schedule_devices.setdefault(door, [])
        door_codes.setdefault(door, [])
        if row["code"] not in door_codes[door]:
            door_codes[door].append(row["code"])
        if is_alarm_point(row["type"]):
            continue
        # .get(x, default): the app's name for it, or the schedule's own
        # words in Title Case if it isn't in DEVICE_NAMES.
        name = DEVICE_NAMES.get(row["type"], row["type"].title())
        schedule_devices[door].append((name, device_label(row)))

    doors = []
    for door_number in sorted(schedule_devices, key=door_sort_key):
        door = Door(door_number)

        # 1. Devices from the schedule, with their label in the name, like
        # "Card Reader (PHX53-CCD15B-071)". The label includes the device ID,
        # so two card readers on one door still get different names.
        for name, label in schedule_devices[door_number]:
            door.devices[f"{name} ({label})"] = "P"

        # 2. Devices from the door type code, unless the schedule already
        # gave the door one of them.
        for code in door_codes[door_number]:
            for name in decode_door_type(code):
                if already_has(door, name):
                    continue
                door.devices[name] = "P"

        # A door can end up with nothing to install (like a monitored-only
        # door with a mechanical lock and no schedule devices left). Those
        # are still added, so every door in the schedules shows up.
        doors.append(door)
    return doors


# True if the door already has this device (or one that counts as the
# same thing), so the door type code doesn't add a second one.
def already_has(door, name):
    # The schedule calls the biometric reader an "Iris Reader".
    if name == "Biometric Reader":
        name = "Iris Reader"
    for existing in door.devices:
        # "Card Reader (PHX53-CCD15B-071)" counts as a "Card Reader".
        if existing == name or existing.startswith(name + " ("):
            return True
    return False


# Guess the project's name from the schedule rows: the building code in the
# second column (like PHX53). Gives back "" if there are no rows.
def guess_project_name(pages):
    for page_text in pages:
        for line in page_text.splitlines():
            cells = re.split(r"\s{2,}", line.strip())
            for position, cell in enumerate(cells[:-1]):
                if cell in SYSTEMS and read_row(cells, position) is not None:
                    return cells[position + 1]
    return ""


# The whole import in one step: read the PDF and build a Project from it.
# Raises PrintsImportError if the PDF can't be read or has no schedules.
def import_prints(pdf_path):
    # Read just the schedule sheets if the bookmarks say where they are.
    # Without bookmarks, read every page (slower, but still works).
    schedule_pages = find_schedule_pages(pdf_path)
    if len(schedule_pages) > 0:
        pages = read_pdf_text(pdf_path, schedule_pages)
    else:
        pages = read_pdf_text(pdf_path)
    rows = find_schedule_rows(pages)
    doors = build_doors(rows)
    if len(doors) == 0:
        raise PrintsImportError("No door schedules were found in this PDF.\n\n"
                                "This reads riser schedules with the columns SYSTEM, BLDG, ... "
                                "DOOR #, DEVICE TYPE, DOOR TYPE, DEVICE ID (like the PHX53 drawings). "
                                "Scanned drawings, and schedules laid out differently, can't be read yet.")
    return Project(guess_project_name(pages), doors=doors)
