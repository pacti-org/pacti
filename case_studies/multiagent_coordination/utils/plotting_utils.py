import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from IPython.display import HTML
from matplotlib.patches import Circle, Rectangle
from utils.multiagent_utils import Coord


# snapshot of the simulation for a timestep
class Snapshot:
    def __init__(self, timestep, robots, goals):
        self.t = timestep
        self.robots = [Coord(robot) for robot in robots]
        self.goals = [Coord(goal) for goal in goals]


def save_trace(trace, robots, goal):
    if trace:
        t = trace[-1].t + 1
    else:
        t = 0
    snap = Snapshot(t, robots, goal)
    trace.append(snap)
    return trace


def plot_grid_world(n, m, robots):
    gridsize = 10
    r1 = robots[0]
    r2 = robots[1]
    if len(robots) > 5:
        print("Need more colors!")

    colors = ["blue", "red", "orange", "yellow", "green"]
    color_map = {}
    for i, robot in enumerate(robots):
        color_map.update({robot: colors[i]})

    xs = np.linspace(0, n * gridsize, n + 1)
    ys = np.linspace(0, m * gridsize, m + 1)
    ax = plt.gca()

    w, h = xs[1] - xs[0], ys[1] - ys[0]
    for i, x in enumerate(xs[:-1]):
        for j, y in enumerate(ys[:-1]):
            if i % 2 == j % 2:
                ax.add_patch(Rectangle((x, y), w, h, fill=True, color="lemonchiffon"))
    for x in xs:
        plt.plot([x, x], [ys[0], ys[-1]], color="black", alpha=0.3)
    for y in ys:
        plt.plot([xs[0], xs[-1]], [y, y], color="black", alpha=0.3)

    for x in range(n):  # plotting the goal positions first
        for y in range(m):
            for robot in robots:
                if (x, y) == robot.goal.xy:
                    ax.add_patch(
                        Circle(
                            ((x + 0.5) * gridsize, (y + 0.5) * gridsize),
                            0.2 * gridsize,
                            color=color_map[robot],
                            alpha=0.3,
                        )
                    )

    for x in range(n):
        for y in range(m):
            for robot in robots:
                if (x, y) == robot.pos.xy:
                    ax.add_patch(
                        Circle(
                            ((x + 0.5) * gridsize, (y + 0.5) * gridsize),
                            0.2 * gridsize,
                            color=color_map[robot],
                            alpha=0.6,
                        )
                    )

    ax.set_aspect("equal", "box")
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    plt.gca().invert_yaxis()
    plt.title("Grid World")
    plt.show()


def animate(trace, n, m, filename):
    colors = ["blue", "red", "orange", "yellow", "green"]
    frames = len(trace)
    print("Rendering %d frames..." % frames)
    gridsize = 10

    # prepare the gridworld
    xs = np.linspace(0, n * gridsize, n + 1)
    ys = np.linspace(0, m * gridsize, m + 1)
    w, h = xs[1] - xs[0], ys[1] - ys[0]
    fig, ax = plt.subplots()

    ax.set_xlim(xs[0], n * gridsize)
    ax.set_ylim(ys[0], m * gridsize)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    def render_frame(i):
        robots = trace[i].robots
        goals = trace[i].goals

        for i, x in enumerate(xs[:-1]):
            for j, y in enumerate(ys[:-1]):
                if i % 2 == j % 2:
                    ax.add_patch(Rectangle((x, y), w, h, fill=True, color="lemonchiffon"))
                else:
                    ax.add_patch(Rectangle((x, y), w, h, fill=True, color="white"))
        for x in xs:
            ax.plot([x, x], [ys[0], ys[-1]], color="black", alpha=0.3)
        for y in ys:
            ax.plot([xs[0], xs[-1]], [y, y], color="black", alpha=0.3)

        for x in range(n):  # plot goals first
            for y in range(m):
                for i, goal in enumerate(goals):
                    if (x, y) == goal.xy:
                        ax.add_patch(
                            Circle(
                                ((x + 0.5) * gridsize, (y + 0.5) * gridsize), 0.2 * gridsize, color=colors[i], alpha=0.3
                            )
                        )

        for x in range(n):  # plot robots on top
            for y in range(m):
                for i, robot in enumerate(robots):
                    if (x, y) == robot.xy:
                        ax.add_patch(
                            Circle(
                                ((x + 0.5) * gridsize, (y + 0.5) * gridsize), 0.2 * gridsize, color=colors[i], alpha=0.6
                            )
                        )

        ax.set_aspect("equal", "box")

    anim = matplotlib.animation.FuncAnimation(fig, render_frame, frames=frames, interval=1000, blit=False)

    anim.save(filename + ".mp4", fps=1)

    plt.close()
    display(HTML(anim.to_html5_video()))
