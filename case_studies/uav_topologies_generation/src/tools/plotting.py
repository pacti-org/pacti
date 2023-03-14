import numpy as np
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from numpy.typing import NDArray


def generate_empty_grid(n_half: int):
    node_xyz = []
    color_xyz = []
    for x in range(0, n_half * 2 + 1):
        for y in range(0, n_half * 2 + 1):
            for z in range(0, n_half * 2 + 1):
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


if __name__ == "__main__":
    # g = generate_empty_grid(1)
    # g.savefig("empty_1", format="svg")
    new_grid = GridBuilder.generate(half_size=1)
    # new_grid.plot.show()
    current_node_state = new_grid.local_state(new_grid.current_point)
    current_node_state.plot.savefig("local_state", format="svg")
