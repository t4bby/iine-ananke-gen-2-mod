# Gyro to right stick

Press **Turbo + Plus** to toggle gyro-to-right-stick. Release the combination before pressing it again. Holding it does not repeatedly toggle the setting. **Turbo + Minus** keeps the firmware's D-pad-to-stick shortcut.

The toggle works in XInput, HID and Switch Pro. Both Joy-Con modes bypass gyro-to-stick and its Turbo + Plus shortcut. Its state carries between supported modes during the session and starts off after reboot. Entering Joy-Con mode suspends the feature even if it was enabled in another mode.

When enabled, gyro X drives right-stick X and gyro Y drives right-stick Y. Moving the controller deflects the stick; stopping returns it to center once the signal falls within the deadzone. This uses angular velocity rather than holding a stick position at a fixed tilt angle. It replaces the right-stick values while enabled.

The hotkey's Plus press is suppressed only in supported modes. Native accelerometer and gyro samples remain available to games, and gyro-to-stick works independently of the host's motion-report request.

## Tuning

Edit the `gyro` object alongside `buttons` in `switch_pro.json`, `xinput.json` and `hid.json` under `mapping/`, then regenerate and flash:

```json
"gyro": {
  "sensitivity": 4,
  "deadzone": 16,
  "axis_x": "x",
  "axis_y": "y",
  "invert_x": true,
  "invert_y": false
}
```

| Setting | Meaning | Range |
| --- | --- | --- |
| `sensitivity` | Multiplier after deadzone removal | 1..1024 |
| `deadzone` | Ignore this amount on either side of center, in native gyro units | 0..32767 |
| `axis_x` | Gyro source for horizontal movement | `"x"`, `"y"`, `"z"` |
| `axis_y` | Gyro source for vertical movement | `"x"`, `"y"`, `"z"` |
| `axis_x` | Gyro source for horizontal stick movement | `"x"`, `"y"`, `"z"` |
| `axis_y` | Gyro source for vertical stick movement | `"x"`, `"y"`, `"z"` |
| `invert_x` | Reverse horizontal stick direction | `true` / `false` |
| `invert_y` | Reverse vertical stick direction | `true` / `false` |

The default sensitivity is one-eighth of the original gyro patch. Increase it for faster stick movement or reduce it for finer control. Use axis selection if movement affects the wrong stick axis; use inversion if the axis is correct but its direction is reversed.

Switch Pro, XInput and HID have independent gyro tuning, even though their native button bank is shared. Joy-Con, keyboard, mouse, touch and multimedia mappings have no `gyro` object. Output is clamped to -32767..32767.

These settings are compiled into the patch and are not exposed in the IINE phone app. Extracting an original firmware supplies the patch's starting gyro settings alongside the decoded native button defaults.

The default sensitivity is one-eighth of the previous value of 32. Lower it further to 1 or 2 for slower movement. If a physical direction is reversed, change its inversion flag. Axis selection and inversion can be tuned independently for each supported mode.
