#!/bin/sh
# Download a clean release checkout; never copy API keys or execute npm scripts.
set -eu
for dependency in git node python3; do
  command -v "$dependency" >/dev/null 2>&1 || { echo "Missing requirement: $dependency" >&2; exit 1; }
done
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ is required")'
node -e 'if (Number(process.versions.node.split(".")[0]) < 22) { console.error("Node.js 22+ is required"); process.exit(1); }'
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT HUP INT TERM
git clone --quiet --depth 1 --branch main https://github.com/WaynezProg/jev-kit.git "$temporary/source"
python3 "$temporary/source/scripts/manage.py" install "$@"
printf '\nManage this installation with: %s/.local/share/jev-kit/jev status | update | uninstall\n' "$HOME"
