# Pacti 
[![Build Status](https://github.com/pacti-org/pacti/actions/workflows/pacti_development.yml/badge.svg)](https://github.com/pacti-org/pacti/actions/workflows/pacti_development.yml)
[![PyPI version](https://badge.fury.io/py/pacti.svg)](https://badge.fury.io/py/pacti)
[![codecov](https://codecov.io/gh/pacti-org/pacti/branch/main/graph/badge.svg)](https://codecov.io/gh/pacti-org/pacti)
[![Getting Started With Pacti Example](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1muppEkj1K4vowBuS1C8plCouCdK50iio?usp=sharing)
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_white.png" width="250">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_colorful.png" width="250">
  <img alt="Logo in light and dark mode." src="https://raw.githubusercontent.com/pacti-org/media/main/docs/logos/pacti_colorful.png" width="250">
</picture>

Pacti is a Python package for carrying out compositional system analysis and design. Pacti represents components in a
system using assume-guarantee specifications, or contracts. Pacti's capabilities, among others, include the following:

- Obtaining sensible system specifications from the specifications of the constituent subsystems.
- Computing specifications of subsystems that need to be added to a design in order to meet an objective.
- Diagnosing incompatibilities when interconnecting components.
