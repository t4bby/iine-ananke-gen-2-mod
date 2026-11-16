# IINE Ananke Gen 2 Mod

Generate modified Mini Ananke Gen 2 firmware from an original V0900 or V0901 `.ufw`.

| Added Feature | Patch details |
| --- | --- |
| Left Joy-Con | Pairing + L selects Left Joy-Con; Pairing + Down keeps Right Joy-Con. Left/Right/Down/Up control stick Up/Down/Left/Right. Y/A/B/X act as D-pad Up/Down/Left/Right. R/ZR duplicate L/ZL; |
| Device names | Default name: Joy-Con modes use `Joy-Con (L)` and `Joy-Con (R)`; Pro mode keeps `Pro Controller`. |
| Gamepad Mapping | Edit native gamepad, keyboard, mouse, multimedia and touch defaults through the JSON files in `mapping/`. Gamepad modes share one mapping bank. Power is excluded. |
| Gyro right stick | Turbo + Plus toggles gyro-to-right-stick in XInput, HID and Switch Pro modes. Tune each mode in its mapping JSON. Turbo + Minus keeps its original function. See [gyro controls](docs/gyro.md). |

## Generate

```sh
python3 patcher.py --apply /path/to/IG05_V0901.ufw
```

Flash `build/firmware/IG05_V0901_MOD.ufw` with the Windows Firmware Upgrade Utility. For V0900, supply its original `.ufw` instead. Use `--output build/custom` for another new output directory. Keep the original firmware for restoration.

Edit the files in `mapping/` to change native defaults. See [mapping documentation](docs/mapping.md) for the format, examples and app behavior.

To extract firmware and its default JSON files:

```sh
python patcher.py --extract /path/to/IG05_V0901.ufw --output build/extracted
```

Requires Python 3.10+; no third-party dependencies. See [patch details](docs/patches.md) for the implementation.

## Resources

- [IINE Android app](https://play.google.com/store/apps/details?id=top.iine.android.client)
- [IINE controller manual](https://iine.store/pages/mini-ananke-gen-2-controller-guide-manual)
- [pi32v2 instruction research and assembler](https://github.com/jvitkauskas/pi32v2-isa)
- [JieLi firmware container and cipher research](https://github.com/kagaimiq/jl-misctools)
- [Quarkslab Ghidra support for JieLi](https://github.com/quarkslab/ghidra-jieli)
- [LiteEMF controller input definitions](https://github.com/LiteEMF/LiteEMF)
- [Nintendo Switch reverse engineering](https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering)
- [JieLi USB bootloader tools](https://github.com/kagaimiq/jl-uboot-tool)
