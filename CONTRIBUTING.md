# Contributing

Contributions are welcome and greatly appreciated.
If you would like to address a bug or add a feature, please first open an issue.
If we decide to move forward with the changes, please fork the repo and open a pull request.

## Installation

Pacti requires Python 3.10 or newer. Clone the repository, install
[PDM](https://pdm-project.org/) using its supported installation method, and
run:

```bash
python3 --version
pdm install
```

PDM is a development tool, not a runtime requirement. To exercise only the
installed package and examples, a standard virtual environment with
`python -m pip install -e .` is sufficient. The complete quality tasks require
the PDM development groups.

Running
```bash
make help
```
shows all available tasks.

## Development

We use [pdm](https://pdm.fming.dev/latest/) to manage dependencies.
Use `pdm add` to install new packages.

Add unit tests to make sure the new functionality is covered. If your functionality falls into one of the existing classes, add your tests to the corresponding file under the tests/ directory. Otherwise, create a new file. We use `pytest` to run our tests. Make sure that your test starts with the name *test* to ensure that it will be executed when `make test` is invoked.

**Before committing:**

1. run `make format` to auto-format the code;
2. run `make test` to run the tests;
3. run `make check` to check source types and quality, executable documentation,
   maintained notebooks, and dependency consistency;
4. make sure that all tests pass and the source code coverage meets our criteria

Finally, in your commit message, try to use helpful keywords such as "add", "fix", "remove", "change" to describe the changes that you have proposed. This helps in generating change log documentation appropriately. You can read more about writing good commit messages [here](https://opensource.com/article/22/12/git-commit-message) and [here](https://cbea.ms/git-commit/).
    
## Continuous Integration and Development
Pacti has continuous integration and development setup with Github Actions. Some workflows are automatically run while others are manual. Instructions for all developers:

1. For a feature or bug-fix branch, make sure the automatically triggered Pacti
   Development workflow passes.
2. Before review, run the local commands above and inspect any manually
   triggered Development Review or Pre-Production workflow requested by a
   maintainer.
3. The checked-in workflows test only their explicitly configured operating
   systems and Python versions. Do not interpret a green workflow as evidence
   for unlisted platforms or interpreters.
4. Package publication remains a separate maintainer-controlled process; normal
   verification workflows must not be used to publish a distribution.
