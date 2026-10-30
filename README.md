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

Pacti requires Python 3.10 or newer. Check the interpreter before creating an
isolated environment:

```console
python3 --version
git clone https://github.com/pacti-org/pacti.git
cd pacti
git switch feature/gr1-contracts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -c "from pacti.iocontract import GR1IoContract; print('GR(1) import: OK')"
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1`. The branch-selection command is temporary while
the GR(1) pull request is under review. The currently published PyPI package
may not yet contain `GR1IoContract`; until a release containing this work is
announced, install the feature branch or a local checkout as shown above.

`z3-solver` is a declared dependency and supplies the Python bindings used by
GR(1); no separate Z3 executable is needed. Spot, Docker, and PDM are not
required for normal contract use. See [Dependencies](#dependencies) for the
optional research and development tools.

## Quick start

This standalone example declares a Boolean request/grant contract. Environment
assumptions may mention only inputs; guarantees may relate inputs and outputs.
The three buckets mean “initially,” “at every step,” and “infinitely often.”
`X(grant)` denotes the grant value at the next step.

```python
from pacti.iocontract import GR1IoContract

request_grant = GR1IoContract.from_dict({
    "input_vars": ["request"],
    "output_vars": ["grant"],
    "variable_sorts": {"request": "bool", "grant": "bool"},
    "assumptions": {
        "init": ["!request"],
        "liv": ["request"],
    },
    "guarantees": {
        "init": ["!grant"],
        "inv": ["request -> X(grant)"],
        "liv": ["grant"],
    },
})

print(request_grant.to_pretty_string())
assert [variable.name for variable in request_grant.inputvars] == ["request"]
assert [variable.name for variable in request_grant.outputvars] == ["grant"]

# An implementation with a stronger same-step guarantee refines its spec.
specification = GR1IoContract.from_dict({
    "input_vars": ["request"],
    "output_vars": ["grant"],
    "variable_sorts": {"request": "bool", "grant": "bool"},
    "assumptions": {},
    "guarantees": {"inv": ["request -> grant"]},
})
implementation = GR1IoContract.from_dict({
    "input_vars": ["request"],
    "output_vars": ["grant"],
    "variable_sorts": {"request": "bool", "grant": "bool"},
    "assumptions": {},
    "guarantees": {"inv": ["grant = request"]},
})
assert implementation.refines(specification)
```

A successful `refines` call is a sound finite-certificate proof. A `False`
result is inconclusive in general: the refinement may be false, or the
implemented finite search may not find a certificate. This is distinct from
checking whether assumptions are locally satisfiable, and from solving the
infinite-trace controller-realizability game.

Run the complete tutorial after installation:

```console
python examples/gr1_quickstart.py
```

It demonstrates inspection, bounded-next temporal formulas, composition,
quotient, merge, refinement, and serialization with semantic assertions.

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
semantics, limitations, and troubleshooting. The executable
[contract-operations walkthrough](examples/gr1_contract_operations.py) covers
lower-level parsing and CAVE behavior. The
[AEB case study](examples/aeb_gr1_composition.py) demonstrates composition and
quotient in an engineering example without requiring the historical research
artifact:

```console
python examples/aeb_gr1_composition.py --no-report
```

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
  Historical TACAS experiments and their container/data prerequisites are not
  needed for the public API examples.

## Development and testing

From the repository root in the configured development environment, run:

```console
make test
make check
```

`make test` runs the maintained pytest suite. `make check` runs source linting,
strict source type checking, executable documentation/notebooks, and installed
dependency consistency. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and CI
details.

## Documentation, community, and citation

General Pacti documentation is available at [pacti.org](https://www.pacti.org).
Questions are welcome in the organization's
[GitHub Discussions](https://github.com/orgs/pacti-org/discussions), or by
email at info@pacti.org.

The Pacti project can be acknowledged by citing:

[Inigo Incer, Apurva Badithela, Josefine Graebener, Piergiuseppe Mallozzi,
Ayush Pandey, Nicolas Rouquette, Sheng-Jung Yu, Albert Benveniste, Benoit
Caillaud, Richard M. Murray, Alberto Sangiovanni-Vincentelli, and Sanjit A.
Seshia. “Pacti: Assume-Guarantee Contracts for Efficient Compositional
Analysis and Design.” ACM Transactions on Cyber-Physical Systems 9, no. 1
(2025): 1–35.](https://doi.org/10.1145/3704736)

Citation metadata for the GR(1)/CAVE research extension will be added after it
is approved by the maintainers; this pull request does not claim a conference
status, DOI, or package release.
