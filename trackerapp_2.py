#ADD DEVICES TO DOORS

# Path provides a safe, platform-independent way to work with file and folder names.
from pathlib import Path

# __file__ is the location of this Python script. resolve() converts it to an absolute
# path, and with_name() replaces the script's filename with door_list.txt. This means
# the app looks for the file next to trackerapp_2.py regardless of the current folder
# from which the script is started.
FILE_PATH = Path(__file__).resolve().with_name("door_list.txt")

# This in-memory list contains all Door records while the application is running.
# The file on disk is used to preserve those records after the program closes.
door_list = []


# The Door class represents a single door with its associated attributes: name, status, location, and restraint. It provides methods to convert the object to and from a single line of text for storage in a file.
class Door:
    def __init__(self, name, status, location, restraint):
        # These attributes store the four pieces of information associated with a door.
        self.name = name
        self.status = status
        self.location = location
        self.restraint = restraint

    # Convert this Door object into one comma-separated line for storage in the text file.
    # The spaces after commas match the format expected by from_single_line().
    def to_single_line(self):
        return f"{self.name}, {self.status}, {self.location}, {self.restraint}"

    # Fill this Door object using a comma-separated line read from the text file.
    # strip() removes the newline and surrounding whitespace, while split() separates
    # the four saved values. A line is only valid if it contains exactly four parts.
    def from_single_line(self, line):
        parts = line.strip().split(", ")
        if len(parts) == 4:
            self.name, self.status, self.location, self.restraint = parts
        else:
            raise ValueError("Invalid line format for Door object.")
        
    # The __repr__ method provides a string representation of the Door object, useful for debugging and logging.
    def __repr__(self):
        return f"Door(name={self.name}, status={self.status}, location={self.location}, restraint={self.restraint})"
    

# Read door_list.txt and rebuild the in-memory door_list at startup.
def load_doors():
    try:
        # Open the file in read mode ("r"). utf-8 ensures normal text is handled correctly.
        with FILE_PATH.open("r", encoding="utf-8") as file:
            for line in file:
                # Ignore completely blank lines rather than trying to treat them as doors.
                if not line.strip():
                    continue

                # Start with a temporary empty Door, then populate it from the line.
                door = Door("", "", "", "")
                try:
                    door.from_single_line(line)
                except ValueError as error:
                    # A malformed saved line should not stop the rest of the file from loading.
                    print(f"Skipped invalid door entry: {error}")
                    continue

                # Store both the Door object and its individual values. The object is used
                # for saving, while the individual values are used by the existing menu code.
                door_list.append([
                    door,
                    door.name,
                    door.status,
                    door.location,
                    door.restraint,
                ])
    except FileNotFoundError:
        # If the file does not exist yet, create an empty file so future saves can use it.
        FILE_PATH.touch()


# Rewrite door_list.txt with the complete current state of the in-memory door_list.
def save_doors():
    # Open in write mode ("w"), which replaces the old file contents instead of appending.
    with FILE_PATH.open("w", encoding="utf-8") as file:
        for door in door_list:
            # door[0] is the Door object in each saved list entry. Convert it to one
            # text line and add a newline so each door is stored on a separate line.
            file.write(door[0].to_single_line() + "\n")


# Basic menu function to display options to the user and call the appropriate functions based on user input
def menu():
    print("************************************************")
    print("********Welcome to the Door Tracker App!********")
    print("************************************************")
    print()
    print(" A - Add a door/doors, R - Remove a door/doors, L - List all doors, Q - Quit")
    choice = input()
    # the users choice is not CASE-SENSITIVE in the menu, but it is CASE-SENSITIVE in the add_door() and remove_door() functions.
    if choice == "A" or choice == "a":
        add_door()
    elif choice == "R" or choice == "r":
        remove_door()
    elif choice == "L" or choice == "l":
        list_doors()
    elif choice == "Q" or choice == "q":
        print("Thank you for using Tracker.")
        global quit
        quit = False
    else:
        print("Invalid choice. Please try again.")
        return True


# Function to add a new door to the list. It prompts the user for door details then creates a new Door object and appends it to the door_list. The user can also view the current list of doors or quit the operation.
def add_door():
    while True:
        print("Please enter the following information: Door Name, Door Status, Door Location, Door Restraint. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
        
        new_door_name = input("Door Name: ")
        if new_door_name == "Q":
            return
        
        # Entering uppercase L here calls the list screen and continue restarts this
        # while loop. That allows the user to choose "L" again or enter another door.
        if new_door_name == "L":
            list_doors()
            continue

        new_door_status = input("Door Status: ")
        if new_door_status == "Q":
            return
        
        new_door_location = input("Door Location: ")
        if new_door_location == "Q":
            return
        
        new_door_restraint = input("Door Restraint: ")
        if new_door_restraint == "Q":
            return
        
        else:
            new_door = Door(new_door_name, new_door_status, new_door_location, new_door_restraint)
            door_list.append([new_door, new_door_name,new_door_status, new_door_location, new_door_restraint])

            # Immediately rewrite door_list.txt so the newly added door survives a restart.
            save_doors()
            print(f"\n{new_door_name} has been added to the list.\n")

# Function to remove a door from the list. It prompts the user for the name of the door to remove, searches for it in the door_list, and removes it if found. The user can also view the current list of doors or quit the operation.
def remove_door():
    while True:
        print("Please enter the name of the door you would like to remove. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
        
        remove_door_name = input("Door Name: ")
        if remove_door_name == "Q":
            return
        
        # Entering uppercase L displays the current list without ending or restarting
        # the remove workflow; continue then prompts for another door name.
        if remove_door_name == "L":
            list_doors()
            continue

        for door in door_list:
            if door[1] == remove_door_name:
                door_list.remove(door)

                # Save after removal so door_list.txt no longer contains the deleted door.
                save_doors()
                print(f"\n{remove_door_name} has been removed from the list.\n")
                return
            
        print(f"\n{remove_door_name} is not in the list. Please try again.\n")

        
# Function to list all doors in the list. It prints each door name on a new line.
def list_doors():
    print("List of all doors:")
    for door in door_list:
        print(f"--------------------------------------------------------------------------------------------------------------------------------------------")  # Print the door name, status, location, and restraint
        print(f"Door:      {door[1]}")  # Print the door name
        print(f"Status:    {door[2]}")  # Print the door status
        print(f"Location:  {door[3]}")  # Print the door location
        print(f"Restraint: {door[4]}")  # Print the door restraint
        print(f"--------------------------------------------------------------------------------------------------------------------------------------------\n")  # Print a separator line

# This block only runs when trackerapp_2.py is executed directly. It will not run
# merely because another Python file imports this module.
if __name__ == "__main__":
    # quit is True while the main menu should continue running.
    quit = True

    # Restore saved doors before the first menu is displayed.
    load_doors()

    # Repeatedly show the menu until menu() changes quit to False.
    while quit:
        menu()
