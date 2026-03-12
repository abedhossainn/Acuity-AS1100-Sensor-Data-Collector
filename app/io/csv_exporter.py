"""CSV export functionality for sensor data."""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.domain.models import SampleRecord


class CSVExporter:
    """Handle CSV export of sensor measurements."""
    
    FIELDNAMES = [
        "timestamp",
        "distance",
        "unit",
        "mode",
        "frequency_hz",
    ]
    
    def __init__(self, output_folder: str, session_name: Optional[str] = None, decimal_places: int = 4):
        """
        Initialize exporter.
        
        Parameters
        ----------
        output_folder : str
            Path where CSV files will be saved
        session_name : str, optional
            Custom session name; defaults to timestamp
        decimal_places : int, optional
            Number of decimal places for values (default 4)
        """
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.decimal_places = max(1, min(10, decimal_places))  # Clamp between 1-10
        
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.session_name = session_name
        self.filepath = self.output_folder / f"{session_name}.csv"
        self._file_handle: Optional[object] = None
        self._writer: Optional[csv.DictWriter] = None
    
    def open(self) -> None:
        """Open CSV file and write header."""
        self._file_handle = open(self.filepath, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file_handle, fieldnames=self.FIELDNAMES)
        self._writer.writeheader()
        self._file_handle.flush()
    
    def close(self) -> None:
        """Close CSV file."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
            self._writer = None
    
    def write_sample(self, sample: SampleRecord) -> None:
        """
        Write a single sample to CSV.
        
        Parameters
        ----------
        sample : SampleRecord
            Sample to write
        """
        if not self._writer:
            raise RuntimeError("CSV file not open. Call open() first.")
        
        # Format value with configured decimal places
        formatted_distance = f"{sample.value:.{self.decimal_places}f}"
        
        row = {
            "timestamp": sample.timestamp_iso,
            "distance": formatted_distance,
            "unit": sample.unit,
            "mode": sample.mode,
            "frequency_hz": sample.interval_hz if sample.interval_hz else "",
        }
        self._writer.writerow(row)
        self._file_handle.flush()
    
    def write_samples(self, samples: List[SampleRecord]) -> None:
        """
        Write multiple samples to CSV.
        
        Parameters
        ----------
        samples : List[SampleRecord]
            List of samples to write
        """
        for sample in samples:
            self.write_sample(sample)
    
    def get_filepath(self) -> Path:
        """Get the full path to the CSV file."""
        return self.filepath
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
