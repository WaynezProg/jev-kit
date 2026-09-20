#!/usr/bin/env python3
"""Prove each baseline bug fails and every hidden reference repair passes."""
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS = json.loads((ROOT / "tasks.json").read_text())
FIXES = json.loads((ROOT / "references.json").read_text())

def run(root, test_path):
    return subprocess.run([sys.executable, "-m", "unittest", test_path[:-3].replace("/", ".")], cwd=root, text=True, capture_output=True)

def replace_function(path, symbol, replacement):
    source = path.read_text()
    tree = ast.parse(source)
    node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == symbol)
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = [replacement if replacement.endswith("\n") else replacement + "\n"]
    path.write_text("".join(lines))

for task in TASKS:
    baseline = run(ROOT, task["test_path"])
    if baseline.returncode == 0:
        raise SystemExit(f"baseline unexpectedly passed: {task['id']}")
    with tempfile.TemporaryDirectory() as temporary:
        copied = Path(temporary) / "fixture"
        shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns("corpus.json", "__pycache__"))
        module, symbol = task["gold_ids"][0].split(".")
        replace_function(copied / "modules" / f"{module}.py", symbol, FIXES[task["id"]])
        repaired = run(copied, task["test_path"])
        if repaired.returncode:
            raise SystemExit(f"reference repair failed: {task['id']}\n{repaired.stdout}\n{repaired.stderr}")
    print(f"verified {task['id']}")
