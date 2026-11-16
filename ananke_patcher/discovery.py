import re
import struct

from . import encoding
from .container import AppArea, require


def find(data: bytes, signature: str, label: str) -> int:
    pattern = b"".join(
        b"." if byte == "??" else re.escape(bytes.fromhex(byte)) for byte in signature.split()
    )
    matches = list(re.finditer(pattern, data, re.DOTALL))
    require(len(matches) == 1, f"{label}: expected one signature match, found {len(matches)}")
    offset = matches[0].start()
    require(offset % 2 == 0, f"{label}: unaligned signature")
    return offset


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def resolve(area: AppArea, layout: dict) -> dict:
    app = area.app
    startup = find(app, layout["startup_signature"], "Initialized RAM copy")
    require(startup < 256, "RAM copy is outside the supported startup sequence")
    ram_source = u32(app, startup + 8) - area.app_base
    ram_length = u32(app, startup + 14)
    require(
        0 < ram_source < len(app)
        and 0 < ram_length <= len(app) - ram_source
        and ram_length % 4 == 0,
        "Invalid initialized RAM copy",
    )
    ram = app[ram_source : ram_source + ram_length]
    hooks = {}
    for hook in layout["hooks"]:
        data = ram if hook["region"] == "ram" else app[:ram_source]
        offset = find(data, hook["signature"], hook["label"]) + hook["patch_offset"]
        address = offset if hook["region"] == "ram" else area.app_base + offset
        app_offset = ram_source + offset if hook["region"] == "ram" else offset
        original = app[app_offset : app_offset + hook["size"]]
        require(len(original) == hook["size"], f"{hook['label']}: truncated instruction")
        hooks[hook["label"]] = {"address": address, "app_offset": app_offset, "original": original}
    pairing = hooks["left_entry"]
    offset, address = pairing["app_offset"], pairing["address"]
    role_config = u16(app, offset + 16)
    first, second = u16(app, offset + 34), u16(app, offset + 36)
    require(first & 0xFFCF == 0xE102 and second >> 12 == 8, "Expected mode-configuration address")
    mode_config = encoding.signed(((first >> 4 & 3) << 12) | (second & 0xFFF), 14)
    require(
        0 < mode_config < role_config and role_config - mode_config == 50,
        "Incompatible role/mode configuration layout",
    )
    state_anchor = find(app[:ram_source], layout["state_signature"], "Nintendo report state")
    active_state = u32(app, state_anchor + 2)
    require(0 < active_state and active_state + 16 < ram_length, "Invalid active Nintendo state")
    require(
        0 < hooks["mapping_entry"]["app_offset"] - state_anchor < 256,
        "State anchor does not belong to the report builder",
    )
    # The Pairing handler must use the same state as the report builder.
    require(
        encoding.immediate(4, active_state) in app[max(ram_source, offset - 512) : offset],
        "Pairing and report state pointers disagree",
    )
    led_original = hooks["led_entry"]["original"]
    require(led_original[:2] == encoding.immediate16(3, 0)[:2], "Expected LED connection selector")
    returns = {
        "already_left": encoding.conditional_target(app, offset + 28, address + 28, 1, 3),
        "commit_left": encoding.short_target(app, offset + 50, address + 50),
        "resume_original": address + 6,
    }
    for name, hook in hooks.items():
        if name != "left_entry":
            prefix = name.removesuffix("_entry")
            returns[f"resume_{prefix}"] = hook["address"] + len(hook["original"])
    rotation = hooks["rotation_entry"]
    returns["skip_rotation"] = encoding.conditional_target(
        app, rotation["app_offset"], rotation["address"], 4, 3
    )
    require(
        all(
            0 <= target < ram_length or area.app_base <= target < area.app_base + ram_source
            for target in returns.values()
        ),
        "Return target outside supported code regions",
    )
    # The report mapper assumes this normalized input-to-Nintendo bit table.
    routes = [
        (2, 4),
        (1, 8),
        (16, 1),
        (8, 2),
        (0x40, 0x400000),
        (0x80, 0x40),
        (0x200, 0x80),
        (0x100, 0x800000),
        (0x4000, 0x400),
        (0x2000, 0x800),
        (0x400, 0x100),
        (0x800, 0x200),
        (0x10000, 0x20000),
        (0x20000, 0x10000),
        (0x40000, 0x80000),
        (0x80000, 0x40000),
        (0x1000, 0x1000),
        (0x8000, 0x2000),
        (0x8000000, 0x20),
        (0x10000000, 0x10),
    ]
    table = b"".join(struct.pack("<I", value) for pair in routes for value in pair)
    require(app.count(table) == 1, "Incompatible normalized Nintendo button table")
    global_anchor = find(app[:ram_source], layout["global_signature"], "Global controller state")
    constants = {
        "global_base": u32(app, global_anchor + 44),
        "role_config": role_config,
        "mode_config": mode_config,
        "active_state": active_state,
    }
    return {
        "hooks": hooks,
        "returns": returns,
        "constants": constants,
        "ram_source": ram_source,
        "ram_length": ram_length,
        "led_original": led_original,
    }
