from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
import hashlib


class FileChunker:
    """Handles file chunking and differential update detection."""

    def __init__(self, chunk_size: int = 1024 * 1024):
        """Initialize the chunker with a specific chunk size.

        Args:
            chunk_size: Size of each chunk in bytes (default: 1MB)
        """
        self.chunk_size = chunk_size

    def get_file_chunks(self, file_path: Path) -> Dict[str, Tuple[int, int]]:
        """
        Analyze an existing file and return its chunks with hashes.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dictionary mapping chunk hashes to (start, end) positions
        """
        chunks = {}

        if not file_path.exists() or file_path.stat().st_size == 0:
            return chunks

        with file_path.open('rb') as f:
            position = 0
            while True:
                chunk_data = f.read(self.chunk_size)
                if not chunk_data:
                    break

                chunk_hash = hashlib.md5(chunk_data).hexdigest()
                chunk_size = len(chunk_data)
                chunks[chunk_hash] = (position, position + chunk_size - 1)
                position += chunk_size

        return chunks

    def _build_ranges(self, total_size: int, start_offset: int = 0) -> List[Tuple[int, int]]:
        """Build contiguous byte ranges using configured chunk size."""
        if total_size <= 0 or start_offset >= total_size:
            return []

        ranges: List[Tuple[int, int]] = []
        start = max(0, start_offset)
        while start < total_size:
            end = min(start + self.chunk_size - 1, total_size - 1)
            ranges.append((start, end))
            start = end + 1

        return ranges

    def find_changed_chunks(
        self,
        response: Any,
        existing_chunks: Dict[str, Tuple[int, int]],
        local_path: Optional[Path] = None
    ) -> List[Tuple[int, int]]:
        """
        Compare a remote file to local file and identify ranges that need downloading.

        Uses file size comparison since HTTP streams aren't seekable.
        If sizes match, assumes file is unchanged. If sizes differ or file
        doesn't exist, downloads the entire file.

        Args:
            response: The file download response
            existing_chunks: Dictionary of existing chunks from get_file_chunks
            local_path: Path to local file for size comparison

        Returns:
            List of (start, end) byte ranges that need to be downloaded
        """
        total_size = int(response.headers.get('content-length', 0))

        if total_size == 0:
            return []

        # If no local file exists, download everything
        if not existing_chunks:
            return self._build_ranges(total_size)

        # Compare file sizes - if local file exists and matches remote size, skip
        if local_path and local_path.exists():
            local_size = local_path.stat().st_size
            if local_size == total_size:
                # File sizes match - assume unchanged
                return []
            if 0 < local_size < total_size:
                # Resume from the already-downloaded prefix
                return self._build_ranges(total_size, start_offset=local_size)

        # Sizes differ or can't compare - download everything
        return self._build_ranges(total_size)
