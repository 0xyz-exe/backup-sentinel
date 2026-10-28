from abc import ABC, abstractmethod
from typing import List, Dict, Any, BinaryIO, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DiscoveredArtifact:
    artifact_key: str
    file_name: str
    format: str
    size_bytes: int
    modified_at: datetime
    metadata: Dict[str, Any]

class StorageAdapter(ABC):
    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Verify storage accessibility and credentials."""
        pass

    @abstractmethod
    def discover_artifacts(self) -> List[DiscoveredArtifact]:
        """List available backup artifacts safely."""
        pass

    @abstractmethod
    def open_stream(self, artifact_key: str) -> BinaryIO:
        """Stream backup artifact content for inspection without full memory load."""
        pass

    @abstractmethod
    def get_local_path(self, artifact_key: str) -> str:
        """Return safe filesystem path if local or download to controlled temp workspace."""
        pass
