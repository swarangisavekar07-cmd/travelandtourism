from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class Destination:
    name: str
    latitude: float
    longitude: float

DESTINATIONS: Dict[str, Destination] = {
    "lonavala": Destination(name="Lonavala", latitude=18.7557, longitude=73.4091),
    "mahabaleshwar": Destination(name="Mahabaleshwar", latitude=17.9237, longitude=73.6586),
    "matheran": Destination(name="Matheran", latitude=18.9867, longitude=73.2679),
}

def get_destination(name: str) -> Destination:
    key = name.strip().lower()
    if key not in DESTINATIONS:
        raise ValueError(
            f"Unknown destination '{name}'. Supported destinations: {list(DESTINATIONS.keys())}"
        )
    return DESTINATIONS[key]
