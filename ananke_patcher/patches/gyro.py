import re
import struct
from pathlib import Path
from string import Template

from .. import encoding
from ..config import GYRO_DEFAULTS, GYRO_MODES, validate_integer
from ..container import require
from ..discovery import find, u16
from .model import Context, Edit, Patch


def build(context: Context, address: int) -> Patch:
    area = context.area
    symbols = context.symbols
    definition = context.layout["gyro"]
    ram_source = symbols["ram_source"]
    ram = area.app[ram_source : ram_source + symbols["ram_length"]]
    combo = find(ram, definition["combo_signature"], "Gyro shortcut")
    release = find(ram, definition["release_signature"], "Gyro release")
    report = find(area.app, definition["report_signature"], "Gamepad report")
    xinput = find(area.app, definition["xinput_signature"], "XInput report") + 14
    keys = find(ram, definition["keys_signature"], "Physical key index")
    latch = u16(ram, combo + 20)
    dpad = u16(ram, combo + 42)
    key_index = u16(ram, keys + 2)
    global_base = symbols["constants"]["global_base"]
    require(u16(ram, release + 2) == latch, "Shortcut latch mismatch")
    require(dpad == symbols["constants"]["role_config"] - 2, "D-pad setting mismatch")
    require(
        u16(ram, keys + 6) == key_index + 7 and u16(ram, keys + 10) == key_index + 8,
        "Key array layout changed",
    )
    require(encoding.immediate(8, global_base) in ram[:combo], "Global state mismatch")
    save = encoding.call_target(ram, combo + 58, 0) & 0x1FFFFFF
    require(area.app_base <= save < area.app_base + len(area.app), "Save call outside application")
    settings_data = bytearray()
    listing = []
    for mode in GYRO_MODES:
        settings = context.config[mode]["gyro"]
        require(
            isinstance(settings, dict) and set(settings) == set(GYRO_DEFAULTS),
            f"{mode}: invalid gyro settings",
        )
        gain = validate_integer(settings["sensitivity"], 1, 1024)
        deadzone = validate_integer(settings["deadzone"], 0, 32767)
        require(
            type(settings["invert_x"]) is bool and type(settings["invert_y"]) is bool,
            f"{mode}: gyro inversion settings must be booleans",
        )
        gain_x = -gain if settings["invert_x"] else gain
        gain_y = -gain if settings["invert_y"] else gain
        settings_data += struct.pack("<hhH", gain_x, gain_y, deadzone)
        listing.append(f"gyro_{mode}_settings:\n.short {gain_x}, {gain_y}, {deadzone}\n")
    values = {
        "latch": latch,
        "indicator": latch - 12,
        "dpad": dpad,
        "active_state": symbols["constants"]["active_state"],
        "global_base": global_base,
        "physical": key_index * 4,
        "settings": address + definition["size"],
    }
    directory = Path(__file__).parent
    code = bytearray.fromhex((directory / "gyro.hex").read_text())
    assert len(code) == definition["size"], "Gyro template size mismatch"
    labels = definition["labels"]
    slots = {
        "release_offset": (1, "latch"),
        "minus_offset": (1, "latch"),
        "indicator_offset": (1, "indicator"),
        "mode_offset": (1, "dpad"),
        "combo_state": (3, "active_state"),
        "plus_offset": (1, "latch"),
        "report_state": (2, "active_state"),
        "report_global": (2, "global_base"),
        "physical_offset": (3, "physical"),
        "report_offset": (3, "latch"),
    }
    for label, (register, value) in slots.items():
        offset = labels[label]
        code[offset : offset + 4] = encoding.immediate16(register, values[value])
    offset = labels["settings_pointer"]
    code[offset : offset + 6] = encoding.immediate(3, values["settings"])
    source = Template((directory / "gyro.s").read_text()).substitute(values)
    for label, target in {
        "save_call": save,
        "gyro_resume": release + 10,
        "report_return": area.app_base + report + 4,
        "xinput_return": area.app_base + xinput + 4,
    }.items():
        offset = labels[label]
        link = label == "save_call"
        code[offset : offset + 4] = encoding.branch(address + offset, target, link=link)
        delta = encoding.signed((target - address - offset - 4) & 0x1FFFFFF, 25)
        instruction = "call" if link else "goto"
        source = re.sub(
            rf"({label}:\n){instruction} 1000000",
            lambda match: f"{match[1]}{instruction} {delta}",
            source,
        )
    code += settings_data
    source += "\n" + "".join(listing)
    edits = [
        Edit(
            ram_source + combo,
            encoding.branch(combo, address + labels["gyro_combo"]) + encoding.NOP,
            "gyro_shortcut",
        ),
        Edit(
            report,
            encoding.branch(area.app_base + report, address + labels["gyro_report"]),
            "gyro_report",
        ),
        Edit(
            xinput,
            encoding.branch(area.app_base + xinput, address + labels["gyro_xinput"]),
            "gyro_xinput",
        ),
    ]
    return Patch(bytes(code), f"\n{source}", edits)
