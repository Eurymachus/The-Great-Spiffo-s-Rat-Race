import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


DECOMPILED_DIRECTORY = re.compile(r"^build-(?P<build_id>\d+)-job-(?P<job_id>\d+)$")


@dataclass(frozen=True)
class ReferenceDeploymentPaths:
    steamcmd_executable: Path
    install_root: Path
    java_executable: str
    vineflower_jar: Path
    decompiled_parent: Path

    def decompiled_root(self, build_id=""):
        if not build_id or not self.decompiled_parent.is_dir():
            return None
        candidates = []
        for path in self.decompiled_parent.iterdir():
            match = DECOMPILED_DIRECTORY.fullmatch(path.name)
            if path.is_dir() and match and match.group("build_id") == str(build_id):
                candidates.append((int(match.group("job_id")), path))
        return max(candidates, default=(0, None))[1]


def resolved_reference_paths():
    install_root = Path(str(settings.PZ_REFERENCE_ROOT).strip())
    return ReferenceDeploymentPaths(
        steamcmd_executable=Path(str(settings.STEAMCMD_EXECUTABLE).strip()),
        install_root=install_root,
        java_executable=str(settings.JAVA_EXECUTABLE).strip(),
        vineflower_jar=Path(str(settings.VINEFLOWER_JAR).strip()),
        decompiled_parent=install_root / "tgsrr_decompiled",
    )
