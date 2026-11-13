# EchoPatch Fix for Autorun (F.E.A.R. on Nintendo Switch)

A patched EchoPatch `dinput8.dll` that runs under **Autorun** (Wine for Nintendo Switch), so EchoPatch's controller support for **F.E.A.R.** can work.

> **Status: experimental.** The patch changes only 3 bytes (9 bytes for the alternative build) in EchoPatch's `dinput8.dll`. Keep a backup of your original files.

**Download:** [Releases](https://github.com/ipungsx/FEAR_EchopatchFIXforAutorun/releases/latest)

---

## The problem

When F.E.A.R. runs on Autorun (build `nx-amd64-fex-2640`) with EchoPatch installed, this popup appears every time the game starts:

```
Failed to enable hook for API: CreateWindowExA
Error: MH_ERROR_MEMORY_ALLOC
```

As a result, none of EchoPatch's features are active, including its SDL3 controller support. On top of that, F.E.A.R. reads the keyboard, mouse and joystick directly through DirectInput, so the Joy-Con buttons and sticks that Autorun translates into keyboard/mouse input never reach the game either. Almost every button stops working, and only the touchscreen can be used in the menus.

## The cause

EchoPatch uses [MinHook](https://github.com/TsudaKageyu/minhook) to install its hooks. Before enabling a hook, MinHook "freezes" every other thread in the process, and it gets the thread list from `CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)`.

Autorun runs the game as a single process without a complete thread list, so that call fails. MinHook then aborts the hook and returns code `9` (`MH_ERROR_MEMORY_ALLOC`). The name is misleading: memory has nothing to do with it.

The clue is in the error message itself. It is *enabling* the hook that fails (`MH_EnableHook`), not *creating* it (`MH_CreateHook`), which means the trampoline memory was allocated successfully.

## The fix

In MinHook's `Freeze()` function, a failed thread snapshot is no longer treated as an error. MinHook skips freezing threads and continues with `MH_OK`. This is safe because when EchoPatch is loaded (`DllMain` of `dinput8.dll`), the game is still effectively running on a single thread.

| File offset | VA | Original | New | Description |
|---|---|---|---|---|
| `0x7393D` | `0x1007453D` | `6A 09 5B` (`push 9; pop ebx`) | `31 DB 90` (`xor ebx, ebx; nop`) | `Freeze()`: continue with `MH_OK` when the thread snapshot fails |

### Alternative build (`MEMORY_PROTECT`)

Use this build only if the main one shows `MH_ERROR_MEMORY_PROTECT`. On top of the fix above, it makes `VirtualProtect` request `PAGE_READWRITE` (`0x04`) instead of `PAGE_EXECUTE_READWRITE` (`0x40`) when writing patches:

| File offset | VA | Original | New | Description |
|---|---|---|---|---|
| `0x73A3A` | `0x1007463A` | `6A 40` | `6A 04` | MinHook `EnableHookLL()` |
| `0x49C2C` | `0x1004A82C` | `6A 40` | `6A 04` | `MemoryHelper` (memory write) |
| `0x66AFC` | `0x100676FC` | `6A 40` | `6A 04` | `MemoryHelper` (single byte write) |

## Installation

1. Make sure F.E.A.R. is in `switch/wine/drive_c/FEAR Platinum/` and has been added to your Autorun library.
2. Back up your existing `dinput8.dll` and `EchoPatch.ini`, if you have them.
3. Download `FEAR_EchoPatch_Autorun.zip` from [Releases](https://github.com/ipungsx/FEAR_EchopatchFIXforAutorun/releases/latest).
4. Extract it and copy the contents of `FEAR Platinum/` to `switch/wine/drive_c/FEAR Platinum/` on your SD card, overwriting the old files.
5. Delete `autoexec.cfg` from the game folder if you created one yourself.
6. Start the game. If no error popup appears, EchoPatch is active.
7. If `MH_ERROR_MEMORY_PROTECT` appears, download `FEAR_EchoPatch_Autorun_MEMORY_PROTECT.zip` and replace `dinput8.dll` with the one inside it.

### `EchoPatch.ini` settings for Switch

The included `EchoPatch.ini` is tuned for the Switch. Changes from the defaults:

| Option | Value | Reason |
|---|---|---|
| `DisableRedundantHIDInit` | `1` | The game no longer grabs the controller through DirectInput, so all controller input goes through SDL3 |
| `MaxFPS` | `60.0` | Matches the Switch display |
| `FastVRAMDetection` | `0` | Avoids VRAM detection through DXGI |
| `HighResolutionReflections`, `NoLODBias`, `ReducedMipMapBias`, `EnablePersistentWorldState` | `0` | Lower GPU and memory load |
| `TouchpadEnabled` | `0` | Not relevant for Joy-Con |
| `EnableCrashHandler` | `0` | Fewer unnecessary hooks |

The controller layout follows EchoPatch's defaults (ZR fire, ZL aim, A jump, B crouch, and so on) and can be changed in the `[Controller]` section.

### Autorun tips

- If a button triggers two actions at once, clear that button in Autorun's mapping for the game (**Y → Controls**), so the input only goes through EchoPatch.
- Avoid pressing **Minus + right stick click** together while playing. That combination opens Autorun's on-screen keyboard, and the game receives no controller input while it is open.
- Use **1280x720** in the game so the window fills the screen.

## Building the patch yourself

If you have the same EchoPatch `dinput8.dll` build (SHA-256 `94cd696b4bb5278ed79244ec564a6001920553d3be44a7730a53ee2e75619670`), you can apply the patch yourself:

```sh
python3 tools/patch_echopatch.py dinput8.dll dinput8_autorun.dll
python3 tools/patch_echopatch.py dinput8.dll dinput8_autorun_mp.dll --memory-protect
```

The script refuses any other build, because the offsets would not match.

| File | SHA-256 |
|---|---|
| `dinput8.dll` (main) | `64730427b77921af31dd4bb101f4580533f64e6eb72fc6be999301799395fdcb` |
| `dinput8.dll` (`MEMORY_PROTECT`) | `19e55601719b419db87ec82dcc31e612a7ef4693754ef5441e848cb0f8e4826b` |

## Compatibility

- **Game:** F.E.A.R. / F.E.A.R. Platinum, `FEAR.exe` with timestamp `0x44EF6AE6` (the version EchoPatch supports)
- **Autorun:** build `nx-amd64-fex-2640`, with either the FEX or Box64 CPU translator
- **Controller:** Joy-Con in handheld mode

## Credits

- **[Autorun](https://github.com/autorunhq/autorun)** by autorunhq: homebrew for running Windows games on Nintendo Switch (formerly Wine-NX).
- **[EchoPatch](https://github.com/Wemino/EchoPatch)** by **Wemino**: a modernization patch for F.E.A.R. and its expansions, including controller support. Every feature comes from EchoPatch; this repository only changes a few bytes so it can run under Autorun.
- **[MinHook](https://github.com/TsudaKageyu/minhook)** by Tsuda Kageyu: the hooking library used by EchoPatch.
- **[SDL3](https://www.libsdl.org/)**: the library EchoPatch uses to read controllers.
- **F.E.A.R.** was developed by Monolith Productions.

Autorun fix by **ipungsx**.

## License

EchoPatch is released under the **GNU General Public License v3.0**, so the modified `dinput8.dll` in this repository is under the same license (see [`LICENSE`](LICENSE)). EchoPatch's full source code is available at <https://github.com/Wemino/EchoPatch>. Every modification is listed in the tables in [The fix](#the-fix) and can be reproduced with [`tools/patch_echopatch.py`](tools/patch_echopatch.py).

This repository does not include any game files. You need your own legitimate copy of F.E.A.R.
