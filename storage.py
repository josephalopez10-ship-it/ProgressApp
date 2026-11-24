import json
import sys
from pathlib import Path
from door import Door
from project import Project

FOLDER = Path(__file__).resolve().parent

PROJECTS_FILE = FOLDER / "project.json"

OLD_DOORS_FILE = FOLDER / "door_list.json"

FIRST_PROJECT_NAME = "My First Project"

project_list = []

def find_projcet(name):
    for project in project_list:
        if project.name.lower() == name.strip().lower():
            return project

    return None

def load_projects():

    if not PROJECTS_FILE.exists():
        move_old_doors()
        return

    try:
        with PROJECTS_FILE.open("r", encoding="utf-8") as file:
            saved_projects - json.load(file)

        for data in saved_projects:
            project_list.append(Project.ffrom_dict(data))

    except(json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"Could not read {PROJECTS_FILE.name}: {error}")
        print(f"Fix or rename the file, then start the app again.")
        sys.exit(1)


def move_old_doors():

    if not OLD_DOORS_FILE.exists():
        return
    try:
        with OLD_DOORS_FILE.open("r", encoding="utf-8") as file:
            saved_doors = json.load(file)
        doors = []
        for door_data in saved_doors:
            doors.append(Door.from_dict(door_data))
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"Could not read {OLD_DOORS_FILE.name}: {error}")
        print("Fix or rename the file, then restart the app again.")
        sys.exit(1)

    project_list.append(Project(FIRST_PROJECT_NAME, doors=doors))

    save_projects()

def save_projects():

    data = []

    for project in project_list:
        data.append(project.to_dict())

    with PROJECTS_FILE.open("w", encoding="utf-8")as file:
        json.dump(data, file, indent=2)