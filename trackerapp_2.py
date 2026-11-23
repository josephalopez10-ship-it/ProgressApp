#ADD DEVICES TO DOORS


# Path provides a safe, platform-independent way to work with file and folder names.
from pathlib import Path
from door import Door
from colorama import Fore, Style, init
init(autoreset=True)

# __file__ is the location of this Python script. resolve() converts it to an absolute
# path, and with_name() replaces the script's filename with door_list.txt. This means
# the app looks for the file next to trackerapp_2.py regardless of the current folder
# from which the script is started.
FILE_PATH = Path(__file__).resolve().with_name("door_list.txt")

# This in-memory list contains all Door records while the application is running.
# The file on disk is used to preserve those records after the program closes.
door_list = []

# functions that finds what color to display the device status when listed to the user.
def status_color(value):
        colors = {
                "C": Fore.GREEN,
                "P": Fore.YELLOW,
                "R": Fore.RED,
            }
        color = colors.get(value)
        if color is None:
            return value
        return f"{color}{value}{Style.RESET_ALL}"

# Basic menu function to display options to the user and call the appropriate functions based on user input
def menu():
    print("                     ************************************************")
    print("                     ********Welcome to the Door Tracker App!********")
    print("                     ************************************************")
    print(f"\n")
    print(" A - Add a door/doors, R - Remove a door/doors, E - Edit a door, L - List all doors, Q - Quit")

    choice = input(f"\n")
    # the users choice is not CASE-SENSITIVE in the menu, but it is CASE-SENSITIVE in the add_door() and remove_door() functions.
    if choice == "A" or choice == "a":
        add_door()
    elif choice == "R" or choice == "r":
        remove_door()
    elif choice == "L" or choice == "l":
        list_doors()
    elif choice == "E" or choice == "e":
        edit_door()
    elif choice == "Q" or choice == "q":
        print(f"                                Thank you for using Tracker.")
        global quit
        quit = False
    else:
        print("Invalid choice. Please try again.")
        return True

#functions that handles checking if the door that the user has inputed is in the door list.
def find_door(name):
    for door in door_list:
        if door.name == name:
            return door
    return None

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
                door = Door("", "", "", "", "", "", "")
                try:
                    door.from_single_line(line)
                except ValueError as error:
                    # A malformed saved line should not stop the rest of the file from loading.
                    print(f"Skipped invalid door entry: {error}")
                    continue

                # Store both the Door object and its individual values. The object is used
                # for saving, while the individual values are used by the existing menu code.
                door_list.append(door)

    except FileNotFoundError:
        # If the file does not exist yet, create an empty file so future saves can use it.
        FILE_PATH.touch()

# Rewrite door_list.txt with the complete current state of the in-memory door_list.
def save_doors():
    # Open in write mode ("w"), which replaces the old file contents instead of appending.
    with FILE_PATH.open("w", encoding="utf-8") as file:
        for door in door_list:
            
            file.write(door.to_single_line() + "\n")

# Function to add a new door to the list. It prompts the user for door details then creates a new Door object and appends it to the door_list. The user can also view the current list of doors or quit the operation.
def add_door():
    while True:
        print(f"Please enter the door name and the status of each device: C - Complete, P - Pending, R - Restrained, N - N/a")
        print()
        new_door_name = input(f"Door Name: \n")

        if new_door_name == "Q":
            return
                
        # Entering uppercase L here calls the list screen and continue restarts this
        # while loop. That allows the user to choose "L" again or enter another door.
        elif new_door_name == "L":
            list_doors()
            continue
        elif find_door(new_door_name) is not None:
            print(f"{new_door_name} already exist please change the entry.")
            continue

        new_door_status = input(f"Door Status: \n").upper()
        if new_door_status == "Q":
            return
        
        new_card_reader = input(f"Card Reader: \n").upper()
        if new_card_reader == "Q":
            return
        
        new_door_contact = input(f"Door Contact: \n").upper()
        if new_door_contact == "Q":
            return
        
        new_lock = input(f"Lock: \n").upper()
        if new_lock == "Q":
            return
        
        new_rex = input(f"REX: \n").upper()
        if new_rex == "Q":
            return
        
        new_door_restraint = input("Restraint: \n").upper()
        if new_door_restraint == "Q":
            return
        
        else:
            new_door = Door(new_door_name, new_door_status, new_card_reader, new_door_contact, new_lock, new_rex, new_door_restraint)
            door_list.append(new_door)

            # Immediately rewrite door_list.txt so the newly added door survives a restart.
            save_doors()
            print(Fore.GREEN+f"\n{new_door_name} successfully added to the list.\n")

# Function to remove a door from the list. It prompts the user for the name of the door to remove, searches for it in the door_list, and removes it if found. The user can also view the current list of doors or quit the operation.
def remove_door():
    while True:
        print("Please enter the name of the door you would like to remove. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
        print()
        remove_door_name = input("Door Name: ")
        print()

        if remove_door_name == "Q":
            return
        if remove_door_name == "L":
            list_doors()
            continue

        found_door = find_door(remove_door_name)
        if found_door is None:
            print(f"{remove_door_name} is not on the list.\n")
            continue
            
        print(Fore.RED+f"Are you sure you want to DELETE: "+f"{remove_door_name} [Y/N]")
        choice = input().upper()
        if choice == "Y":
            door_list.remove(found_door)
            save_doors()
            print(Fore.RED+f"\n{remove_door_name} has been DELETED from the list.\n")
        elif choice == "N":
            print()
            continue
            
        else:
            print("Invalid option please try again.")
            print()
            continue   

# Function to edit a doors attributes.
def edit_door():

    while True:
        door_to_edit = input(f"Enter the name of the door to edit:\n")
        print()

        if door_to_edit == "Q":
            return
        # create variable to track and then check whether or not the user input is in the list
        found_door = find_door(door_to_edit)
        if found_door is None:
            print(f"Not in list please try again")
            continue

        #print all information for the chosen door so the user cna see it before editing
        print(f"You chose to edit: {door_to_edit}")
        print(f"Name:         {status_color(found_door.name)}")
        print(f"Status:       {status_color(found_door.status)}")
        print(f"Card Reader:  {status_color(found_door.card_reader)}")
        print(f"Door Contact: {status_color(found_door.door_contact)}")
        print(f"Lock:         {status_color(found_door.lock)}")
        print(f"REX:          {status_color(found_door.rex)}")
        print(f"Restraint:    {status_color(found_door.restraint)}")

        # small menu of options to edit
        print("####################################################")
        print(f"N - Door name, S - Status, C - Card Reader")
        print(f"D - Door Contact, L - Lock, E - REX, R - Restraint")
        print("####################################################\n")
        print()
        choice = input(f"What would you like to edit?\n")


        #tupel of options to choose from
        options_to_edit = {
            "N": ("name", "Door name"),
            "S": ("status", "Status"),
            "C": ("card_reader", "Card Reader"),
            "D": ("door_contact", "Door Contact"),
            "L": ("lock", "Lock"),
            "E": ("rex", "REX"),
            "R": ("restraint", "Restraint"),
        }

        if choice == "Q":
            continue
        
        elif choice not in options_to_edit:
            print(f"Invalid option try again. OPTIONS ARE CASE-SENSIITVE.")
            continue
    
        # print the door and antribute of the door that is being edited
        attribute, label = options_to_edit[choice]
        print(f"\nEditing door: {found_door.name}, {label}:\n")
        new_label = input(f"\nEnter updated information.\n")

        if choice != "N":
            new_label = new_label.upper()

        # check if the new name chosen by the user is int he list
        if choice == "N" and find_door(new_label) is not None:
            print(f"\n{new_label} already exists in the list. Please choose another name.\n")
            continue
        if new_label == "Q":
            continue

        setattr(found_door, attribute, new_label)
        save_doors()
        print(f"Data has been updated.\n")
        
# Function to list all doors in the list. It prints each door name on a new line.
def list_doors():
    print("\nList of all doors:\n")

    for door in door_list:
        
        print(f"---------------------------------------------------------------------------------------------------------------------------------------")  # Print the door name, status, location, and restraint
        print(f"Door:         {status_color(door.name)}")  # Print the door name
        print(f"Status:       {status_color(door.status)}")  # Print the door status
        print(f"Card Reader:  {status_color(door.card_reader)}")  # Print the door card reader
        print(f"Door Contact: {status_color(door.door_contact)}")  # Print the door contact
        print(f"Lock:         {status_color(door.lock)}")  # Print the door lock
        print(f"REX:          {status_color(door.rex)}")  # Print the door REX
        print(f"Restraint:    {status_color(door.restraint)}")  # Print the door restraint
        print(f"---------------------------------------------------------------------------------------------------------------------------------------\n")  # Print a separator line

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
