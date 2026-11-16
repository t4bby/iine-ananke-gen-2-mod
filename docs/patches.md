# Firmware patches

The generator reads the UFW/JLFS directories and embedded scrambling key, then locates code and data by signatures. `ananke_patcher/patches/layout.json` defines masked signatures and template operand slots. `discovery.py` resolves the initialized RAM copy, mode/role fields, state pointer and branch destinations. Missing or ambiguous matches stop generation.

## Joy-Con changes

| Hook | Purpose |
| --- | --- |
| `left_entry` | Pairing + L selects Nintendo role 1. |
| `mapping_entry` | Left report: rotate D-pad to stick and Y/A/B/X to Up/Down/Left/Right; duplicate R/ZR to L/ZL. |
| `rotation_entry` | Bypass sideways rotation for Left. |
| `conversion_entry` | Preserve direction bits until the Left report mapper. |
| `led_entry` | Select player LED mask 1 for Left. |

Assembly sources describe injected instructions; `.hex` templates provide their encoded bytes. The ordered `templates` list in `layout.json` defines each template's source, size, labels, constant slots and displaced instructions. Assembly placeholders such as `${role_config}` are filled from discovered symbols before writing the listing.

## Native mapping defaults

The native configuration has a 112-byte main record followed by five 200-byte banks: keyboard, mouse, consumer, touch and gamepad. Each bank has an eight-byte header and a 192-byte payload. Gamepad modes share the same bank.

Keyboard, mouse, consumer and gamepad payloads contain 32 six-byte `<BBHH` records: type, attributes, value and extra. Types 1/2/3/4 select gamepad/keyboard/mouse/consumer actions. An all-zero gamepad entry means pass-through; type 1 with a zero destination mask disables the input.

Power occupies the final reserved slot. It is excluded from editable inputs and destination masks. The generator preserves its original record when rebuilding a bank.

Touch uses sixteen `<4BI2H` records: flags, three parameters, input mask, X and Y. Reserved Power records, if present, are preserved here too.

Keyboard, mouse, consumer and touch defaults are located by signatures and replaced in place. Custom gamepad defaults replace zero-initialization at five signature-resolved call sites: factory reset, profile initialization, app set/get fallbacks and USB initialization. Each calls a small wrapper that loads the new table pointer and tail-calls the firmware's memcpy. The original header, CRC and save/load code stays in use.

Existing saved profiles override factory defaults. The [mapping guide](mapping.md) describes how to edit the JSON and load the new defaults.

## Package output

The application grows with 16-byte padding; `cfg_tool.bin` follows it. Flash growth uses 4 KiB alignment and stays within the next protected region. The generator rebuilds affected CRCs and reads the output package again. Encrypted UFW members use the trailer key and their file offsets. If flash growth moves a member, the generator decrypts it at its original offset and encrypts it at its new offset, including encrypted padding. Decoded metadata stays unchanged. All UFW member CRCs are checked after decryption.

The output includes the `.ufw`, decoded patched application, injected code/data, assembly listing and mapping JSON files. Only the `.ufw` is passed to the firmware updater.

## Adding patches

`builder.py` consumes patch objects and handles bounds, overlap checks and package rebuilding. It has no controller-specific patch logic.

Add a provider under `ananke_patcher/patches/` with `build(context, address) -> Patch`, then register it in `BUILDERS` in that package's `__init__.py`. Providers run in order. `context` contains the decoded application, mapping configuration, layout and discovered symbols; `address` is where that provider's payload will be appended.

A `Patch` contains optional `payload` bytes, an `assembly` listing, and `Edit` objects. Each edit identifies an application offset, replacement bytes and a name. For RAM-resident code, use its stored application offset when creating the edit. A provider can return only edits when no injected payload is necessary.

For another preassembled template, append a definition to the `templates` list in `layout.json`. The template provider resolves its constants, labels, return branches and displaced instructions. Add any new firmware-specific discovery logic to the patch layer rather than the builder.

Callers may also pass their own ordered `patches` iterable to `generate()` instead of using the registered providers.

## Gyro-to-stick provider

`gyro.py` locates three hooks by signatures: the RAM shortcut handler, the shared gamepad send path, and the separate XInput send path. The send hooks run after native D-pad conversion and right-stick initialization. The shared hook also runs after Nintendo's sideways rotation, so later transforms cannot overwrite the generated stick values.

The existing shortcut latch uses bits 0 (Minus latch), 1 (Plus latch) and 7 (gyro enabled). Releasing a shortcut clears the debounce bits while preserving bit 7. The replacement bypasses the original whole-byte accesses to this latch. Its location is decoded from the original instructions; no additional RAM or persistent configuration format is needed.

Minus performs the native toggle and calls the original save routine. Plus toggles the temporary gyro bit in XInput, HID and Switch Pro. Both the shortcut and report hooks bypass Left and Right Joy-Con, preserving their stick and Plus inputs even when the session gyro bit is set. The send hooks preserve scratch registers, suppress the hotkey's Plus input and modify only the right-stick fields. They restore the displaced argument setup before returning to the native send path.

The report code selects a tuning record using the active mode and Nintendo role. Three six-byte records follow the injected code, each containing signed X/Y gains and an unsigned deadzone, compiled from the corresponding mapping JSON. Joy-Con, keyboard, mouse, touch and multimedia reports are excluded.

Calibrated gyro axes are read from the normalized input structure. Each axis removes its deadzone, applies its signed gain and clamps to the signed stick range. Native motion samples remain unchanged. Input sampling is independent of the host's motion-report flag.

`gyro.s` describes the injected code; `gyro.hex` is its preassembled template. See [gyro controls and tuning](gyro.md).

## Device names

`names.py` patches the base name builder and the Nintendo and generic Bluetooth name branches. The default name becomes `IG05 Gamepad (Tabby)`. Nintendo names are selected from the saved role setting: `Joy-Con (L)`, `Joy-Con (R)` or the original `Pro Controller`.

The generic Bluetooth branch uses the same Tabby name without its old `(BLE)` suffix. Other mode-specific names, such as Xbox and keyboard names, are preserved. The patch changes name callbacks; it does not change USB IDs, Bluetooth addresses, SDP service descriptions or the controller's protocol identity.

Names are stored in the appended payload. Copy lengths stay within the native 33-byte scratch buffers and 28-byte output limit. Signatures locate the code paths and original name strings for each firmware version. `names.s` and `names.hex` contain the source and encoded template.

A host may retain its cached name until the controller is forgotten and paired again.
