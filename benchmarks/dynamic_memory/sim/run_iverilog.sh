#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
iverilog=${IVERILOG:-iverilog}
vvp=${VVP:-vvp}

for executable in "${iverilog}" "${vvp}"; do
    if ! command -v "${executable}" >/dev/null 2>&1 && [[ ! -x "${executable}" ]]; then
        echo "ERROR simulator=iverilog missing=${executable}" >&2
        exit 2
    fi
done

cd "${script_dir}"
mkdir -p build generated

compile_command=("${iverilog}")
if [[ -n "${IVERILOG_BASE:-}" ]]; then
    compile_command+=("-B" "${IVERILOG_BASE}")
fi
compile_command+=(
    -g2012
    -s tb_dynamic_memory
    -o build/tb_dynamic_memory.vvp
    -f files.f
)

"${compile_command[@]}"
"${vvp}" build/tb_dynamic_memory.vvp \
    +VCD=generated/dynamic_memory.vcd \
    | tee generated/simulation_iverilog.log

if ! grep -q '^RESULT benchmark=dynamic_memory status=PASS ' generated/simulation_iverilog.log; then
    echo "ERROR benchmark=dynamic_memory reason=missing_pass_result" >&2
    exit 1
fi

python3 "${script_dir}/../../../scripts/vcd_trace_hash.py" \
    generated/dynamic_memory.vcd
echo "ARTIFACT benchmark=dynamic_memory log=${script_dir}/generated/simulation_iverilog.log"
echo "ARTIFACT benchmark=dynamic_memory waveform=${script_dir}/generated/dynamic_memory.vcd"
