#!/usr/bin/env python3
"""Create a byte-identical working copy of an OpenAPI YAML source file."""

from __future__ import annotations

import argparse
from pathlib import Path


def default_output(source: Path) -> Path:
    if source.suffix.lower() in {".yaml", ".yml"}:
        return source.with_name(f"{source.stem}.enriched{source.suffix}")
    return source.with_name(f"{source.name}.enriched.yaml")


def create_working_copy(source: Path, output: Path | None = None) -> Path:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"source YAML does not exist: {source}")
    destination = (output or default_output(source)).resolve()
    if destination == source:
        raise ValueError("output must differ from the source YAML")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing working copy: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="original YAML; it is never modified")
    parser.add_argument("--output", type=Path, help="working-copy path (default: <name>.enriched.yaml)")
    args = parser.parse_args()
    try:
        destination = create_working_copy(args.source, args.output)
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        parser.error(str(error))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
