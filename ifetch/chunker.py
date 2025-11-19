from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
import hashlib

##########################################################################################

# try using a new streaming class to operate chunks like a file

# source: https://gist.github.com/obskyr/b9d4b4223e7eaf4eedcd9defabb34f13

from io import BytesIO, SEEK_SET, SEEK_END


class ResponseStream(object):
    def __init__(self, request_iterator):
        self._bytes = BytesIO()
        self._iterator = request_iterator

    def _load_all(self):
        self._bytes.seek(0, SEEK_END)
        for chunk in self._iterator:
            self._bytes.write(chunk)

    def _load_until(self, goal_position):
        current_position = self._bytes.seek(0, SEEK_END)
        while current_position < goal_position:
            try:
                current_position += self._bytes.write(next(self._iterator))
            except StopIteration:
                break

    def tell(self):
        return self._bytes.tell()

    def read(self, size=None):
        left_off_at = self._bytes.tell()
        if size is None:
            self._load_all()
        else:
            goal_position = left_off_at + size
            self._load_until(goal_position)

        self._bytes.seek(left_off_at)
        return self._bytes.read(size)
    
    def seek(self, position, whence=SEEK_SET):
        if whence == SEEK_END:
            self._load_all()
        else:
            self._bytes.seek(position, whence)


##########################################################################################

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

    def find_changed_chunks(
        self,
        response: Any,
        existing_chunks: Dict[str, Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """
        Compare a remote file to local chunks and identify ranges that need downloading.

        Args:
            response: The file download response
            existing_chunks: Dictionary of existing chunks from get_file_chunks

        Returns:
            List of (start, end) byte ranges that need to be downloaded
        """
        if not existing_chunks:
            total_size = int(response.headers.get('content-length', 0))
            if total_size > 0:
                return [(0, total_size - 1)]
            return []

        total_size = int(response.headers.get('content-length', 0))

        # Save current position to return to it after analysis

        current_pos = 0
        ## 
        stream = ResponseStream(response.iter_content(self.chunk_size))

        current_pos = stream.tell() 

        # Create a list of all byte positions that need downloading
        changed_ranges = []
        position = 0

        ### ... this fails, unsupported operation: seek,  workaround?
        stream.seek(0)

        while position < total_size:
            ## was: chunk_data = response.raw.read(self.chunk_size)
            chunk_data = stream.read(self.chunk_size)
            if not chunk_data:
                break

            chunk_hash = hashlib.md5(chunk_data).hexdigest()
            chunk_size = len(chunk_data)

            # If this chunk doesn't exist locally or is at a different position
            if chunk_hash not in existing_chunks:
                changed_ranges.append((position, position + chunk_size - 1))

            position += chunk_size

        # Restore the original position
        ### ... without using seek ????? 
        ### not supported : response.raw.seek(current_pos)
        stream.seek(current_pos)

        # Optimize the ranges by merging adjacent or overlapping ranges
        if changed_ranges:
            changed_ranges.sort()
            optimized = [changed_ranges[0]]

            for current_start, current_end in changed_ranges[1:]:
                prev_start, prev_end = optimized[-1]

                # If ranges overlap or are adjacent, merge them
                if current_start <= prev_end + 1:
                    optimized[-1] = (prev_start, max(prev_end, current_end))
                else:
                    optimized.append((current_start, current_end))

            return optimized

        return []
