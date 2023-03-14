
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from typing import Tuple

def plot_steps(step_bounds : list[Tuple[float, float]], step_names : list[str], ylabel: str, title: str) -> Figure:
    vertices = []
    N = len(step_bounds)
    assert N == len(step_names)
    for i in range(N):
        vertices.append((i + 1, step_bounds[i][0]))
    for i in range(N):
        vertices.append((N - i, step_bounds[N-1-i][1]))
    x,y = zip(*vertices)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect="auto")
    x_lims = ax.get_xlim()
    y_lims = ax.get_ylim()
    ax.set_ylim(0, 100)
    ax.set_xticks(list(range(1,N+1)), labels=step_names, rotation=90)
    aspect = (x_lims[1] - x_lims[0]) / (y_lims[1] - y_lims[0])
    # print(aspect)
    #ax.set_aspect(aspect)
    plt.title(title)
    plt.xlabel('Sequence step')
    plt.ylabel(ylabel)
    plt.fill(x, y, facecolor="deepskyblue")
    return fig


if __name__ == "__main__":
    plot_steps([(1,2),(3,4),(0.3,0.7), (0.7, 0.9)], ["Step1", "Step2", "Step3", "Step4"])
    plt.show()