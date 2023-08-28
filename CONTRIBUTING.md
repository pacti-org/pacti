# Contributing

Contributions are welcome and greatly appreciated.
If you would like to address a bug or add a feature, please first open an issue.
If we decide to move forward with the changes, please fork the repo and open a pull request.

## Installation

Clone the repo and run

```bash
pdm install
```

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

1. run `make format` to auto-format the code
2. run `make test` to run the tests (fix any issue)
3. run `make check` to check everything (types, docs, quality, and dependencies)
4. make sure that all tests pass and the source code coverage meets our criteria

Finally, in your commit message, try to use helpful keywords such as "add", "fix", "remove", "change" to describe the changes that you have proposed. This helps in generating change log documentation appropriately. You can read more about writing good commit messages [here](https://opensource.com/article/22/12/git-commit-message) and [here](https://cbea.ms/git-commit/).
    
## Continuous Integration and Development
Pacti has continuous integration and development setup with Github Actions. Some workflows are automatically run while others are manual. Instructions for all developers:

1. If you are in the process of developing a feature/fixing a bug in your own development branch: Make sure that the Pacti Development workflow passes. This will automatically be run with every commit, so you should be getting notifications of what Pacti functionality failed (if any).
2. If you are contributing a development feature to any branch (that is, your development has finished): Run the Pacti Development Review workflow. This will test the functionality and also code quality.
3. If you are reviewing a pull-request to the main branch from another developer: Make sure to go to the "Actions" tab and run the Pacti Pre-Production workflow manually. This workflow tests the package for functionality and quality on two Python versions.
4. The Pacti Production workflow makes sure that the software works with all OS and all Python versions.
