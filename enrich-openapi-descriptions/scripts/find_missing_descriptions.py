#!/usr/bin/env python3
"""Inventory empty or absent standard descriptions in Swagger/OpenAPI YAML.

This deliberately uses the standard library and scans YAML structure by indentation,
so it does not reserialize or modify the source file.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>(?:[^:#]|:(?!\s))+|['\"].+['\"]):(?:\s*(?P<value>.*?))?\s*$")
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
EMPTY_VALUES = {"", "''", '""', "null", "~"}


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def scan(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8-sig")
    stack: list[tuple[int, str]] = []
    found: list[dict[str, object]] = []
    nodes: dict[tuple[str, ...], int] = {}

    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith(("#", "- ")):
            continue
        match = KEY_RE.match(line)
        if not match:
            continue
        indent = len(match.group("indent").expandtabs(2))
        key = unquote(match.group("key").strip())
        value = (match.group("value") or "").split(" #", 1)[0].strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parts = [item[1] for item in stack] + [key]
        nodes[tuple(parts)] = lineno

        if key == "description" and value.lower() in EMPTY_VALUES:
            parent = parts[-2] if len(parts) > 1 else ""
            if parts[:2] == ["info", "description"]:
                kind = "service"
            elif any(part.lower() in HTTP_METHODS for part in parts):
                kind = "operation-or-member"
            elif "properties" in parts or "definitions" in parts or "schemas" in parts:
                kind = "field-or-schema"
            else:
                kind = "other"
            found.append({"line": lineno, "path": ".".join(parts), "parent": parent, "kind": kind, "present": True})

        # Scalars cannot own nested keys, but empty mappings can.
        if value == "" or value in {"{}", "[]"}:
            stack.append((indent, key))

    existing_paths = {str(item["path"]) for item in found}

    def add_absent(parent: tuple[str, ...], kind: str) -> None:
        candidate = parent + ("description",)
        dotted = ".".join(candidate)
        has_description = candidate in nodes
        if not has_description and dotted not in existing_paths:
            found.append({
                "line": nodes[parent],
                "path": dotted,
                "parent": parent[-1],
                "kind": kind,
                "present": False,
            })

    if ("info",) in nodes:
        add_absent(("info",), "service")
    for node in nodes:
        if len(node) >= 3 and node[0] == "paths" and node[-1].lower() in HTTP_METHODS:
            add_absent(node, "operation")
        if len(node) >= 5 and node[0] == "paths" and node[-2] == "responses":
            add_absent(node, "response")
        if len(node) >= 2 and node[-2] == "properties":
            add_absent(node, "field")

    found.sort(key=lambda item: (int(item["line"]), str(item["path"])))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_file", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    items = scan(args.yaml_file)
    if args.format == "json":
        print(json.dumps({"file": str(args.yaml_file), "count": len(items), "items": items}, ensure_ascii=False, indent=2))
    else:
        print("| line | kind | key present | YAML path |")
        print("|---:|---|:---:|---|")
        for item in items:
            safe_path = str(item["path"]).replace("|", "\\|")
            present = "yes" if item["present"] else "no"
            print(f'| {item["line"]} | {item["kind"]} | {present} | `{safe_path}` |')
        print(f"\nTotal: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
