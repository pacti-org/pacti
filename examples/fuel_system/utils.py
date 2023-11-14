from pacti.terms.polyhedra import PolyhedralTerm, PolyhedralTermList
from pacti.contracts import PolyhedralIoContract
from pacti.iocontract import Var
from typing import Dict, List, Optional, Tuple, Union
from pacti import write_contracts_to_file
import pacti.utils.plots as plh_plots
import matplotlib.pyplot as plt
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Polygon as MplPatchPolygon
from matplotlib.axes import Axes
import numpy as np
import operator
import sys
import re
from typing import Optional
from collections import Counter


from scipy.spatial import QhullError


# cpu_info_message = f"{cpu_info['brand_raw']} @ {cpu_info['hz_advertised_friendly']} with up to {cpu_info['count']} threads."

tuple2float = Tuple[float, float]
numeric = Union[int, float]
tuple2 = Tuple[Optional[numeric], Optional[numeric]]

def check_tuple(t: tuple2) -> tuple2float:
    if t[0] is None:
        a = -1.0
    else:
        a = t[0]
    if t[1] is None:
        b = -1.0
    else:
        b = t[1]
    return (a, b)

def get_numerical_bounds(c: PolyhedralIoContract, var: str) -> tuple2float:
    return check_tuple(c.get_variable_bounds(var))

def nochange_contract(step: int, name: str) -> PolyhedralIoContract:
    """
    Constructs a no-change contract between entry/exit variables derived from the name and step index.

    Args:
        s: step index
        name: name of the variable

    Returns:
        A no-change contract.
    """
    return PolyhedralIoContract.from_strings(
        input_vars=[f"{name}{step}_entry"],
        output_vars=[f"{name}{step}_exit"],
        assumptions=[
            f"0 <= {name}{step}_entry"
        ],
        guarantees=[
            f"{name}{step}_exit = {name}{step}_entry"
        ],
    )
    
def scenario_sequence(
    c1: PolyhedralIoContract,
    c2: PolyhedralIoContract,
    variables: List[str],
    c1index: int,
    c2index: Optional[int] = None,
    file_name: Optional[str] = None,
    tactics_order: Optional[List[int]] = None
) -> Tuple[PolyhedralIoContract, List[List[Tuple[int, float, int]]]]:
    """
    Composes c1 with a c2 modified to rename its entry variables according to c1's exit variables

    Args:
        c1: preceding step in the scenario sequence
        c2: next step in the scenario sequence
        variables: list of entry/exit variable names for renaming
        c1index: the step number for c1's variable names
        c2index: the step number for c2's variable names; defaults ti c1index+1 if unspecified

    Returns:
        c1 composed with a c2 modified to rename its c2index-entry variables
        to c1index-exit variables according to the variable name correspondences
        with a post-composition renaming of c1's exit variables to fresh outputs
        according to the variable names.
    """
    if not c2index:
        c2index = c1index + 1
    c2_inputs_to_c1_outputs = [(f"{v}{c2index}_entry", f"{v}{c1index}_exit") for v in variables]
    keep_c1_outputs = [f"{v}{c1index}_exit" for v in variables]
    renamed_c1_outputs = [(f"{v}{c1index}_exit", f"output_{v}{c1index}") for v in variables]

    c2_with_inputs_renamed = c2.rename_variables(c2_inputs_to_c1_outputs)
    c12_with_outputs_kept, tactics = c1.compose_tactics(c2_with_inputs_renamed, vars_to_keep=keep_c1_outputs, simplify=False, tactics_order=tactics_order)
    c12 = c12_with_outputs_kept.rename_variables(renamed_c1_outputs)

    if file_name:
        write_contracts_to_file(
            contracts=[c1, c2_with_inputs_renamed, c12_with_outputs_kept],
            names=["c1", "c2_with_inputs_renamed", "c12_with_outputs_kept"],
            file_name=file_name,
        )

    return c12, tactics

def bound(c: PolyhedralIoContract, var: str) -> Tuple[str, str]:
    """
    Get the bounds on a contract variable, distinguishing among three
    outcomes: a numerical bound, no bounds, and errors interpreted as unknown bounds.

    Args:
        c: PolyhedralIoContract
            A Pacti contract

        var: str
            The name of a contract variable of c.

    Returns:
        A tuple with the string representation of the variable lower and upper bounds.
        A bound is either the string representation of a floating point number (up to 2 decimals)
        or None if there is no bound.
    """
    try:
        b = c.get_variable_bounds(var)
        if isinstance(b[0], float):
            low = f"{b[0]:.2f}"
        else:
            low = "None"
        if isinstance(b[1], float):
            high = f"{b[1]:.2f}"
        else:
            high = "None"
        return low, high
    except ValueError:
        return "unknown", "unknown"


def bounds(c: PolyhedralIoContract) -> List[str]:
    """
    Produces the list of input and output variable bounds for a contract.

    Args:
        c: PolyhedralIoContract
            A Pacti contract

    Returns:
        The list of bounds for all input variables followed by those for the output variables.
    """
    bounds = []
    for v in sorted(c.inputvars, key=operator.attrgetter("name")):
        low, high = bound(c, v.name)
        bounds.append(f" input {v.name} in [{low},{high}]")

    for v in sorted(c.outputvars, key=operator.attrgetter("name")):
        low, high = bound(c, v.name)
        bounds.append(f"output {v.name} in [{low},{high}]")

    return bounds


def polyhedral_term_key(t: PolyhedralTerm) -> str:
    """
    Produces a key for sorting a PolyhedralTerm

    Args:
        t: PolyhedralTerm
            A term.

    Returns:
        The term's sorting key as the concatenation of its sorted variable names.
    """
    return ",".join(sorted([v.name for v in t.vars]))


def show_termlist(tl: PolyhedralTermList) -> str:
    """
    Produces a human-friendly string representation of a PolyhedralTermList.

    Sorting the terms by the variables involved makes reading a term list easier
    and facilitates comparing term lists.
    Args:
        tl: PolyhedralTermList
            A term list

    Returns:
        The string representation of the term list based on sorting the individual terms by their variables.
    """
    return f"{str(PolyhedralTermList(sorted(tl.terms, key=polyhedral_term_key)))}"


def show_contract(c: PolyhedralIoContract) -> str:
    """
    Produces a human-friendly string representation of a PolyhedralIoContract.

    Args:
        c: PolyhedralIoContract
            A contract.

    Returns:
        The string representation of the contract based on sorting input and output variables
        and the assumption and guarantee term lists.
    """
    buff = ""
    inputs = sorted([v.name for v in c.inputvars])
    buff += "Inputs : [" + ",".join(inputs) + "]\n"
    outputs = sorted([v.name for v in c.outputvars])
    buff += "Outputs: [" + ",".join(outputs) + "]\n"
    a = sorted(c.a.terms, key=polyhedral_term_key)
    buff += "A: " + "\n\t".join([str(PolyhedralTermList(a))]) + "\n"
    g = sorted(c.g.terms, key=polyhedral_term_key)
    buff += "G: " + "\n\t".join([str(PolyhedralTermList(g))]) + "\n"

    return buff


def get_bounds(ptl: PolyhedralTermList, var: str) -> Tuple[float, float]:
    """
    Get the bounds on a polyhedral term list variable, with errors interpreted
    as minimum or maximum possible values.

    Args:
        ptl: PolyhedralTermList
            A polyhedral term list.

        var: str
            A variable name.

    Returns:
        A tuple of floating point numbers for the minimum and maximum value of the named variable.
    """
    try:
        min = ptl.optimize(objective={Var(var): 1}, maximize=False)
    except ValueError:
        min = sys.float_info.min

    if min is None:
        min = sys.float_info.min

    try:
        max = ptl.optimize(objective={Var(var): 1}, maximize=True)
    except ValueError:
        max = sys.float_info.max

    if max is None:
        max = sys.float_info.max

    return min, max


def calculate_output_bounds_for_input_value(
    ptl: PolyhedralTermList, inputs: Dict[Var, float], output: Var
) -> Tuple[float, float]:
    """
    Get the bounds for an output variable of a polyhedral term list
    in the context of values for input variables,
    with errors interpreted as minimum or maximum possible values.

    Args:
        ptl: PolyhedralTermList
            A polyhedral term list.

        inputs: Dict[Var, float]
            Values for input variables of the polyhedral term list.

        var: str
            A variable name.

    Returns:
        A tuple of floating point numbers for the minimum and maximum value of the named variable.

    """
    return get_bounds(ptl.evaluate(inputs).simplify(), output.name)


# Add a callback function for the mouse click event
def _on_hover(ptl: PolyhedralTermList, x_var: Var, y_var: Var, fig, ax: Axes, event):
    if event.inaxes == ax:
        x_coord, y_coord = event.xdata, event.ydata
        y_min, y_max = calculate_output_bounds_for_input_value(
            ptl, {x_var: x_coord}, y_var
        )
        ax.set_title(
            f"@ {x_var.name}={x_coord:.2f}\n{y_min:.2f} <= {y_var.name} <= {y_max:.2f}"
        )
        fig.canvas.draw_idle()

def _on_hovers(ptls: List[PolyhedralTermList], x_var: Var, y_vars: List[Var], fig, axl: List[Axes], event):
    if event.inaxes in axl:
        x_coord = event.xdata
        for i, ax in enumerate(axl):
            y_min, y_max = calculate_output_bounds_for_input_value(
                ptls[i], {x_var: x_coord}, y_vars[i]
            )
            axl[i].set_title(
                f"@ {x_var.name}={x_coord:.2f}\n{y_min:.2f} <= {y_vars[i].name} <= {y_max:.2f}"
            )
        fig.canvas.draw_idle()


def plot_input_output_polyhedral_term_list(
    ptl: PolyhedralTermList, x_var: Var, y_var: Var
) -> MplFigure:
    """
    In a Jupyter notebook, show a 2-D plot of the input/output relationship
    among variables of a polyhedral term list.

    Clicking in an area of the 2-D plot shows the bounds of the output variable
    corresponding to the value of the input variable corresponding to the location
    of the mouse click.

    Args:
        ptl: PolyhedralTermList
            A polyhedral term list of two variables only: x_var and y_var.

        x_var: Var
            The input variable.

        y_var: Var
            The output variable.

    Returns:
        A 2-D plot figure for interactive visualization in a Jupyter notebook.
    """
    x_lims = get_bounds(ptl, x_var.name)
    y_lims = get_bounds(ptl, y_var.name)
    res_tuple = PolyhedralTermList.termlist_to_polytope(ptl, PolyhedralTermList([]))
    # variables = res_tuple[0]
    a_mat = res_tuple[1]
    b = res_tuple[2]

    x, y = plh_plots._get_bounding_vertices(a_mat, b)

    # generate figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, aspect="equal")
    ax.set_xlim(x_lims)
    ax.set_ylim(ymin=y_lims[0], ymax=y_lims[1])
    ax.set_xlabel(x_var.name)
    ax.set_ylabel(y_var.name)
    ax.set_aspect((x_lims[1] - x_lims[0]) / (y_lims[1] - y_lims[0]))

    poly = MplPatchPolygon(
        xy=np.column_stack([x, y]).tolist(),
        # xy=np.column_stack([x, y]).flatten().tolist(),
        animated=False,
        closed=True,
        facecolor="deepskyblue",
        edgecolor="deepskyblue",
    )
    ax.add_patch(poly)

    # Connect the event to the callback function
    fig.canvas.mpl_connect(
        "button_press_event", lambda event: _on_hover(ptl, x_var, y_var, fig, ax, event)
    )

    return fig


def retain_constraints_involving_variables(
    ptl: PolyhedralTermList, vs: List[Var]
) -> PolyhedralTermList:
    """
    Retain only the constraints (terms) involving all variables in the provided list.

    Args:
        ptl: PolyhedralTermList
            The initial polyhedral term list.

        vs: List[Var]
            List of variables. Only terms involving all variables from this list are retained.

    Returns:
        A new PolyhedralTermList containing only the terms involving all variables from the list.
    """
    ts = []
    for term in ptl.terms:
        if all(term.contains_var(var_to_seek=v) for v in vs):
            ts.append(term)
        elif any(term.contains_var(var_to_seek=v) for v in vs) and all(
            v in vs for v in term.variables.keys()
        ):
            ts.append(term)

    return PolyhedralTermList(terms=ts)


def plot_input_outputs_polyhedral_term_list(
    ptl: PolyhedralTermList, x_var: Var, y_vars: List[Var]
) -> MplFigure:
    """
    In a Jupyter notebook, show a 2-D plot of the input/output relationship
    among variables of a polyhedral term list.

    Clicking in an area of the 2-D plot shows the bounds of the output variable
    corresponding to the value of the input variable corresponding to the location
    of the mouse click.

    Args:
        ptl: PolyhedralTermList
            A polyhedral term list of two variables only: x_var and y_var.

        x_var: Var
            The input variable.

        y_vars: Var
            The output variables.

    Returns:
        A stacked figure of a 2-D plot figure for each output variable
        as a function of the input variable.

        This stacked figure supports interactive visualization in a Jupyter notebook.
    """
    num_plots = len(y_vars)
    x_lims = get_bounds(ptl, x_var.name)

    fig, axs = plt.subplots(
        nrows=num_plots, ncols=1, 
        figsize=(6, 4 * num_plots), 
        constrained_layout=True
    )

    ptls: List[PolyhedralTermList] = []
    axl: List[Axes] = []
    for i, y_var in enumerate(y_vars):
        y_ptl: PolyhedralTermList = retain_constraints_involving_variables(
            ptl, [x_var, y_var]
        )
        ptls.append(y_ptl)
        y_lim: Tuple[float, float] = get_bounds(y_ptl, y_var.name)

        res_tuple = PolyhedralTermList.termlist_to_polytope(
            y_ptl, PolyhedralTermList([])
        )
        # variables = res_tuple[0]
        a_mat: np.ndarray = res_tuple[1]
        b: np.ndarray = res_tuple[2]

        try:
            x, y = plh_plots._get_bounding_vertices(a_mat, b)

            ax: Axes = axs if num_plots == 1 else axs[i]
            ax.set_xlim(x_lims)
            ax.set_ylim(ymin=y_lim[0], ymax=y_lim[1])
            ax.set_xlabel(x_var.name)
            ax.set_ylabel(y_var.name)
            ax.set_aspect((x_lims[1] - x_lims[0]) / (y_lim[1] - y_lim[0]))

            poly = MplPatchPolygon(
                xy=np.column_stack([x, y]).tolist(),
                # xy=np.column_stack([x, y]).flatten().tolist(),
                animated=False,
                closed=True,
                facecolor="deepskyblue",
                edgecolor="deepskyblue",
            )
            ax.add_patch(poly)
            axl.append(ax)
        except QhullError as e:
            print(f"x_var: {x_var.name}, y_var: {y_var.name}")
            print(f"term list\n" + show_termlist(y_ptl))
            print(f"QhullError: {e}")
            pass
        except IndexError as e:
            print(f"x_var: {x_var.name}, y_var: {y_var.name}")
            print(f"term list\n" + show_termlist(y_ptl))
            print(f"IndexError: {e}")
            pass

    # Connect the event to the callback function
    fig.canvas.mpl_connect(
        "button_press_event", lambda event: _on_hovers(ptls, x_var, y_vars, fig, axl, event)
    )

    return fig

def plot_steps(
    step_bounds: List[Tuple[float, float]], step_names: List[str], ylabel: str, title: str, text: str, nth_tick: int = 1
) -> MplFigure:
    """
    Create a two-panel plot (two subplots) where the left panel displays a filled polygon representing the input data,
    and the right panel displays some text.

    Args:
        step_bounds:
            A list of tuples, each containing two float values representing the lower and upper bounds of a step.
        step_names:
            A list of strings representing the names of the steps.
        ylabel:
            A string representing the label for the y-axis.
        title:
            A string representing the title of the plot.
        text:
            A string representing the text to be displayed in the right panel.
        nth_tick:
            Show step names at every nth tick

    Returns:
        A two-panel plot figure.
    """
    assert nth_tick >= 1
    assert nth_tick < len(step_names)

    vertices = []
    N = len(step_bounds)
    assert N == len(step_names)
    for i in range(N):
        vertices.append((i + 1, step_bounds[i][0]))
    for i in range(N):
        vertices.append((N - i, step_bounds[N - 1 - i][1]))
    x, y = zip(*vertices)

    fig = plt.figure()
    ax1: Axes = fig.add_subplot(1, 2, 1, aspect="auto")

    y_min = min(min(bounds) for bounds in step_bounds)
    y_max = max(max(bounds) for bounds in step_bounds)

    ax1.set_ylim(y_min, y_max)

    ax1.set_xticks(range(1, N + 1)[::nth_tick], step_names[::nth_tick], rotation=90, ha="right")

    plt.title(title)
    plt.xlabel("Sequence step")
    plt.ylabel(ylabel)
    plt.fill(x, y, facecolor="deepskyblue")

    ax2 = fig.add_subplot(1, 2, 2, aspect="auto")
    # Build a rectangle in axes coords
    left, width = 0, 1
    bottom, height = 0, 1
    right = left + width
    top = bottom + height
    p = plt.Rectangle((left, bottom), width, height, fill=False)
    p.set_transform(ax2.transAxes)
    p.set_clip_on(False)
    ax2.add_patch(p)

    ax2.text(
        x=0,
        y=0.5 * (bottom + top),
        s=text,
        horizontalalignment="left",
        verticalalignment="center",
        transform=ax2.transAxes,
        fontdict={"family": "monospace", "size": 8},
    )
    ax2.set_axis_off()

    return fig

def plot_steps0(
    step_bounds: List[Tuple[float, float]], step_names: List[str], ylabel: str, title: str, text: str, nth_tick: int = 1
) -> MplFigure:
    """
    Create a two-panel plot (two subplots) where the left panel displays a filled polygon representing the input data,
    and the right panel displays some text.

    Args:
        step_bounds:
            A list of tuples, each containing two float values representing the lower and upper bounds of a step.
        step_names:
            A list of strings representing the names of the steps.
        ylabel:
            A string representing the label for the y-axis.
        title:
            A string representing the title of the plot.
        text:
            A string representing the text to be displayed in the right panel.
        nth_tick:
            Show step names at every nth tick

    Returns:
        A two-panel plot figure.
    """
    assert nth_tick >= 1
    assert nth_tick < len(step_names)

    vertices = []
    N = len(step_bounds)
    assert N == len(step_names)
    for i in range(N):
        vertices.append((i + 1, step_bounds[i][0]))
    for i in range(N):
        vertices.append((N - i, step_bounds[N - 1 - i][1]))
    x, y = zip(*vertices)

    fig = plt.figure()
    ax1: Axes = fig.add_subplot(1, 2, 1, aspect="auto")
    ax1.set_ylim(0, 120)

    ax1.set_xticks(range(1, N + 1)[::nth_tick], step_names[::nth_tick], rotation=90, ha="right")

    plt.title(title)
    plt.xlabel("Sequence step")
    plt.ylabel(ylabel)
    plt.fill(x, y, facecolor="deepskyblue")

    ax2 = fig.add_subplot(1, 2, 2, aspect="auto")
    # Build a rectangle in axes coords
    left, width = 0, 1
    bottom, height = 0, 1
    right = left + width
    top = bottom + height
    p = plt.Rectangle((left, bottom), width, height, fill=False)
    p.set_transform(ax2.transAxes)
    p.set_clip_on(False)
    ax2.add_patch(p)

    ax2.text(
        x=0,
        y=0.5 * (bottom + top),
        s=text,
        horizontalalignment="left",
        verticalalignment="center",
        transform=ax2.transAxes,
        fontdict={"family": "monospace", "size": 8},
    )
    ax2.set_axis_off()

    return fig

def add_constant_and_replace(s: str, constant: int) -> str:
    def replacer(match):
        # Extract the number from the match, add the constant, and return the new number as a string
        return str(int(match.group(0)) + constant)
    
    # Use re.sub with a function as the replacement argument
    return re.sub(r'\d+', replacer, s)

def contract_shift(c: PolyhedralIoContract, offset: int) -> PolyhedralIoContract:
    a_vars, a_a, a_b, _, _ = PolyhedralTermList.termlist_to_polytope(c.a, PolyhedralTermList())
    a_renamed = [Var(add_constant_and_replace(s=v.name, constant=offset)) for v in a_vars]
    a_shifted = PolyhedralTermList.polytope_to_termlist(a_a, a_b, a_renamed)
    
    g_vars, g_a, g_b, _, _ = PolyhedralTermList.termlist_to_polytope(c.g, PolyhedralTermList())
    g_renamed = [Var(add_constant_and_replace(s=v.name, constant=offset)) for v in g_vars]
    g_shifted = PolyhedralTermList.polytope_to_termlist(g_a, g_b, g_renamed)
    
    inputs_shifted = [Var(add_constant_and_replace(s=v.name, constant=offset)) for v in c.inputvars]
    outputs_shifted = [Var(add_constant_and_replace(s=v.name, constant=offset)) for v in c.outputvars]
    
    return PolyhedralIoContract(a_shifted, g_shifted, inputs_shifted, outputs_shifted)

def contract_statistics(c: PolyhedralIoContract) -> Tuple[float, List[Tuple[int, int]]]:
    """For a given contract, calculate summary statistics about its assumptions and guarantees.
    
    Args:
        c: PolyhedralIoContract
        
    Returns:
        A tuple of:
        - the density of the variables used in the assumption and guarantee constraints;
        - the list of the count of constraints using a given number of variables, sorted by count.
    """
    terms: List[PolyhedralTerm] = c.a.terms + c.g.terms
    nvars: int = len(c.vars)
    counts: List[int] = [len(t.vars) for t in terms]
    density: float = sum(counts) / ( nvars * len(terms) )
    
    # Use Counter to count occurrences of each value in counts
    count_occurrences = Counter(counts)
    
    # Convert Counter to sorted list of tuples
    sorted_counts = sorted(count_occurrences.items(), reverse=True)
    
    return density, sorted_counts