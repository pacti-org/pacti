Gear
====

Gear is a Python package for carrying out compositional system analysis and
design. Gear represents components in a system using assume-guarantee
specifications, or contracts. Gear's capabilities include the following:

- Obtaining sensible specifications systems from the specification of their
  subsystems.
- Computing specifications of elements that need to be added to a design in
  order to meet an objective.
- Verifying whether a component meets a specification.


Installing
----------

As Gear is in development, we use [pdm](https://github.com/pdm-project/pdm) manage the dependencies. 
To install run:

```bash
pdm install
```


The installation will provide access to the command-line tool `gear` and to the Python package of the same name. 

To launch the command tool run:

```bash
pdm run gear
```


Links
-----

- Documentation: :code:`docs/_build/html/index.html`
- Source Code: https://github.com/iincer/contractTool



> NOTE: Working with PEP 582
> 
> With PEP 582, dependencies will be installed into __pypackages__ directory under the project root. With PEP 582 enabled globally, you can also use the project interpreter to run scripts directly.
> Check [pdm documentation](https://pdm.fming.dev/latest/usage/pep582/) on PEP 582.
> 
> To configure VSCode to support PEP 582, open `.vscode/settings.json` (create one if it does not exist) and add the following entries:
> ```json
> {
>   "python.autoComplete.extraPaths": ["__pypackages__/3.10/lib"],
>   "python.analysis.extraPaths": ["__pypackages__/3.10/lib"]
> }
> ```
> > To configure PyCharm to support PEP 582, mark the following folders as `source`:
* `__pypackages__/3.10/lib`
* `__pypackages__/3.10/lib`
> ```