#!/bin/bash
#Launcher script for MAOnline game server

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):$PYTHONPATH"

#Find conda python - try multiple common locations
CONDA_PYTHON=""
for path in \
    "$HOME/miniconda3/envs/maonline/bin/python" \
    "$HOME/anaconda3/envs/maonline/bin/python" \
    "$(conda info --base 2>/dev/null)/envs/maonline/bin/python"; do
    if [ -f "$path" ]; then
        CONDA_PYTHON="$path"
        break
    fi
done

if [ -z "$CONDA_PYTHON" ] || [ ! -f "$CONDA_PYTHON" ]; then
    echo "Error: Conda environment 'maonline' not found"
    echo "Please ensure the environment is created: conda create -n maonline python=3.9"
    exit 1
fi

"$CONDA_PYTHON" server/game_server.py "$@"

