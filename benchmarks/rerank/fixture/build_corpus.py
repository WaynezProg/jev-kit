#!/usr/bin/env python3
"""Freeze a retrieval corpus from the authored fixture modules.

Run only before a benchmark campaign.  The resulting corpus.json is checked in
so a campaign never changes its retrieval candidates after observing results.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULES = ROOT / "modules"
items = []
for module_path in sorted(MODULES.glob("*_tools.py")):
    source = module_path.read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # The corpus represents source available to retrieval, but strips
            # prose that could state the corrected requirement verbatim.
            # ast.unparse also removes source comments from this search field.
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:]
            text = ast.unparse(node)
            items.append({
                "id": f"{module_path.stem}.{node.name}",
                "path": f"modules/{module_path.name}",
                "symbol": node.name,
                "text": text,
            })
(ROOT / "corpus.json").write_text(json.dumps(items, indent=2) + "\n")
print(f"wrote {len(items)} corpus entries")
