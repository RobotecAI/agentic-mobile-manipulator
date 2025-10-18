from enum import Enum
from typing import Dict, List


class Collection(Enum):
    RETURNED_PACKAGES_TABLE = "t1"
    OUTBOUND_SHIPMENT_TABLE = "t2"
    INSPECTION_TABLE = "t4"


RACK_TO_OBJECT_TYPE: Dict[str, str] = {
    "J02": "cpu",
    "J01": "cpu",
    "D02": "gpu",
    "D01": "gpu",
    "D04": "gpu",
    "D03": "gpu",
    "C04": "gpu",
    "C03": "gpu",
    "C02": "gpu",
    "C01": "gpu",
    "A04": "cpu",
    "A03": "cpu",
    "G04": "pipes",
    "G03": "pipes",
    "A06": "cpu",
    "A05": "cpu",
    "A02": "cpu",
    "A01": "cpu",
    "G06": "pipes",
    "G05": "pipes",
    "G02": "pipes",
    "G01": "pipes",
    "H02": "pipes",
    "H01": "pipes",
    "L10": "hammers",
    "L09": "hammers",
    "L06": "hammers",
    "L05": "hammers",
    "L08": "hammers",
    "L07": "hammers",
    "L04": "hammers",
    "L03": "hammers",
    "L02": "hammers",
    "L01": "hammers",
    "B04": "cpu",
    "B03": "cpu",
    "B02": "cpu",
    "B01": "cpu",
    "K02": "nails",
    "K01": "nails",
    "I02": "nails",
    "I01": "nails",
    "F10": "hammers",
    "F09": "hammers",
    "F06": "motherboard",
    "F05": "motherboard",
    "F04": "motherboard",
    "F03": "motherboard",
    "F02": "motherboard",
    "F01": "motherboard",
    "F08": "motherboard",
    "F07": "motherboard",
}


def get_object_type_to_racks(object_type: str) -> List[str]:
    # invert the dictionary, handle multiple racks for the same object type
    object_type_to_racks: Dict[str, List[str]] = {}
    for rack, obj_type in RACK_TO_OBJECT_TYPE.items():
        if obj_type not in object_type_to_racks:
            object_type_to_racks[obj_type] = []
        object_type_to_racks[obj_type].append(rack)
    return object_type_to_racks.get(object_type, [])


def get_object_type_to_racks_all() -> Dict[str, List[str]]:
    # invert the dictionary, handle multiple racks for the same object type
    object_type_to_racks: Dict[str, List[str]] = {}
    for rack, obj_type in RACK_TO_OBJECT_TYPE.items():
        if obj_type not in object_type_to_racks:
            object_type_to_racks[obj_type] = []
        object_type_to_racks[obj_type].append(rack)
    return object_type_to_racks
