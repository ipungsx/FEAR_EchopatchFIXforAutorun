#!/usr/bin/env python3
"""
Patch EchoPatch's dinput8.dll so its hooks can be enabled under Autorun
(Nintendo Switch).

Usage:
    python3 patch_echopatch.py <original dinput8.dll> <output dinput8.dll> [--memory-protect]

The patch is applied only to the exact build listed in ORIGINAL_SHA256,
because the offsets belong to that build.
"""
import hashlib
import sys

ORIGINAL_SHA256 = "94cd696b4bb5278ed79244ec564a6001920553d3be44a7730a53ee2e75619670"

# (file offset, original bytes, new bytes, description)
FREEZE_FIX = [
    (0x7393D, bytes.fromhex("6a095b"), bytes.fromhex("31db90"),
     "MinHook Freeze(): continue with MH_OK when the thread snapshot fails"),
]

# Optional: only if Freeze fix alone ends with MH_ERROR_MEMORY_PROTECT.
MEMORY_PROTECT_FIX = [
    (0x73A3A, b"\x6a\x40", b"\x6a\x04", "MinHook EnableHookLL(): VirtualProtect RWX -> RW"),
    (0x49C2C, b"\x6a\x40", b"\x6a\x04", "MemoryHelper: VirtualProtect RWX -> RW"),
    (0x66AFC, b"\x6a\x40", b"\x6a\x04", "MemoryHelper (1 byte write): VirtualProtect RWX -> RW"),
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 1
    src, dst = args
    data = bytearray(open(src, "rb").read())

    digest = hashlib.sha256(data).hexdigest()
    if digest != ORIGINAL_SHA256:
        print("This dinput8.dll is a different EchoPatch build (sha256 %s)." % digest)
        print("Offsets do not match it; nothing was written.")
        return 1

    patches = list(FREEZE_FIX)
    if "--memory-protect" in sys.argv:
        patches += MEMORY_PROTECT_FIX

    for off, old, new, desc in patches:
        if data[off:off + len(old)] != old:
            print("Unexpected bytes at 0x%X; nothing was written." % off)
            return 1
        data[off:off + len(new)] = new
        print("0x%X: %s -> %s  (%s)" % (off, old.hex(), new.hex(), desc))

    open(dst, "wb").write(data)
    print("Written: %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
