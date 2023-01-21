import matplotlib.pyplot as plt
import numpy as np
def display_sensor_contracts(sensor_input="u", output="y", leak=0.0, start=0.0, umin=0.0, ymin=0.0, 
                             K=0.0, ymax_lin=0.0, xlim_min=0.0, xlim_max=0.0,
                             ylim_min=0.0, ylim_max=0.0, show=True, ax=None):
    """
    Plot three contracts: lag, linear, saturation on a 2-D plane
    """
    if ax is None:
        _, ax = plt.subplots()
    slope = (ymax_lin - leak)/(K - start)
    intercept = leak - slope*start
    ax.hlines(y=leak, xmin=xlim_min, xmax=start, color='r', lw=2, ls='--', label='OFF')
    ax.axvline(x=start, ls='dotted', color='k')
    ax.plot(np.linspace(start, K,2), slope*np.linspace(start,K,2) + intercept, color='#006400', lw=2, label='Linear')
    ax.hlines(y=ymax_lin, xmin=K, xmax=xlim_max, color='blue', lw=2, ls='--', label='Saturation')
    ax.axvline(x=K, ls='dotted', color='k')
    ax.set_xlabel(sensor_input, fontsize=14)
    ax.set_xscale('log')
    ax.set_xlim(xlim_min, xlim_max)
    ax.set_ylabel(output, fontsize=14)
    ax.set_yscale('log')
    ax.set_ylim(ylim_min, ylim_max)
    ax.legend()
    if show:
        plt.show()
    return ax

import copy
def remove_quantization_errors(contract, tolerance = 1e-4):
    """
    Removes terms that have all coefficients lower than tolerance
    """
    from_contract = copy.deepcopy(contract)
    index = 0
    # Remove quantization error from assumptions
    for t_i in list(from_contract.a.terms):
        all_coeff = 0
        for var, coeff in t_i.variables.items():
            all_coeff += np.abs(coeff)
        if all_coeff < tolerance:
            from_contract.a.terms.remove(t_i)
        index += 1
    # Remove quantization error from guarantees
    index = 0
    for t_i in list(from_contract.g.terms):
        all_coeff = 0
        for var, coeff in t_i.variables.items():
            all_coeff += np.abs(coeff)
        if all_coeff < tolerance:
            from_contract.g.terms.remove(t_i)
        index += 1
    return from_contract