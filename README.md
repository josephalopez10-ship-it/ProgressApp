11-22-2026 11:45PM
I'm an access control tehcnician learning Python by creating an app that can track the progress of projects I'm working on. 
For now I'm working on getting the main functionality and playing around with some OOP and then I'll work on GUI.

Functionality:
- The user will have a list of doors. In the future I would like to add a Project class so the user can have multiple lists of doors.
- The user will be able to add, remove and edit doors, devices and their respective status by searching their name
- The user will be able to view a list of all doors in the current list they are working in

Door:
- A door can have any combination of the following access control devices: Card reader, Door contact, Lock and REX
- A door will be a dictionary containing devices specific to that door: overall door completion status, device, device status and a section for restraints
- Doors have one final entry after REX called Restraint. Here the user types details of anything restraining project progress.
- When the user adds a door to a list they are prompted to enter devices and their statuses
- All door information is gained through user input. GUI will help fix this
- Doors in the same list cannot share the same name
- A Door's status is based on the collective status of its devices

Devices:
-Devices are entered through user input
-all devices need to be compelte for the door status to be complete
- if any device or devices are pending the door status is pending
- if any device or devices are restrained the door is restrained
- if their is a combination of complete, pending and restrained device statuses the door status will be restrained
- a pending devices is one taht has yet ot be installed. a restrianed device is one that cannot bw instaalled for some reasona and is haltign progess.

Status:
- Door statuses: C - complete, P - pending, R - restrained
- Device statuses: C - complete, P - pending, R - restrained, N - N/a
- Status colors: C - green, P - yellow, R - Red
####################################################################################################################################################################################################3

11-23-2026

i got the basic functionaloty down now. Im going to try the GUI. No real idea how I want it to look, will keep it basic .



