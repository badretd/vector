"""Vosk model presence check + installer from bundled zip archives."""
import shutil
import zipfile
from pathlib import Path


def vosk_model_ok(path) -> bool:
    p = Path(path)
    if not p.is_dir():
        return False
    return (p / "am").exists() or (p / "conf").exists() or (p / "graph").exists()


def install_vosk_model(zip_path, target_dir) -> None:
    """Extract a Vosk model zip into `target_dir`.

    Vosk zips normally contain one top-level directory; we strip it so that
    `target_dir/am`, `target_dir/conf`, ... end up in place.
    """
    zip_path = Path(zip_path)
    target_dir = Path(target_dir)

    if not zip_path.is_file():
        raise FileNotFoundError(str(zip_path))

    parent = target_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = parent / (target_dir.name + "_extract_tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)

        candidates = list(tmp_dir.iterdir())
        if len(candidates) == 1 and candidates[0].is_dir():
            model_root = candidates[0]
        else:
            model_root = tmp_dir

        if target_dir.exists():
            shutil.rmtree(target_dir)

        shutil.move(str(model_root), str(target_dir))
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)