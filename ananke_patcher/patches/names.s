.text
name_base:
if ((r1 & 8) == 0) goto name_default
r1 = h[r6+2] (u)
if (r1 == 4) goto name_xbox
if (r1 == 8) goto name_xbox
if (r1 != 16) goto name_default
base_pro_pointer:
r0 = ${pro}
call name_role
r1 = sp + 3
rep 14 {
r2 = b[r0++=1] (u)
b[r1++=1] = r2
}
goto name_base_return
name_xbox:
xbox_pointer:
r0 = ${xbox}
r1 = sp + 3
rep 24 {
r2 = b[r0++=1] (u)
b[r1++=1] = r2
}
goto name_base_return
name_default:
default_pointer:
r0 = ${gamepad}
r1 = sp + 3
rep 21 {
r2 = b[r0++=1] (u)
b[r1++=1] = r2
}
name_base_return:
goto 1000000

name_nintendo:
pro_pointer:
r0 = ${pro}
call name_role
name_nintendo_return:
goto 1000000

name_generic:
generic_pointer:
r0 = ${gamepad}
r1 = r5
rep 21 {
r2 = b[r0++=1] (u)
b[r1++=1] = r2
}
name_generic_return:
goto 1000000

name_role:
role_pointer:
r1 = ${role}
r1 = b[r1+0] (u)
if (r1 == 1) goto name_left
if (r1 != 2) goto name_done
right_pointer:
r0 = ${right}
rts
name_left:
left_pointer:
r0 = ${left}
name_done:
rts
