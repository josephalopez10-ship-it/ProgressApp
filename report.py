# DOOR REPORT
# Makes a plain text report of every door and device, to print or email.
# A .txt file opens in any program (Notepad, a phone, an email) with nothing
# extra to install.
# Kept in its own file so the GUI (or anything else) can use it:
#   import report
#   report.make_text_report(doors, "door_report.txt", summary_text)
#
# Example of what the report looks like:
#
#   DOOR PROGRESS REPORT
#   Created November 23, 2026 at 02:50 PM
#
#   3 doors: 2 complete, 0 pending, 1 restrained
#   Devices: 10 of 11 complete (91%)
#
#   ============================================================
#   Joes Door                                           COMPLETE
#   ------------------------------------------------------------
#       Card Reader                                     Complete
#       Lock                                            Complete

# datetime gives today's date and time, to print on the report.
from datetime import datetime

# What each status letter means, written out in full for the report.
STATUS_NAMES = {"C": "Complete", "P": "Pending", "R": "Restrained", "N": "N/a"}

# How many characters wide the report is. 60 fits on a printed page and in
# most email windows.
WIDTH = 60


# Build the text report and save it to file_path.
#   doors        = the list of Door objects to put in the report
#   file_path    = where to save the file, for example "door_report.txt"
#   summary_text = the totals to show near the top (the GUI's summary text)
def make_text_report(doors, file_path, summary_text):
    # Build the report as a list of lines, then write them all at the end.
    lines = []
    lines.append("DOOR PROGRESS REPORT")
    # strftime turns the date into text: %B = month name, %d = day,
    # %Y = year, %I:%M %p = time like 02:30 PM.
    lines.append(datetime.now().strftime("Created %B %d, %Y at %I:%M %p"))
    # An empty string makes a blank line.
    lines.append("")
    lines.append(summary_text)
    lines.append("")

    for door in doors:
        # The door status in capitals, so it stands out from its devices.
        door_status = STATUS_NAMES[door.status()].upper()
        # "=" * WIDTH makes a line of 60 "=" characters.
        lines.append("=" * WIDTH)
        # Put the name on the left and the status on the right edge.
        # :<{...} pads the name with spaces to that many characters, so every
        # status ends up lined up in the same column.
        lines.append(f"{door.name:<{WIDTH - len(door_status)}}{door_status}")
        lines.append("-" * WIDTH)

        if len(door.devices) == 0:
            lines.append("    (no devices yet)")

        # One line for each device, indented 4 spaces under its door.
        for device_name, device_status in door.devices.items():
            # .get() falls back to the letter itself if it isn't in STATUS_NAMES.
            status_name = STATUS_NAMES.get(device_status, device_status)
            lines.append(f"    {device_name:<{WIDTH - 4 - len(status_name)}}{status_name}")

        lines.append("")

    # Open the file for writing ("w" erases anything already in it) and write
    # all the lines, joined together with a new line ("\n") between each one.
    with open(file_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
