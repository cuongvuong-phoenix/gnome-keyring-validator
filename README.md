# gnome-keyring-validator

A tiny utility that checks a GNOME Keyring file for corruption and, when something breaks, tells you **which application's entry** is to blame via a desktop notification. It can run as a one-shot check or sit in the background and watch the file for changes.

### Why?

If you're using GNOME Keyring with an empty-password keyring (for auto-login), it will store data in a plaintext, INI-style key file.

A single malformed line (e.g. an unescaped newline inside a secret, a stray character) can corrupt the whole file, and the only symptom you usually see is all of your saved accounts are logged out.

This tool parses the file the same way GLib does, so it catches exactly the kind of corruption that takes the real keyring down.

## Features

- **Validates** a keyring file using GLib's own `KeyFile` parser - the same parser the keyring uses, so a pass here means the file is genuinely well-formed.
- **Pinpoints the culprit.** When the file is corrupt, it isolates each `[section]` and reports the broken one along with its `display-name`, so you know which app's entry to fix.
- **Desktop notifications** via `notify-send` (critical urgency) the moment corruption is detected.
- **Watch mode** keeps an eye on the keyring file and re-checks it on every change, with graceful shutdown on `SIGHUP`, `SIGINT`, and `SIGTERM`.

## Requirements

- Python 3.12+
- [PyGObject](https://pygobject.gnome.org/) - provides `gi` (`Gio`, `GLib`)
- `notify-send` (from `libnotify`) for desktop notifications

On most GNOME systems, `PyGObject` and `libnotify` are already installed. If not:

```sh
# Arch
sudo pacman -S python-gobject libnotify

# Debian / Ubuntu
sudo apt install python3-gi libnotify-bin

# Fedora
sudo dnf install python3-gobject libnotify
```

## Usage

```sh
# One-shot check
./main.py ~/.local/share/keyrings/Default.keyring

# Watch the file and notify on any future corruption
./main.py ~/.local/share/keyrings/Default.keyring --watch
```

- If the file is valid, the tool exits quietly.
- If the file is corrupt, you'll get a critical desktop notification like:

  ```
  Keyring corrupted
  ID: 14 | App: Target App For Corruption
  ```

- If the file is corrupt but no single section can be blamed, the notification will still popup, telling that it cannot auto-detect corrupted sections and you would need to take a closer look yourself.

## Caveats

- Read-only. This tool **diagnoses** corruption; it never modifies your keyring. Always back up before editing a keyring by hand.
- It expects the plaintext key-file format used by GNOME Keyring. Encrypted or binary keyring blobs aren't something it can parse.
- Notifications require a running notification daemon (any standard GNOME/KDE/etc. desktop has one).

## License

MIT
