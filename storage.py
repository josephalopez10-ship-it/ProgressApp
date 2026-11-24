# STORAGE
# Saves and loads every project to and from projects.json.
# Used by the GUI (trackerapp_gui.py).
#
# projects.json holds a list of projects, and each project holds its doors:
#   [
#     {"name": "Westfield Mall", "job_number": "24-117", ..., "doors": [...]},
#     {"name": "City Hospital",  "job_number": "24-130", ..., "doors": [...]}
#   ]

# json saves and reads lists and dictionaries as text.
import json
# sys lets us close the app on purpose with sys.exit().
import sys
# Path is a built-in tool for working with file locations.
from pathlib import Path
# Door and Project are our own classes, from door.py and project.py.
from door import Door
from project import Project

# The folder this file is in. Both save files live here, no matter which
# folder the app is started from.
FOLDER = Path(__file__).resolve().parent

# Where all the projects are saved. With Path, "/" joins a folder and a file
# name into one path. This name must match the line in .gitignore exactly,
# so your job data is never committed to git.
PROJECTS_FILE = FOLDER / "projects.json"

# The old save file from before projects existed. Only read once, to move
# its doors into the first project. It's never changed or deleted.
OLD_DOORS_FILE = FOLDER / "door_list.json"

# The name of the project the old doors are moved into.
FIRST_PROJECT_NAME = "My First Project"

# Every project is stored in this list while the app is running.
# Each item is a Project object (see project.py).
project_list = []


# Look through project_list for a project with this name.
# Ignores upper/lowercase and extra spaces, like find_door().
# Returns the Project, or None if there's no project with that name.
def find_project(name):
    for project in project_list:
        if project.name.lower() == name.strip().lower():
            # return stops the loop right away, as soon as it's found.
            return project

    return None


# Read projects.json and put every saved project into project_list.
# This runs once, when the app starts.
def load_projects():

    # No projects.json yet: this is the first run since projects were added.
    # Move the old doors into a project (if there are any), then stop.
    if not PROJECTS_FILE.exists():
        move_old_doors()
        return

    try:
        with PROJECTS_FILE.open("r", encoding="utf-8") as file:
            # json.load reads the whole file and gives back a list of
            # dictionaries, one dictionary per project.
            saved_projects = json.load(file)

        # Turn each dictionary back into a Project object (which also turns
        # its doors back into Door objects).
        for data in saved_projects:
            project_list.append(Project.from_dict(data))

    # If the file is damaged, stop the app instead of carrying on with an
    # empty list. Otherwise the next save would overwrite the damaged file
    # and every project in it would be lost for good.
    # JSONDecodeError = not valid JSON, KeyError = something missing (like a
    # project with no "doors"), TypeError = the wrong kind of data.
    except(json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"Could not read {PROJECTS_FILE.name}: {error}")
        print(f"Fix or rename the file, then start the app again.")
        sys.exit(1)


# One-time move (a "migration"): put the doors from the old door_list.json
# into a new project called "My First Project", then save it to
# projects.json. door_list.json itself is left alone, as a backup.
# Only called when projects.json doesn't exist yet.
def move_old_doors():

    # Nothing to move if there was never an old save file.
    if not OLD_DOORS_FILE.exists():
        return
    try:
        with OLD_DOORS_FILE.open("r", encoding="utf-8") as file:
            saved_doors = json.load(file)
        # Turn each saved door dictionary back into a Door object.
        doors = []
        for door_data in saved_doors:
            doors.append(Door.from_dict(door_data))
    # Same as load_projects(): stop rather than lose the old doors.
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"Could not read {OLD_DOORS_FILE.name}: {error}")
        print("Fix or rename the file, then start the app again.")
        sys.exit(1)

    project_list.append(Project(FIRST_PROJECT_NAME, doors=doors))

    # Save right away, so next time projects.json exists and this move
    # doesn't happen again.
    save_projects()


# Save every project in project_list to projects.json.
# Call this after every change, so nothing is lost if the app closes.
def save_projects():

    # JSON can't save Project objects directly, so turn each one into a
    # dictionary (which also turns its doors into dictionaries).
    data = []

    for project in project_list:
        data.append(project.to_dict())

    # "w" mode erases the old file and writes it fresh.
    # indent=2 spreads the file over several lines so it's easy to read.
    with PROJECTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


# ---------------------------------------------------------------------------
# Settings: small choices the app remembers between runs, like light or dark
# mode. Kept in their own file, settings.json, separate from your job data:
#   {"theme": "dark"}
# ---------------------------------------------------------------------------
SETTINGS_FILE = FOLDER / "settings.json"


# Read one setting, or give back default if it was never saved (or if
# settings.json is missing or damaged; a lost setting isn't worth stopping
# the app for, unlike lost job data).
def load_setting(name, default):
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            settings = json.load(file)
        return settings.get(name, default)
    except (OSError, json.JSONDecodeError, AttributeError):
        return default


# Save one setting, keeping any other settings already in the file.
def save_setting(name, value):
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as file:
            settings = json.load(file)
        # A damaged file might hold something that isn't a dictionary.
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, json.JSONDecodeError):
        settings = {}

    settings[name] = value
    with SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(settings, file, indent=2)
