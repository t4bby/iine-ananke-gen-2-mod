; Pairing + L selects role 1; other inputs resume the stock Pair+Up test.
; External goto placeholders are fixed by the generator.

.text
left_entry:
r1 = 0x80000040
r2 = r0 & r1
if (r2 != r1) goto original
r0 = ${role_config}
r1 = h[r4+12] (u)
r1 &= 16
if (r1 == 0) goto select_left
r1 = b[r8+r0] (u)
if (r1 != 1) goto select_left
already_left:
goto 1000000
select_left:
r2 = r8 + ${mode_config}
r1 = 2
h[r2+0] = r1
r3 = 8
h[r2+2] = r3
r3 = 16
h[r2+4] = r3
r1 = 1
commit_left:
goto 1000000
original:
r1 = 0x80010000
resume_original:
goto 1000000

; Left Nintendo report mapper with rotated directions and duplicated shoulders.
; See docs/patches.md for register contracts and limitations.
.text
mapping_entry:
r0 = ${active_state}
r0 = b[r0+3] (u)
if (r0 != 1) goto mapping_exit
r2 = r8 >> 17
r2 &= 1
r3 = r8 >> 16
r3 &= 1
r2 -= r3
r3 = 32767
r2 *= r3
r11 = r2
r2 = r8 >> 19
r2 &= 1
r3 = r8 >> 18
r3 &= 1
r2 -= r3
r3 = 32767
r2 *= r3
r7 = r2
r1 = 0xfff0fff0
r1 &= r8
r2 = r8 & 1
r2 <<= 17
r1 |= r2
r2 = r8 & 2
r2 <<= 17
r1 |= r2
r2 = r8 & 4
r2 <<= 17
r1 |= r2
r2 = r8 & 8
r2 <<= 13
r1 |= r2
r2 = r8 & 0xc0
r2 <<= 16
r1 |= r2
r8 = r1
mapping_exit:
r0 = 48
b[r5+0] = r0
resume_mapping:
goto 1000000
rotation_entry:
if (r4 == 1) goto skip_rotation
if (r4 == 3) goto skip_rotation
resume_rotation:
goto 1000000
skip_rotation:
goto 1000000
conversion_entry:
r2 = ${active_state}
r2 = h[r2+12] (u)
r2 &= 16
if (r2 == 0) goto original_conversion
r2 = ${active_state}
r2 = b[r2+3] (u)
if (r2 != 1) goto original_conversion
rts
original_conversion:
[--sp] = rets
r3 = r0
resume_conversion:
goto 1000000
