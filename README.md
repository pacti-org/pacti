# Gear

Gear is a Python package for carrying out compositional system analysis and design. Gear represents components in a
system using assume-guarantee specifications, or contracts. Gear's capabilities include the following:

- Obtaining sensible system specifications from the specifications of the constituent subsystems.
- Computing specifications of subsystems that need to be added to a design in order to meet an objective.
- Verifying whether a component meets a specification.

## Examples


### Composition


Suppose we have the following system:

<img src="docs/source/_static/circuit_series_composition.svg" width="350" alt="Buffers connected in series">


Components $M$ and $M'$ obey, respectively, contracts $C = (|i| \le 2, o \le i \le 2o + 5)$ and $C' = (-1 \le o \le 1/3, o' \le o)$. We can use gear to obtain the specification of the system by executing the command

`gear examples/example.json result.json`

Gear places the result of composition in the file result.json. The output is

```
   Composed contract:
   InVars: {<Var i>}
   OutVars:{<Var o_p>}
   A: 3*i <= 1, -1*i <= 2
   G: 1*o_p + -1*i <= 0
```

### Quotient


Now we consider an example of quotient. Consider the following circuits:

<img src="docs/source/_static/circuit_series_quotient.svg" width="350" alt="Buffers connected in series">

We wish to implement a system $M$ with specification $C = (i \le 1, o' \le 2i)$, and to do this we have available a component $M'$ with specification $C' = (i \le 2, o \le 2i)$. We use the quotient operation in gear to obtain the specification of the component that we are missing so that the resulting object meets the specification $C$. We run the command

`gear examples/example_quotient.json result.json`

And gear outputs

```
   Contract quotient:
   InVars: {<Var o>}
   OutVars:{<Var o_p>}
   A: 1/2*o <= 1
   G: -1*o + 1*o_p <= 1
```

# Installing

## System requirements

[pdm](https://github.com/pdm-project/pdm) (Make sure you run pdm version larger than 2.1.4)

[scipy](https://scipy.org/install/)

The installation will provide access to the command-line tool `gear` and to the the Python package of the same name. Any updates to the dev folder `src/gear` will immediately be available in the system.


## Install Dependencies

As Gear is in development, we use pdm manage the dependencies. To install run:

```bash
pdm install
```

The installation will provide access to the command-line tool `gear` and to the Python package of the same name.
To launch the command-line tool run `pdm run gear`


## Examples

You can run examples via the command line:


```bash
pdm run gear examples/example.json output.json
```

Or via python a script

```bash
pdm run python src/gear/cli.py ./examples/example.json ./output.json
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