# DOOR TRACKER APP
# Tracks the install progress of each door and the devices on it
# (card reader, door contact, lock, REX, restraint).
#
# Status codes used for every device:
#   C = Complete   (shown in green)
#   P = Pending    (shown in yellow)
#   R = Restrained (shown in red)
#   N = N/a        (no color, the door doesn't have this device)
#
# All doors are saved in door_list.json, so they are still there the next time
# the app starts.
#
# TODO: ADD DEVICES TO DOORS

import json
# Path is a built-in tool for working with file locations.
from pathlib import Path
# Door is the class from door.py that holds one door's information.
from door import Door
# colorama lets us print colored text in the terminal.
# Fore = text colors, Style.RESET_ALL = go back to normal color.
from colorama import Fore, Style, init
# autoreset=True puts the color back to normal after every print().
init(autoreset=True)

# Where the save file lives. This always points to door_list.json in the same
# folder as this script, no matter which folder you run the app from.
FILE_PATH = Path(__file__).resolve().with_name("door_list.json")

# Every door is stored in this list while the app is running.
# Each item in the list is a Door object (see door.py).
door_list = []

# The only status letters a device is allowed to have.
VALID_STATUSES = ["C", "P", "R", "N"]


# Ask the user for a device status, and keep asking until they type a valid one.
# prompt = the text shown to the user, for example "Card Reader".
# Returns "C", "P", "R", "N", or "Q" (if the user wants to quit).
# Lowercase is accepted, because .upper() turns "c" into "C".
def ask_status(prompt):
    while True:
        value = input(f"{prompt}: \n").upper()
        if value in VALID_STATUSES or value == "Q":
            return value
        print(Fore.RED+f"|{value}| is not a valid entry. Please enter C,P,R, or N (Q to quit)")


# Return a status letter with its color added, ready to print.
# Example: status_color("C") gives a green "C".
# Anything not in the colors dictionary (like "N" or a door name) is returned
# unchanged, so it prints in the normal color.
def status_color(value):
        # A dictionary that matches each status letter to its color.
        colors = {
                "C": Fore.GREEN,
                "P": Fore.YELLOW,
                "R": Fore.RED,
            }
        # .get() returns None instead of crashing if the letter isn't in the dictionary.
        color = colors.get(value)
        if color is None:
            return value
        # Color code + the letter + reset code, so only this letter is colored.
        return f"{color}{value}{Style.RESET_ALL}"


# Show the main menu, read the user's choice, and run the matching function.
# Menu letters work in upper or lowercase here. Inside the add, remove and
# edit screens, Q and L must be typed in uppercase.
def menu():
    print("                     ************************************************")
    print("                     ********Welcome to the Door Tracker App!********")
    print("                     ************************************************")
    print(f"\n")
    print(" A - Add a door/doors, R - Remove a door/doors, E - Edit a door, L - List all doors, Q - Quit")

    choice = input(f"\n")
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
        # "global" lets this function change the quit variable created at the
        # bottom of the file. Setting it to False stops the main loop.
        global quit
        quit = False
    else:
        print("Invalid choice. Please try again.")
        return True


# Check that a door name is safe to save.
# Returns True if the name is OK. Otherwise it prints the reason and returns False.
def is_valid_name(name):
    # .strip() removes spaces, so a name of only spaces also counts as blank.
    if name.strip() == "":
        print(Fore.RED+"Door name cannot be blank.")
        return False
    return True


# Look through door_list for a door with this exact name.
# Returns that Door object if found, or None if no door has that name.
# Used by add (to stop duplicates), remove, and edit.
def find_door(name):
    for door in door_list:
        if door.name == name:
            # return stops the loop right away, as soon as the door is found.
            return door
    return None


# Read door_list.json and put every saved door into door_list.
# This runs once, when the app starts.
def load_doors():
    # First time running the app: no save file yet, so start with an empty list.
    if not FILE_PATH.exists():
        return

    with FILE_PATH.open("r", encoding="utf-8") as file:
        #json.load reads file and give back list of dictionaries

        saved_doors = json.load(file)

    for data in saved_doors:
        door_list.append(Door.from_dict(data))


# Save every door in door_list to door_list.json.
# This is called after every add, remove, and edit, so nothing is lost if
# the app closes.
def save_doors():

    #json cant save door object directly so turn them into dictionaries
    data = []
    for door in door_list:
        data.append(door.to_dict())

    with FILE_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


# Add new doors. Asks for a door name, then each device on it and its status.
# Keeps looping so several doors can be added in a row.
# Q = go back to the main menu (the current door is not saved), L = show the door list.
def add_door():
    while True:
        print(f"Please enter the door name and the status of each device: C - Complete, P - Pending, R - Restrained, N - N/a")
        print()
        new_door_name = input(f"Door Name: \n")

        # Check the name before asking for any device statuses.
        if new_door_name == "Q":
            return
        elif new_door_name == "L":
            list_doors()
            # continue jumps back to the top of the while loop to ask for a name again.
            continue
        elif not is_valid_name(new_door_name):
            continue
        elif find_door(new_door_name) is not None:
            # A door with this name already exists.
            print(f"{new_door_name} already exist please change the entry.")
            continue

        # Start the door with no devices, then add them one at a time.
        new_door = Door(new_door_name)
        print("\nAdd the devices on this door. Press ENTER on a blank device name when done.\n")

        while True:
            device_name = input("Device name: \n")

            # Q = cancel this door without saving it.
            if device_name == "Q":
                return

            # A blank name means the user is finished adding devices.
            # break leaves this inner loop only, not the outer one.
            if device_name.strip() == "":
                break

            # Each device name can only be used once per door,
            # because it's the key in the devices dictionary.
            if device_name in new_door.devices:
                print(Fore.RED+f"{device_name} is already on this door.")
                continue

            # ask_status() only accepts C, P, R, N or Q.
            device_status = ask_status(f"{device_name} status")
            if device_status == "Q":
                return

            new_door.devices[device_name] = device_status

        # The inner loop is finished (blank device name), so the door is complete.
        # These lines are lined up with "while True:" above, so they run once,
        # after all the devices are entered, not after every device.
        door_list.append(new_door)
        # Save right away so the new door is kept even if the app closes.
        save_doors()
        print(Fore.GREEN+f"\n{new_door_name} successfully added to the list ({new_door.status()}).\n")

# Remove doors. Asks for a door name, confirms with Y/N, then deletes it.
# Keeps looping so several doors can be removed in a row.
# Q = go back to the main menu, L = show the door list.
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

        # Ask before deleting, since a deleted door can't be brought back.
        print(Fore.RED+f"Are you sure you want to DELETE: "+f"{remove_door_name} [Y/N]")
        choice = input().upper()
        if choice == "Y":
            door_list.remove(found_door)
            # Save so the door is also gone from door_list.json.
            save_doors()
            print(Fore.RED+f"\n{remove_door_name} has been DELETED from the list.\n")
        elif choice == "N":
            print()
            continue

        else:
            print("Invalid option please try again.")
            print()
            continue


# Edit a door: rename it, change a device's status, add a device, or delete one.
# Shows the door first, then asks what to change, then saves the change.
# Q at the door name = go back to the main menu.
# Q at any later question = cancel and start over with a new door name.
def edit_door():

    while True:
        door_to_edit = input(f"Enter the name of the door to edit:\n")
        print()

        if door_to_edit == "Q":
            return

        found_door = find_door(door_to_edit)
        if found_door is None:
            print(f"Not in list please try again")
            continue

        # Show the door so the user can see it before changing it.
        print(f"You chose to edit: {found_door.name}\n")
        show_door(found_door)

        # Menu of what can be changed.
        print("\n####################################################")
        print("N - Rename door,  S - Change a device status")
        print("A - Add a device, D - Delete a device,  Q - Back")
        print("####################################################\n")
        choice = input("What would you like to do?\n").upper()

        if choice == "Q":
            continue

        # N: rename the door
        elif choice == "N":
            new_name = input("Enter the new door name:\n")
            if new_name == "Q":
                continue
            if not is_valid_name(new_name):
                continue
            if find_door(new_name) is not None:
                print(f"\n{new_name} already exists in the list. Please choose another name.\n")
                continue
            found_door.name = new_name

        # S: change the status of a device that's already on the door
        elif choice == "S":
            device_name = input("Which device?\n")
            if device_name == "Q":
                continue
            # "not in" checks whether this name is a key in the devices dictionary.
            if device_name not in found_door.devices:
                print(Fore.RED + f"{device_name} is not on this door.")
                continue
            new_status = ask_status(f"{device_name} status")
            if new_status == "Q":
                continue
            found_door.devices[device_name] = new_status

        # A: add a new device to the door
        elif choice == "A":
            device_name = input("New device name:\n")
            if device_name == "Q" or device_name.strip() == "":
                continue
            if device_name in found_door.devices:
                print(Fore.RED + f"{device_name} is already on this door.")
                continue
            new_status = ask_status(f"{device_name} status")
            if new_status == "Q":
                continue
            found_door.devices[device_name] = new_status

        # D: delete a device from the door
        elif choice == "D":
            device_name = input("Which device do you want to delete?\n")
            if device_name == "Q":
                continue
            if device_name not in found_door.devices:
                print(Fore.RED + f"{device_name} is not on this door.")
                continue
            # del removes this device name and its status from the dictionary.
            del found_door.devices[device_name]

        else:
            print("Invalid option, please try again.")
            continue

        # We only get here if one of the changes above was made,
        # because every "cancel" path above uses continue.
        save_doors()
        print(Fore.GREEN + f"\nData has been updated. {found_door.name} is now {found_door.status()}.\n")


# Print one door: its name, overall status, and every device with its status.
# Used by list_doors() and edit_door().
def show_door(door):
    print(f"Door:         {door.name}")
    print(f"Status:       {status_color(door.status())}")

    if len(door.devices) == 0:
        print("  (no devices yet)")

    # .items() gives each device name together with its status.
    # :<14 pads the name to 14 characters so all the statuses line up.
    for device_name, device_status in door.devices.items():
        print(f"  {device_name:<14}{status_color(device_status)}")


# Print every door and the status of each of its devices.
# Statuses are colored by status_color(): green = C, yellow = P, red = R.
def list_doors():
    print("\nList of all doors:\n")

    # Nothing to show yet, so say so and leave the function.
    if len(door_list) == 0:
        print("No doors have been added yet.\n")
        return

    for door in door_list:
        print("-" * 60)
        show_door(door)
        print("-" * 60 + "\n")

# This is where the app actually starts.
# The code below only runs when you run this file directly
# (python trackerapp_2.py), not when another file imports it.
if __name__ == "__main__":
    # The main loop keeps running while quit is True.
    # (The name is a little backwards: menu() sets it to False when the user picks Q.)
    quit = True

    # Load the saved doors before showing the menu.
    load_doors()

    # Show the menu again and again until the user quits.
    while quit:
        menu()
