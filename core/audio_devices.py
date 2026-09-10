"""Microphone discovery and samplerate negotiation helpers."""

import sys

import sounddevice as sd

from config import TARGET_RATE


def choose_input_device():
    """Interactively ask the user which input device to use.

    Prints a numbered list and loops until a valid index is entered.
    Returns the selected device index.
    """
    devices = sd.query_devices()
    inputs = [(i, d) for i, d in enumerate(devices) if d['max_input_channels'] > 0]

    if not inputs:
        print("No input devices found.")
        sys.exit(1)

    try:
        default_idx = sd.default.device[0]
    except Exception:
        default_idx = -1

    print("\nAvailable input devices:")
    for i, d in inputs:
        marker = "  (default)" if i == default_idx else ""
        print(f"  [{i}] {d['name']}{marker}")

    while True:
        choice = input("\nEnter microphone number: ").strip()
        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a number.")
            continue
        if any(i == idx for i, _ in inputs):
            print(f"Selected: {devices[idx]['name']}\n")
            return idx
        print("That number is not in the list.")


def pick_samplerate(device_index):
    """Return TARGET_RATE if the device supports it, otherwise its default rate.

    Vosk works best at 16 kHz, but not every mic supports that rate natively.
    In that case we fall back to the device default and resample later.
    """
    try:
        sd.check_input_settings(
            device=device_index,
            samplerate=TARGET_RATE,
            dtype='int16',
            channels=1,
        )
        return TARGET_RATE
    except Exception:
        info = sd.query_devices(device_index)
        return int(info['default_samplerate'])