from typing import Union
from unittest.mock import patch

from pacti.contracts import PolyhedralIoContract
from pacti.iocontract import Var
from pacti.utils.plots import plot_assumptions, plot_guarantees

numeric = Union[int, float]


def test_plotguarantees() -> None:
    c = PolyhedralIoContract.from_strings(
        input_vars=["x"], output_vars=["y", "z"], assumptions=["2x <= 4"], guarantees=["-4x + y <= 2"]
    )
    with patch("pacti.utils.plots.plt.figure") as show_pt:
        plot_assumptions(c, "x", "y", {"z": 0}, (0, 1), (0, 1), show=True)
        assert show_pt.called
        plot_guarantees(c, Var("x"), "y", {Var("z"): 0}, (0, 1), (0, 1), show=True)
        assert show_pt.call_count == 2

        def x_transform(r: numeric, s: numeric) -> numeric:
            return r - s

        def y_transform(r: numeric, s: numeric) -> numeric:
            return r + s

        plot_guarantees(
            c,
            Var("x"),
            "y",
            {Var("z"): 0},
            (0, 1),
            (0, 1),
            show=True,
            new_x_var="a",
            new_y_var="b",
            x_transform=x_transform,
            y_transform=y_transform,
        )
        assert show_pt.call_count == 4


if __name__ == "__main__":
    test_plotguarantees()
