
import matplotlib.pyplot as plt
import numpy as np
from typing import Tuple

def plot_phases(phase_bounds : list[Tuple[float, float]], phase_names : list[str]):
    vertices = []
    N = len(phase_bounds)
    assert N == len(phase_names)
    for i in range(N):
        vertices.append((i + 1, phase_bounds[i][0]))
    for i in range(N):
        vertices.append((N - i, phase_bounds[N-1-i][1]))
    x,y = zip(*vertices)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect="auto")
    x_lims = ax.get_xlim()
    y_lims = ax.get_ylim()
    ax.set_xticks(list(range(1,N+1)), labels=phase_names, rotation=90)
    aspect = (x_lims[1] - x_lims[0]) / (y_lims[1] - y_lims[0])
    print(aspect)
    #ax.set_aspect(aspect)
    plt.fill(x, y, facecolor="deepskyblue")
    return fig


if __name__ == "__main__":
    plot_phases([(1,2),(3,4),(0.3,0.7), (0.7, 0.9)], ["Phase1", "Phase2", "Phase3", "Phase4"])
    plt.show()