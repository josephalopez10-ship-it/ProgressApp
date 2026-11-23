# The Door class holds all the information about one door:
# its name, its overall status, and the status of each device on it.
#
# It also converts a door to and from one line of text, which is how doors
# are saved in door_list.txt. For example:
#   Main Entrance, C, C, P, C, C, N
#   (name, status, card reader, door contact, lock, REX, restraint)
class Door:
    # __init__ runs when a new Door is created, for example:
    #   Door("Main Entrance", "C", "C", "P", "C", "C", "N")
    # "self" means "this particular door".
    def __init__(self, name, devices=None):
        # Store the seven values on the door, so they can be used later as
        # door.name, door.status, door.card_reader, and so on.
        self.name = name
        if devices is None:
            devices = {}
        self.devices = devices

    #function to find the a doors overall status based on compeltion of its devices
    def status(self):
        statuses = self.devices.values()
        if len(self.devices) == 0:
            return "P"
        if "R" in statuses:
            return "R" 

        for s in statuses:
            if s != "C" and s != "N":
                return "P"

        return "C"

    # turn door to dicitonary so it cna be saved as json
    def to_dict(self):
        return {"name": self.name, "devices": self.devices}

    # creat door from dicitonary
    @staticmethod
    def from_dict(data):
        return Door(data["name"], data["devices"])

    # __repr__ controls what you see when you print a Door directly, like
    # print(door). Handy for checking what's inside a door while testing.
    def __repr__(self):
        return f"Door(name={self.name}, status={self.status()}, devices={self.devices})"
