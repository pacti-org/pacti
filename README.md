[![Build Status](https://github.com/pacti-org/pacti/actions/workflows/pacti_development.yml/badge.svg)](https://github.com/pacti-org/pacti/actions/workflows/pacti_development.yml)
[![PyPI version](https://badge.fury.io/py/Pacti.svg)](https://badge.fury.io/py/Pacti)
[![codecov](https://codecov.io/gh/pacti-org/pacti/branch/main/graph/badge.svg)](https://codecov.io/gh/pacti-org/pacti)
[![Getting Started With Pacti Example](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1muppEkj1K4vowBuS1C8plCouCdK50iio?usp=sharing)
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_white.png" width="250">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_colorful.png" width="250">
  <img alt="Pacti project logo." src="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_colorful.png" width="250">
</picture>

## Overview

Pacti is an open-source Python package for compositional system analysis and
design. It represents components with *assume-guarantee contracts*: assumptions
describe the environments in which a component promises to operate, and
guarantees describe what the component promises in those environments. Pacti
can compose component specifications, compute a missing component with
quotient, compare contracts by refinement, and diagnose incompatible
interconnections.

Pacti supports polyhedral contracts and typed GR(1) contracts. The GR(1)
extension is useful when requirements include state initialization, safety
conditions that hold at every step, recurring progress obligations, or a
bounded number of next-state references. Its Context-Aided Variable
Elimination (CAVE) procedures compute sound finite-window bounds while hiding
internal variables during contract operations.

## Installation

Pacti requires Python 3.11 or newer. Install the published package with:

```console
pip install pacti
```

Typed GR(1) contracts are available starting with Pacti 0.4.0. To run the
repository examples, clone this repository and run the commands from its root
using the environment where Pacti is installed.

`z3-solver` is a declared dependency and supplies the Python bindings used by
GR(1); no separate Z3 executable is needed. Spot, Docker, and PDM are not
required for normal contract use. See [Dependencies](#dependencies) for the
optional research and development tools.

## Quick start

This GR(1) example connects two Boolean components through an internal wire.
Each component copies its input to its output at every step; composition
eliminates the wire and computes the relation between request and response.

```python
from pacti.iocontract import GR1IoContract

def connector(input_name, output_name):
    return GR1IoContract.from_dict({
        "input_vars": [input_name],
        "output_vars": [output_name],
        "variable_sorts": {input_name: "bool", output_name: "bool"},
        "assumptions": {},
        "guarantees": {"inv": [f"{output_name} = {input_name}"]},
    })

producer = connector("request", "wire")
consumer = connector("wire", "response")
system = producer.compose(consumer)
print(system.g.to_pretty_string())
```

```text
INV:
  □(response = request)
```

The composed contract has input `request`, output `response`, and no
assumptions. See the [GR(1) getting started guide](docs/gr1-contracts.md) and
[example index](examples/README.md) for temporal requirements, quotient,
refinement, and larger systems. The executable
[quick start](examples/gr1_quickstart.py) also covers merge and serialization:

```console
python examples/gr1_quickstart.py
```

## Supported contract types and operations

- Polyhedral contracts express affine inequalities and support Pacti's
  established composition, quotient, merge, and refinement workflows.
- `GR1IoContract` supports Boolean, integer, and real interface variables;
  conjunctive INIT, invariant, and recurring-liveness buckets; bounded nested
  `X`; composition; quotient; merge; finite-certificate refinement; and
  lossless dictionary serialization.

The GR(1) implementation is not an arbitrary-LTL engine, controller
synthesizer, or complete GR(1) realizability/game solver. Boolean and linear
integer/real arithmetic are the validated solver scope. Solver `unknown` and
unsupported quantifier-elimination results raise an explicit error instead of
being treated as a proof.

Read the [GR(1) contracts guide](docs/gr1-contracts.md) for syntax, operation
semantics, and limitations. Refinement uses sound, incomplete finite-certificate
checks; see [Refinement](docs/gr1-contracts.md#refinement) for interpreting results.
The [AEB composition case study](examples/aeb_gr1_composition.py) computes a
system specification from supervisor and vehicle contracts. The
[manuscript example](examples/README.md#aeb-quotient-and-manuscript-example)
adds clearance prediction and the safety target `C_T`, and verifies the
quotient and target-refinement results from the [GR(1) paper](https://arxiv.org/abs/2610.37534).

## Dependencies

- **Core:** dependencies declared in `pyproject.toml`, including `z3-solver`,
  NumPy, SciPy, SymPy, Matplotlib, and the existing Pacti parser/runtime
  packages. `python -m pip install -e .` installs them.
- **Development:** PDM and the dependency groups in `pyproject.toml` provide
  pytest, coverage, mypy, Black, Flake8, notebook checks, and build tools. See
  [CONTRIBUTING.md](CONTRIBUTING.md).
- **Optional research:** Spot and its Buddy Python binding are used only by
  selected independent temporal checks. Do not install the unrelated package
  named `spot` from PyPI; follow the
  [official Spot installation instructions](https://spot.lre.epita.fr/install.html).
  Historical experiments and their container/data prerequisites are not
  needed for the public API examples.

## Development and testing

From the repository root in the configured development environment, run:

```console
make test
make check
```

`make test` runs the maintained pytest suite. `make check` runs source linting,
strict source type checking, notebook linting and type checking, executable
documentation/notebooks, and dependency vulnerability scanning. See
[CONTRIBUTING.md](CONTRIBUTING.md) for setup and CI details.

## Documentation, community, and citation

General Pacti documentation is available at [pacti.org](https://www.pacti.org).
Questions are welcome in the organization's
[GitHub Discussions](https://github.com/orgs/pacti-org/discussions), or by
email at info@pacti.org.

The Pacti project can be acknowledged by citing:

[Inigo Incer, Apurva Badithela, Josefine Graebener, Piergiuseppe Mallozzi, Ayush Pandey, Nicolas Rouquette, Sheng-Jung Yu, Albert Benveniste, Benoit Caillaud, Richard M. Murray, Alberto Sangiovanni-Vincentelli, and Sanjit A. Seshia.
"Pacti: Assume-Guarantee Contracts for Efficient Compositional Analysis and Design." ACM Transactions on Cyber-Physical Systems 9, no. 1 (2025): 1-35.](https://doi.org/10.1145/3704736)

[Yiğit Narter, Emily Zhao, and Inigo Incer.
"Computing GR(1) Assume-Guarantee Contracts." arXiv:2610.37534 (2026).](https://arxiv.org/abs/2610.37534)
