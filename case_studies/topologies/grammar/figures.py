from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

direction_to_coordinates = {
    "ego": [0, 0, 0],
    "front": [0, 1, 0],
    "bottom": [0, 0, -1],
    "left": [-1, 0, 0],
    "right": [1, 0, 0],
    "top": [0, 0, 1],
    "rear": [0, -1, 0],
}


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


def generate_empty_grid(size: int):
    node_xyz = []
    color_xyz = []
    for x in range(0, size + 1):
        for y in range(0, size + 1):
            for z in range(0, size + 1):
                node_xyz.append([x, y, z])
                color_xyz.append("white")

    return plot_3d_grid(np.array(node_xyz), np.array(color_xyz))


def plot_3d_grid(
        node_xyz: list | NDArray,
        color_xyz: list | NDArray,
        edge_xyz: list | NDArray = None,
) -> Figure:
    if isinstance(node_xyz, list):
        node_xyz = np.array(node_xyz)
    if isinstance(color_xyz, list):
        color_xyz = np.array(color_xyz)
    if isinstance(edge_xyz, list):
        edge_xyz = np.array(edge_xyz)

    # Create the 3D figure
    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")

    # Plot the nodes - alpha is scaled by "depth" automatically
    ax.scatter(*node_xyz.T, s=100, c=color_xyz, edgecolors="black", linewidth=1)

    # Plot the edges
    if edge_xyz is not None:
        for vizedge in edge_xyz:
            ax.plot(*vizedge.T, color="tab:gray")

    # Turn gridlines off
    ax.grid(True)
    # Suppress tick labels
    for dim in (ax.xaxis, ax.yaxis, ax.zaxis):
        dim.set_ticks([])
    # Set axes labels
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")

    fig.tight_layout()
    # fig.show()
    return fig


fig = generate_empty_grid(2)
# fig.savefig(f"grid4.pdf", transparent=True)
#
# g = DirectionsGrid()
# fig = g.plot
#
# fig.savefig(f"direction.pdf", transparent=True)
