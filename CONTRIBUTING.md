# Contributing

Contributions are welcome, and they are greatly appreciated!

## Tasks

This project uses [duty](https://github.com/pawamoy/duty) to run tasks.
A Makefile is also provided.

Once the project is installed (`make setup`), run
```bash
make help
```
to see all available tasks

## Development

We use [pdm](https://pdm.fming.dev/latest/) to manage the dependencies.
Use `pdm add` to install new packages.

**Before committing:**

1. run `make format` to auto-format the code
2. run `make check` to check everything (types, docs, quality, and dependencies)
3. run `make test` to run the tests (fix any issue)
4. make sure that all tests pass and the source code coverage meets our criteria
5. if you updated the documentation or the project dependencies:
    1. run `make docs-serve`
    2. go to http://localhost:8000 and check that everything looks good
    
## Continuous Integration and Development
Pacti has continuous integration and development setup with Github Actions. Some workflows are automatically run while others are manual. Instructions for all developers:

1. If you are in the process of developing a feature/fixing a bug in your own development branch: Make sure that the Pacti Development workflow passes. This will automatically be run with every commit, so you should be getting notifications of what Pacti functionality failed (if any).
2. If you are contributing a development feature to any branch (that is, your development has finished): Run the Pacti Development Review workflow. This will test the functionality and also code quality.
3. If you are reviewing a pull-request to the main branch from another developer: Make sure to go to the "Actions" tab and run the Pacti Pre-Production workflow manually. This workflow tests the package for functionality and quality on two Python versions.
4. The Pacti Production workflow makes sure that the software works with all OS and all Python versions.
