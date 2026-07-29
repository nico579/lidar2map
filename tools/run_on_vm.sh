#!/usr/bin/env bash
#
# Compatibility launcher for run_on_vm.py.
#
# Historical syntax remains valid:
#   bash tools/run_on_vm.sh [--bundle] user@host "--lidar ..."
#
# Recommended syntax keeps every remote argument separate:
#   bash tools/run_on_vm.sh --session var-83 user@host -- --lidar ...
#
# The Python controller supervises tmux, synchronizes results progressively and
# can be restarted later with the same VM/session without relaunching lidar2map.

set -euo pipefail

SCRIPT_DIR="$(cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1 &&
   python3 -c "import sys; raise SystemExit(sys.version_info < (3, 8))" \
     >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1 &&
     python -c "import sys; raise SystemExit(sys.version_info < (3, 8))" \
       >/dev/null 2>&1; then
  PYTHON=python
else
  echo "run_on_vm requires Python 3.8 or newer." >&2
  exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/run_on_vm.py" "$@"
