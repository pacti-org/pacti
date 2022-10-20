# Gear

Gear is a Python package for carrying out compositional system analysis and design. Gear represents components in a
system using assume-guarantee specifications, or contracts. Gear's capabilities include the following:

- Obtaining sensible specifications systems from the specification of their subsystems.
- Computing specifications of elements that need to be added to a design in order to meet an objective.
- Verifying whether a component meets a specification.

# Installing

## System requirements

[pdm](https://github.com/pdm-project/pdm) (Make sure you run pdm version larger than 2.1.4)

[scipy](https://scipy.org/install/)

## Install Dependencies

As Gear is in development, we use pdm manage the dependencies. To install run:

```bash
pdm install
```

The installation will provide access to the command-line tool `gear` and to the Python package of the same name.

To launch the command tool run:

```bash
pdm run gear examples/example.json output.json
```

Or via python script

```bash
pdm run python src/gear/cli.py ./examples/example.json ./output.json
```


## Examples

You can run examples via command line:

```bash
pdm run gear exampl
```


## Links

- Documentation: ``
- Source Code: ``

## Troubleshooting

### Working With Apple Silicon

Some packages do not fully support Apple Silicon (i.e. `scipy`, `numpy`). 
We recommend installing them at system level via pip as:

```bash
pip install --pre -i https://pypi.anaconda.org/scipy-wheels-nightly/simple scipy
```

Or via brew:

```bash
brew install scipy
```


### Working with PEP 582

With PEP 582, dependencies will be installed into __pypackages__ directory under the project root. With PEP 582 enabled
globally, you can also use the project interpreter to run scripts directly.
Check [pdm documentation](https://pdm.fming.dev/latest/usage/pep582/) on PEP 582.

To configure VSCode to support PEP 582, open `.vscode/settings.json` (create one if it does not exist) and add the
following entries:

```json
{
  "python.autoComplete.extraPaths": [
    "__pypackages__/3.10/lib"
  ],
  "python.analysis.extraPaths": [
    "__pypackages__/3.10/lib"
  ]
}
```

To configure PyCharm to support PEP 582, mark the following folders as 'Sources Root':

- `__pypackages__/3.10/lib`
- `src`