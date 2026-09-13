#!/usr/bin/env python3
"""
reset_app.py — reset Vector Voice to factory settings.

Removes the user settings file. Optionally wipes the extracted Vosk model
and log files. Uses only the standard library; does NOT import the package
so that it can run even if dependencies are broken.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Paths (must mirror infrastructure/settings_repository.py)
# ---------------------------------------------------------------------------

def user_settings_path() -> Path:
    """Return the directory that holds settings.json."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "vector_voice"


def vosk_model_dir() -> Path:
    return PROJECT_ROOT / "model"


def log_files() -> list[Path]:
    return sorted(PROJECT_ROOT.glob("*.log"))


# ---------------------------------------------------------------------------
# ANSI helpers (no-op when colors are unsupported)
# ---------------------------------------------------------------------------

_USE_COLOR = sys.stdout.isatty() and os.name != "nt"


def _c(text: str, code: str) -> str:
    return text if not _USE_COLOR else f"\033[{code}m{text}\033[0m"


def green(s: str) -> str:  return _c(s, "32")
def yellow(s: str) -> str: return _c(s, "33")
def red(s: str) -> str:    return _c(s, "31")
def bold(s: str) -> str:   return _c(s, "1")
def dim(s: str) -> str:    return _c(s, "2")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_targets(wipe_vosk: bool, wipe_logs: bool):
    """Return a list of (label, path, kind) where kind is 'file' or 'dir'."""
    targets = []

    settings_dir = user_settings_path()
    settings_file = settings_dir / "settings.json"

    if settings_file.exists():
        targets.append(("User settings file", settings_file, "file"))
    elif settings_dir.exists() and any(settings_dir.iterdir()):
        targets.append((
            "User settings directory (contains leftovers)",
            settings_dir,
            "dir",
        ))

    if wipe_vosk:
        model = vosk_model_dir()
        if model.exists():
            targets.append(("Installed Vosk model", model, "dir"))

    if wipe_logs:
        for lf in log_files():
            targets.append(("Log file", lf, "file"))

    return targets


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def human_size(path: Path) -> str:
    if path.is_file():
        total = path.stat().st_size
    else:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    for unit in ("B", "KB", "MB", "GB"):
        if total < 1024:
            return f"{total:.0f} {unit}"
        total /= 1024
    return f"{total:.1f} TB"


def print_targets(targets) -> None:
    if not targets:
        print(yellow("Nothing to reset — already clean."))
        return
    print(bold("Will delete:"))
    for label, path, kind in targets:
        try:
            size = human_size(path)
        except Exception:
            size = "?"
        tag = "file" if kind == "file" else "dir "
        print(f"  [{tag}] {dim(str(path))}  ({size})  — {label}")
    print()


def ask_confirm(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N] " if default_no else " [Y/n] "
    try:
        answer = input(prompt + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not answer:
        return not default_no
    return answer in ("y", "yes", "д", "да")


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------

def remove(path: Path, kind: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"  {dim('(dry-run)')} would remove {path}")
        return True
    try:
        if kind == "dir":
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  {green('removed')} {path}")
        return True
    except FileNotFoundError:
        return True
    except Exception as exc:
        print(f"  {red('failed')}  {path}: {exc}")
        return False


def cleanup_empty_settings_dir() -> None:
    """Remove the settings directory if it is empty after reset."""
    d = user_settings_path()
    try:
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
            print(f"  {green('removed')} {d} (empty)")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reset_app.py",
        description="Reset Vector Voice to factory settings.",
    )
    p.add_argument("--wipe-vosk-model", action="store_true",
                   help="delete the extracted Vosk model (model/ directory)")
    p.add_argument("--wipe-logs", action="store_true",
                   help="delete *.log files in the project root")
    p.add_argument("--all", action="store_true",
                   help="same as --wipe-vosk-model --wipe-logs")
    p.add_argument("-y", "--yes", action="store_true",
                   help="do not ask for confirmation")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="only show what would be deleted")
    p.add_argument("--keep-settings", action="store_true",
                   help="keep settings.json (only wipe model/logs)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    wipe_vosk = args.wipe_vosk_model or args.all
    wipe_logs = args.wipe_logs or args.all

    print(bold("Vector Voice — factory reset"))
    print(dim(f"Project root: {PROJECT_ROOT}"))
    print()

    targets = discover_targets(wipe_vosk, wipe_logs)

    if args.keep_settings:
        settings_dir = user_settings_path()
        targets = [
            t for t in targets
            if settings_dir not in t[1].parents and t[1] != settings_dir
        ]

    print_targets(targets)
    if not targets:
        return 0

    if args.dry_run:
        print(dim("dry-run: nothing was deleted."))
        return 0

    if not args.yes and not ask_confirm("Continue?", default_no=True):
        print("Cancelled.")
        return 1

    ok = True
    for _label, path, kind in targets:
        ok &= remove(path, kind, dry_run=False)

    if not args.keep_settings:
        cleanup_empty_settings_dir()

    print()
    if ok:
        print(green(bold(
            "Done. The next launch will show the first-time setup wizard."
        )))
        return 0
    print(red(bold("Finished with errors — see output above.")))
    return 2


if __name__ == "__main__":
    sys.exit(main())