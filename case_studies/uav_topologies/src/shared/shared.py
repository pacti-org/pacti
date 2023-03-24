from aenum import Enum, auto


class Direction(Enum):
    ego = auto()
    front = auto()
    bottom = auto()
    left = auto()
    right = auto()
    top = auto()
    rear = auto()

    @property
    def opposite(self):
        if self == Direction.ego:
            return Direction.ego
        if self == Direction.front:
            return Direction.rear
        if self == Direction.bottom:
            return Direction.top
        if self == Direction.left:
            return Direction.right
        if self == Direction.right:
            return Direction.left
        if self == Direction.top:
            return Direction.bottom
        if self == Direction.rear:
            return Direction.front

    @property
    def x_symmetric(self):
        if self == Direction.left:
            return Direction.right
        if self == Direction.right:
            return Direction.left
        return self


class SymbolType(Enum):
    UNOCCUPIED = auto()
    FUSELAGE = auto()
    EMPTY = auto()
    ROTOR = auto()
    WING = auto()
    CONNECTOR = auto()


all_symbols_types = {
    SymbolType.FUSELAGE,
    SymbolType.EMPTY,
    SymbolType.ROTOR,
    SymbolType.WING,
    SymbolType.CONNECTOR,
}

symbols_short: dict = {
    SymbolType.UNOCCUPIED: "U",
    SymbolType.FUSELAGE: "F",
    SymbolType.EMPTY: "E",
    SymbolType.ROTOR: "R",
    SymbolType.CONNECTOR: "C",
    SymbolType.WING: "W",
}


def symbols_short_in(x: str):
    return f"{symbols_short[x]}in"


def symbols_short_out(x: str):
    return f"{symbols_short[x]}on"


symbols_colors: dict = {
    SymbolType.UNOCCUPIED: "white",
    SymbolType.FUSELAGE: "red",
    SymbolType.EMPTY: "white",
    SymbolType.ROTOR: "green",
    SymbolType.CONNECTOR: "grey",
    SymbolType.WING: "blue",
}


class DirectionsAssignment(object):
    _instance = None
    data = None

    def __new__(cls):
        if cls._instance is None:
            print("Creating the object")
            cls._instance = super(DirectionsAssignment, cls).__new__(cls)
            cls.data = {}
        return cls._instance

    def set_direction_assignment(self, dirs: dict[str, int]):
        self.data = dirs


direction_to_coordinates = {
    "ego": [0, 0, 0],
    "front": [0, 1, 0],
    "bottom": [0, 0, -1],
    "left": [-1, 0, 0],
    "right": [1, 0, 0],
    "top": [0, 0, 1],
    "rear": [0, -1, 0],
}
