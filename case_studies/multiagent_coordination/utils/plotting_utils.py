"""Utility functions for plotting."""
import display
import matplotlib.pyplot as plt  # noqa: WPS301
import numpy as np
from IPython.display import HTML
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle, Rectangle
from utils.multiagent_utils import Coord, Robot


class Snapshot:
    """
    Snapshot class.

    Stores the timestep, the robots and their goals
    at the current time.
    """

    def __init__(self, timestep: int, robots: list[Robot], goals: list[Coord]):  # noqa: BLK100
        """
        Inititalize a snapshot.

        Args:
            timestep: Current timestep.
            robots: List of robots.
            goals: List of goals corresponding to the robots.

        """
        self.t = timestep
        self.robots = [Coord(robot) for robot in robots]
        self.goals = [Coord(goal) for goal in goals]


def save_trace(trace: list[Snapshot], robots: list[Robot], goal: list[Coord]) -> list[Snapshot]:
    """
    Save the current snapshot to the trace.

    Args:
        trace: List of snapshots from the simulation.
        robots: List of robots.
        goal: List of goals corresponding to the robots.

    Returns:
        The updated trace.
    """
    if trace:
        t = trace[-1].t + 1
    else:
        t = 0
    snap = Snapshot(t, robots, goal)
    trace.append(snap)
    return trace


def plot_grid_world(grid_n: int, grid_m: int, robots: list[Robot]) -> None:  # noqa: WPS231
    """
    Plot the grid world.

    Args:
        grid_n: Gridsize n.
        grid_m: Gridsize m.
        robots: List of robots.
    """
    gridsize = 10
    if len(robots) > 5:
        print("Need more colors!")

    colors = ["blue", "red", "orange", "yellow", "green"]
    color_map = {}
    for i, robot in enumerate(robots):
        color_map.update({robot: colors[i]})

    xs = np.linspace(0, grid_n * gridsize, grid_n + 1)
    ys = np.linspace(0, grid_m * gridsize, grid_m + 1)
    ax = plt.gca()

    w, h = xs[1] - xs[0], ys[1] - ys[0]
    for i, x in enumerate(xs[:-1]):
        for j, y in enumerate(ys[:-1]):
            if i % 2 == j % 2:
                ax.add_patch(Rectangle((x, y), w, h, fill=True, color="lemonchiffon"))
    for x in xs:
        plt.plot([x, x], [ys[0], ys[-1]], color="black", alpha=0.3)  # noqa: WPS432
    for y in ys:
        plt.plot([xs[0], xs[-1]], [y, y], color="black", alpha=0.3)  # noqa: WPS432

    for x in range(grid_n):  # plotting the goal positions first
        for y in range(grid_m):
            for robot in robots:
                if (x, y) == robot.goal.xy:  # noqa: WPS309
                    ax.add_patch(
                        Circle(
                            ((x + 0.5) * gridsize, (y + 0.5) * gridsize),  # noqa: BLK100
                            0.2 * gridsize,  # noqa: WPS432
                            color=color_map[robot],
                            alpha=0.3,  # noqa: WPS432
                        )
                    )

    for x in range(grid_n):
        for y in range(grid_m):
            for robot in robots:
                if (x, y) == robot.pos.xy:  # noqa: WPS309
                    ax.add_patch(
                        Circle(
                            ((x + 0.5) * gridsize, (y + 0.5) * gridsize),
                            0.2 * gridsize,  # noqa: WPS432
                            color=color_map[robot],
                            alpha=0.6,  # noqa: WPS432
                        )
                    )  # noqa: WPS432,WPS319

    ax.set_aspect("equal", "box")
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    plt.gca().invert_yaxis()
    plt.title("Grid World")
    plt.show()


def animate(trace: list[Snapshot], grid_n: int, grid_m: int, filename: str) -> None:  # noqa: WPS231
    """
    Animate the simulation trace and save in file.

    Args:
        trace: List of snapshots from the simulation.
        grid_n: Gridsize grid_n.
        grid_m: Gridsize grid_m.
        filename: Name of the file that will contain the video.
    """
    colors = ["blue", "red", "orange", "yellow", "green"]
    frames = len(trace)
    print("Rendering %d frames..." % frames)
    gridsize = 10

    # prepare the gridworld
    xs = np.linspace(0, grid_n * gridsize, grid_n + 1)
    ys = np.linspace(0, grid_m * gridsize, grid_m + 1)
    w, h = xs[1] - xs[0], ys[1] - ys[0]
    fig, ax = plt.subplots()

    ax.set_xlim(xs[0], grid_n * gridsize)
    ax.set_ylim(ys[0], grid_m * gridsize)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    def render_frame(i: int) -> None:  # noqa: WPS231,WPS430
        robots = trace[i].robots
        goals = trace[i].goals

        for i, x in enumerate(xs[:-1]):
            for j, y in enumerate(ys[:-1]):
                if i % 2 == j % 2:
                    ax.add_patch(Rectangle((x, y), w, h, fill=True, color="lemonchiffon"))
                else:
                    ax.add_patch(Rectangle((x, y), w, h, fill=True, color="white"))
        for x in xs:
            ax.plot([x, x], [ys[0], ys[-1]], color="black", alpha=0.3)  # noqa: WPS432
        for y in ys:
            ax.plot([xs[0], xs[-1]], [y, y], color="black", alpha=0.3)  # noqa: WPS432

        for x in range(grid_n):  # plot goals first
            for y in range(grid_m):
                for i, goal in enumerate(goals):
                    if (x, y) == goal.xy:  # noqa: WPS309
                        ax.add_patch(
                            Circle(
                                ((x + 0.5) * gridsize, (y + 0.5) * gridsize),
                                0.2 * gridsize,  # noqa: WPS432
                                color=colors[i],
                                alpha=0.3,  # noqa: WPS432
                            )
                        )  # noqa: WPS432,WPS319

        for x in range(grid_n):  # plot robots on top
            for y in range(grid_m):
                for i, robot in enumerate(robots):
                    if (x, y) == robot.xy:  # noqa: WPS309
                        ax.add_patch(
                            Circle(
                                ((x + 0.5) * gridsize, (y + 0.5) * gridsize),
                                0.2 * gridsize,  # noqa: WPS432
                                color=colors[i],
                                alpha=0.6,  # noqa: WPS432
                            )
                        )

        ax.set_aspect("equal", "box")

    anim = FuncAnimation(fig, render_frame, frames=frames, interval=1000, blit=False)

    anim.save(filename + ".mp4", fps=1)

    plt.close()
    display(HTML(anim.to_html5_video()))
