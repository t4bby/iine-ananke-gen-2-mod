import re
from pathlib import Path
from string import Template

from .. import encoding
from ..container import require
from ..discovery import find, u32
from .model import Context, Edit, Patch


def build(context: Context, address: int) -> Patch:
    area = context.area
    definition = context.layout["names"]
    labels = definition["labels"]
    app = area.app
    base = find(app, definition["base_signature"], "Base device name") + 2
    nintendo = find(app, definition["nintendo_signature"], "Nintendo device name") + 4
    generic = find(app, definition["generic_signature"], "Generic device name") + 10
    base_return = find(app, definition["base_return_signature"], "Base name return")
    generic_return = find(app, definition["generic_return_signature"], "Generic name return")
    original = u32(app, base + 2)
    require(
        app[original - area.app_base : original - area.app_base + 13] == b"IG05 Gamepad\0",
        "Unexpected device name",
    )
    pro = find(app, b"Pro Controller\0slide".hex(" "), "Pro Controller name")
    xbox = find(app, b"\0Xbox Wireless Controller\0".hex(" "), "Xbox device name") + 1
    strings = {
        "gamepad": b"IG05 Gamepad (Tabby)\0",
        "left": b"Joy-Con (L)\0".ljust(14, b"\0"),
        "right": b"Joy-Con (R)\0".ljust(14, b"\0"),
    }
    values = {
        "pro": area.app_base + pro,
        "xbox": area.app_base + xbox,
        "role": context.symbols["constants"]["global_base"]
        + context.symbols["constants"]["role_config"],
    }
    data = bytearray()
    for name, value in strings.items():
        values[name] = address + definition["size"] + len(data)
        data += value
    directory = Path(__file__).parent
    code = bytearray.fromhex((directory / "names.hex").read_text())
    assert len(code) == definition["size"], "Device name template size mismatch"
    for label, value in {
        "base_pro_pointer": "pro",
        "pro_pointer": "pro",
        "xbox_pointer": "xbox",
        "default_pointer": "gamepad",
        "generic_pointer": "gamepad",
        "role_pointer": "role",
        "left_pointer": "left",
        "right_pointer": "right",
    }.items():
        offset = labels[label]
        code[offset : offset + 6] = encoding.immediate(1 if value == "role" else 0, values[value])
    source = Template((directory / "names.s").read_text()).substitute(values)
    for label, target in {
        "name_base_return": base_return,
        "name_nintendo_return": nintendo + 4,
        "name_generic_return": generic_return,
    }.items():
        offset = labels[label]
        destination = area.app_base + target
        code[offset : offset + 4] = encoding.branch(address + offset, destination)
        delta = encoding.signed((destination - address - offset - 4) & 0x1FFFFFF, 25)
        source = re.sub(
            rf"({label}:\n)goto 1000000", lambda match: f"{match[1]}goto {delta}", source
        )
    edits = [
        Edit(
            base,
            encoding.branch(area.app_base + base, address + labels["name_base"]) + encoding.NOP,
            "device_name_base",
        ),
        Edit(
            nintendo,
            encoding.branch(area.app_base + nintendo, address + labels["name_nintendo"]),
            "device_name_nintendo",
        ),
        Edit(
            generic,
            encoding.branch(area.app_base + generic, address + labels["name_generic"]),
            "device_name_generic",
        ),
    ]
    source += "\n" + "".join(
        f"name_{name}_string:\n.byte {', '.join(str(byte) for byte in value)}\n"
        for name, value in strings.items()
    )
    return Patch(bytes(code + data + bytes(len(data) & 1)), f"\n{source}.balign 2\n", edits)
