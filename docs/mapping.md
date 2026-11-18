# Controller mappings

The JSON files in `mapping/` define native button defaults and per-mode gyro tuning. Edit them and regenerate the firmware:

```sh
python patcher.py --apply /path/to/IG05_V0901.ufw --output build/custom
```

Use `--mapping /path/to/mapping` to select another complete mapping folder. Output directories must be new.

## Modes and shared settings

| File | Pairing shortcut | Native bank |
| --- | --- | --- |
| `left_joycon.json` | L | Gamepad (shared) |
| `right_joycon.json` | Down | Gamepad (shared) |
| `switch_pro.json` | Up | Gamepad (shared) |
| `xinput.json` | Left | Gamepad (shared) |
| `hid.json` | Right | Gamepad (shared) |
| `keyboard.json` | A | Keyboard |
| `mouse.json` | B | Mouse |
| `touch.json` | X | Touch |
| `multimedia.json` | Y | Consumer controls |

The firmware shares one gamepad mapping bank. Make the same assignment changes in all five gamepad files; conflicting button assignments are rejected. Gyro tuning is independent for Switch Pro, XInput and HID; it is disabled in both Joy-Con modes. Keyboard, mouse, touch and multimedia have separate banks.

Mappings apply to normalized inputs before each mode builds its reports. The Left report patch then rotates the directional inputs and maps the rail buttons as shown below. Right retains its original rotation and shoulder behavior. These conversions are not additional app-visible mapping options.

## Left Joy-Con orientation

These conversions apply only in Left Joy-Con mode, after native button assignments:

| Controller input | Left Joy-Con output |
| --- | --- |
| Left | Stick Up |
| Right | Stick Down |
| Down | Stick Left |
| Up | Stick Right |
| Y | D-pad Up |
| A | D-pad Down |
| B | D-pad Left |
| X | D-pad Right |
| L | L |
| ZL | ZL |
| R | SR |
| ZR | SL |

Opposite stick directions cancel; diagonals drive both axes. Minus and Plus keep their existing assignments.

## JSON format

Each file has a `buttons` object; `switch_pro.json`, `xinput.json` and `hid.json` also have a `gyro` object. See [gyro tuning](gyro.md) for its settings. Its keys name physical inputs; values select their actions. Keep the existing keys and change their values. The examples below show individual entries inside that object, not complete files.

The device's usual input names are `A`, `B`, `X`, `Y`, `L`, `R`, `ZL`, `ZR`, `Minus`, `Plus`, `Home`, `Capture`, `L3`, `R3`, `Up`, `Down`, `Left` and `Right`. Other names preserve native firmware slots and may have no physical input on this model.

### Gamepad buttons

```json
"L": "ZL"
```

Physical L performs the normalized ZL action. A button mapped to its own name keeps the native pass-through action. Use `null` to disable an input:

```json
"L": null
```

A gamepad action can also select multiple buttons:

```json
"L": {"type": "gamepad", "buttons": ["L", "ZL"]}
```

Destination names use the same input names. The Left report conversion still applies afterward; virtual-axis names such as `LeftStickUp` are not native mapping targets.

### Keyboard

```json
"A": {"type": "keyboard", "modifiers": 2, "keys": [4]}
```

This sends Left Shift + A. `keys` accepts up to three numeric USB HID keyboard usage codes (0..255); zero is an empty key slot. Examples: A = 4, B = 5, Enter = 40, Space = 44.

`modifiers` is a byte mask. Add the desired values:

| Modifier | Left | Right |
| --- | --- | --- |
| Ctrl | 1 | 16 |
| Shift | 2 | 32 |
| Alt | 4 | 64 |
| GUI | 8 | 128 |

Omitted `modifiers` defaults to zero. Use an empty `keys` list for a modifier-only action, or `null` for no keyboard action.

### Mouse

```json
"A": {"type": "mouse", "buttons": 1},
"Up": {"type": "mouse", "y": -2},
"Right": {"type": "mouse", "x": 2},
"X": {"type": "mouse", "wheel": -1}
```

`buttons` is a mask: left = 1, right = 2, middle = 4, fourth = 8, fifth = 16. Add values for multiple buttons; omission means zero.

One action can contain at most one movement field: `x`, `y` or `wheel`, with a signed amount from -128 to 127. Negative X moves left; negative Y moves up. Button clicks and movement can share one action. Use `null` for no mouse action.

### Multimedia / consumer controls

```json
"X": {"type": "consumer", "usage": 233}
```

`usage` is a numeric USB HID consumer usage: volume up = 233, volume down = 234, mute = 226, play/pause = 205. The optional `extra` word defaults to zero. Both words accept 0..65535. Use `null` for no consumer action.

### Touch

```json
"A": {"flags": 0, "parameters": [0, 0, 0], "x": 3000, "y": 2000}
```

Touch uses a separate native format. Each entry keeps `flags` (0..255), exactly three `parameters` bytes (0..255 each), and `x`/`y` words (0..65535). The gesture flags and parameters are not fully decoded; preserve the extracted values unless you understand their behavior. Touch entries require these fields and do not accept `null`.

### Raw records

Unrecognized six-byte records can be preserved as:

```json
"A": {"type": "raw", "bytes": "020000040000"}
```

This is a native record, not a packet or macro. Prefer the named action formats above.

## Defaults and the phone app

The checked-in button defaults were decoded from V0901 and match the supplied V0900 image. Gyro values are patch defaults. To extract defaults from your own supported firmware:

```sh
python patcher.py --extract /path/to/IG05_V0900.ufw --output build/extracted
python patcher.py --apply /path/to/IG05_V0900.ufw --mapping build/extracted/mapping --output build/custom
```

**Saved mappings on the controller override flashed defaults.** Use the IINE app's mapping/default reset, if available for this model, to load the new factory values. Subsequent app edits use the firmware's existing save/load path.

The generator preserves the native configuration protocol; it does not modify the Android app. The app may show normalized button assignments rather than the Left report patch's stick/D-pad conversion.

An action needs a host mode that emits its report type. Placing a keyboard or mouse action in another bank does not add USB/Bluetooth reports or guarantee that the host or app supports it.
