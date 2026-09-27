from pathlib import Path

PROJECT_PATH = Path(__file__).parent.parent
BULLET_CD = 0.10
DEFAULT_HIT_CD = 0.25

DIRECTION_LOOKUP = {
    0.0: "east",
    45.0: "south_east",
    90.0: "south",
    135.0: "south_west",
    180.0: "west",
    -135.0: "north_west",
    -90.0: "north",
    -45.0: "north_east",
}
DIRECTION_VELOCITY = {
    0.0: (700, 0),
    45.0: (495, 495),
    90.0: (0, 700),
    135.0: (-495, 495),
    180.0: (-700, 0),
    -135.0: (-495, -495),
    -90.0: (0, -700),
    -45.0: (495, -495),
}
SPAWN_ANCHORS = {
    "north": (0.5, 0.0),
    "south": (0.5, 1.0),
    "east": (1.0, 0.5),
    "west": (0.0, 0.5),
    "north_east": (1.0, 0.0),
    "south_east": (1.0, 1.0),
    "north_west": (0.0, 0.0),
    "south_west": (0.0, 1.0),
}
