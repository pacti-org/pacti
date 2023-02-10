<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logos/pacti_white.png" width="250">
  <source media="(prefers-color-scheme: light)" srcset="docs/logos/pacti_colorful.png" width="250">
  <img alt="Logo in light and dark mode." src="docs/logos/pacti_colorful.png" width="250">
</picture>

Pacti is a Python package for carrying out compositional system analysis and design. Pacti represents components in a
system using assume-guarantee specifications, or contracts. Pacti's capabilities include the following:

- Obtaining sensible system specifications from the specifications of the constituent subsystems.
- Computing specifications of subsystems that need to be added to a design in order to meet an objective.
- Verifying whether a component meets a specification.

## Examples


### Composition


Suppose we have the following system:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/source/_static/exports/circuit_series_composition_white.svg" width="250">
  <source media="(prefers-color-scheme: light)" srcset="docs/source/_static/exports/circuit_series_composition_black.svg" width="250">
  <img alt="Logo in light and dark mode." src="docs/source/_static/exports/circuit_series_composition_black.svg" width="250">
</picture>


Components $M$ and $M'$ obey, respectively, contracts $C = (|i| \le 2, o \le i \le 2o + 2)$ and $C' = (-1 \le o \le 1/5, o' \le o)$. We can use Pacti to obtain the specification of the system by executing the command

`pacti examples/example.json result.json`

Pacti places the result of composition in the file result.json. The output is

```
  Composed contract:      
  InVars: [<Var i>]       
  OutVars:[<Var o_p>]     
  A: 5*i <= 1, -1/2*i <= 0
  G: -1*i + 1*o_p <= 0
```

### Quotient


Now we consider an example of quotient. Consider the following circuits:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/source/_static/exports/circuit_series_quotient_white.svg" width="250">
  <source media="(prefers-color-scheme: light)" srcset="docs/source/_static/exports/circuit_series_quotient_black.svg" width="250">
  <img alt="Logo in light and dark mode." src="docs/source/_static/exports/circuit_series_quotient_black.svg" width="250">
</picture>

We wish to implement a system $M$ with specification $C = (|i| \le 1, o' = 2i + 1)$, and to do this we have available a component $M'$ with specification $C' = (|i| \le 2, o = 2i)$. We use the quotient operation in Pacti to obtain the specification of the component that we are missing so that the resulting object meets the specification $C$. We run the command

`pacti examples/example_quotient.json result.json`

And Pacti outputs

```
  Contract quotient:
  InVars: [<Var o>]
  OutVars:[<Var o_p>]
  A: 1*o <= 2, -1*o <= 2
  G: -1*o + 1*o_p <= 1, 1*o + -1*o_p <= -1
```

# Installing

## System requirements

[pdm](https://github.com/pdm-project/pdm) (Make sure you run pdm version larger than 2.1.4)


The installation will provide access to the command-line tool `pacti` and to the Python package of the same name. Any updates to the dev folder `src/pacti` will immediately be available in the system.


## Install Dependencies

As Pacti is in development, we use pdm manage the dependencies. To install run:

```bash
pdm install
```

The installation will provide access to the command-line tool `pacti` and to the Python package of the same name.
To launch the command-line tool run `pdm run pacti`


## Examples

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
