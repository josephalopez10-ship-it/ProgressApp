# DOOR REPORT
# Makes a report of every door and device, to print or email, in one of
# two formats:
#   make_text_report() - a plain .txt file. Opens in any program (Notepad,
#                        a phone, an email).
#   make_pdf_report()  - a .pdf file with a table and colored statuses.
#                        Looks the same on every computer and prints nicely.
# Kept in its own file so the GUI (or anything else) can use it:
#   import report
#   report.make_text_report(doors, "door_report.txt", summary_text)
#   report.make_pdf_report(doors, "door_report.pdf", summary_text)
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
# reportlab is the library that builds PDF files (installed with pip, and
# listed in requirements.txt).
# colors        = named colors like colors.green
# letter        = the page size (8.5 x 11 inches)
# inch          = lets us write sizes in inches, like 0.75 * inch
# getSampleStyleSheet = ready-made text styles (title, normal text, ...)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
# "platypus" is reportlab's way of building a page out of pieces (called
# "flowables") stacked top to bottom: a title, some text, a table...
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# What each status letter means, written out in full for the report.
STATUS_NAMES = {"C": "Complete", "P": "Pending", "R": "Restrained", "N": "N/a"}

# The PDF's text color for each status, the same colors as the app.
STATUS_COLORS = {
    "C": colors.HexColor("#2e7d32"),   # green
    "P": colors.HexColor("#b58900"),   # yellow
    "R": colors.HexColor("#c62828"),   # red
}

# How many characters wide the text report is. 60 fits on a printed page and in
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


# Build the PDF and save it to file_path.
#   doors        = the list of Door objects to put in the report
#   file_path    = where to save the PDF, for example "door_report.pdf"
#   summary_text = the totals to show near the top (the GUI's summary text)
def make_pdf_report(doors, file_path, summary_text):
    styles = getSampleStyleSheet()

    # The pieces of the page, top to bottom. We add to this list, then
    # reportlab lays them all out and starts new pages when needed.
    story = []
    story.append(Paragraph("Door Progress Report", styles["Title"]))
    # strftime turns the date into text: %B = month name, %d = day,
    # %Y = year, %I:%M %p = time like 02:30 PM.
    story.append(Paragraph(datetime.now().strftime("Created %B %d, %Y at %I:%M %p"), styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))
    # Paragraph text uses <br/> instead of "\n" for a new line.
    story.append(Paragraph(summary_text.replace("\n", "<br/>"), styles["Heading3"]))
    story.append(Spacer(1, 0.2 * inch))

    # The table is a list of rows, and each row is a list of cells.
    # The first row is the heading.
    rows = [["Door", "Device", "Status"]]

    # Table styles are a list of instructions. Each one says which cells it
    # applies to, as (column, row) from the top left. (-1, -1) means
    # "the last column, last row", so (0, 0) to (-1, 0) is the whole first row.
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d0d0d0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    for door in doors:
        door_status = door.status()
        # The door's own row: its name and overall status, in bold on light grey.
        rows.append([door.name, "", STATUS_NAMES[door_status]])
        # len(rows) - 1 is the number of the row just added.
        door_row = len(rows) - 1
        style.append(("FONTNAME", (0, door_row), (-1, door_row), "Helvetica-Bold"))
        style.append(("BACKGROUND", (0, door_row), (-1, door_row), colors.HexColor("#f0f0f0")))
        style.append(("TEXTCOLOR", (2, door_row), (2, door_row), STATUS_COLORS[door_status]))

        if len(door.devices) == 0:
            rows.append(["", "(no devices yet)", ""])

        # One row for each device, under its door.
        for device_name, device_status in door.devices.items():
            rows.append(["", device_name, STATUS_NAMES.get(device_status, device_status)])
            device_row = len(rows) - 1
            # N isn't in STATUS_COLORS, so N devices stay black.
            if device_status in STATUS_COLORS:
                style.append(("TEXTCOLOR", (2, device_row), (2, device_row), STATUS_COLORS[device_status]))

    # colWidths sets how wide each column is.
    # repeatRows=1 repeats the heading row at the top of every page.
    table = Table(rows, colWidths=[2.6 * inch, 2.6 * inch, 1.3 * inch], repeatRows=1)
    table.setStyle(TableStyle(style))
    story.append(table)

    # Create the PDF file and lay out everything in the story.
    document = SimpleDocTemplate(file_path, pagesize=letter,
                                 leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                                 topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                                 title="Door Progress Report")
    document.build(story)
