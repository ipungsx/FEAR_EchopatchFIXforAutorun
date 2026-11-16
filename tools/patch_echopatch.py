#!/usr/bin/env python3
"""
Patch EchoPatch's dinput8.dll so its hooks can be enabled under Autorun
(Nintendo Switch).

Usage:
    python3 patch_echopatch.py <original dinput8.dll> <output dinput8.dll> [--memory-protect]
    python3 patch_echopatch.py <dinput8.dll> --check

No file offsets are hard-coded. Each patch is located by byte signature and
every signature must match exactly once, so the same tool works for any
EchoPatch release. Verified against EchoPatch 4.3.0, 4.4.0 and 4.5.2, and
against the Extraction Point and Perseus Mandate copies of those releases.
"""
import hashlib
import sys

# (name, signature, old bytes inside the signature, new bytes)
#
# Freeze(): MinHook's Freeze() aborts the hook when the thread snapshot fails
#   (`test eax, eax; jne +5; push 9; pop ebx`). Autorun has no complete thread
#   list, so the snapshot always fails and every hook is refused with
#   MH_ERROR_MEMORY_ALLOC. Replace `push 9; pop ebx` (6A 09 5B) with
#   `xor ebx, ebx; nop` (31 DB 90) so it continues with MH_OK (0).
#
# EnableHookLL() / MemoryHelper: request PAGE_READWRITE (0x04) instead of
#   PAGE_EXECUTE_READWRITE (0x40) from VirtualProtect. Only needed if the
#   build above ends with MH_ERROR_MEMORY_PROTECT under Autorun.
FREEZE_FIX = (
    "Freeze(): continue with MH_OK when the thread snapshot fails",
    bytes.fromhex("85C07505" "6A095B"),
    bytes.fromhex("6A095B"),
    bytes.fromhex("31DB90"),
)

MEMORY_PROTECT_FIXES = [
    (
        "EnableHookLL(): VirtualProtect RWX -> RW",
        bytes.fromhex("83C805" "6A40" "5053"),
        bytes.fromhex("6A40"),
        bytes.fromhex("6A04"),
    ),
    (
        "MemoryHelper (memory write): VirtualProtect RWX -> RW",
        bytes.fromhex("8D45FC" "8BF2" "50" "6A40"),
        bytes.fromhex("6A40"),
        bytes.fromhex("6A04"),
    ),
    (
        "MemoryHelper (1 byte write): VirtualProtect RWX -> RW",
        bytes.fromhex("8D45FC" "8BF1" "50" "6A40" "6A01"),
        bytes.fromhex("6A40"),
        bytes.fromhex("6A04"),
    ),
]


def find_all(data, needle):
    offsets = []
    start = data.find(needle)
    while start != -1:
        offsets.append(start)
        start = data.find(needle, start + 1)
    return offsets


def locate(data, name, signature, old):
    """Return the file offset of `old` inside the single `signature` match."""
    matches = find_all(data, signature)
    if len(matches) != 1:
        raise SystemExit(
            "!! %s: signature matched %d times, expected exactly 1. "
            "This is not a supported EchoPatch dinput8.dll, or the build "
            "changed. Nothing was written." % (name, len(matches))
        )
    offset = matches[0] + signature.find(old)
    if data[offset:offset + len(old)] != old:
        raise SystemExit(
            "!! %s: unexpected bytes at 0x%X. Nothing was written." % (name, offset)
        )
    return offset


def check(data):
    print("dinput8.dll SHA-256: %s" % hashlib.sha256(bytes(data)).hexdigest())
    for patch in [FREEZE_FIX] + MEMORY_PROTECT_FIXES:
        name, signature, old, _ = patch
        matches = find_all(data, signature)
        if len(matches) == 1:
            print("  ok    %s  (file offset 0x%X)"
                  % (name, matches[0] + signature.find(old)))
        else:
            print("  MISS  %s  (%d matches)" % (name, len(matches)))
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if "--check" in sys.argv:
        if len(args) != 1:
            print(__doc__)
            return 1
        return check(bytearray(open(args[0], "rb").read()))

    if len(args) != 2:
        print(__doc__)
        return 1
    src, dst = args

    data = bytearray(open(src, "rb").read())

    patches = [FREEZE_FIX]
    if "--memory-protect" in sys.argv:
        patches += MEMORY_PROTECT_FIXES

    for name, signature, old, new in patches:
        offset = locate(data, name, signature, old)
        data[offset:offset + len(new)] = new
        print("0x%06X: %s -> %s  (%s)" % (offset, old.hex(), new.hex(), name))

    with open(dst, "wb") as out:
        out.write(data)

    print("Written: %s" % dst)
    print("SHA-256: %s" % hashlib.sha256(bytes(data)).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
