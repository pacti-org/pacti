To insert *local* figures (PNG or JPG), follow the conversion to Base64 technique described here: 
https://mljar.com/blog/jupyter-notebook-insert-image/

Note: Inserting *.SVG as Base64 figures will render locally with `make docs-serve` only.
Github's ipynb rendering will show only an icon, not the SVG image.

For SVG to PDF conversion, use this free service:
https://cloudconvert.com/svg-to-pdf

# Syncing case study notebooks to python files for testing.

There are several options:
- nbconvert: https://github.com/FormalSystems/pacti/discussions/222
- jupytext: https://jupytext.readthedocs.io/en/latest/using-cli.html

The Jupytext doc explains how to use this as a pre-commit hook: https://jupytext.readthedocs.io/en/latest/using-pre-commit.html

With jupytext, the config doc suggests we can add configuration either to `pyproject.toml` or a file `jupytext.toml`

I tried adding the following to either file:

```
[tool.jupytext]
formats = "case_studies///ipynb,tests/case_studies///py:percent"
```

In the end, I had to specify the configuration at the command line for each conversion:

```
nfr@nfr-desktop:/opt/local/github.formalsystems/pacti$ pdm run jupytext --set-formats case_studies///ipynb,tests/case_studies///py:percent case_studies/space_mission/space_mission_power.ipynb
[jupytext] Reading case_studies/space_mission/space_mission_power.ipynb in format ipynb
[jupytext] Updating notebook metadata with '{"jupytext": {"formats": "case_studies///ipynb,tests/case_studies///py:percent"}}'
[jupytext] Updating case_studies/space_mission/space_mission_power.ipynb
[jupytext] Updating tests/case_studies/space_mission/space_mission_power.py
WARNING:root:[jupytext] creating missing directory tests/case_studies/space_mission/
nfr@nfr-desktop:/opt/local/github.formalsystems/pacti$
```

This is missing the ability to filter cells that we do not want to export to python, similar to this functionality:
https://nbconvert.readthedocs.io/en/latest/removing_cells.html

The strategy would be:

1) Run nbconvert to remove cells by converting the notebook to another notebook
2) On the resulting notebook, run jupytext to convert to python

It is awkward but it should work.
