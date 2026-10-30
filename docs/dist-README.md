[![Build Status](https://github.com/pacti-org/pacti/actions/workflows/pacti_development.yml/badge.svg)](https://github.com/pacti-org/pacti/actions/workflows/pacti_development.yml)
[![PyPI version](https://badge.fury.io/py/pacti.svg)](https://badge.fury.io/py/pacti)
[![codecov](https://codecov.io/gh/pacti-org/pacti/branch/main/graph/badge.svg)](https://codecov.io/gh/pacti-org/pacti)
[![Getting Started With Pacti Example](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1muppEkj1K4vowBuS1C8plCouCdK50iio?usp=sharing)


<img alt="Logo in light and dark mode." src="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_colorful.png" width="250">


Pacti is an open-source Python package for carrying out compositional system analysis and design. Pacti represents components in a
system using assume-guarantee specifications, or contracts. Pacti's capabilities, among others, include the following:

- Obtaining sensible system specifications from the specifications of the constituent subsystems.
- Computing specifications of subsystems that need to be added to a design in order to meet an objective.
- Diagnosing incompatibilities when interconnecting components.

Pacti includes typed GR(1) contracts with initial, invariant, recurring
liveness, and bounded-next formulas. The extension supports composition,
quotient, merge, serialization, and finite-certificate refinement. It is not a
controller synthesizer or a complete infinite-trace realizability checker.
`z3-solver` is installed as a normal dependency; Spot and the historical
research artifact are optional and are not needed for the public API. The
source distribution contains the executable quick start at
`examples/gr1_quickstart.py` and the detailed guide at
`docs/gr1-contracts.md`. Until maintainers announce a release containing the
GR(1) API, install the integration branch rather than assuming the current PyPI
package includes `GR1IoContract`.


Documentation can be found on the project's website: www.pacti.org.
For questions about Pacti and to interact with the community, please go to the organization's [GitHub Discussions page](https://github.com/orgs/pacti-org/discussions).
Pacti's developers can be reached at info@pacti.org.

The Pacti project can be acknowledged by citing

[Inigo Incer, Apurva Badithela, Josefine Graebener, Piergiuseppe Mallozzi, Ayush Pandey, Sheng-Jung Yu, Albert Benveniste, Benoit Caillaud, Richard M. Murray, Alberto Sangiovanni-Vincentelli, and Sanjit A. Seshia. 
"Pacti: Scaling Assume-Guarantee Reasoning for System Analysis and Design." ArXiv abs/2303.17751 (2023).](https://arxiv.org/abs/2303.17751)
