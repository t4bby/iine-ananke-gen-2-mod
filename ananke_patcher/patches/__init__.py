import json
from collections.abc import Iterator
from pathlib import Path

from ..container import AppArea
from ..discovery import resolve
from . import gyro, names, native, templates
from .model import Context, Patch

BUILDERS = (templates.build, native.build, gyro.build, names.build)


def plan(area: AppArea, config: dict) -> Iterator[Patch]:
    layout = json.loads((Path(__file__).parent / "layout.json").read_text())
    context = Context(area, config, layout, resolve(area, layout))
    address = area.app_base + len(area.app)
    for build in BUILDERS:
        patch = build(context, address)
        yield patch
        address += len(patch.payload)
