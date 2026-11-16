from .. import encoding
from ..config import compile_banks, locate_defaults
from ..container import require
from ..discovery import find
from .model import Context, Edit, Patch


def build(context: Context, payload_address: int) -> Patch:
    app, app_base = context.area.app, context.area.app_base
    config = context.config
    banks = compile_banks(config, app)
    changes, offsets = [], locate_defaults(app)
    for bank, offset in offsets.items():
        data = banks[bank]
        if app[offset : offset + len(data)] != data:
            changes.append((offset, data, f"native_{bank}_defaults"))
    code, assembly = b"", ""
    if any(banks["gamepad"]):
        # Both factory reset and invalid/missing-profile initialization zero bank 4.
        # Redirect their memset calls to a tail-call wrapper around the native memcpy.
        sites = {
            "factory_reset": "41 20 72 20 74 20 50 16",
            "profile_init": "00 e1 08 d0 41 20 72 20",
            "app_set": "41 20 72 20 74 20 f0 16",
            "app_get": "41 20 72 20 a0 16",
            "usb_init": "58 88 41 20 72 20",
        }
        calls = {
            name: find(app, signature, f"Gamepad {name}") + len(signature.split())
            for name, signature in sites.items()
        }
        boot = calls["profile_init"]
        copy_call = boot + 44
        require(
            app[copy_call - 2 : copy_call] == bytes.fromhex("7220"), "Native memcpy anchor changed"
        )
        target = encoding.call_target(app, copy_call, app_base)
        memset = encoding.call_target(app, boot, app_base)
        require(target != memset, "Native copy and fill calls must differ")
        table_address = payload_address + 10
        code = (
            encoding.immediate(1, table_address)
            + encoding.branch(payload_address + 6, target)
            + banks["gamepad"]
        )
        for name, offset in calls.items():
            require(
                encoding.call_target(app, offset, app_base) == memset,
                "Gamepad initialization fill calls disagree",
            )
            call = encoding.branch(app_base + offset, payload_address, link=True)
            changes.append((offset, call, f"native_gamepad_{name}"))
        delta = encoding.signed((target - payload_address - 10) & 0x1FFFFFF, 25)
        assembly = f"\n// Native gamepad defaults wrapper\nr1 = {table_address:#x}\ngoto {delta}\n"
    edits = [Edit(offset, data, name) for offset, data, name in changes]
    return Patch(bytes(code), assembly, edits)
