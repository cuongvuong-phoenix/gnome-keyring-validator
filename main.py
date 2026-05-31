#!/usr/bin/env python

import os
import re
import signal
import subprocess
import sys

from gi.repository import Gio, GLib

if len(sys.argv) < 2:
    print(
        "[ERROR] Expect at least 1 argument. Please provide the path to the keyring file"
    )
    sys.exit(1)


KEYRING_PATH = os.path.expanduser(sys.argv[1])
WATCH = len(sys.argv) == 3 and sys.argv[2] == "--watch"


def validate_data(data: str):
    kf = GLib.KeyFile.new()
    try:
        kf.load_from_bytes(
            GLib.Bytes.new(data.encode("utf-8")), GLib.KeyFileFlags.KEEP_COMMENTS
        )
        return True
    except GLib.Error:
        return False


def get_display_name(block: str):
    match = re.search(r"^display-name=(.+)$", block, re.MULTILINE)
    return match.group(1).strip() if match else "Unknown application"


def get_corrupted_sections(content: str):
    # Split into structural blocks
    blocks = content.split("\n\n")

    corrupted_sections: list[tuple[str, str]] = []

    for block in blocks:
        # Get section_id first
        match = re.match(r"^\[(\d+)\]", block.strip())
        if not match:
            continue

        section_id = match.group(1)

        test_blocks = [
            b
            for b in blocks
            # Then get same-section blocks
            if b.strip().startswith(f"[{section_id}")
        ]
        test_content = "\n\n".join(test_blocks) + "\n"

        if not validate_data(test_content):
            display_name = get_display_name(block)
            corrupted_sections.append((section_id, display_name))

    return corrupted_sections


def notify_corrupted(corrupted_sections: list[tuple[str, str]]):
    if len(corrupted_sections) == 0:
        msg = "The file is corrupted but cannot auto-identify the root cause"
    else:
        section_msgs = list(
            map(lambda s: f"ID: {s[0]} | App: {s[1]}", corrupted_sections)
        )
        msg = f"{'\n'.join(section_msgs)}"

    cmd = [
        "notify-send",
        "--urgency=critical",
        "--icon=dialog-error",
        "--app-name='gnome-keyring-validator'",
        "Keyring corrupted",
        msg,
    ]

    try:
        subprocess.run(cmd, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to trigger notification: {e}", file=sys.stderr)


def check_file():
    if not os.path.exists(KEYRING_PATH):
        return

    with open(KEYRING_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if validate_data(content):
        return

    notify_corrupted(get_corrupted_sections(content))


def monitor_file():
    file_obj = Gio.File.new_for_path(KEYRING_PATH)
    monitor = file_obj.monitor_file(Gio.FileMonitorFlags.NONE, None)

    monitor.connect(
        "changed",
        lambda _monitor, _file, _other_file, event_type: (
            check_file()
            if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT
            else None
        ),
    )

    loop = GLib.MainLoop()

    def handle_shutdown_signal(signum, _frame):
        sig_name = signal.Signals(signum).name
        print(
            f"[SIGNAL] Received system signal {sig_name} ({signum}). Terminating loop gracefully..."
        )
        loop.quit()

    # [1] Terminal emulator closing / hangup events
    signal.signal(signal.SIGHUP, handle_shutdown_signal)
    # [2] Ctrl+C
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    # [15] kill / systemd stop / desktop logout requests
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        loop.run()
    except Exception as e:
        print(f"[ERROR] Unexpected execution error: {e}", file=sys.stderr)
    finally:
        # This block is guaranteed to run after `loop.quit()` or crashes
        print("[SHUTDOWN] Performing graceful application cleanup...")
        monitor.cancel()  # Release kernel file tracking descriptors safely


def main():
    check_file()

    if WATCH:
        monitor_file()


if __name__ == "__main__":
    main()
