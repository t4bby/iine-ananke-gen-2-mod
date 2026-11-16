from collections.abc import Iterable
from pathlib import Path

from . import container as fw
from .config import serialize_mapping
from .patches import plan
from .patches.model import Patch

ROOT = Path(__file__).resolve().parents[1]


def generate(
    input_bytes: bytes,
    config: dict,
    source_name: str = "IG05",
    *,
    patches: Iterable[Patch] | None = None,
) -> dict[str, bytes]:
    fw.require(Path(source_name).name == source_name, "Invalid output basename")
    package, member, raw, area = fw.load_source(input_bytes)
    app = bytearray(area.app)
    payload = bytearray()
    sources = []
    touched = set()

    for patch in plan(area, config) if patches is None else patches:
        for edit in patch.edits:
            end = edit.offset + len(edit.data)
            fw.require(
                0 <= edit.offset <= end <= len(app), f"Patch outside application: {edit.name}"
            )
            span = set(range(edit.offset, end))
            fw.require(not touched.intersection(span), f"Overlapping patch: {edit.name}")
            touched.update(span)
            app[edit.offset : end] = edit.data
        payload += patch.payload
        sources.append(patch.assembly)

    assert all(
        patched == original or offset in touched
        for offset, (patched, original) in enumerate(zip(app, area.app))
    ), "Unexpected original application change"
    extension = (len(payload) + 15) & ~15
    app += payload + bytes(extension - len(payload))
    output = fw.repack(package, member, raw, area, app)
    files = {
        f"{source_name}_MOD.ufw": output,
        "app-patched.bin": bytes(app),
        "patch.bin": bytes(payload),
        "patch.s": "".join(sources).encode(),
    }
    files.update(
        {f"mapping/{mode}.json": serialize_mapping(mapping) for mode, mapping in config.items()}
    )
    return files


def write_outputs(output_dir: Path | str, files: dict[str, bytes]) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        target = output_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
