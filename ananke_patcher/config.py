import json
import struct
from pathlib import Path

from .container import require
from .discovery import find

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "mapping"
BUTTONS = (
    "A",
    "B",
    "C",
    "X",
    "Y",
    "Z",
    "L",
    "R",
    "ZL",
    "ZR",
    "Minus",
    "Plus",
    "Home",
    "L3",
    "R3",
    "Capture",
    "Up",
    "Down",
    "Left",
    "Right",
    "Menu",
    "Mode",
    "Fn",
    *(f"M{i}" for i in range(1, 9)),
)
BANKS = {
    "left_joycon": "gamepad",
    "right_joycon": "gamepad",
    "switch_pro": "gamepad",
    "xinput": "gamepad",
    "hid": "gamepad",
    "keyboard": "keyboard",
    "mouse": "mouse",
    "multimedia": "consumer",
    "touch": "touch",
}
GYRO_MODES = ("switch_pro", "xinput", "hid")
GYRO_DEFAULTS = {"sensitivity": 32, "deadzone": 8, "invert_x": True, "invert_y": False}
TYPES = {"gamepad": 1, "keyboard": 2, "mouse": 3, "consumer": 4}
ACTION_FIELDS = {
    "gamepad": {"buttons"},
    "keyboard": {"modifiers", "keys"},
    "mouse": {"buttons", "x", "y", "wheel"},
    "consumer": {"usage", "extra"},
}
MOUSE_AXES = {"x": 0x40, "y": 0x80, "wheel": 0x20}
ENTRY = struct.Struct("<BBHH")
TOUCH = struct.Struct("<4BI2H")
BANK_SIZE = 192
BUTTON_MASK = (1 << len(BUTTONS)) - 1


def validate_integer(value: object, low: int, high: int) -> int:
    require(
        type(value) is int and low <= value <= high, f"Expected integer {low}..{high}: {value!r}"
    )
    return value


def button_mask(names: list[str]) -> int:
    require(
        isinstance(names, list) and all(name in BUTTONS for name in names), "Unknown gamepad button"
    )
    return sum(1 << BUTTONS.index(name) for name in set(names))


def decode_action(record: bytes, index: int, bank: str) -> str | dict | None:
    kind, attributes, value, extra = ENTRY.unpack(record)
    if record == bytes(ENTRY.size):
        return BUTTONS[index] if bank == "gamepad" else None
    if kind == 1 and attributes == 0 and not ((value | extra << 16) & ~BUTTON_MASK):
        bits = value | extra << 16
        return {
            "type": "gamepad",
            "buttons": [name for i, name in enumerate(BUTTONS) if bits & (1 << i)],
        }
    if kind == 2 and attributes == 0:
        keys = [value >> 8, extra & 255, extra >> 8]
        while keys and keys[-1] == 0:
            keys.pop()
        return {"type": "keyboard", "modifiers": value & 255, "keys": keys}
    if kind == 3 and attributes == 0 and extra == 0:
        flags, amount = value & 255, value >> 8
        axes = flags & 0xE0
        if axes in (0x20, 0x40, 0x80) or axes == amount == 0:
            action = {"type": "mouse", "buttons": flags & 31}
            if axes:
                action[{0x20: "wheel", 0x40: "x", 0x80: "y"}[axes]] = (
                    amount - 256 if amount >= 128 else amount
                )
            return action
    if kind == 4 and attributes == 0:
        return {"type": "consumer", "usage": value, "extra": extra}
    return {"type": "raw", "bytes": record.hex()}


def encode_action(action: str | dict | None, index: int, bank: str) -> bytes:
    if isinstance(action, str):
        require(bank == "gamepad" and action in BUTTONS, f"Unknown gamepad action: {action!r}")
        if action == BUTTONS[index]:
            return bytes(ENTRY.size)  # Native pass-through, including analog trigger handling.
        action = {"type": "gamepad", "buttons": [action]}
    if action is None:
        return ENTRY.pack(TYPES["gamepad"] if bank == "gamepad" else 0, 0, 0, 0)
    require(isinstance(action, dict), f"Invalid action: {action!r}")
    kind = action.get("type")
    if kind == "raw":
        require(set(action) == {"type", "bytes"}, "Unknown raw action field")
        data = bytes.fromhex(action["bytes"])
        require(len(data) == ENTRY.size, "Raw action must contain six bytes")
        if data[0] & 7 == TYPES["gamepad"]:
            require(
                not (int.from_bytes(data[2:], "little") & ~BUTTON_MASK),
                "Power cannot be a mapping target",
            )
        return data
    require(
        kind in ACTION_FIELDS and not (set(action) - ACTION_FIELDS[kind] - {"type"}),
        f"Unknown action or field: {action!r}",
    )
    value = extra = 0
    if kind == "gamepad":
        bits = button_mask(action.get("buttons", []))
        value, extra = bits & 65535, bits >> 16
    elif kind == "keyboard":
        keys = action.get("keys", [])
        require(
            isinstance(keys, list) and len(keys) <= 3,
            "Keyboard action supports up to three keycodes",
        )
        keys = [validate_integer(key, 0, 255) for key in keys] + [0] * (3 - len(keys))
        value = validate_integer(action.get("modifiers", 0), 0, 255) | keys[0] << 8
        extra = keys[1] | keys[2] << 8
    elif kind == "mouse":
        value = validate_integer(action.get("buttons", 0), 0, 31)
        axes = [axis for axis in MOUSE_AXES if axis in action]
        require(len(axes) <= 1, "A native mouse action supports one movement axis or wheel")
        if axes:
            axis = axes[0]
            value |= MOUSE_AXES[axis]
            value |= (validate_integer(action[axis], -128, 127) & 255) << 8
    else:
        value = validate_integer(action.get("usage", 0), 0, 65535)
        extra = validate_integer(action.get("extra", 0), 0, 65535)
    return ENTRY.pack(TYPES[kind], 0, value, extra)


def locate_defaults(app: bytes) -> dict[str, int]:
    start = find(
        app,
        "02 00 00 04 00 00 02 00 00 05 00 00 00 00 00 00 00 00 02 00 00 1b 00 00",
        "Native keyboard/mouse/consumer defaults",
    )
    touch = find(app, "13 06 00 32 00 00 01 00 d0 07 d0 07", "Native touch defaults")
    require(
        start + 3 * BANK_SIZE <= len(app) and touch + BANK_SIZE <= len(app),
        "Truncated native defaults",
    )
    return {
        "keyboard": start,
        "mouse": start + BANK_SIZE,
        "consumer": start + 2 * BANK_SIZE,
        "touch": touch,
    }


def read_default_banks(app: bytes) -> dict[str, bytes]:
    offsets = locate_defaults(app)
    return {
        "gamepad": bytes(BANK_SIZE),
        **{bank: app[offset : offset + BANK_SIZE] for bank, offset in offsets.items()},
    }


def extract_defaults(app: bytes) -> dict:
    return _decode_banks(read_default_banks(app))


def _decode_banks(raw: dict) -> dict:
    banks = {
        bank: {
            name: decode_action(data[i * ENTRY.size : (i + 1) * ENTRY.size], i, bank)
            for i, name in enumerate(BUTTONS)
        }
        for bank, data in raw.items()
        if bank != "touch"
    }
    touch = {}
    for flags, p0, p1, p2, source, x, y in TOUCH.iter_unpack(raw["touch"]):
        require(source and source & (source - 1) == 0, "Unsupported touch input mask")
        index = source.bit_length() - 1
        if index >= len(BUTTONS):
            continue  # Preserve the reserved Power record without exposing it in JSON.
        name = BUTTONS[index]
        require(name not in touch, "Duplicate native touch input")
        touch[name] = {"flags": flags, "parameters": [p0, p1, p2], "x": x, "y": y}
    banks["touch"] = touch
    return {
        mode: {
            "buttons": banks[bank].copy(),
            **({"gyro": GYRO_DEFAULTS.copy()} if mode in GYRO_MODES else {}),
        }
        for mode, bank in BANKS.items()
    }


def load_mappings(path: Path = DEFAULT_PATH) -> dict:
    config = {}
    for mode in BANKS:
        item = json.loads((Path(path) / f"{mode}.json").read_text())
        require(
            set(item) == ({"buttons", "gyro"} if mode in GYRO_MODES else {"buttons"})
            and isinstance(item["buttons"], dict),
            f"{mode}: expected buttons object; gyro settings apply only to Switch Pro, XInput and HID",
        )
        config[mode] = item
    return config


def encode_touch(source: int, action: dict) -> bytes:
    require(
        isinstance(action, dict) and set(action) == {"flags", "parameters", "x", "y"},
        "Touch actions need flags, parameters, x and y",
    )
    params = action["parameters"]
    require(isinstance(params, list) and len(params) == 3, "Touch parameters need three bytes")
    values = [
        validate_integer(action["flags"], 0, 255),
        *(validate_integer(p, 0, 255) for p in params),
    ]
    return TOUCH.pack(
        *values,
        source,
        validate_integer(action["x"], 0, 65535),
        validate_integer(action["y"], 0, 65535),
    )


def compile_banks(config: dict, app: bytes) -> dict[str, bytes]:
    raw = read_default_banks(app)
    original = _decode_banks(raw)
    banks = {}
    for mode, bank in BANKS.items():
        buttons = config[mode]["buttons"]
        require(
            set(buttons) == set(original[mode]["buttons"]),
            f"{mode}: keep the native input names; Power is not editable",
        )
        if bank == "touch":
            data = bytearray(raw[bank])
            for offset in range(0, len(data), TOUCH.size):
                source = TOUCH.unpack_from(data, offset)[4]
                index = source.bit_length() - 1
                if index < len(BUTTONS):
                    data[offset : offset + TOUCH.size] = encode_touch(
                        source, buttons[BUTTONS[index]]
                    )
            data = bytes(data)
        else:
            data = b"".join(encode_action(buttons[name], i, bank) for i, name in enumerate(BUTTONS))
            data += raw[bank][len(BUTTONS) * ENTRY.size :]  # Keep the reserved Power slot intact.
        require(
            bank not in banks or banks[bank] == data,
            f"{mode}: native gamepad settings are shared; use the same assignments in all gamepad JSON files",
        )
        banks[bank] = data
    return banks


def serialize_mapping(mapping: dict) -> bytes:
    sections = []
    for section, entries in mapping.items():
        rows = [f"{json.dumps(name)}: {json.dumps(value)}" for name, value in entries.items()]
        body = ",\n    ".join(rows)
        sections.append(f"{json.dumps(section)}: {{\n    {body}\n  }}")
    body = ",\n  ".join(sections)
    return f"{{\n  {body}\n}}\n".encode()
