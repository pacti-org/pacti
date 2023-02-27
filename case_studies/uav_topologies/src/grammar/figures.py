from dataclasses import dataclass

import numpy as np
from ..shared import direction_to_coordinates

from ..tools.plotting import plot_3d_grid


@dataclass
class DirectionsGrid:
    ego: str = "yellow"
    front: str = "white"
    bottom: str = "white"
    left: str = "white"
    right: str = "white"
    top: str = "white"
    rear: str = "white"

    @property
    def plot(self):
        nodes = list(direction_to_coordinates.values())
        colors = [self.ego, self.front, self.bottom, self.left, self.right, self.top, self.rear]

        node_xyz = np.array(nodes)
        color_xyz = np.array(colors)
        edges = np.array(
            [
                [direction_to_coordinates["rear"], direction_to_coordinates["front"]],
                [direction_to_coordinates["top"], direction_to_coordinates["bottom"]],
                [direction_to_coordinates["left"], direction_to_coordinates["right"]],
            ]
        )

        return plot_3d_grid(node_xyz, color_xyz, edges)
