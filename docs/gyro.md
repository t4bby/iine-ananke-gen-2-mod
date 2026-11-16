# Gyro to right stick

Press **Turbo + Plus** to toggle gyro-to-right-stick. Release the combination before pressing it again. Holding it does not repeatedly toggle the setting. **Turbo + Minus** keeps the firmware's D-pad-to-stick shortcut.

The toggle works in XInput, HID and Switch Pro. Both Joy-Con modes bypass gyro-to-stick and its Turbo + Plus shortcut. Its state carries between supported modes during the session and starts off after reboot. Entering Joy-Con mode suspends the feature even if it was enabled in another mode.

When enabled, gyro Z drives right-stick X and gyro X drives right-stick Y. Moving the controller deflects the stick; stopping returns it to center once the signal falls within the deadzone. This uses angular velocity rather than holding a stick position at a fixed tilt angle. It replaces the right-stick values while enabled.

The hotkey's Plus press is suppressed only in supported modes. Native accelerometer and gyro samples remain available to games, and gyro-to-stick works independently of the host's motion-report request.

## Tuning

Edit the `gyro` object alongside `buttons` in `switch_pro.json`, `xinput.json` and `hid.json` under `mapping/`, then regenerate and flash:

```json
"gyro": {
  "sensitivity": 32,
  "deadzone": 8,
  "invert_x": true,
  "invert_y": false
}
```

| Setting | Meaning | Range |
| --- | --- | --- |
| `sensitivity` | Multiplier after deadzone removal | 1..1024 |
| `deadzone` | Ignore this amount on either side of center, in native gyro units | 0..32767 |
| `invert_x` | Reverse horizontal stick direction | `true` / `false` |
| `invert_y` | Reverse vertical stick direction | `true` / `false` |

Switch Pro, XInput and HID have independent gyro tuning, even though their native button bank is shared. Joy-Con, keyboard, mouse, touch and multimedia mappings have no `gyro` object. Output is clamped to -32767..32767.

These settings are compiled into the patch and are not exposed in the IINE phone app. Extracting an original firmware supplies the patch's starting gyro settings alongside the decoded native button defaults.
