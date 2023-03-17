import matplotlib.pyplot as plt
import numpy as np
import copy
from typing import Union
from pacti.iocontract import IoContract


def display_sensor_contracts(
    sensor_input: str = "u",
    output: str = "y",
    leak: float = 0.0,
    start: float = 0.0,
    K: float = 0.0,
    ymax_lin: float = 0.0,
    xlim_min: float = 0.0,
    xlim_max: float = 0.0,
    ylim_min: float = 0.0,
    ylim_max: float = 0.0,
    show: bool = True,
    ax: Union[plt.Axes, None] = None,
) -> plt.Axes:
    """
    Plot three contracts: lag, linear, saturation on a 2-D plane

    Args:
        sensor_input (str, optional): Sensor input. Defaults to "u".
        output (str, optional): Sensor output. Defaults to "y".
        leak (float, optional): Leak value. Defaults to 0.0.
        start (float, optional): Start value at which linear regime starts.
                                 Defaults to 0.0.
        K (float, optional): Activation constant, also used as end of
                             linear regime. Defaults to 0.0.
        ymax_lin (float, optional): Maximum value of output at the end of
                                    linear regime. Defaults to 0.0.
        xlim_min (float, optional): Minimum limit for plot X axis.
                                    Defaults to 0.0.
        xlim_max (float, optional): Maximum limit for plot axes.
                                    Defaults to 0.0.
        ylim_min (float, optional): Minimum limit for plot Y axis.
                                    Defaults to 0.0.
        ylim_max (float, optional): Maximum limit for plot Y axis.
                                    Defaults to 0.0.
        show (bool, optional): Plot is displayed if True, and hidden if False.
                               Defaults to True.
        ax (Union[plt.Axes, None], optional): Matplotlib Axes object
                                              to use for plotting.
                                              Defaults to None.

    Returns:
        plt.Axes: The matplotlib.pyplot.Axes object
                  that consists of the figure data
    """
    if ax is None:
        _, ax = plt.subplots()
    slope = (ymax_lin - leak) / (K - start)
    intercept = leak - slope * start
    ax.hlines(y=leak, xmin=xlim_min, xmax=start, color="r",
              lw=2, ls="--", label="OFF")
    ax.axvline(x=start, ls="dotted", color="k")
    ax.plot(
        np.linspace(start, K, 2),
        slope * np.array(np.linspace(start, K, 2)) + intercept,
        color="#006400", lw=2, label="Linear"
    )
    ax.hlines(y=ymax_lin, xmin=K, xmax=xlim_max,
              color="blue", lw=2, ls="--", label="Saturation")
    ax.axvline(x=K, ls="dotted", color="k")
    ax.set_xlabel(sensor_input, fontsize=14)
    ax.set_xscale("log")
    ax.set_xlim(xlim_min, xlim_max)
    ax.set_ylabel(output, fontsize=14)
    ax.set_yscale("log")
    ax.set_ylim(ylim_min, ylim_max)
    ax.legend()
    if show:
        plt.show()
    return ax


def remove_quantization_errors(contract: IoContract,
                               tolerance: float = 1e-4) -> IoContract:
    """Removes quantization errors that creep in Pacti computations
       All terms that have coefficients lower than the specified `tolerance`
       are removed.
    Args:
        contract (IoContract): A contract (`pacti.iocontract.IoContract`)
                               object
        tolerance (float, optional): The tolerance value. Defaults to 1e-4.

    Returns:
        IoContract: Updated contract (`pacti.iocontract.IoContract`)
    """
    from_contract = copy.deepcopy(contract)
    index = 0
    # Remove quantization error from assumptions
    for t_i in list(from_contract.a.terms):
        all_coeff = 0
        for _, coeff in t_i.variables.items():
            all_coeff += np.abs(coeff)
        if all_coeff < tolerance:
            from_contract.a.terms.remove(t_i)
        index += 1
    # Remove quantization error from guarantees
    index = 0
    for t_i in list(from_contract.g.terms):
        all_coeff = 0
        for _, coeff in t_i.variables.items():
            all_coeff += np.abs(coeff)
        if all_coeff < tolerance:
            from_contract.g.terms.remove(t_i)
        index += 1
    return from_contract
