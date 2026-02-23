#!/usr/bin/env python3

import struct
from pathlib import Path

BOOT_META_MAGIC = 0x4F54414D
BOOT_META_REPLICA_SIZE = 256

words = [0] * (BOOT_META_REPLICA_SIZE // 4)
words[0] = BOOT_META_MAGIC
words[1] = 1   # seq
words[2] = 0   # active_slot
words[3] = 0   # target_slot
words[4] = 0   # state: confirmed
words[5] = 0   # boot_count
words[6] = 3   # max_boot_count

crc = 0xFFFFFFFF
for w in words[:-1]:
    for shift in (0, 8, 16, 24):
        crc ^= (w >> shift) & 0xFF
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if (crc & 1) else 0)
        crc &= 0xFFFFFFFF
words[-1] = (~crc) & 0xFFFFFFFF

replica = struct.pack('<' + 'I' * len(words), *words)
Path('boot_meta.bin').write_bytes(replica + replica)
