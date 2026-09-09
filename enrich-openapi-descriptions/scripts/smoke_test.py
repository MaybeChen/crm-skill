#!/usr/bin/env python3
"""Run dependency-free smoke tests for find_missing_descriptions.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import find_missing_descriptions as scanner


FIXTURE = '''swagger: "2.0"
info:
  description: ""
  title: Test API
paths:
  /items:
    post:
      operationId: createItem
definitions:
  Item:
    type: object
    properties:
      itemId:
        type: string
      itemName:
        type: string
        x-description-zh: ""
'''

EXPECTED = {
    ("info.description", True),
    ("paths./items.post.description", False),
    ("definitions.Item.properties.itemId.x-description-zh", False),
    ("definitions.Item.properties.itemName.x-description-zh", True),
}


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory) / "api.yaml"
        fixture.write_text(FIXTURE, encoding="utf-8")
        items = scanner.scan(fixture)
        actual = {(str(item["path"]), bool(item["present"])) for item in items}
        assert actual == EXPECTED, f"unexpected inventory: {actual!r}"

        script = Path(__file__).with_name("find_missing_descriptions.py")
        json_output = subprocess.run(
            [sys.executable, str(script), str(fixture), "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert len(json.loads(json_output)["items"]) == 4
        markdown_output = subprocess.run(
            [sys.executable, str(script), str(fixture), "--format", "markdown"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert "info.description" in markdown_output

    print("smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
