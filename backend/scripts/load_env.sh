#!/bin/bash
set -euo pipefail

env_file="${1:-/app/backend/.env}"

if [ ! -f "$env_file" ]; then
  exit 0
fi

python - "$env_file" <<'PY'
import pathlib
import shlex
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    sys.exit(0)

content = path.read_text(encoding='utf-8')
for raw_line in content.replace('\r\n', '\n').replace('\r', '\n').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue

    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip()

    if not key:
        continue

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]

    print(f"export {shlex.quote(key)}={shlex.quote(value)}")
PY
