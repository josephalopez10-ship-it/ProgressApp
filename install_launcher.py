# INSTALL LAUNCHER
# Adds TrackerApp to your apps menu, with its icon, so it opens with a click
# instead of from a terminal.
#
# Run it ONCE with the project's own Python (the one in .venv, which has
# sv_ttk and reportlab installed):
#     .venv/bin/python install_launcher.py
# Run it again if you move the ProgressApp folder, so the launcher points at
# the new place. To take the launcher away again:
#     .venv/bin/python install_launcher.py --remove
#
# How it works: Linux desktops (Cinnamon, GNOME, KDE...) build their apps
# menu from small text files ending in .desktop, kept in
# ~/.local/share/applications. This script writes one for TrackerApp.

# sys gives the path of the Python running this script (sys.executable),
# and the words typed after the script's name (sys.argv).
import sys
# subprocess runs another program; here, the desktop's menu refresher.
import subprocess
from pathlib import Path

# The folder this file (and the app) is in.
FOLDER = Path(__file__).resolve().parent

# Where the desktop looks for menu entries. Path.home() is your home folder,
# like /home/senpai.
LAUNCHER_FILE = Path.home() / ".local" / "share" / "applications" / "trackerapp.desktop"


# Build the text of the .desktop file.
# python_path = the Python that will run the app (the .venv one).
# folder      = the folder trackerapp_gui.py and icon.png are in.
# Each line is "Key=Value". The keys are the standard ones every Linux
# desktop understands.
def make_desktop_entry(python_path, folder):
    # Paths go inside "quotes" on the Exec line, so a folder name with a
    # space in it still works.
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=TrackerApp\n"
        "Comment=Track the install progress of doors and devices\n"
        # The command that starts the app.
        f'Exec="{python_path}" "{folder / "trackerapp_gui.py"}"\n'
        # The folder to start in.
        f"Path={folder}\n"
        f"Icon={folder / 'icon.png'}\n"
        # False = don't open a terminal window alongside the app.
        "Terminal=false\n"
        # Which section of the apps menu it goes in.
        "Categories=Office;ProjectManagement;\n"
        # Must match className= in trackerapp_gui.py, so the taskbar knows
        # the open window belongs to this launcher (same icon, no duplicate).
        "StartupWMClass=TrackerApp\n"
    )


# Write the launcher file, then ask the desktop to refresh its apps menu.
def install():
    # parents=True also makes any missing folders on the way; exist_ok=True
    # means "it's fine if the folder is already there".
    LAUNCHER_FILE.parent.mkdir(parents=True, exist_ok=True)
    # sys.executable is the Python running this script. Run it with
    # .venv/bin/python, and the launcher uses that one too.
    LAUNCHER_FILE.write_text(make_desktop_entry(sys.executable, FOLDER), encoding="utf-8")
    refresh_menu()
    print(f"Launcher installed: {LAUNCHER_FILE}")
    print("Look for TrackerApp in your apps menu (under Office).")


# Delete the launcher file, if there is one.
def remove():
    if LAUNCHER_FILE.exists():
        LAUNCHER_FILE.unlink()   # unlink() deletes a file
        refresh_menu()
        print(f"Launcher removed: {LAUNCHER_FILE}")
    else:
        print("There was no launcher to remove.")


# Most desktops notice a new .desktop file by themselves within a few
# seconds; this just hurries them along. If the refresher program isn't
# installed, that's fine, so the error is ignored.
def refresh_menu():
    try:
        subprocess.run(["update-desktop-database", str(LAUNCHER_FILE.parent)], check=False)
    except OSError:
        pass


# This part only runs when the file is started directly, not when the
# tests import it. sys.argv[1:] is the list of words after the script name.
if __name__ == "__main__":
    if "--remove" in sys.argv[1:]:
        remove()
    else:
        install()
