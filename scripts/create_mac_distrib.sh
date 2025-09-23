#!/usr/bin/env bash

set -e


FREEZE_SCRIPT=$(dirname "$0")/create_standalone/create_standalone.py
DEFAULT_BUILD_VENV=$(mktemp -d)
# WITH_DEBUG='YES'
default_python_path=$(which python3)
scriptDir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
PROJECT_ROOT=$(realpath "$scriptDir/..")

create_standalone(){
    uv_path=$1
    echo 'create_standalone'
    shift;

#     Generates the .egg-info needed for the version metadata
#     temp_dir=$(mktemp -d)
#     trap 'echo "Cleaning up temporary build environment" && rm -rf ${temp_dir}' RETURN
#     UV_PROJECT_ENVIRONMENT="${temp_dir}/build_mac_standalone_venv" $uv_path build --wheel
    BOOTSTRAP_SCRIPT="${scriptDir}/create_standalone/bootstrap_standalone.py"
    $uv_path run --isolated --frozen --no-managed-python --group freeze --no-dev "$FREEZE_SCRIPT" gce "$BOOTSTRAP_SCRIPT" ${WITH_DEBUG:+--build-with-debug}
}


create_venv() {
    base_python_path=$1
    venv_path=$2
    $base_python_path -m venv $venv_path
    . $venv_path/bin/activate
    python -m pip install --disable-pip-version-check uv
    deactivate
}

if ! command -v uv 2>&1 >/dev/null
then
    build_venv=$DEFAULT_BUILD_VENV
    python_path=$default_python_path

    create_venv $python_path $build_venv
    trap "rm -rf $build_venv" EXIT
    uv_exec="$build_venv/bin/uv"
else
    uv_exec=$(which uv)
fi

create_standalone $uv_exec
