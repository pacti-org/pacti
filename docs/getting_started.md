
## Installing

### System requirements

[pdm](https://github.com/pdm-project/pdm) (Make sure you run pdm version larger than 2.1.4)

[scipy](https://scipy.org/install/)

The installation will provide access to the command-line tool `pacti` and to the the Python package of the same name. Any updates to the dev folder `src/pacti` will immediately be available in the system.


### Install Dependencies

As Gear is in development, we use pdm manage the dependencies. To install run:

```bash
pdm install
```

The installation will provide access to the command-line tool `pacti` and to the Python package of the same name.
To launch the command-line tool run `pdm run pacti`


### Examples

You can run examples via the command line:


```bash
pdm run pacti examples/example.json output.json
```

Or via python a script

```bash
pdm run python src/pacti/cli.py ./examples/example.json ./output.json
```


## Links

- Documentation: `make docs-serve`
- Source Code: https://github.com/iincer/contractTool

## Troubleshooting

### Working With Apple ICs

Some packages do not fully support recent Apple ICs (i.e., `scipy`, `numpy`). 
We recommend installing them at system level via pip as:

```bash
pip install --pre -i https://pypi.anaconda.org/scipy-wheels-nightly/simple scipy
```

Or via brew:

```bash
brew install scipy
```


### Working with PEP 582

With PEP 582, dependencies will be installed into the __pypackages__ directory under the project root. With PEP 582 enabled
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