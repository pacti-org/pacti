from pathlib import Path

from gear.utils.string_contract import StrContract

# match_LTL_no_spaces = r"((?<=[G|F|X])(?=[^\s]))|((?<=[U])(?=[a-z]))|(?=[U])+(?<=[a-z])"
# #  LTL to LateX
# spot_f = spot.formula(str(formula))._repr_latex_()


ASSUMPTIONS_HEADER = "ASSUMPTIONS"
GUARANTEES_HEADER = "GUARANTEES"
INS_HEADER = "INPUTS"
OUTS_HEADER = "OUTPUTS"
HEADERS = {ASSUMPTIONS_HEADER, GUARANTEES_HEADER, INS_HEADER, OUTS_HEADER}
END_CONTRACT = "--"
COMMENT_CHAR = "#"
DATA_INDENT = 1


def parse_contracts(
    file_path: Path,
) -> list[StrContract]:
    """Returns: assumptions, guarantees, inputs, outputs"""

    contracts: list[StrContract] = []

    assumptions = []
    guarantees = []
    inputs = []
    outputs = []

    with open(file_path) as ifile:
        current_header = ""

        for line in ifile:
            line = strip(line)

            # skip empty lines
            if not line:
                continue

            if line == END_CONTRACT:
                current_header = ""
                contracts.append(
                    StrContract(assumptions=assumptions, guarantees=guarantees, inputs=inputs, outputs=outputs)
                )
                assumptions = []
                guarantees = []
                inputs = []
                outputs = []
                continue

            if line in HEADERS:
                current_header = line
                continue

            if current_header == ASSUMPTIONS_HEADER:
                assumptions.append(line)
            elif current_header == GUARANTEES_HEADER:
                guarantees.append(line)
            elif current_header == INS_HEADER:
                inputs.append(line)
            elif current_header == OUTS_HEADER:
                outputs.extend([l.strip() for l in line.split(",")])
            else:
                raise Exception("Header not supported")

    return contracts


def strip(line: str) -> str:
    """Returns a comment-free, stripped string"""

    line = line.split(COMMENT_CHAR, 1)[0]
    return line.strip()
