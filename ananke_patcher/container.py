import binascii
from dataclasses import dataclass, replace

from .formats import JlfsEntry, UfwEntry, UfwHeader, name


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def crc16(data: bytes) -> int:
    return binascii.crc_hqx(data, 0)


def cipher(data: bytes, key: int = 0xFFFF) -> bytearray:
    out = bytearray(data)
    for i in range(len(out)):
        out[i] ^= key & 255
        key = ((key << 1) ^ (0x1021 if key & 0x8000 else 0)) & 0xFFFF
    return out


def sfc(data: bytes, key: int, address: int = 0) -> bytes:
    return b"".join(
        cipher(data[i : i + 32], key ^ ((address + i) >> 2)) for i in range(0, len(data), 32)
    )


def scrambling_key(record: bytes) -> int:
    require(
        len(record) == 34 and crc16(record[:32]) == int.from_bytes(record[32:], "little"),
        "Scrambling-key record CRC mismatch",
    )
    threshold = sum(record[:16]) & 255
    threshold = 0xAA if threshold >= 0xE0 else 0x55 if threshold <= 0x10 else threshold
    return sum(1 << i for i in range(16) if record[16 + i] ^ record[15 - i] < threshold)


def checked(schema, data, message):
    require(len(data) == schema.layout.size, f"Truncated {message}")
    record = schema.parse(data)
    require(crc16(data[2:]) == record.crc, f"{message} CRC mismatch")
    return record


def jlfs_header(record) -> bytes:
    record.crc = crc16(record.pack()[2:])
    return record.pack()


@dataclass
class Member:
    slot: int
    entry: object

    @property
    def name(self) -> str:
        return name(self.entry)

    @property
    def offset(self) -> int:
        return self.entry.offset

    @property
    def length(self) -> int:
        return self.entry.size


@dataclass
class Package:
    data: bytes
    header: object
    members: list[Member]

    def payload(self, member: Member) -> bytes:
        return self.data[member.offset : member.offset + member.length]

    def member(self, filename: str) -> Member:
        matches = [m for m in self.members if m.name == filename]
        require(len(matches) == 1, f"Expected one {filename} member")
        return matches[0]

    @property
    def key(self) -> int:
        tail = self.payload(self.member("tail.bin"))
        require(
            len(tail) == 64
            and tail[34:40] == bytes.fromhex("139265367342")
            and tail[48:54] == b"JLUFW\0",
            "Unsupported UFW trailer",
        )
        return scrambling_key(tail[:34])

    def decoded_payload(self, member: Member) -> bytes:
        entry = member.entry
        data = bytearray(self.data[member.offset : member.offset + entry.padded_size])
        if entry.encryption_size:
            start = entry.encryption_offset
            end = start + entry.encryption_size
            data[start:end] = sfc(data[start:end], self.key, member.offset)
        return bytes(data[: member.length])


def parse_ufw(data: bytes) -> Package:
    header = checked(UfwHeader, cipher(data[:64]), "UFW header")
    require(header.size == len(data), "UFW file size mismatch")
    require(header.count > 0 and 64 + 80 * header.count <= len(data), "Invalid UFW table bounds")
    require(header.chip.split(b"\0")[0] == b"AC695X", "Expected AC695X firmware")
    require(crc16(data[64 : 64 + 80 * header.count]) == header.table_crc, "UFW table CRC mismatch")
    members = [
        Member(i, UfwEntry.parse(cipher(data[64 + i * 80 : 144 + i * 80])))
        for i in range(header.count)
    ]
    require(len({m.name for m in members}) == len(members), "Duplicate UFW member names")
    occupied = sorted(
        (m.offset, m.offset + m.entry.padded_size) for m in members if m.entry.padded_size
    )
    require(
        all(64 + 80 * header.count <= start <= end <= len(data) for start, end in occupied)
        and all(end <= next_start for (_, end), (next_start, _) in zip(occupied, occupied[1:])),
        "Invalid or overlapping UFW members",
    )
    require(all(m.length <= m.entry.padded_size for m in members), "Invalid UFW padded size")
    require(
        all(
            m.entry.encryption_offset + m.entry.encryption_size <= m.entry.padded_size
            for m in members
        ),
        "Invalid UFW encryption bounds",
    )
    package = Package(bytes(data), header, members)
    for member in members:
        require(
            crc16(package.decoded_payload(member)) == member.entry.data_crc,
            f"UFW {member.name} CRC mismatch",
        )
    return package


def flash_layout(raw: bytes) -> tuple[int, int, int]:
    candidates = []
    for base in (0, 0x1000, 0x10000, 0x80000, 0x100000, 0x180000):
        if base + 32 > len(raw):
            continue
        header = cipher(raw[base : base + 32])
        if crc16(header[2:]) == int.from_bytes(header[:2], "little"):
            candidates.append(base)
    require(len(candidates) == 1, "Flash directory missing or ambiguous")
    base = candidates[0]
    entries = []
    for offset in range(base + 32, min(base + 4096, len(raw)), 32):
        entry = checked(JlfsEntry, cipher(raw[offset : offset + 32]), "Flash directory entry")
        entries.append(entry)
        if entry.index:
            break
    require(entries and entries[-1].index, "Unterminated flash directory")

    def one(filename):
        matches = [e for e in entries if name(e) == filename]
        require(len(matches) == 1, f"Expected one flash {filename}")
        return matches[0]

    area_offset = base + one("app_dir_head").offset
    config = one("isd_config.ini")
    blob = raw[base + config.offset : base + config.offset + 34]
    key = scrambling_key(blob)
    boundaries = [base + e.offset for e in entries if base + e.offset > area_offset]
    require(
        boundaries and area_offset < len(raw) <= min(boundaries), "Invalid application flash bounds"
    )
    return area_offset, key, min(boundaries)


@dataclass
class AppArea:
    plain: bytes
    app: bytes
    cfg: bytes
    area_offset: int
    key: int
    flash_limit: int
    header: object
    entries: dict

    @property
    def app_offset(self) -> int:
        return self.entries["app.bin"][1].offset

    @property
    def app_base(self) -> int:
        return self.header.offset


def unpack_app(raw: bytes) -> AppArea:
    area_offset, key, flash_limit = flash_layout(raw)
    decoded = sfc(raw[area_offset:], key)
    header = checked(JlfsEntry, decoded[:32], "Application-area header")
    require(name(header) == "app_area_head", "Expected app_area_head")
    require(32 < header.size <= len(decoded), "Invalid application-area size")
    plain = decoded[: header.size]
    require(crc16(plain[32:]) == header.data_crc, "Application-area payload CRC mismatch")
    entries = {}
    entry = None
    for offset in range(32, len(plain) - 31, 32):
        entry = checked(JlfsEntry, plain[offset : offset + 32], "Application directory entry")
        require(name(entry) not in entries, "Duplicate application member name")
        entries[name(entry)] = (offset, entry)
        if entry.index:
            break
    require(entry is not None and entry.index, "Unterminated application directory")
    payloads = []
    for filename in ("app.bin", "cfg_tool.bin"):
        require(filename in entries, f"Missing {filename}")
        entry = entries[filename][1]
        require(
            offset + 32 <= entry.offset and entry.offset + entry.size <= len(plain),
            f"Invalid {filename} bounds",
        )
        payload = plain[entry.offset : entry.offset + entry.size]
        require(crc16(payload) == entry.data_crc, f"{filename} CRC mismatch")
        payloads.append(payload)
    app, cfg = (entries[n][1] for n in ("app.bin", "cfg_tool.bin"))
    require(
        app.offset + app.size == cfg.offset and cfg.offset + cfg.size == len(plain),
        "Unsupported application/cfg arrangement",
    )
    require(0x1E00000 <= header.offset < 0x2000000, "Unsupported SFC mapping")
    return AppArea(
        bytes(plain), *map(bytes, payloads), area_offset, key, flash_limit, header, entries
    )


def load_source(data: bytes) -> tuple[Package, Member, bytes, AppArea]:
    package = parse_ufw(data)
    member = package.member("flash.bin")
    raw = package.payload(member)
    require(crc16(raw) == member.entry.data_crc, "flash.bin CRC mismatch")
    area = unpack_app(raw)
    require(b"IG05 Gamepad\0" in area.app, "Expected IG05 application")
    return package, member, raw, area


def repack(package: Package, member: Member, raw: bytes, area: AppArea, new_app: bytes) -> bytes:
    extension = len(new_app) - len(area.app)
    require(extension >= 0 and extension % 16 == 0, "Invalid app extension")
    plain = bytearray(area.plain[: area.app_offset]) + new_app + area.cfg
    length = max(len(raw), (area.area_offset + len(plain) + 4095) & ~4095)
    require(length <= area.flash_limit, "Application overlaps another flash region")
    for filename in ("app.bin", "cfg_tool.bin"):
        slot, original = area.entries[filename]
        entry = replace(original)
        if filename == "app.bin":
            entry.size, entry.data_crc = len(new_app), crc16(new_app)
        else:
            entry.offset += extension
        plain[slot : slot + 32] = jlfs_header(entry)
    header = replace(area.header)
    header.size, header.data_crc = len(plain), crc16(plain[32:])
    plain[:32] = jlfs_header(header)
    flash = bytearray(raw) + b"\xff" * (length - len(raw))
    flash[area.area_offset : area.area_offset + len(plain)] = sfc(plain, area.key)
    growth = len(flash) - len(raw)
    data = bytearray(package.data)
    data[member.offset : member.offset + member.length] = flash
    for item in package.members:
        entry = replace(item.entry)
        if item == member:
            entry.data_crc, entry.size, entry.padded_size = crc16(flash), len(flash), len(flash)
        elif item.offset >= member.offset + member.length:
            entry.offset += growth
        if entry.offset != item.offset and entry.encryption_size:
            start = item.offset + entry.encryption_offset
            end = start + entry.encryption_size
            decoded = sfc(package.data[start:end], package.key, item.offset)
            start = entry.offset + entry.encryption_offset
            data[start : start + entry.encryption_size] = sfc(decoded, package.key, entry.offset)
        slot = 64 + item.slot * 80
        data[slot : slot + 80] = cipher(entry.pack())
    header = replace(package.header)
    header.size, header.table_crc = len(data), crc16(data[64 : 64 + 80 * header.count])
    header.crc = crc16(header.pack()[2:])
    data[:64] = cipher(header.pack())
    rebuilt = parse_ufw(data)
    actual_flash = rebuilt.payload(rebuilt.member("flash.bin"))
    require(
        crc16(actual_flash) == rebuilt.member("flash.bin").entry.data_crc,
        "Rebuilt flash CRC mismatch",
    )
    actual_area = unpack_app(actual_flash)
    require(actual_area.app == new_app and actual_area.cfg == area.cfg, "Rebuilt app/cfg mismatch")
    require(actual_flash[: area.area_offset] == raw[: area.area_offset], "Boot data changed")
    require(len(data) == len(package.data) + growth, "Unexpected UFW size change")
    for original in package.members:
        if original != member:
            require(
                package.decoded_payload(original)
                == rebuilt.decoded_payload(rebuilt.member(original.name)),
                f"{original.name} changed",
            )
    return bytes(data)
