# The Project class holds one job: its details and all of its doors.
#
# Example:
#   project.name       = "Westfield Mall"
#   project.job_number = "24-117"
#   project.address    = "1200 Main St"
#   project.customer   = "Acme Builders"
#   project.doors      = [Door("Main Entrance", {...}), Door("Loading Dock", {...})]
#
# Door names only have to be different INSIDE one project, so two projects
# can each have a door called "Main Entrance".

# Door is the class from door.py that holds one door and its devices.
from door import Door


class Project:
    # __init__ runs when a new Project is created, for example:
    #   Project("Westfield Mall", job_number="24-117")
    # Everything except the name is optional. ="" makes the default an empty
    # string, so a project can be created with just a name and filled in later.
    def __init__(self, name, job_number="", address="", customer="", doors=None):
        self.name = name
        self.job_number = job_number
        self.address = address
        self.customer = customer

        # Same reason as Door's devices: use None as the default, then make a
        # new list here, so every project gets its own list instead of all
        # projects sharing ONE list.
        if doors is None:
            doors = []
        self.doors = doors

    # Look through this project's doors for one with this name.
    # Ignores upper/lowercase and extra spaces, so "main entrance " finds
    # "Main Entrance".
    # Returns the Door, or None if this project has no door with that name.
    def find_door(self, name):
        for door in self.doors:
            if door.name.lower() == name.strip().lower():
                # return stops the loop right away, as soon as the door is found.
                return door
        return None

    # Turn this project into a dictionary so it can be saved as JSON.
    # Each door is turned into a dictionary too, using Door's own to_dict(),
    # so each class takes care of saving its own information.
    # "self" must be the first parameter of every method: when you call
    # project.to_dict(), Python passes the project in as self automatically.
    def to_dict(self):
        door_dicts = []
        for door in self.doors:
            door_dicts.append(door.to_dict())
        return {
            "name": self.name,
            "job_number": self.job_number,
            "address": self.address,
            "customer": self.customer,
            "doors": door_dicts,
        }

    # The opposite of to_dict(): build a Project from a saved dictionary.
    # @staticmethod means it has no "self": you call it on the class itself,
    # Project.from_dict(data), because the project doesn't exist yet.
    @staticmethod
    def from_dict(data):
        # Turn each saved door dictionary back into a Door object.
        doors = []
        for door_data in data["doors"]:
            doors.append(Door.from_dict(door_data))
        # .get(key, "") gives "" if that key is missing, so older or
        # hand-edited files without a job number (for example) still load.
        return Project(
            data["name"],
            job_number=data.get("job_number", ""),
            address=data.get("address", ""),
            customer=data.get("customer", ""),
            doors=doors)

    # What you see when you print(project). Handy while testing.
    def __repr__(self):
        return f"Project(name={self.name}, job_number={self.job_number}, doors={len(self.doors)})"
