import os

door_list_folder = os.path.join(os.path.expanduser("~"), "ProgressApp")
file_path = os.path.join(door_list_folder, "door_list.txt")






door_list = []

while True:
    
    print(" A - Add a door/doors, R - Remove a door/doors, L - List all doors, Q - Quit")
    choice = input().upper()

    if choice == "A":
        while True:
            print("Enter the door name you would like to add. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
            door_name = input()

            if door_name == "Q":
                break

            elif door_name == "L":
                print("List of all doors:")
                for door in door_list:
                    print(door)
            else:
                door_list.append(door_name)
                with open(file_path, "a", encoding="utf-8") as file:
                    for door in door_list:
                        file.write(door + "\n")

    elif choice == "R":
        while True:
            print("Enter the door you would like to remove. L - view door list, Q - quit. CHOICES ARE CASE-SENSITIVE.")
            door_name = input()

            if door_name == "Q":
                break

            elif door_name == "L":
                print("List of all doors:")
                for door in door_list:
                    print(door)

            elif door_name in [door for door in door_list]:
                door_list.remove(door_name)
                print(f"{door_name} has been removed from the list.")
                

            else:
                print(f"{door_name} not found in the list.")

    elif choice == "L":
        print("List of all doors:")
        for door in door_list:
            print(door)

    elif choice == "Q":
        break

    else:
        print("Invalid choice. Please try again.")