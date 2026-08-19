PYTHON ?= python3

export PYTHONPATH := $(CURDIR)/src

.PHONY: help doctor validate test demo ci anvil-check

help:
	@echo "AnvilHDL Timing-Safety Lab"
	@echo
	@echo "  make doctor       show required and optional host tools"
	@echo "  make validate     validate metadata, fixtures, scenarios, and links"
	@echo "  make test         run the dependency-free unit/regression suite"
	@echo "  make demo         analyze all bounded timing scenarios"
	@echo "  make ci           run every host-only CI check"
	@echo "  make anvil-check  run fixtures with ANVIL_BIN or ANVIL_COMMAND"

doctor:
	$(PYTHON) scripts/doctor.py

validate:
	$(PYTHON) -m compileall -q src scripts tests
	$(PYTHON) scripts/validate_repository.py

test:
	$(PYTHON) -m unittest discover -s tests -v

demo:
	$(PYTHON) -m anvil_lab --all --fail-on-mismatch

ci: validate test
	$(PYTHON) -m anvil_lab --all --fail-on-mismatch

anvil-check:
	$(PYTHON) scripts/anvil_conformance.py
