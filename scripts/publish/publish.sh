#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: working tree is dirty (uncommitted or untracked changes). Commit or stash before releasing." >&2
    exit 1
fi

git clone https://github.com/GrowVolution/WebFluid tmp
cd tmp
pip install -r requirements.txt
python -m build
twine upload dist/*
cd stubs
python -m build
twine upload dist/*
cd ../..
rm -rf tmp