# EchoPatch Fix for Autorun (F.E.A.R. on Nintendo Switch)

A patched EchoPatch `dinput8.dll` that runs under **Autorun** (Wine for Nintendo Switch), so EchoPatch's controller support for **F.E.A.R.** can work.

> **Status: experimental.** The patch changes only 3 bytes (9 bytes for the alternative build) in EchoPatch's `dinput8.dll`. Keep a backup of your original files.

**Base:** EchoPatch **4.5.2** (latest). This includes the in-game **Button Mapping** menu, which is what the earlier 4.3.0-based build was missing.

**Download:** [Releases](https://github.com/ipungsx/FEAR_EchopatchFIXforAutorun/releases/latest)

---

## Version history

| Release | EchoPatch base | Notes |
|---|---|---|
| 2.0 | **4.5.2** | Button Mapping menu, FPS Limit menu option, `.asi` plugin loader, console rework, hardware cursor fix. Patcher is now signature-based, so it works for any EchoPatch version |
| 1.0 | 4.3.0 | First Autorun fix. Patcher used hard-coded offsets and only accepted one build |

### Why 4.3.0 could not map buttons in-game

EchoPatch only added the **Button Mapping** submenu in **4.4.0** (commit `Add a button-mapping sub-menus to the Controller screen`). In 4.3.0 the controller screen only had sensitivity, edge acceleration, rumble, gyro and touchpad, so walk/run had to be set by editing the `[Controller]` section of `EchoPatch.ini` by hand. Updating to 4.5.2 gives you `Options > Controls > Configure joystick/gamepad > Button Mapping`, where walk/run can be assigned from the list (command `16` = Hold to Walk, `18` = Toggle Walk/Run).

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

The patcher finds each site by byte signature, so the offsets below are simply where the signatures land in the **EchoPatch 4.5.2** build. Other EchoPatch versions land at different offsets, but the tool handles them automatically.

| File offset (4.5.2) | VA | Original | New | Description |
|---|---|---|---|---|
| `0xB069F` | `0x100B129F` | `6A 09 5B` (`push 9; pop ebx`) | `31 DB 90` (`xor ebx, ebx; nop`) | `Freeze()`: continue with `MH_OK` when the thread snapshot fails |

### Alternative build (`MEMORY_PROTECT`)

Use this build only if the main one shows `MH_ERROR_MEMORY_PROTECT`. On top of the fix above, it makes `VirtualProtect` request `PAGE_READWRITE` (`0x04`) instead of `PAGE_EXECUTE_READWRITE` (`0x40`) when writing patches:

| File offset (4.5.2) | VA | Original | New | Description |
|---|---|---|---|---|
| `0xB079C` | `0x100B139C` | `6A 40` | `6A 04` | MinHook `EnableHookLL()` |
| `0x555FC` | `0x100561FC` | `6A 40` | `6A 04` | `MemoryHelper` (memory write) |
| `0x957CC` | `0x100963CC` | `6A 40` | `6A 04` | `MemoryHelper` (single byte write) |

## Installation

1. Make sure F.E.A.R. is in `switch/wine/drive_c/FEAR Platinum/` and has been added to your Autorun library.
2. Back up your existing `dinput8.dll` and `EchoPatch.ini`, if you have them.
3. Download `FEAR_EchoPatch_Autorun.zip` from [Releases](https://github.com/ipungsx/FEAR_EchopatchFIXforAutorun/releases/latest).
4. Extract it and copy the contents of `FEAR Platinum/` to `switch/wine/drive_c/FEAR Platinum/` on your SD card, overwriting the old files.
5. Delete `autoexec.cfg` from the game folder if you created one yourself.
6. Start the game. If no error popup appears, EchoPatch is active.
7. If `MH_ERROR_MEMORY_PROTECT` appears, download `FEAR_EchoPatch_Autorun_MEMORY_PROTECT.zip` and replace `dinput8.dll` with the one inside it.

### `EchoPatch.ini` settings for Switch

The included `EchoPatch.ini` is EchoPatch 4.5.2's default config with a few options tuned for the Switch. Changes from the 4.5.2 defaults:

| Option | Value | Reason |
|---|---|---|
| `CheckLAAPatch` | `0` | No interactive LAA prompt under Autorun |
| `HighFPSFixes` | `0` | Fewer hooks, and the framerate is capped at 60 anyway |
| `FastVRAMDetection` | `0` | Avoids VRAM detection through DXGI |
| `FixSoundWrapperLoading` | `0` | No local DirectSound wrapper is used |
| `MaxFPS` | `60` | Matches the Switch display |
| `HighResolutionReflections`, `NoLODBias`, `ReducedMipMapBias` | `0` | Lower GPU load |
| `EnablePersistentWorldState`, `SavePersistentWorldState` | `0` | Lower memory load |
| `RumbleEnabled` | `1` | Joy-Con rumble |
| `TouchpadEnabled` | `0` | Not relevant for Joy-Con |
| `EnableCrashHandler` | `0` | Fewer unnecessary hooks |

`DisableRedundantHIDInit` stays at `1` (the 4.5.2 default): the game no longer grabs the controller through DirectInput, so all controller input goes through SDL3.

The controller layout follows EchoPatch's defaults (ZR fire, ZL aim, A jump, B crouch, and so on). It can be changed either in the `[Controller]` section of the file or, in-game, from `Options > Controls > Configure joystick/gamepad > Button Mapping`.

### Mapping walk/run on the Switch

Walk/run are F.E.A.R. engine commands, not EchoPatch features, so they are simply entries in the Button Mapping list:

- `16` = **Hold to Walk** — hold the button to walk instead of run
- `18` = **Toggle Walk/Run** — tap to switch between walking and running

Since a Joy-Con has no extra paddles, the easiest place to put them is a *hold* on a button that is otherwise unused, for example:

```ini
; Lean Right (tap), Hold to Walk (hold)
GAMEPAD_DPAD_RIGHT = 21
GAMEPAD_DPAD_RIGHT_HOLD = 16
GAMEPAD_DPAD_RIGHT_HOLD_TIME = 400
```

Or do it in-game from the Button Mapping menu.

### Autorun tips

- If a button triggers two actions at once, clear that button in Autorun's mapping for the game (**Y → Controls**), so the input only goes through EchoPatch.
- Avoid pressing **Minus + right stick click** together while playing. That combination opens Autorun's on-screen keyboard, and the game receives no controller input while it is open.
- Use **1280x720** in the game so the window fills the screen.

## Building the patch yourself

The patcher works on **any** EchoPatch `dinput8.dll` release, because it finds each site by byte signature rather than by a fixed offset. Get the official `dinput8.dll` from [EchoPatch's releases](https://github.com/Wemino/EchoPatch/releases) (this build uses 4.5.2, SHA-256 `64bb954e4f268ac5092294d365249b9eb01d6fe7003a56aeb23f419692c331a8`), then run:

```sh
# Check that the signatures are found (no file is written)
python3 tools/patch_echopatch.py dinput8.dll --check

# Main build: fix MinHook's Freeze()
python3 tools/patch_echopatch.py dinput8.dll dinput8_autorun.dll

# Alternative build: also switch VirtualProtect to PAGE_READWRITE
python3 tools/patch_echopatch.py dinput8.dll dinput8_autorun_mp.dll --memory-protect
```

Every signature must match exactly once, otherwise the tool writes nothing and tells you which one failed. The main build only changes 3 bytes; the alternative build changes 3 more.

| File | Base | SHA-256 |
|---|---|---|
| `dinput8.dll` (main, 4.5.2) | EchoPatch 4.5.2 | `175f6ba56eed1100b464b23956de98e46d1fd4e0dde3afa7a9dd6096541e8aa2` |
| `dinput8.dll` (`MEMORY_PROTECT`, 4.5.2) | EchoPatch 4.5.2 | `0425ed283e7c769684eda40119ff32fa086e05b19a8eee6d727260ef81d51196` |
| `EchoPatch.ini` (Switch, 4.5.2) | EchoPatch 4.5.2 | `ab4e535822c380a4fda3f3ee7b3bb43179827e350f57d3618ef742add91e92f3` |
| `dinput8.dll` (main, 4.3.0) | EchoPatch 4.3.0 | `64730427b77921af31dd4bb101f4580533f64e6eb72fc6be999301799395fdcb` |
| `dinput8.dll` (`MEMORY_PROTECT`, 4.3.0) | EchoPatch 4.3.0 | `19e55601719b419db87ec82dcc31e612a7ef4693754ef5441e848cb0f8e4826b` |

## Compatibility

- **Game:** F.E.A.R. / F.E.A.R. Platinum, `FEAR.exe` with timestamp `0x44EF6AE6` (the version EchoPatch supports)
- **EchoPatch:** 4.5.2 (latest at the time of writing). Older builds (1.0) were based on 4.3.0
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
