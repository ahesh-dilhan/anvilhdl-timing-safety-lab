PYTHON ?= python3

export PYTHONPATH := $(CURDIR)/src

.PHONY: help doctor validate test demo rtl-demo rtl-questa synth-quartus ci anvil-check

help:
	@echo "AnvilHDL Timing-Safety Lab"
	@echo
	@echo "  make doctor       show required and optional host tools"
	@echo "  make validate     validate metadata, fixtures, scenarios, and links"
	@echo "  make test         run the dependency-free unit/regression suite"
	@echo "  make demo         analyze all bounded timing scenarios"
	@echo "  make rtl-demo     run the dynamic-memory RTL counterexample (Icarus)"
	@echo "  make rtl-questa   run the same RTL benchmark with licensed Questa"
	@echo "  make synth-quartus synthesize both RTL clients on the pinned FPGA"
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

rtl-demo:
	benchmarks/dynamic_memory/sim/run_iverilog.sh

rtl-questa:
	benchmarks/dynamic_memory/sim/run_questa.sh

synth-quartus:
	benchmarks/dynamic_memory/quartus/run_variant.sh unsafe \
		unsafe_dynamic_memory_client \
		benchmarks/dynamic_memory/rtl/unsafe_dynamic_memory_client.sv
	benchmarks/dynamic_memory/quartus/run_variant.sh safe \
		safe_dynamic_memory_client \
		benchmarks/dynamic_memory/rtl/safe_dynamic_memory_client.sv
	$(PYTHON) benchmarks/dynamic_memory/quartus/collect_results.py \
		benchmarks/dynamic_memory/quartus/build/unsafe \
		benchmarks/dynamic_memory/quartus/build/safe \
		--output benchmarks/dynamic_memory/quartus/build/results.csv
	@echo "Parsed results: benchmarks/dynamic_memory/quartus/build/results.csv"

ci: validate test
	$(PYTHON) -m anvil_lab --all --fail-on-mismatch

anvil-check:
	$(PYTHON) scripts/anvil_conformance.py
