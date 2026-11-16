# Deus Ex: Mankind Divided — Russian Voice Loudness Fix

Normalizes the loudness of the Russian voice-over in *Deus Ex: Mankind Divided*
relative to the English original. This repository contains the **source code** of
the mod's build tooling and the installer itself.

> ⚠️ This repository only contains scripts. The mod's data (FSB banks,
> `patches.json`, the built `.7z`) is **not** committed here — it is large and
> contains modified game audio. See Releases for the ready-to-use archive.

## Contents

```
installer.py            — GUI installer (Python 3 + Tkinter, dark theme)
work/                   — build scripts
work/datautils/         — Glacier (.archive) format parsing
work/fsb5/              — FSB5 parser (third-party module)
```

## What the scripts do

- **Localization extraction** — unpack text and voice from the game's archives.
- **Loudness measurement & normalization** — compare RU vs EN loudness (LUFS via
  `ebur128`) and match RU to EN where the difference is ≥ 3 dB.
- **Bank rebuild** — re-encode FSB5 banks via FMOD FSBank.
- **Patch application** — byte-level insertion of banks into the game's archives
  (with `.bak` backups).
- **Mod packaging** — generate `patches.json` and the installer package.

## Installer

`installer.py` is a self-contained GUI installer with game auto-detection,
a progress bar and a rollback button. It is compiled into a single exe via
PyInstaller (end users do not need Python):

```bash
pyinstaller --onefile --windowed --icon icon.ico --add-data "icon.ico;." installer.py
```

## Third-party code

`work/fsb5/` is a third-party FSB5 reader module (by Simon Pinfold). See the
module's source for its license.

## License

MIT (see `LICENSE`). This is a fan-made project, not affiliated with Square Enix /
Eidos-Montréal.
