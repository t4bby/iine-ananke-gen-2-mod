from dataclasses import astuple, dataclass
from struct import Struct
from typing import ClassVar


class Record:
    layout: ClassVar[Struct]

    @classmethod
    def parse(cls, data: bytes):
        return cls(*cls.layout.unpack(data))

    def pack(self) -> bytes:
        return self.layout.pack(*astuple(self))


@dataclass
class UfwHeader(Record):
    layout = Struct("<HHIHHI48s")

    crc: int
    table_crc: int
    size: int
    count: int
    flags: int
    alignment: int
    chip: bytes


@dataclass
class UfwEntry(Record):
    layout = Struct("<HHHHIIIII36s16s")

    kind: int
    index: int
    data_crc: int
    reserved: int
    offset: int
    size: int
    padded_size: int
    encryption_offset: int
    encryption_size: int
    extra: bytes
    name: bytes


@dataclass
class JlfsEntry(Record):
    layout = Struct("<HHIIBBH16s")

    crc: int
    data_crc: int
    offset: int
    size: int
    flags: int
    reserved: int
    index: int
    name: bytes


def name(record):
    return record.name.split(b"\0")[0].rstrip(b"\xff").decode("ascii")
