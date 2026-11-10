# Typed GR(1) contracts

`GR1IoContract` extends Pacti's assume-guarantee operations to a typed,
bounded-next fragment of GR(1). It is intended for compositional reasoning
about temporal component requirements, not for synthesizing a controller.

A contract separates two responsibilities:

- **assumptions** describe the input behaviors the environment must provide;
- **guarantees** describe the behavior the component promises whenever those
  assumptions hold.

Each side has three conjunctive buckets:

- `init`: formulas that hold in the initial state;
- `inv`: formulas that hold at every state (informally, `G phi`);
- `liv`: formulas that recur infinitely often (informally, `GF phi`).

Entries in a bucket are conjoined. Each liveness entry remains a distinct
justice obligation: `liv: ["p", "q"]` means `GF p & GF q`, not
`GF (p & q)`.

## Install the integration branch

Python 3.10 or newer is required. While the GR(1) pull request is under review,
the released PyPI package may not contain this API. Use an isolated source
checkout of the integration branch:

```console
git clone https://github.com/pacti-org/pacti.git
cd pacti
git switch feature/gr1-contracts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python examples/gr1_quickstart.py
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1`. Installation pulls in
the `z3-solver` Python package; a system Z3 executable is not required. The
quick start does not require Spot, Docker, PDM, benchmark data, or the original
research repository.

If `python3 --version` reports an older interpreter, install a supported Python
and invoke it explicitly (for example, `python3.11 -m venv .venv`). If the
import resolves to another Pacti installation, verify the active interpreter
and package location with:

```console
python -c "import sys, pacti; print(sys.executable); print(pacti.__file__)"
```

## Construct and inspect a temporal contract

The following block is standalone and executable. `request` is controlled by
the environment; `grant` is controlled by the component. `X(grant)` refers to
the value of `grant` one transition later.

```python
from pacti.iocontract import GR1IoContract

arbiter = GR1IoContract.from_dict({
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

assert [variable.name for variable in arbiter.inputvars] == ["request"]
assert [variable.name for variable in arbiter.outputvars] == ["grant"]
assert len(arbiter.a.liv_terms()) == 1
assert len(arbiter.g.inv_terms()) == 1
print(arbiter.to_pretty_string())
```

The dictionary returned by `to_dict()` is the persistence API. It records the
interface, sorts, and canonical formulas and can be passed back to
`from_dict()`. `to_pretty_string()` is a presentation API; code should not
parse its output.

## Formula syntax and variable sorts

Every interface variable must have a `bool`, `int`, or `real` declaration in
`variable_sorts`. Declarations are checked across composition, quotient, and
merge, including variables that do not appear in a formula. A name cannot
silently change sort between contracts.

Formula strings use base names such as `request`, not internal flattened names
such as `request_0`. `X(value)` and `next(value)` mean the next value. Nested
next operators are supported to a finite, syntactically determined depth.
Boolean operators include `!`/`not`, `&`/`and`, `|`/`or`, `->`/`=>`, and
`<->`. Comparisons, parentheses, exact decimals, and rational linear
arithmetic are supported.

The bucket supplies the outer temporal operator. Do not put arbitrary `G`,
`F`, `U`, or other LTL operators inside a core formula. This integer example
has one bounded-next safety condition and one recurring threshold obligation:

```python
from pacti.iocontract import GR1IoContract

counter = GR1IoContract.from_dict({
    "input_vars": ["enable"],
    "output_vars": ["count"],
    "variable_sorts": {"enable": "bool", "count": "int"},
    "assumptions": {},
    "guarantees": {
        "init": ["count = 0"],
        "inv": ["enable -> X(count) = count + 1"],
        "liv": ["count >= 10"],
    },
})

assert counter.variable_sorts == {"enable": "bool", "count": "int"}
```

This contract states a requirement; it does not prove that a controller can
make `count >= 10` recur under every input behavior.

## Refinement

`candidate.refines(specification)` attempts to prove that the candidate needs
no stronger environment assumptions and provides no weaker guarantees. The two
contracts must have matching input/output interfaces.

```python
from pacti.iocontract import GR1IoContract

sorts = {"request": "bool", "grant": "bool"}
specification = GR1IoContract.from_dict({
    "input_vars": ["request"],
    "output_vars": ["grant"],
    "variable_sorts": sorts,
    "assumptions": {},
    "guarantees": {"inv": ["request -> grant"]},
})
implementation = GR1IoContract.from_dict({
    "input_vars": ["request"],
    "output_vars": ["grant"],
    "variable_sorts": sorts,
    "assumptions": {},
    "guarantees": {"inv": ["grant = request"]},
})

assert implementation.refines(specification)
```

`True` is a sound finite-certificate result. `False` does not always establish
semantic non-refinement: either refinement is false or the implemented finite
support search did not find a certificate. This boundary is especially
important when liveness obligations are involved.

## Composition, quotient, and merge

Composition connects compatible outputs and inputs. Shared connected variables
are hidden unless retained with `vars_to_keep`. Quotient computes a residual:
given a target and a known component, it computes the missing contract whose
composition with the known component is intended to refine the target. Merge
conjoins two compatible contracts without hiding connected variables.

```python
from pacti.iocontract import GR1IoContract, Var

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
assert system.inputvars == [Var("request")]
assert system.outputvars == [Var("response")]
assert Var("wire") not in system.a.vars + system.g.vars

residual = system.quotient(producer)
assert residual.inputvars == [Var("wire")]
assert residual.outputvars == [Var("response")]
assert producer.compose(residual).refines(system)

monitor = GR1IoContract.from_dict({
    "input_vars": ["request"],
    "output_vars": ["healthy"],
    "variable_sorts": {"request": "bool", "healthy": "bool"},
    "assumptions": {},
    "guarantees": {"inv": ["healthy"]},
})
merged = producer.merge(monitor)
assert set(variable.name for variable in merged.outputvars) == {"wire", "healthy"}
```

These are methods: the public API does not overload `|` for composition or `/`
for quotient. The quotient check above is the useful contract law to validate;
pretty-printed formulas can vary after sound simplification.

## What CAVE computes

Composition and quotient can require hidden-variable elimination. CAVE combines
the formula being projected with relevant context and computes sound
finite-window under- or over-approximations as required by the contract
operation. It keeps INIT and invariant context aligned across the bounded-next
horizon and treats separate liveness obligations as separate support choices.

CAVE is not claimed to perform exact temporal quantifier elimination for every
GR(1) formula. Its use in finite-certificate refinement is sound for the
implemented, tested fragment but incomplete for general infinite traces.

`is_empty()` likewise checks the finite feasibility conditions represented by
the term list. It does not solve a GR(1) game, establish controller
realizability, or synthesize a strategy. Local satisfiability, a successful
refinement certificate, and infinite-trace realizability are different claims.

Solver `unknown`, solver failures, unsupported quantifier elimination, and
unexpected tactic subgoals raise `GR1SolverError` when a conclusive answer is
required. They are never accepted as proofs of unsatisfiability. Boolean and
linear integer/real arithmetic are the validated scope. Parsing an expression
outside that scope is not a promise that Z3 can eliminate it soundly with the
configured tactics.

## Examples

- `python examples/gr1_quickstart.py` — beginner workflow with semantic checks.
- `python examples/gr1_contract_operations.py` — parsing, bounded behaviors,
  renaming, CAVE refinement/relaxation, composition, quotient, and round trip.
- `python examples/aeb_gr1_composition.py --no-report` — nontrivial automated
  emergency-braking composition and quotient. It shows how supervisor and
  vehicle contracts expose only the external distance/mode-to-speed interface
  after internal command variables are hidden. Omit `--no-report` to also
  create `examples/aeb_gr1_composition_output.txt`.

The AEB source documents which numerical values are example parameters rather
than measurements from a reference implementation. The historical benchmark
suite is not a prerequisite for learning or using this API.

## Optional Spot validation

The core package does not depend on Spot. Selected research comparisons use the
Spot LTL library and its Buddy bindings as an independent temporal engine. The
package named `spot` on PyPI is unrelated. Follow the
[official Spot installation instructions](https://spot.lre.epita.fr/install.html)
and verify the environment with:

```console
python -c 'import spot, buddy; print(spot.version())'
```

Absence of Spot does not affect contract construction, CAVE, or the examples
above.

## Troubleshooting

- **`ImportError` for `GR1IoContract`:** confirm that the active interpreter is
  using this branch's checkout. The currently released PyPI package may not yet
  expose GR(1).
- **Sort or interface error:** inspect `input_vars`, `output_vars`, and
  `variable_sorts` on both operands. Connected names must have the same sort,
  and two composed components cannot both control the same output.
- **`GR1SolverError`:** the solver did not produce a conclusive supported
  result. Preserve the exception and formula when reporting the issue; do not
  interpret it as unsatisfiable. Reduce nonlinear or otherwise unsupported
  arithmetic to the documented linear fragment where possible.
- **A `False` refinement result:** first test a smaller requirement and inspect
  its temporal buckets. `False` is not, by itself, a counterexample or proof of
  non-refinement because the finite certificate search is incomplete.
- **Spot import failure:** Spot is optional. Install Spot and Buddy from the
  official project only when running the independent research comparisons.

For reproducible bug reports, include the Python and Z3 versions from
`python -c 'import sys, z3; print(sys.version); print(z3.get_version_string())'`
and a minimal `to_dict()` payload without private data.

## Development verification

Contributors can run the whole suite and all configured quality checks from the
repository root:

```console
make test
make check
```

The executable documentation check runs the Markdown snippets, beginner and
advanced examples, maintained notebooks, and the AEB no-report command. The
focused correctness regressions include interface equality/hash behavior, sort
conflicts and propagation, solver inconclusiveness, quantifier-elimination
boundaries, and the polyhedral fallback used by the feedback-amplifier
notebook.

## Research scope

This repository contains maintained source-level examples and tests, not the
full frozen benchmark datasets or generated result directories. The historical
reproduction artifact remains separate pending archival locations and
third-party redistribution review. No conference status, DOI, benchmark result,
or package release is implied here.
