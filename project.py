# The Project class holds one job: its details and all oof its doors.

#example:
#

from door import Door

class Project:
    def __init__(self, name, job_number="", address="", customer="", doors=None):
        self.name = name
        self.job_number = job_number
        self.address = address
        self.customer = customer

        if doors is None:
            doors = []
        self.doors = doors

    def find_door(self, name):
        for door in self.doors:
            if door.name.lower() == name.strip().lower():
                return door
        return None

    def to_dict():
        door_dicts = []
        for door in self.doors:
            door_dicts.append(door.to_dict())
        return {
            "name": self.name,
            "job_number": self.job_number,
            "address": self.address,
            "customer": self.customer,
            "doors": door_dicts,
        }

    @staticmethod
    def from_dict(data):
        doors = []
        for door_data in data["doors"]:
            doors.append(Door.from_dict(door_data))
        return Project(
            data["name"],
            job_number=data.get("job_number", ""),
            address=data.get("address", ""),
            customer=data.get("customer", ""),
            doors=doors)

    def __repr__(self):
        return f"Project(name={self.name}, job_number={self.job_number}, doors={len(self.doors)})"
    