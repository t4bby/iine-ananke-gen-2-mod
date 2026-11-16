from .config import extract_defaults, serialize_mapping
from .container import load_source


def extract(input_bytes: bytes) -> dict[str, bytes]:
    _, _, raw, area = load_source(input_bytes)
    files = {
        "flash.raw.bin": raw,
        "app.bin": area.app,
        "cfg_tool.bin": area.cfg,
    }
    files.update(
        {
            f"mapping/{mode}.json": serialize_mapping(mapping)
            for mode, mapping in extract_defaults(area.app).items()
        }
    )
    return files
