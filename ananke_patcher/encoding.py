import struct

from .container import require

NOP = b"\0\0"


def immediate(register: int, value: int) -> bytes:
    require(0 <= register < 16 and 0 <= value <= 0xFFFFFFFF, "Invalid immediate operand")
    return struct.pack("<HI", 0xFFC0 | register, value)


def branch(source: int, target: int, *, link: bool = False) -> bytes:
    # BR23 long branches wrap within its 25-bit RAM/SFC address window.
    delta = (target - source - 4) & 0x1FFFFFF
    if delta & 0x1000000:
        delta -= 0x2000000
    require(delta % 2 == 0 and -(1 << 22) <= delta < (1 << 22), "Branch out of range/alignment")
    value = (delta // 2) & ((1 << 22) - 1)
    return struct.pack("<HH", (0xEA80 if link else 0xEAC0) | (value >> 16), value & 0xFFFF)


def immediate16(register: int, value: int) -> bytes:
    require(0 <= register < 16 and -32768 <= value <= 32767, "Invalid short immediate")
    return struct.pack("<HH", 0xE040 | register, value & 0xFFFF)


def add14(register: int, base: int, value: int) -> bytes:
    require(0 <= register < 16 and 0 <= base < 16 and -8192 <= value <= 8191, "Invalid add operand")
    value &= 0x3FFF
    return struct.pack(
        "<HH", 0xE100 | register | ((value >> 12) << 4), (base << 12) | (value & 0xFFF)
    )


def signed(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def conditional_target(data: bytes, offset: int, address: int, register: int, constant: int) -> int:
    first, second = struct.unpack_from("<HH", data, offset)
    require(
        first & 0xFF80 == 0xF800 and first & 15 == register, "Expected compare-immediate branch"
    )
    immediate_value = signed(((first >> 4 & 7) << 7) | (second >> 9), 10)
    require(immediate_value == constant, "Unexpected branch comparison")
    return address + 4 + 2 * signed(second & 0x1FF, 9)


def short_target(data: bytes, offset: int, address: int) -> int:
    word = struct.unpack_from("<H", data, offset)[0]
    require(word & 0xE00C == 0x8004, "Expected short goto")
    displacement = ((word & 3) << 9) | ((word >> 4 & 15) << 5) | (word >> 8 & 31)
    return address + 2 + 2 * signed(displacement, 12)


def call_target(data: bytes, offset: int, base: int) -> int:
    first, second = struct.unpack_from("<HH", data, offset)
    require(first & 0xFFC0 == 0xEA80, "Expected BR23 call")
    return base + offset + 4 + 2 * signed(((first & 63) << 16) | second, 22)
