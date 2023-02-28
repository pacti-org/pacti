
## Installing

### System requirements

[pdm](https://github.com/pdm-project/pdm) (Make sure you run pdm version larger than 2.1.4)

[scipy](https://scipy.org/install/)

The installation will provide access to the command-line tool `pacti` and to the the Python package of the same name. Any updates to the dev folder `src/pacti` will immediately be available in the system.


### Install Dependencies

As Pacti is in development, we use pdm manage the dependencies. To install run:

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

