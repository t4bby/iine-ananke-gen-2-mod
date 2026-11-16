import re
from pathlib import Path
from string import Template

from .. import encoding
from ..container import require
from .model import Context, Edit, Patch

DIRECTORY = Path(__file__).resolve().parent
ENCODERS = {
    "immediate16": lambda slot, value: encoding.immediate16(slot["register"], value),
    "add14": lambda slot, value: encoding.add14(slot["register"], slot["base"], value),
}


def build(context: Context, address: int) -> Patch:
    code = bytearray()
    labels = {}
    sources = []
    symbols = context.symbols
    values = {
        **symbols["constants"],
        "active_state": f"{symbols['constants']['active_state']:#x}",
        "led_selector": int.from_bytes(symbols["led_original"][2:], "little"),
    }
    for definition in context.layout["templates"]:
        name = definition["name"]
        data = bytearray.fromhex((DIRECTORY / f"{name}.hex").read_text())
        assert len(data) == definition["size"], f"{name}: unexpected template size"
        start = len(code)
        for slot in definition.get("constants", []):
            require(slot["kind"] in ENCODERS, f"Unknown instruction encoding: {slot['kind']}")
            encoded = ENCODERS[slot["kind"]](slot, symbols["constants"][slot["value"]])
            data[slot["offset"] : slot["offset"] + len(encoded)] = encoded
        for label, offset in definition["labels"].items():
            require(label not in labels, f"Duplicate patch label: {label}")
            labels[label] = start + offset
            if label in symbols["returns"]:
                data[offset : offset + 4] = encoding.branch(
                    address + start + offset, symbols["returns"][label]
                )
        for label, symbol in definition.get("originals", {}).items():
            offset = definition["labels"][label]
            original = symbols[symbol]
            data[offset : offset + len(original)] = original
        code += data
        source = Template((DIRECTORY / definition["source"]).read_text()).substitute(values)
        sources.append(source)
    assembly = "\n".join(sources)
    for label, target in symbols["returns"].items():
        if label in labels:
            displacement = encoding.signed((target - address - labels[label] - 4) & 0x1FFFFFF, 25)
            assembly = re.sub(
                rf"({re.escape(label)}:\n)goto 1000000",
                lambda match: f"{match[1]}goto {displacement}",
                assembly,
            )
    edits = []
    for name, hook in symbols["hooks"].items():
        if name not in labels:
            continue
        size = len(hook["original"])
        require(size >= 4 and size % 2 == 0, f"Invalid hook span: {name}")
        data = encoding.branch(hook["address"], address + labels[name])
        data += encoding.NOP * ((size - 4) // 2)
        edits.append(Edit(hook["app_offset"], data, name))
    return Patch(bytes(code), assembly, edits)
