

from pacti.contracts import PolyhedralIoContract
from pacti.utils.plots import plot_assumptions, plot_guarantees
from unittest.mock import patch


def test_plotguarantees():
    c = PolyhedralIoContract.from_strings(input_vars=["x"],
                                          output_vars=["y"],
                                          assumptions=["2x <= 4"],
                                          guarantees=["-4x + y <= 2"])
    with patch("pacti.utils.plots.plt.show") as show_pt:
        plot_assumptions(c)
        assert show_pt.called
        plot_guarantees(c)
        assert show_pt.call_count == 2