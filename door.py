# The Door class holds all the information about one door:
# its name, and a dictionary of the devices on it with each device's status.
#
# Example:
#   door.name    = "Main Entrance"
#   door.devices = {"Card Reader": "C", "Lock": "P", "REX": "N"}

# The only status letters a device is allowed to have:
#   C = Complete, P = Pending, R = Restrained, N = N/a
# Kept here, with the Door class, so every file that works with doors can use
# it: from door import Door, VALID_STATUSES
VALID_STATUSES = ["C", "P", "R", "N"]

# What each letter means, written out in full. The letters are what gets
# saved; these words are only for showing to people (the app's table and
# the reports): from door import STATUS_NAMES
STATUS_NAMES = {"C": "Complete", "P": "Pending", "R": "Restrained", "N": "N/a"}


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

    # Work out the door's overall status from its devices.
    #   No devices            -> P (nothing installed yet)
    #   Any device is R       -> R (R wins, even if other devices are P)
    #   All devices C or N    -> C (N devices are ignored)
    #   Anything else         -> P
    # It's recalculated every time it's called, so it's never out of date.
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

    # Count this door's devices: how many are complete, out of how many.
    # N devices are skipped (continue jumps to the next device), the same way
    # they're ignored for the door status.
    # Returns two numbers at once, as a tuple: (done, total).
    #   Door("Lobby", {"Lock": "C", "REX": "P", "Sounder": "N"}).progress()
    #   -> (1, 2)
    # Used by the app's Devices column and its summary at the top.
    def progress(self):
        done = 0
        total = 0
        for device_status in self.devices.values():
            if device_status == "N":
                continue
            total += 1
            if device_status == "C":
                done += 1
        return done, total

    # Look for a device on this door, ignoring upper/lowercase and extra spaces.
    # Returns the device name exactly as it's saved (for example "Card Reader"
    # when the user typed "card reader"), or None if the door doesn't have it.
    # Use the returned name to read or change the device: door.devices[name]
    def find_device(self, name):
        for device_name in self.devices:
            if device_name.lower() == name.strip().lower():
                return device_name
        return None

    # Turn this door into a dictionary so it can be saved as JSON.
    def to_dict(self):
        return {"name": self.name, "devices": self.devices}

    # The opposite of to_dict(): build a Door from a saved dictionary.
    # @staticmethod means you call it on the class itself: Door.from_dict(data)
    @staticmethod
    def from_dict(data):
        return Door(data["name"], data["devices"])

    # __repr__ controls what you see when you print a Door directly, like
    # print(door). Handy for checking what's inside a door while testing.
    def __repr__(self):
        return f"Door(name={self.name}, status={self.status()}, devices={self.devices})"
