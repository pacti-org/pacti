from __future__ import annotations

import random
from dataclasses import dataclass, field

from matplotlib.figure import Figure

from case_studies.uav_topologies_generation.src.contracts_utils.union import ContractsUnions
from pacti.terms.polyhedra import PolyhedralContract
from .figures import DirectionsGrid
from ..tools.plotting import plot_3d_grid
from .rule import Rule
from .symbols import Symbol, Unoccupied, Fuselage, Empty, Rotor, Wing, Connector
from ..shared import Direction, SymbolType, symbols_colors
from ..tools.constraints import from_symbol_directions_to_constraints


@dataclass
class SymbolConnection:
    symbol_a: Symbol
    symbol_b: Symbol


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
        return f"({self.x},{self.y},{self.z})"

    def __hash__(self):
        return hash(self.__str__())

    def __lt__(self, other):
        if self.x < other.x and self.y < other.y and self.z < other.z:
            return True
        else:
            return False

    @property
    def all_directions(self) -> list[Point]:
        return [self.front, self.rear, self.top, self.bottom, self.left, self.right]

    @property
    def symmetry_directions(self) -> list[Point]:
        return [self.front, self.rear, self.top, self.bottom, self.right]

    @property
    def y_symmetric(self) -> Point:
        if self.y != 0:
            return Point(self.x, -self.y, self.z)
        else:
            return self

    @property
    def x_symmetric(self) -> Point:
        if self.x != 0:
            return Point(-self.x, self.y, self.z)
        else:
            return self

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
class Edge:
    s: Point
    d: Point

    def __hash__(self):
        return hash(self.s) + hash(self.d)


@dataclass
class LocalState:
    ego: Symbol
    front: Symbol
    bottom: Symbol
    left: Symbol
    right: Symbol
    top: Symbol
    rear: Symbol

    def matches(self, rule: Rule) -> bool:
        for direction, symbol in self.__dict__.items():
            if direction == "ego":
                continue
            if symbol.symbol_type not in getattr(rule.conditions, direction):
                return False
        return True

    def has_non_empty_symbols(self) -> bool:
        for direction, symbol in self.__dict__.items():
            if symbol.symbol_type != SymbolType.EMPTY and symbol.symbol_type != SymbolType.UNOCCUPIED:
                return True
        return False

    @property
    def contract(self) -> ContractsUnions:
        symbols_dirs = self.get_all_symbol_types_and_directions()
        constraints, symbols = from_symbol_directions_to_constraints(symbols_dirs)

        """Creating Contracts"""
        contract_union = ContractsUnions()
        for constraint in constraints:
            # new_c = StrContract(assumptions=constraint, inputs=list(symbols))
            # new_c = StrContract(guarantees=constraint, outputs=list(symbols))
            # print(constraint)
            # io_contract = string_to_polyhedra_contract(new_c)

            io_contract = PolyhedralContract.from_string(
                OutputVars=list(symbols),
                InputVars=[],
                assumptions=[],
                guarantees=constraint)


            contract_union.contracts.add(io_contract)
        return contract_union

    def get_all_symbol_types_and_directions(self) -> dict[SymbolType, set[Direction]]:
        ret = {}
        for direction, symbol in self.__dict__.items():
            if direction == "ego":
                continue
            # if symbol.symbol_type == SymbolType.UNOCCUPIED:
            #     continue
            if symbol.symbol_type not in ret.keys():
                ret[symbol.symbol_type] = {getattr(Direction, direction)}
            else:
                ret[symbol.symbol_type].add(getattr(Direction, direction))
        return ret

    @property
    def plot(self) -> Figure:
        local_grid = DirectionsGrid(
            ego=symbols_colors[self.ego.symbol_type],
            front=symbols_colors[self.front.symbol_type],
            bottom=symbols_colors[self.bottom.symbol_type],
            left=symbols_colors[self.left.symbol_type],
            right=symbols_colors[self.right.symbol_type],
            top=symbols_colors[self.top.symbol_type],
            rear=symbols_colors[self.rear.symbol_type],
        )
        return local_grid.plot


class LooseEnds:
    def __init__(self):
        self.nodes: dict[Point, list[Point]] = {}
        self.keep: set[Point] = set()

    @property
    def leaves(self) -> set[Point]:
        ret = set()
        for node, nodes in self.nodes.items():
            if len(nodes) <= 1:
                ret.add(node)
        return ret

    @property
    def to_remove(self) -> set[Point]:
        for k in set(self.keep):
            if k in self.nodes.keys():
                if len(self.nodes[k]) == 1:
                    self.keep.remove(k)
        return set(self.nodes.keys()) - self.keep

    def add_node(self, value: Point):
        self.nodes[value] = []

    def add_edge(self, value1: Point, value2: Point):
        if value1 not in self.nodes.keys():
            self.nodes[value1] = []
        if value2 not in self.nodes.keys():
            self.nodes[value2] = []
        self.nodes[value1].append(value2)
        self.nodes[value2].append(value1)

    def delete_branch(self, leaf: Point):
        queue = [leaf]
        visited = set()
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in self.nodes[node]:
                self.nodes[neighbor].remove(node)
                if neighbor not in visited:
                    queue.append(neighbor)
        del self.nodes[leaf]

    def delete_branch_recursive(self, leaf: Point) -> set[Point]:
        removed_nodes = set()
        self._delete_branch_recursive(leaf, removed_nodes)
        return removed_nodes

    def _delete_branch_recursive(self, leaf: Point, removed_nodes: set):
        removed_nodes.add(leaf)
        if leaf not in self.nodes.keys():
            return
        for neighbor in self.nodes[leaf]:
            self.nodes[neighbor].remove(leaf)
            if neighbor not in removed_nodes and len(self.nodes[neighbor]) <= 1:
                self._delete_branch_recursive(neighbor, removed_nodes)
        del self.nodes[leaf]

    def get_edges(self) -> set[tuple[Point, Point]]:
        edges = set()
        for node in self.nodes:
            for neighbor in self.nodes[node]:
                edges.add((node, neighbor))
        return edges


@dataclass
class Connections:
    point_to_points: dict[Point, list[Point]] = field(default_factory=dict)

    def append(self, edge: Edge):
        if edge.s not in self.point_to_points.keys():
            self.point_to_points[edge.s] = []
        self.point_to_points[edge.s].append(edge.d)

    @property
    def edges(self) -> set[Edge]:
        edges = set()
        for point_a, to_points in self.point_to_points.items():
            for point_b in to_points:
                edges.add(Edge(point_a, point_b))
        return edges

    def remove_from_to_point(self, point: Point):
        for point_a, to_points in self.point_to_points.items():
            if point in to_points:
                self.point_to_points[point_a].remove(point)
        if point in self.point_to_points.keys():
            del self.point_to_points[point]


@dataclass
class GridBuilder:
    grid: dict[Point, Symbol]
    connections: Connections = field(default_factory=Connections)
    name: str = ""
    current_point: Point | None = None
    dimension: int = 0
    points_to_visit: set[Point] = field(default_factory=set)
    points_visited: set[Point] = field(default_factory=set)
    loose_ends: LooseEnds = field(default_factory=LooseEnds)
    leaves_connectors: set[Point] = field(default_factory=set)
    n_wings = 0
    n_rotors = 0
    grammar_string = ""

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

        return cls(grid=grid, current_point=current_node, dimension=dim, points_to_visit={current_node})

    @property
    def plot(self) -> Figure:
        node_xyz = []
        color_xyz = []
        for point, symbol in self.grid.items():
            node_xyz.append([point.x, point.y, point.z])
            color_xyz.append(symbols_colors[symbol.symbol_type])

        return plot_3d_grid(node_xyz, color_xyz)

    # def cleanup(self):
    #     to_remove: set[Point] = set()
    #
    #     for point_l in self.leaves_connectors:
    #         current_point = point_l
    #         while len(self.connections.point_to_points[current_point]) == 1:
    #             to_remove.add(current_point)
    #             current_point = self.connections.point_to_points[current_point][0]
    #
    #     for point, symbol in self.grid.items():
    #         if symbol.symbol_type == SymbolType.EMPTY or point in to_remove:
    #             self.grid[point] = Unoccupied()
    #             self.connections.remove_from_to_point(point)
    #             print(self.connections)
    #             print("")

    #
    # for edge in self.connections.point_to_points:
    #     if
    #     if point == edge.s or point == edge.d:
    #         to_remove_edges.add(edge)

    def cleanup(self):
        loose_ends = self.loose_ends.to_remove
        for point, symbol in self.grid.items():
            if symbol.symbol_type == SymbolType.EMPTY or point in loose_ends:
                self.grid[point] = Unoccupied()
                self.connections.remove_from_to_point(point)
                print(f"{point} removed")

    # def cleanup_loose_ends(self):
    #     """Remove loose ends and empty nodes"""
    #     removed: set[Point] = set()
    #     for point, symbol in self.grid.items():
    #         if symbol.symbol_type == SymbolType.EMPTY or point in self.loose_ends.to_remove:
    #             self.grid[point] = Unoccupied()
    #             removed.add(point)
    #     for point in removed:
    #         to_remove_edges: set[Edge] = set()
    #         for edge in self.connections.edges:
    #             if point == edge.s or point == edge.d:
    #                 to_remove_edges.add(edge)
    #         for edge in to_remove_edges:
    #             self.connections.remove(edge)
    #     for src, dest in self.loose_ends.get_edges():
    #         edge = Edge(src, dest)
    #         if edge in self.connections:
    #             self.connections.remove(edge)
    #         edge = Edge(dest, src)
    #         if edge in self.connections:
    #             self.connections.remove(edge)

    @property
    def plot_with_edges(self) -> Figure:
        node_xyz = []
        color_xyz = []

        for point, symbol in self.grid.items():
            if symbol.symbol_type is not SymbolType.UNOCCUPIED and symbol.symbol_type is not SymbolType.EMPTY:
                node_xyz.append([point.x, point.y, point.z])
                color_xyz.append(symbols_colors[symbol.symbol_type])

        edge_xyz = [((edge.s.x, edge.s.y, edge.s.z), (edge.d.x, edge.d.y, edge.d.z)) for edge in self.connections.edges]

        return plot_3d_grid(node_xyz, color_xyz, edge_xyz)

    def symbol(self, point: Point | None = None) -> Symbol:
        if point is None:
            point = self.current_point
        return self.grid[point]

    def update_current_point(self):
        """choose an 'unoccupied' point around the current_point"""
        # print(f"{len(self.points_to_visit)}")
        self.current_point = self.points_to_visit.pop()
        # # DEBUG
        # if len(self.points_to_visit) > 1:
        #     self.current_point = sorted(self.points_to_visit)[0]
        self.points_visited.add(self.current_point)
        # print(f"{len(self.points_to_visit)}")

    def apply_rule(self, rule: Rule):
        production = rule.production
        self.grammar_string = f"[{self.current_point}]({rule.name})"
        # print(self.current_point)

        if production.symbol_type == SymbolType.FUSELAGE:
            self.grid[self.current_point] = Fuselage()
        elif production.symbol_type == SymbolType.EMPTY:
            self.grid[self.current_point] = Empty()
            self.grid[self.current_point.x_symmetric] = Empty()
        elif production.symbol_type == SymbolType.ROTOR:
            self.grid[self.current_point] = Rotor()
            if self.current_point != self.current_point.x_symmetric:
                self.grid[self.current_point.x_symmetric] = Rotor()
                self.n_rotors += 1
            self.n_rotors += 1
        elif production.symbol_type == SymbolType.WING:
            self.grid[self.current_point] = Wing()
            if self.current_point != self.current_point.x_symmetric:
                self.grid[self.current_point.x_symmetric] = Wing()
                self.n_wings += 1
            self.n_wings += 1
        elif production.symbol_type == SymbolType.CONNECTOR:
            self.grid[self.current_point] = Connector()
            self.loose_ends.add_node(self.current_point)
            self.leaves_connectors.add(self.current_point)
            if self.current_point != self.current_point.x_symmetric:
                self.grid[self.current_point.x_symmetric] = Connector()
                self.loose_ends.add_node(self.current_point.x_symmetric)
                self.leaves_connectors.add(self.current_point.x_symmetric)

        else:
            raise AttributeError("SymbolNotSupported")

        def connect_points(src: Point, dest: Point):
            connection_1 = Edge(s=src, d=dest)
            if isinstance(self.grid[src], Connector):
                if isinstance(self.grid[dest], Connector):
                    self.loose_ends.add_edge(src, dest)
            else:
                if isinstance(self.grid[dest], Connector):
                    removed_nodes = self.loose_ends.delete_branch_recursive(dest)
                    self.loose_ends.keep |= removed_nodes

            self.connections.append(connection_1)

        if production.connection is not None:
            src = self.current_point
            dest = getattr(self.current_point, production.connection.name)
            connect_points(src, dest)
            src = self.current_point.x_symmetric
            dest = getattr(self.current_point.x_symmetric, production.connection.x_symmetric.name)
            connect_points(src, dest)

        """Update points to explore"""
        edge = self.dimension // 2
        unoccupied_points = set(
            filter(
                lambda p: isinstance(self.grid[p], Unoccupied)
                          and (abs(p.x) < edge and abs(p.y) < edge and abs(p.z) < edge)
                          and p not in self.points_visited,
                [p for p in self.current_point.symmetry_directions],
            )
        )

        # print(unoccupied_points)
        self.points_to_visit |= unoccupied_points
        self.plot_with_edges.show()

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
            rear=self.grid[point.rear],
        )


def delete_loose_end(graph: dict[Point, list[Point]], node: Point):
    for elem in graph[node]:
        delete_loose_end(graph, elem)


if __name__ == "__main__":
    new_grid = GridBuilder.generate(half_size=1)
    new_grid.plot.show()
    current_node_state = new_grid.local_state(new_grid.current_point)
    current_node_state.plot.show()
