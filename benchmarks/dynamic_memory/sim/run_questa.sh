#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
questa_bin=${QUESTA_BIN:-${HOME}/intelFPGA_lite/21.1/questa_fse/linux_x86_64}

for executable in vlib vlog vsim; do
    if [[ ! -x "${questa_bin}/${executable}" ]]; then
        echo "ERROR simulator=questa missing=${questa_bin}/${executable}" >&2
        exit 2
    fi
done

cd "${script_dir}"
mkdir -p generated

if [[ -z "${LM_LICENSE_FILE:-}" && -z "${MGLS_LICENSE_FILE:-}" ]]; then
    echo "PREFLIGHT simulator=questa license_environment=UNSET note=set_LM_LICENSE_FILE_if_vsim_reports_checkout_failure"
else
    echo "PREFLIGHT simulator=questa license_environment=SET"
fi

if [[ ! -f work/_info ]]; then
    "${questa_bin}/vlib" work
fi

"${questa_bin}/vlog" -sv -work work -f files.f
if ! "${questa_bin}/vsim" -c -lib work tb_dynamic_memory \
    +VCD=generated/dynamic_memory.vcd -l generated/simulation_questa.log \
    -do run.do; then
    echo "ERROR simulator=questa reason=simulation_failed hint=check_LM_LICENSE_FILE" >&2
    exit 1
fi

if ! grep -q '^# RESULT benchmark=dynamic_memory status=PASS ' generated/simulation_questa.log; then
    echo "ERROR benchmark=dynamic_memory reason=missing_pass_result" >&2
    exit 1
fi

echo "ARTIFACT benchmark=dynamic_memory log=${script_dir}/generated/simulation_questa.log"
echo "ARTIFACT benchmark=dynamic_memory waveform=${script_dir}/generated/dynamic_memory.vcd"
