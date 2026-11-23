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
    def __init__(self, name, door_status, card_reader, door_contact, lock, rex, restraint):
        # Store the seven values on the door, so they can be used later as
        # door.name, door.status, door.card_reader, and so on.
        self.name = name
        self.status = door_status
        self.card_reader = card_reader
        self.door_contact = door_contact
        self.lock = lock
        self.rex = rex
        self.restraint = restraint

    # Turn this door into one line of text for the save file.
    # The values are separated by ", " (a comma and a space).
    # from_single_line() splits on that same ", ", so the two must match.
    def to_single_line(self):
        return f"{self.name}, {self.status}, {self.card_reader}, {self.door_contact}, {self.lock}, {self.rex}, {self.restraint}"

    # The opposite of to_single_line(): fill in this door from one line of
    # the save file.
    # .strip() removes the newline at the end of the line.
    # .split(", ") cuts the line into a list wherever ", " appears.
    def from_single_line(self, line):
        parts = line.strip().split(", ")
        # A good line has exactly 7 values. If it doesn't, the line is broken,
        # so raise an error. load_doors() catches the error and skips that line.
        if len(parts) == 7:
            # Put the 7 values into the 7 attributes, in order.
            self.name, self.status, self.card_reader, self.door_contact, self.lock, self.rex, self.restraint = parts
        else:
            raise ValueError("Invalid line format for Door object.")

    # __repr__ controls what you see when you print a Door directly, like
    # print(door). Handy for checking what's inside a door while testing.
    def __repr__(self):
        return f"Door(name={self.name}, status={self.status}, card_reader={self.card_reader}, door_contact={self.door_contact}, lock={self.lock}, rex={self.rex}, restraint={self.restraint})"
