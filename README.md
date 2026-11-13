# EchoPatch Fix for Autorun (F.E.A.R. di Nintendo Switch)

Versi `dinput8.dll` EchoPatch yang sudah dipatch agar bisa berjalan di **Autorun** (Wine untuk Nintendo Switch), sehingga dukungan controller EchoPatch untuk **F.E.A.R.** bisa aktif.

> **Status: eksperimental.** Patch ini hanya mengubah 3 byte (atau 9 byte untuk versi alternatif) pada `dinput8.dll` EchoPatch. Gunakan dengan cadangan file asli.

*English summary at the bottom.*

---

## Masalah

Saat F.E.A.R. dijalankan di Autorun (build `nx-amd64-fex-2640`) dengan EchoPatch terpasang, muncul popup berikut setiap kali game dimulai:

```
Failed to enable hook for API: CreateWindowExA
Error: MH_ERROR_MEMORY_ALLOC
```

Akibatnya tidak ada satu pun fitur EchoPatch yang aktif, termasuk dukungan controller lewat SDL3. Di sisi lain, F.E.A.R. membaca keyboard, mouse, dan joystick langsung melalui DirectInput, sehingga tombol dan stik Joy-Con yang diterjemahkan Autorun menjadi keyboard/mouse juga tidak sampai ke game. Hasilnya, hampir semua tombol tidak berfungsi dan hanya layar sentuh yang bisa dipakai di menu.

## Penyebab

EchoPatch memakai [MinHook](https://github.com/TsudaKageyu/minhook) untuk memasang hook. Sebelum mengaktifkan hook, MinHook "membekukan" semua thread lain di proses dengan meminta daftar thread lewat `CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)`.

Autorun menjalankan game sebagai satu proses tanpa daftar thread yang lengkap, sehingga pemanggilan itu gagal. MinHook kemudian menghentikan proses pemasangan hook dan mengembalikan kode `9` (`MH_ERROR_MEMORY_ALLOC`). Nama error ini menyesatkan, karena masalahnya sama sekali bukan kekurangan memori.

Petunjuknya ada pada pesan error itu sendiri: yang gagal adalah *enable* hook (`MH_EnableHook`), bukan *create* hook (`MH_CreateHook`). Artinya alokasi memori untuk trampoline sebenarnya sudah berhasil.

## Perbaikan

Di fungsi `Freeze()` milik MinHook, kegagalan mengambil daftar thread tidak lagi dianggap error. MinHook melewati pembekuan thread dan melanjutkan dengan status `MH_OK`. Langkah ini aman, karena saat EchoPatch dimuat (`DllMain` dari `dinput8.dll`), game praktis masih berjalan di satu thread.

| Offset file | VA | Asli | Baru | Keterangan |
|---|---|---|---|---|
| `0x7393D` | `0x1007453D` | `6A 09 5B` (`push 9; pop ebx`) | `31 DB 90` (`xor ebx, ebx; nop`) | `Freeze()`: lanjut dengan `MH_OK` saat snapshot thread gagal |

### Versi alternatif (`alternatif/MEMORY_PROTECT`)

Jika versi utama memunculkan `MH_ERROR_MEMORY_PROTECT`, gunakan versi ini. Selain perbaikan di atas, izin `VirtualProtect` saat menulis patch diubah dari `PAGE_EXECUTE_READWRITE` (`0x40`) menjadi `PAGE_READWRITE` (`0x04`):

| Offset file | VA | Asli | Baru | Keterangan |
|---|---|---|---|---|
| `0x73A3A` | `0x1007463A` | `6A 40` | `6A 04` | MinHook `EnableHookLL()` |
| `0x49C2C` | `0x1004A82C` | `6A 40` | `6A 04` | `MemoryHelper` (tulis memori) |
| `0x66AFC` | `0x100676FC` | `6A 40` | `6A 04` | `MemoryHelper` (tulis 1 byte) |

## Instalasi

1. Pastikan F.E.A.R. sudah ada di `switch/wine/drive_c/FEAR Platinum/` dan sudah ditambahkan ke library Autorun.
2. Cadangkan `dinput8.dll` dan `EchoPatch.ini` milikmu jika ada.
3. Salin isi folder [`FEAR Platinum/`](FEAR%20Platinum) dari repo ini ke `switch/wine/drive_c/FEAR Platinum/` di kartu SD, lalu timpa file lama.
4. Hapus `autoexec.cfg` di folder game jika pernah kamu buat sendiri.
5. Jalankan game. Jika tidak ada popup error, berarti EchoPatch sudah aktif.
6. Jika muncul `MH_ERROR_MEMORY_PROTECT`, ganti `dinput8.dll` dengan file dari [`alternatif/MEMORY_PROTECT/`](alternatif/MEMORY_PROTECT).

### Pengaturan `EchoPatch.ini` untuk Switch

`EchoPatch.ini` di repo ini sudah disesuaikan untuk Switch. Perubahannya dari pengaturan bawaan:

| Opsi | Nilai | Alasan |
|---|---|---|
| `DisableRedundantHIDInit` | `1` | Game tidak lagi mengambil controller lewat DirectInput, sehingga input sepenuhnya lewat SDL3 |
| `MaxFPS` | `60.0` | Sesuai layar Switch |
| `FastVRAMDetection` | `0` | Menghindari deteksi VRAM via DXGI |
| `HighResolutionReflections`, `NoLODBias`, `ReducedMipMapBias`, `EnablePersistentWorldState` | `0` | Mengurangi beban GPU dan memori |
| `TouchpadEnabled` | `0` | Tidak relevan untuk Joy-Con |
| `EnableCrashHandler` | `0` | Mengurangi hook yang tidak diperlukan |

Susunan tombol controller mengikuti bawaan EchoPatch (ZR tembak, ZL bidik, A lompat, B jongkok, dan seterusnya) dan bisa diubah di bagian `[Controller]`.

### Tips di Autorun

- Jika satu tombol menjalankan dua aksi sekaligus, kosongkan tombol tersebut di mapping Autorun (**Y → Controls** pada game), supaya input hanya lewat EchoPatch.
- Jangan menekan **Minus + klik stik kanan** bersamaan saat bermain. Kombinasi itu membuka keyboard layar Autorun, dan selama keyboard terbuka game tidak menerima input controller.
- Gunakan resolusi **1280x720** di game supaya jendela memenuhi layar.

## Membuat patch sendiri

Jika kamu punya `dinput8.dll` EchoPatch dengan build yang sama (SHA-256 `94cd696b4bb5278ed79244ec564a6001920553d3be44a7730a53ee2e75619670`), patch bisa dibuat sendiri:

```sh
python3 tools/patch_echopatch.py dinput8.dll dinput8_autorun.dll
python3 tools/patch_echopatch.py dinput8.dll dinput8_autorun_mp.dll --memory-protect
```

Skrip akan menolak file dengan build berbeda, karena offset-nya tidak akan cocok.

| File | SHA-256 |
|---|---|
| `FEAR Platinum/dinput8.dll` | `64730427b77921af31dd4bb101f4580533f64e6eb72fc6be999301799395fdcb` |
| `alternatif/MEMORY_PROTECT/dinput8.dll` | `19e55601719b419db87ec82dcc31e612a7ef4693754ef5441e848cb0f8e4826b` |

## Kompatibilitas

- **Game:** F.E.A.R. / F.E.A.R. Platinum, `FEAR.exe` dengan timestamp `0x44EF6AE6` (versi yang didukung EchoPatch)
- **Autorun:** build `nx-amd64-fex-2640`, dengan penerjemah CPU FEX maupun Box64
- **Controller:** Joy-Con dalam mode handheld

## Credits

- **[Autorun](https://github.com/autorunhq/autorun)** oleh autorunhq: homebrew untuk menjalankan game Windows di Nintendo Switch (sebelumnya Wine-NX).
- **[EchoPatch](https://github.com/Wemino/EchoPatch)** oleh **Wemino**: patch modernisasi untuk F.E.A.R. dan ekspansinya, termasuk dukungan controller. Semua fitur berasal dari EchoPatch; repo ini hanya mengubah beberapa byte agar bisa berjalan di Autorun.
- **[MinHook](https://github.com/TsudaKageyu/minhook)** oleh Tsuda Kageyu: library hooking yang dipakai EchoPatch.
- **[SDL3](https://www.libsdl.org/)**: library yang dipakai EchoPatch untuk membaca controller.
- **F.E.A.R.** dikembangkan oleh Monolith Productions.

Perbaikan untuk Autorun oleh **ipungsx**.

## Lisensi

EchoPatch dirilis di bawah **GNU General Public License v3.0**, sehingga file `dinput8.dll` hasil modifikasi di repo ini juga tunduk pada lisensi yang sama (lihat [`LICENSE`](LICENSE)). Kode sumber lengkap EchoPatch tersedia di <https://github.com/Wemino/EchoPatch>. Seluruh modifikasi yang dilakukan tercantum di tabel pada bagian [Perbaikan](#perbaikan) dan dapat direproduksi dengan [`tools/patch_echopatch.py`](tools/patch_echopatch.py).

Repo ini tidak menyertakan file game apa pun. Kamu harus memiliki salinan F.E.A.R. yang sah.

---

## English summary

Patched EchoPatch `dinput8.dll` for running **F.E.A.R.** with controller support under **Autorun** (Wine on Nintendo Switch).

Under Autorun, EchoPatch fails at startup with `Failed to enable hook for API: CreateWindowExA / MH_ERROR_MEMORY_ALLOC`. The real cause is MinHook's `Freeze()`: it calls `CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD)` to suspend other threads before writing a hook, that call fails under Autorun, and MinHook reports it as `MH_ERROR_MEMORY_ALLOC` (code 9).

The fix changes 3 bytes at file offset `0x7393D` (`push 9; pop ebx` to `xor ebx, ebx; nop`), so a failed thread snapshot no longer aborts the hook and `MH_OK` is returned instead. The `alternatif/MEMORY_PROTECT` build additionally requests `PAGE_READWRITE` instead of `PAGE_EXECUTE_READWRITE` for `VirtualProtect`, for use if `MH_ERROR_MEMORY_PROTECT` appears.

Install: copy `FEAR Platinum/` to `switch/wine/drive_c/FEAR Platinum/` on the SD card. Credits: Autorun (autorunhq), EchoPatch (Wemino), MinHook (Tsuda Kageyu), SDL3. Licensed under GPL-3.0, like EchoPatch.
