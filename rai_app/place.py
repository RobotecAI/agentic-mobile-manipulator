import json
from typing import List, Optional

from models import Pose


class Place:
    def __init__(self, name: str, pose: Pose):
        self.name = name
        self.pose = pose

    def get_text(self) -> str:
        return f"Place(name={self.name}, pose={self.pose})"

    def __repr__(self) -> str:
        return f"Place(name={self.name})"


class PlaceCollection:
    def __init__(self, places: List[Place]):
        self.places = places

    @classmethod
    def from_json(cls, json_path: str) -> "PlaceCollection":
        with open(json_path, "r") as f:
            data = json.load(f)
        places: List[Place] = []
        for k, v in data.items():
            places.append(
                Place(name=k, pose=Pose(x=v["x"], y=v["y"], z=v["z"], yaw=v["yaw"]))
            )
        return cls(places=places)

    def get_place_by_name(self, name: str) -> Optional[Place]:
        return next((place for place in self.places if place.name == name), None)

    def get_place_pose_by_name(self, name: str) -> Optional[Pose]:
        return next((place.pose for place in self.places if place.name == name), None)

    def get_all_places(self) -> List[Place]:
        return self.places

    def __repr__(self) -> str:
        return f"PlaceCollection(places={self.places})"
