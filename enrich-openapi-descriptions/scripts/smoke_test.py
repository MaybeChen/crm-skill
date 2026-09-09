#!/usr/bin/env python3
"""Run dependency-free smoke tests for find_missing_descriptions.py."""

from __future__ import annotations

import json
import subprocess
import sys
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
      responses:
        "200":
          schema:
            type: object
definitions:
  Item:
    type: object
    properties:
      itemId:
        type: string
      itemName:
        type: string
        x-description-zh: ""
      knownField:
        type: string
        description: Known description.
'''

EXPECTED = {
    ("info.description", True),
    ("paths./items.post.description", False),
    ("paths./items.post.responses.200.description", False),
    ("definitions.Item.properties.itemId.description", False),
    ("definitions.Item.properties.itemName.description", False),
}


def main() -> int:
    # Do not use tempfile.TemporaryDirectory here. Some embedded or partially
    # relocated Windows Python installations contain mismatched os/shutil
    # modules, which can make TemporaryDirectory cleanup fail after all tests
    # have already passed. A sibling file only needs pathlib.unlink cleanup.
    fixture = Path(__file__).with_name(f".smoke-test-api-{id(scanner)}.yaml")
    try:
        fixture.write_text(FIXTURE, encoding="utf-8")
        items = scanner.scan(fixture)
        actual = {(str(item["path"]), bool(item["present"])) for item in items}
        assert actual == EXPECTED, f"unexpected inventory: {actual!r}"
        all_items = scanner.scan(fixture, include_populated=True)
        populated = {str(item["path"]): item for item in all_items}
        known = populated["definitions.Item.properties.knownField.description"]
        assert known["empty"] is False
        assert known["value"] == "Known description."

        script = Path(__file__).with_name("find_missing_descriptions.py")
        json_output = subprocess.run(
            [sys.executable, str(script), str(fixture), "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert len(json.loads(json_output)["items"]) == 5
        all_json_output = subprocess.run(
            [sys.executable, str(script), str(fixture), "--include-populated", "--format", "json"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert any(
            item["path"] == "definitions.Item.properties.knownField.description"
            for item in json.loads(all_json_output)["items"]
        )
        markdown_output = subprocess.run(
            [sys.executable, str(script), str(fixture), "--format", "markdown"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert "info.description" in markdown_output
    finally:
        fixture.unlink(missing_ok=True)

    print("smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
