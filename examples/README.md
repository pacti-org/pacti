# Examples

This index covers the nine maintained GR(1) example and research scripts.
For Pacti's polyhedral examples, see the [Getting Started notebook](../docs/getting_started.ipynb)
and [official documentation](https://www.pacti.org).

Use Python 3.11 or newer with `pip install pacti` (GR(1) requires Pacti 0.4.0
or newer), and run the commands below from the repository root. Pacti supplies
Z3 and the numerical dependencies, including NumPy and Matplotlib. Only the
optional E6 automata comparison needs Spot and Buddy; pytest is needed for
regression tests. The research scripts use implementation details and should
be run from a checkout matching the installed Pacti version.

## GR(1) quick start

| File | Purpose and operations |
| --- | --- |
| [gr1_quickstart.py](gr1_quickstart.py) | Introduces typed request/grant contracts, a `healthy` monitor, and a Boolean `request → wire → response` connection, with construction, composition, quotient, refinement, merge, and serialization checks. |

```console
python examples/gr1_quickstart.py
```

This short tutorial prints contracts and progress messages and checks its
results with assertions. The [GR(1) guide](../docs/gr1-contracts.md) explains
temporal syntax and the limits of finite-certificate refinement.

## Introductory composition and lower-level operations

| File | Purpose and operations |
| --- | --- |
| [gr1_contract_operations.py](gr1_contract_operations.py) | Connects Boolean producer `q → p` and consumer `p → r` to compute `q = X(r)`, then derives a quotient; also demonstrates typed parsing (`request`, `temperature`, `counter`, `grant`), lasso behaviors, renaming, serialization, and CAVE refinement/relaxation eliminating `p`. |

```console
python examples/gr1_contract_operations.py
```

This is a small illustrative system, with readable contracts, status messages,
and semantic assertions. It also provides the lower-level CAVE walkthrough;
it does not reproduce the manuscript's AEB case study.

## AEB composition

| File | Purpose and operations |
| --- | --- |
| [aeb_gr1_composition.py](aeb_gr1_composition.py) | Composes the manuscript's supervisor and vehicle, hiding `u`, `MOV`, `DCL`, and `STP` to expose `(d, URG, WRN) → v`, and computes a supervisor quotient using that composition as the target. |

```console
python examples/aeb_gr1_composition.py --no-report
```

The system computation derives the clear-road compatibility condition
`!URG & !WRN -> d >= 20` and speed guarantees. It prints verified compact
summaries, generated contracts, and refinement results. Its quotient is
`C_COMP / C_V`, where `C_COMP = C_S.compose(C_V)`: it does **not** construct
`C_T` or the clearance predictor. Its factories supply the manuscript audit
below. Omit `--no-report` to also write `examples/aeb_gr1_composition_output.txt`.
The performance table in this script contains recorded measurements, rather
than timings of the current execution.

## AEB quotient and manuscript example

**[aeb_predicted_clearance.py](aeb_predicted_clearance.py) is the entry point
for the `C_T` and clearance-prediction example in Sections 2.5 and 5.1 of
[Computing GR(1) Assume–Guarantee Contracts](https://arxiv.org/abs/2610.37534).**
It reproduces composition, quotient, and target-refinement checks.

| Paper notation | Python construction | Interface and role |
| --- | --- | --- |
| `C_S` | `baseline.make_supervisor()` | Distance `d` and hazard flags `URG`, `WRN` to speed command `u` and modes `MOV`, `DCL`, `STP`. |
| `C_V` | `baseline.make_vehicle()` | Command and modes to forward speed `v`, with one-step tracking error at most `1/2`. |
| `C_D` | `make_prediction()` | Given clearance predictor `(d, v) → z`, with `X(z) = d - Delta_t * X(v)` and `Delta_t = 1`. |
| `C_T` | `make_target()` | Target `(d, URG, WRN) → v` for safety and recurring progress. |
| `C_comp` / `C_SVD` | `sv` / `svd` in `run_audit()` | `C_S.compose(C_V)`, then composition with `C_D`, exposing speed `v`, then predicted clearance `z`. |
| `Q = C_T / C_V` | `target.quotient(vehicle)` inside `traced_quotient()` | Missing **supervisor** requirements, with inputs `(d, URG, WRN)` and outputs `(u, MOV, DCL, STP)`. |

The clearance predictor is given; the quotient derives the supervisor contract.
`C_T` inherits the supervisor's environment assumptions and adds `d >= 3/2`
and `!URG & !WRN -> d >= 20` to its invariant assumptions. Its guarantees are
`X(v) <= d - 1` at every step and `!URG & !WRN & X(v) >= 3/2` infinitely often,
with no initial guarantee. Together with `C_D`, the safety bound expresses a
next predicted clearance of at least `d_s = 1`; it is a prediction under the
stated model, not a physical stopping-distance simulation.

The audit establishes `C_S.refines(Q)`, `C_V.compose(Q).refines(C_T)`, and
`C_S.compose(C_V).refines(C_T)`. The last check combines recurring clear-road
opportunities from the target assumptions with invariant speed bounds at
certificate horizon zero. Reverse refinement of the recomposed target is not
established. The quotient retains vehicle admissibility, including separate
`GF MOV`; modulo `u >= 0`, its safety and progress projections reduce to
`u <= d - 3/2` and `GF(!URG & !WRN & u >= 2)`. These are contextual forms,
not the complete raw quotient. The three printed clearance envelopes are
sound consequences of the generated composition, not equivalent replacements
for it.

```console
python examples/aeb_predicted_clearance.py
```

This runs the audit and fresh performance measurements (one warm-up and ten
runs), prints detailed formulas and certificates, and writes
`examples/aeb_predicted_clearance_output.txt`. It imports the supervisor/vehicle
factories and observation helpers from [aeb_gr1_composition.py](aeb_gr1_composition.py);
timing instrumentation comes from [gr1_cave_scalability.py](gr1_cave_scalability.py).
Keep these files together. For verification without the full timing loop or
report file, use the existing regression suite (which measures one repetition):

```console
python -m pytest -q tests/test_aeb_predicted_clearance.py
```

## Additional AEB diagnostics

These supervisor/actuator studies use distance `d`, emergency flag `e`, command
`u`, and actuator response `a`. They are separate from the manuscript's
`C_T`/clearance-prediction example and contain neither `C_T` nor `z`.

| File | Purpose and operations |
| --- | --- |
| [gr1_aeb_full_buckets.py](gr1_aeb_full_buckets.py) | Audits INIT, invariant, and liveness composition/quotient projections for a supervisor with `u <= 2 - d/10`, including the derived compatibility condition `!e -> d >= 10`. |
| [gr1_aeb_increasing_distance.py](gr1_aeb_increasing_distance.py) | Uses the increasing envelope `u <= d/10 - 1` to derive `!e -> d <= 25`, then checks composition, quotient, recomposition refinement, and serialization. |

```console
python examples/gr1_aeb_full_buckets.py
python examples/gr1_aeb_increasing_distance.py
```

Both print contracts and prediction tables. In Pacti 0.4.0, the full-bucket
script reports `OVERALL: FAIL` for some historical hand-written quotient
predictions even though it exits with status zero; do not treat it as a passing
reproduction of those predictions. The predictions omit an additional recurrence
assumption and successor-state constraints; some also compare reduced formulas
without their invariant context. Quotient is not an inverse that must recover
the original actuator. The script is retained because
[test_gr1_aeb_full_buckets.py](../tests/test_gr1_aeb_full_buckets.py) imports its
factories and helpers for canonical-bucket, finite-window, serialization, and
non-mutation regressions. Run that test file for the maintained expectations.
The increasing-distance script's prediction checks pass.

## CAVE research tools

| File | Purpose and operations |
| --- | --- |
| [gr1_cave_scalability.py](gr1_cave_scalability.py) | Instruments refinement CAVE on Boolean hidden variables `p_k`, anchors `a_k`, target cores `t_i`, and supports `s_j`; its separate AEB mode times `C_COMP / C_V`, not `C_T / C_V`. |
| [gr1_cave_experiments.py](gr1_cave_experiments.py) | Runs the paper's E1–E8 research families: refinement/relaxation, Boolean and linear-real elimination, bounded-lasso checks, `y_i`/`m_i` composition chains, optional Spot comparisons, ablations, and the manuscript's three-component composition and `C_T / C_V` timing in E8. |
| [plot_gr1_cave_scalability.py](plot_gr1_cave_scalability.py) | Plots runtime and candidate counts from a complete schema-4 scalability CSV; performs no contract operation. |

Start with the established lightweight diagnostics:

```console
python examples/gr1_cave_scalability.py --pilot
python examples/gr1_cave_experiments.py --selftest --output-dir /tmp/pacti-cave-selftest
python examples/gr1_cave_experiments.py --e8 --preset quick --output-dir /tmp/pacti-cave-e8
```

The pilot prints candidate selection and counters. The experiment driver
prints progress and writes CSVs and `MANIFEST.json`; inspect row statuses for
errors, timeouts, or skipped optional comparisons. E8 measures the manuscript
operations but does not replace the semantic audit above. The other families
use synthetic variables (`p/a/b/t/s`, real `u/d/v`, Boolean `mt/ms`, or random
external/hidden bits); they are research measurements, not introductory examples.
The `--selftest` falling-edge case also checks the illustrative refinement and
relaxation example from Section 4.2, using hidden `p` and retained `q`, `s`.
E6 alone requires [Spot and Buddy](../docs/gr1-contracts.md#optional-spot-validation).

For orientation, a local Python 3.11 / Pacti 0.4.0 / Z3 5.4.1 run took about
24 seconds for the AEB composition audit and 19 seconds for the manuscript
audit including its ten timing repetitions. The quick start, operations
walkthrough, actuator audits, pilot, and self-test each took under 3 seconds;
the E8 quick run took about 4 seconds. These are illustrative wall times,
not benchmark results.

Full sweeps are substantially more expensive than the pilot. The scalability
script uses 21 configurations, each with one warm-up and ten measured calls,
and has no timeout; use `--resume` to continue an interrupted run. The experiment
script's `--preset paper` runs large grids, with per-worker limits up to 600
seconds. Total runtime depends on the grid, solver, and machine; the quick
preset is a smoke run, not a reproduction of the paper's timing statistics.

```console
python examples/gr1_cave_scalability.py --synthetic --output-dir /tmp/pacti-cave-scaling
python examples/plot_gr1_cave_scalability.py --input /tmp/pacti-cave-scaling/gr1_cave_scalability_results.csv --output-dir /tmp/pacti-cave-plots
```

The plotting command requires all 210 measured calls and their aggregates;
partial data and the unified driver's `e1.csv` are not accepted. Its Matplotlib
output comprises six PDF figures. For a quick CLI check without a dataset,
run `python examples/plot_gr1_cave_scalability.py --help`.
