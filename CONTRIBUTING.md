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
2. run `make check` to check everything (fix any warning)
3. run `make test` to run the tests (fix any issue)
4. if you updated the documentation or the project dependencies:
    1. run `make docs-serve`
    2. go to http://localhost:8000 and check that everything looks good


**Activate Pre-Commit Hooks**
```bash
pre-commit install
```