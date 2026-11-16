#!/usr/bin/env python3
"""Extract or patch IINE Mini Ananke Gen 2 firmware."""

import argparse
import struct
import sys
from pathlib import Path

from ananke_patcher.builder import ROOT, generate, write_outputs
from ananke_patcher.config import DEFAULT_PATH, load_mappings
from ananke_patcher.extraction import extract


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--extract",
        dest="mode",
        action="store_const",
        const="extract",
        help="Extract firmware and default mappings",
    )
    modes.add_argument(
        "--apply",
        dest="mode",
        action="store_const",
        const="apply",
        help="Apply patches and configured mappings",
    )
    parser.add_argument("firmware", type=Path, help="Original IG05 firmware package")
    parser.add_argument(
        "--mapping", type=Path, help="Mapping directory for --apply (default: mapping/)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="New output directory (default: build/extracted or build/firmware)",
    )
    args = parser.parse_args(argv)
    if args.mode == "extract" and args.mapping is not None:
        parser.error("--mapping is only available with --apply")

    data = args.firmware.read_bytes()
    if args.mode == "extract":
        files = extract(data)
        output = args.output or ROOT / "build/extracted"
        result = output
    else:
        files = generate(data, load_mappings(args.mapping or DEFAULT_PATH), args.firmware.stem)
        output = args.output or ROOT / "build/firmware"
        result = output / f"{args.firmware.stem}_MOD.ufw"
    write_outputs(output, files)
    print(result)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, struct.error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
