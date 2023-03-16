
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from typing import Tuple

def plot_steps(step_bounds : list[Tuple[float, float]], step_names : list[str], ylabel: str, title: str, text: str) -> Figure:
    vertices = []
    N = len(step_bounds)
    assert N == len(step_names)
    for i in range(N):
        vertices.append((i + 1, step_bounds[i][0]))
    for i in range(N):
        vertices.append((N - i, step_bounds[N-1-i][1]))
    x,y = zip(*vertices)
    fig = plt.figure()
    ax1 = fig.add_subplot(1, 2, 1, aspect="auto")
    x_lims = ax1.get_xlim()
    y_lims = ax1.get_ylim()
    ax1.set_ylim(0, 120)
    ax1.set_xticks(list(range(1,N+1)), labels=step_names, rotation=90)
    aspect = (x_lims[1] - x_lims[0]) / (y_lims[1] - y_lims[0])
    # print(aspect)
    #ax.set_aspect(aspect)

    plt.title(title)
    plt.xlabel('Sequence step')
    plt.ylabel(ylabel)
    plt.fill(x, y, facecolor="deepskyblue")

    ax2 = fig.add_subplot(1, 2, 2, aspect="auto")
    # # Build a rectangle in axes coords
    left, width = 0, 1
    bottom, height = 0, 1
    right = left + width
    top = bottom + height
    p = plt.Rectangle((left, bottom), width, height, fill=False)
    p.set_transform(ax2.transAxes)
    p.set_clip_on(False)
    ax2.add_patch(p)

    ax2.text(0.5 * (left + right), 0.5 * (bottom + top), text,
        horizontalalignment='center',
        verticalalignment='center',
        transform=ax2.transAxes)
    ax2.set_axis_off()

    return fig


if __name__ == "__main__":
    plot_steps([(1,2),(3,4),(0.3,0.7), (0.7, 0.9)], ["Step1", "Step2", "Step3", "Step4"])
    plt.show()