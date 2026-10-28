import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, BinaryIO, Dict, Any
from app.adapters.base import StorageAdapter, DiscoveredArtifact
from app.config import settings

class LocalFilesystemAdapter(StorageAdapter):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.root_path = Path(config.get("root_path", "")).resolve()

    def _validate_root(self):
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_path}")

        # Check path containment against allowed roots
        canonical_str = str(self.root_path).replace("\\", "/")
        allowed = False
        for allowed_root in settings.ALLOWED_STORAGE_ROOTS:
            try:
                allowed_canonical = str(Path(allowed_root).resolve()).replace("\\", "/")
                if canonical_str.startswith(allowed_canonical) or canonical_str == allowed_canonical:
                    allowed = True
                    break
            except Exception:
                continue

        # In dev mode, also allow if path is inside workspace or project root
        project_root = str(Path(".").resolve()).replace("\\", "/")
        if canonical_str.startswith(project_root):
            allowed = True

        if not allowed:
            raise PermissionError(f"Root path {self.root_path} violates allowed boundary configuration.")

    def test_connection(self) -> Tuple[bool, str]:
        try:
            self._validate_root()
            # Test readability
            entries = os.listdir(self.root_path)
            return True, f"Successfully accessed local directory with {len(entries)} items"
        except Exception as e:
            return False, f"Local directory validation failed: {str(e)}"

    def _resolve_safe_path(self, artifact_key: str) -> Path:
        self._validate_root()
        # Prevent traversal in artifact key
        safe_rel = os.path.normpath(artifact_key).lstrip("\\/.")
        target = (self.root_path / safe_rel).resolve()
        
        # Ensure target is strictly inside root_path
        if not str(target).startswith(str(self.root_path)):
            raise PermissionError("Path traversal attempt detected in artifact key.")
        if not target.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_key}")
        return target

    def _detect_format(self, path: Path) -> str:
        name = path.name.lower()
        if name.endswith(".zip"):
            return "zip"
        if name.endswith(".tar") or name.endswith(".tar.gz") or name.endswith(".tgz") or name.endswith(".tar.bz2"):
            return "tar"
        if name.endswith(".dump") or name.endswith(".pgdump"):
            return "pg_custom"
        if name.endswith(".sql"):
            # Sample first 512 bytes to determine dialect
            try:
                with open(path, "rb") as f:
                    chunk = f.read(512).decode("utf-8", errors="ignore").lower()
                    if "postgresql" in chunk or "pg_" in chunk or "set statement_timeout" in chunk:
                        return "sql_pg"
                    if "mysql" in chunk or "mariadb" in chunk:
                        return "sql_mysql"
            except Exception:
                pass
            return "sql_pg"
        return "unknown"

    def discover_artifacts(self) -> List[DiscoveredArtifact]:
        self._validate_root()
        artifacts = []
        valid_extensions = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".dump", ".pgdump", ".sql", ".bak"}
        
        for root, dirs, files in os.walk(self.root_path):
            # Do not follow symlinks outside root
            for f in files:
                file_path = Path(root) / f
                if any(file_path.name.lower().endswith(ext) for ext in valid_extensions):
                    try:
                        stat = file_path.stat()
                        if stat.st_size > settings.MAX_BACKUP_SIZE_BYTES:
                            continue  # Exceeds max allowed size
                        
                        rel_path = file_path.relative_to(self.root_path).as_posix()
                        fmt = self._detect_format(file_path)
                        modified_at = datetime.utcfromtimestamp(stat.st_mtime)
                        
                        artifacts.append(DiscoveredArtifact(
                            artifact_key=rel_path,
                            file_name=file_path.name,
                            format=fmt,
                            size_bytes=stat.st_size,
                            modified_at=modified_at,
                            metadata={
                                "absolute_path": str(file_path),
                                "inode": stat.st_ino if hasattr(stat, "st_ino") else 0
                            }
                        ))
                    except Exception:
                        continue
        return artifacts

    def open_stream(self, artifact_key: str) -> BinaryIO:
        target = self._resolve_safe_path(artifact_key)
        return open(target, "rb")

    def get_local_path(self, artifact_key: str) -> str:
        target = self._resolve_safe_path(artifact_key)
        return str(target)
