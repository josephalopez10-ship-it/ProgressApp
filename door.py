# The Door class represents a single door with its associated attributes: name, status, location, and restraint. It provides methods to convert the object to and from a single line of text for storage in a file.
class Door:
    def __init__(self, name, door_status, card_reader, door_contact, lock, rex, restraint):
        # These attributes store the four pieces of information associated with a door.
        self.name = name
        self.status = door_status
        self.card_reader = card_reader
        self.door_contact = door_contact
        self.lock = lock
        self.rex = rex
        self.restraint = restraint

    # Convert this Door object into one comma-separated line for storage in the text file.
    # The spaces after commas match the format expected by from_single_line().
    def to_single_line(self):
        return f"{self.name}, {self.status}, {self.card_reader}, {self.door_contact}, {self.lock}, {self.rex}, {self.restraint}"

    # Fill this Door object using a comma-separated line read from the text file.
    # strip() removes the newline and surrounding whitespace, while split() separates
    # the seven saved values. A line is only valid if it contains exactly seven parts.
    def from_single_line(self, line):
        parts = line.strip().split(", ")
        if len(parts) == 7:
            self.name, self.status, self.card_reader, self.door_contact, self.lock, self.rex, self.restraint = parts
        else:
            raise ValueError("Invalid line format for Door object.")
        
    # The __repr__ method provides a string representation of the Door object, useful for debugging and logging.
    def __repr__(self):
        return f"Door(name={self.name}, status={self.status}, card_reader={self.card_reader}, door_contact={self.door_contact}, lock={self.lock}, rex={self.rex}, restraint={self.restraint})"
