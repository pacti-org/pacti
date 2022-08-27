.PHONY: create
create:
	pdm venv create --with conda

.PHONY: activate
activate:
	conda activate ./.venv

.PHONY: conda
conda:
	conda env update --file environment.yml --prune

.PHONY: pdm
pdm:
	pdm install

.PHONY: docs
docs:
	sphinx-build -b html docs/source docs/_build

#* Cleaning
.PHONY: pycache-remove
pycache-remove:
	find . | grep -E r"(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

.PHONY: dsstore-remove
dsstore-remove:
	find . | grep -E ".DS_Store" | xargs rm -rf

.PHONY: mypycache-remove
mypycache-remove:
	find . | grep -E ".mypy_cache" | xargs rm -rf

.PHONY: ipynbcheckpoints-remove
ipynbcheckpoints-remove:
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf

.PHONY: pytestcache-remove
pytestcache-remove:
	find . | grep -E ".pytest_cache" | xargs rm -rf

.PHONY: build-remove
build-remove:
	rm -rf build/

.PHONY: cleanup
cleanup: pycache-remove dsstore-remove mypycache-remove ipynbcheckpoints-remove pytestcache-remove
