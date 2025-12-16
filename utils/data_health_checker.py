from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, List

__all__ = ["DataHealthChecker", "create_health_checker"]


class DataHealthChecker:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir)
    
    def check_file_integrity(self, file_path: str) -> bool:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False
    
    def health_check_and_repair(self, file_paths: List[str]) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for file_path in file_paths:
            if os.path.exists(file_path):
                results[file_path] = self.check_file_integrity(file_path)
            else:
                results[file_path] = True
        return results


def create_health_checker(base_file: str) -> DataHealthChecker:
    data_dir = os.path.join(os.path.dirname(os.path.dirname(base_file)), "data")
    return DataHealthChecker(data_dir)
