import os

door_list = []

# Basic menu function to display options to the user and call the appropriate functions based on user input
def menu():
    print("************************************************")
    print("********Welcome to the Door Tracker App!********")
    print("************************************************")
    print()
    print(" A - Add a door/doors, R - Remove a door/doors, L - List all doors, Q - Quit")
    choice = input()
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

# Function to add a door to the list. It prompts the user for a door name and adds it to the list if it's not already present. The user can also view the current list of doors or quit the operation.
def add_door():
    while True:
        print("Enter the door name you would like to add. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
        door_name = input()

        if door_name == "Q":
            return 

        elif door_name == "L":
            list_doors()

        else:
            door_list.append(door_name)
            print(f"\n{door_name} has been added to the list.\n")

# Function to remove a door from the list. It prompts the user for a door name and removes it from the list if it exists. The user can also view the current list of doors or quit the operation.
def remove_door():
    while True:
        print("Enter the door you would like to remove. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
        door_name = input()

        if door_name == "Q":
            return 

        elif door_name == "L":
            list_doors()

        elif door_name in [door for door in door_list]:
            door_list.remove(door_name)
            print(f"{door_name} has been removed from the list.")

        else:
            print(f"{door_name} not found in the list.")

# Function to list all doors in the list. It prints each door name on a new line.
def list_doors():
    print("List of all doors:")
    for door in door_list:
        print(door)



# main loop to keep the program running until the user chooses to quit. It calls the menu function repeatedly until the quit variable is set to False.
while quit:
    menu()
