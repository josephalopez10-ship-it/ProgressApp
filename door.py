# The Door class holds all the information about one door:
# its name, and a dictionary of the devices on it with each device's status.
#
# Example:
#   door.name    = "Main Entrance"
#   door.devices = {"Card Reader": "C", "Lock": "P", "REX": "N"}
class Door:
    # __init__ runs when a new Door is created, for example:
    #   Door("Main Entrance", {"Card Reader": "C", "Lock": "P"})
    # devices is optional. If it isn't given, the door starts with no devices.
    def __init__(self, name, devices=None):
        self.name = name
        # Use None as the default and create the dictionary here. Writing
        # devices={} above would make every door share ONE dictionary.
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
