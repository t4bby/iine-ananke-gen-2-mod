; Force the player-one mask only for the Left Nintendo role.
.text
led_entry:
r3 = h[r10+12] (u)
if ((r3 & 16) == 0) goto original_led
r3 = b[r10+3] (u)
if (r3 != 1) goto original_led
r1 = 1
original_led:
r3 = ${led_selector}
resume_led:
goto 1000000
