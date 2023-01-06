from __future__ import annotations

import random
from dataclasses import dataclass, field

from case_studies.topologies.grammar import Symbol, SymbolConnection, Unoccupied, LocalState
from case_studies.topologies.grammar.figures import plot_3d_grid
from matplotlib.figure import Figure


@dataclass
class Grid:
    nodes: list[list[list[Symbol]]]
    connections: set[SymbolConnection] = field(default_factory=set)
    name: str = ""


@dataclass
class Point:
    x: int
    y: int
    z: int

    def __str__(self):
        return f"{self.x},{self.y},{self.z}"

    def __hash__(self):
        return hash(self.__str__())

    @property
    def front(self) -> Point:
        return Point(self.x, self.y + 1, self.z)

    @property
    def rear(self) -> Point:
        return Point(self.x, self.y - 1, self.z)

    @property
    def top(self) -> Point:
        return Point(self.x, self.y, self.z + 1)

    @property
    def bottom(self) -> Point:
        return Point(self.x, self.y, self.z - 1)

    @property
    def left(self) -> Point:
        return Point(self.x - 1, self.y, self.z)

    @property
    def right(self) -> Point:
        return Point(self.x + 1, self.y, self.z)


@dataclass
class GridBuilder:
    grid: dict[Point, Symbol]
    connections: set[SymbolConnection] = field(default_factory=set)
    name: str = ""
    current_point: Point | None = None
    dimension: int = 0

    @classmethod
    def generate(cls, half_size: int = -1):
        if half_size == -1:
            """Choose random size"""
            half_size = random.randint(1, 3)
        dim = half_size * 2 + 1
        grid = {}
        for x in range(-half_size, half_size + 1):
            for y in range(-half_size, half_size + 1):
                for z in range(-half_size, half_size + 1):
                    point = Point(x, y, z)
                    grid[point] = Unoccupied()

        """Center at 0,0,0 """
        current_node = Point(0, 0, 0)

        return cls(grid=grid, current_point=current_node, dimension=dim)

    @property
    def plot(self) -> Figure:
        node_xyz = []
        color_xyz = []
        for point, symbol in self.grid.items():
            node_xyz.append([point.x, point.y, point.z])
            from case_studies.topologies.grammar.symbols import symbols_colors
            color_xyz.append(symbols_colors[symbol.symbol_type])

        return plot_3d_grid(node_xyz, color_xyz)

    def symbol(self, point: Point | None = None) -> Symbol:
        if point is None:
            point = self.current_point
        return self.grid[point]

    def local_state(self, point: Point | None = None) -> LocalState:
        if point is None:
            point = self.current_point

        return LocalState(
            ego=self.grid[point],
            front=self.grid[point.front],
            bottom=self.grid[point.bottom],
            left=self.grid[point.left],
            right=self.grid[point.right],
            top=self.grid[point.top],
            rear=self.grid[point.bottom]
        )


if __name__ == '__main__':
    new_grid = GridBuilder.generate(half_size=1)
    new_grid.plot.show()
    current_node_state = new_grid.local_state(new_grid.current_point)
    current_node_state.plot.show()
