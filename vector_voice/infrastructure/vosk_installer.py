"""Install a Vosk model from a bundled zip archive."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from vector_voice.domain.ports import VoskModelInstallerPort


class ZipVoskModelInstaller(VoskModelInstallerPort):
    def is_installed(self, path: str) -> bool:
        p = Path(path)
        if not p.is_dir():
            return False
        return (p / "am").exists() or (p / "conf").exists() or (p / "graph").exists()

    def install(self, archive_path: str, target_dir: str) -> None:
        """Extract a Vosk zip, stripping the top-level directory if present."""
        zip_path = Path(archive_path)
        target = Path(target_dir)

        if not zip_path.is_file():
            raise FileNotFoundError(str(zip_path))

        parent = target.parent
        parent.mkdir(parents=True, exist_ok=True)

        tmp = parent / (target.name + "_extract_tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp)

            candidates = list(tmp.iterdir())
            root = candidates[0] if len(candidates) == 1 and candidates[0].is_dir() else tmp

            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(root), str(target))
        finally:
            if tmp.exists():
                shutil.rmtree(tmp, ignore_errors=True)