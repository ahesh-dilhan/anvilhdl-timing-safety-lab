#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 VARIANT TOP RTL_FILE [RTL_FILE ...]" >&2
}

if [[ $# -lt 3 ]]; then
    usage
    exit 2
fi

variant=$1
top=$2
shift 2

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
quartus_args=(
    -t "${script_dir}/run.tcl"
    --variant "${variant}"
    --top "${top}"
)
for rtl_file in "$@"; do
    quartus_args+=(--rtl "${rtl_file}")
done

quartus_sh "${quartus_args[@]}"
