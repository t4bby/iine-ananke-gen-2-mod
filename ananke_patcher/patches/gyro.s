.text
gyro_combo:
r0 = r15
r0 = [r8+r0<<2]
r1 = 0x800c00
r0 &= r1
r1 = 0x800400
if (r0 == r1) goto gyro_minus
r1 = 0x800800
if (r0 == r1) goto gyro_plus
gyro_release:
release_offset:
r1 = ${latch}
r2 = b[r8+r1] (u)
r2 &= 128
b[r8+r1] = r2
goto gyro_resume

gyro_minus:
minus_offset:
r1 = ${latch}
r2 = b[r8+r1] (u)
if ((r2 & 1) != 0) goto gyro_resume
r2 &= 128
r2 |= 1
b[r8+r1] = r2
r0 = 1
indicator_offset:
r1 = ${indicator}
b[r8+r1] = r0
mode_offset:
r1 = ${dpad}
r0 = b[r8+r1] (u)
r0 ^= 1
b[r8+r1] = r0
save_call:
call 1000000
goto gyro_resume

gyro_plus:
combo_state:
r3 = ${active_state}
r1 = h[r3+12] (u)
if ((r1 & 25) == 0) goto gyro_release
if ((r1 & 16) == 0) goto gyro_toggle
r1 = b[r3+3] (u)
if (r1 != 3) goto gyro_release
gyro_toggle:
plus_offset:
r1 = ${latch}
r2 = b[r8+r1] (u)
if ((r2 & 2) != 0) goto gyro_resume
r2 ^= 128
r2 &= 128
r2 |= 2
b[r8+r1] = r2
gyro_resume:
goto 1000000

gyro_report:
r1 = sp + 168
[--sp] = {rets, r0-r3, r10-r11}
call gyro_apply
{rets, r0-r3, r10-r11} = [sp++]
report_return:
goto 1000000

gyro_xinput:
r1 = r4
[--sp] = {rets, r0-r3, r10-r11}
call gyro_apply
{rets, r0-r3, r10-r11} = [sp++]
r0 = 8
xinput_return:
goto 1000000

gyro_apply:
[--sp] = {rets}
report_state:
r2 = ${active_state}
r3 = h[r2+12] (u)
if ((r3 & 25) == 0) goto gyro_done
r10 = 16
if ((r3 & 1) != 0) goto gyro_selected
r10 = 8
if ((r3 & 8) != 0) goto gyro_selected
r0 = b[r2+3] (u)
if (r0 != 3) goto gyro_done
r10 = 0
gyro_selected:
report_global:
r2 = ${global_base}
physical_offset:
r3 = ${physical}
r3 = r2 + r3
r3 = [r3+0]
r0 = 0x800c00
r3 &= r0
r0 = 0x800800
if (r3 != r0) goto gyro_status
r0 = [r1+0]
r0 &= 0xfffff7ff
[r1+0] = r0
gyro_status:
report_offset:
r3 = ${latch}
r2 = b[r2+r3] (u)
if ((r2 & 128) == 0) goto gyro_done
settings_pointer:
r3 = ${settings}
r3 += r10
r11 = h[r3+4] (u)
r2 = b[r3+6] (u)
r2 = r1 + r2
r0 = h[r2+0] (s)
r10 = h[r3+0] (s)
call gyro_scale
h[r1+8] = r0
r2 = b[r3+7] (u)
r2 = r1 + r2
r0 = h[r2+0] (s)
r10 = h[r3+2] (s)
call gyro_scale
h[r1+10] = r0
gyro_done:
{pc} = [sp++]

gyro_scale:
r2 = abs(r0)
if (r2 <= r11) goto gyro_center
ifs (r0 > 0) goto gyro_positive
r0 += r11
goto gyro_multiply
gyro_positive:
r0 -= r11
gyro_multiply:
r0 *= r10
r2 = 32767
ifs (r0 > r2) goto gyro_limit
r2 = -32767
ifs (r0 < r2) goto gyro_limit
rts
gyro_limit:
r0 = r2
rts
gyro_center:
r0 = 0
rts
