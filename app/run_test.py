import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.table_extractor import extract_records_from_rows


test_rows = [
    {
        "words": [
            {"text": "1", "x0": 45.35, "x1": 48.25, "top": 191.5},
            {"text": "15086", "x0": 61.2, "x1": 78.7, "top": 191.5},
            {"text": "RAJKUMAR", "x0": 86.65, "x1": 119.47, "top": 191.76},
            {"text": "SINGH", "x0": 121.45, "x1": 140.24, "top": 191.76},
            {"text": "PORIKA", "x0": 142.55, "x1": 164.43, "top": 191.75},
            {"text": "E5", "x0": 193.9, "x1": 200.19, "top": 191.96},
            {"text": "ABU", "x0": 220.1, "x1": 232.81, "top": 191.96},
            {"text": "ROAD", "x0": 234.95, "x1": 251.79, "top": 191.96},
            {"text": "VIZAG", "x0": 298.8, "x1": 316.32, "top": 192.21},
        ]
    },
    {
        "words": [
            {"text": "2", "x0": 44.9, "x1": 48.03, "top": 213.36},
            {"text": "17426", "x0": 61.2, "x1": 78.5, "top": 213.59},
            {"text": "RAMASHISH", "x0": 86.65, "x1": 122.18, "top": 213.56},
            {"text": "KUMAR", "x0": 126, "x1": 148.33, "top": 213.56},
            {"text": "E3", "x0": 193.9, "x1": 200.19, "top": 214.06},
            {"text": "ABU", "x0": 220.1, "x1": 232.81, "top": 214.06},
            {"text": "ROAD", "x0": 234.95, "x1": 251.79, "top": 214.06},
            {"text": "PATNA-CGD", "x0": 299.3, "x1": 333.81, "top": 214.06},
            {"text": "CGD", "x0": 383.3, "x1": 395.48, "top": 214.06},
        ]
    },
    {
        "words": [
            {"text": "The", "x0": 46.8, "x1": 60.13, "top": 63.27},
            {"text": "following", "x0": 63.1, "x1": 94.97, "top": 63.27},
        ]
    },
]

result = extract_records_from_rows(test_rows)
print(json.dumps(result, indent=2))

assert len(result) == 2, f"Expected 2 records, got {len(result)}"
assert result[0]["sn"] == "1"
assert result[0]["name"] == "RAJKUMAR SINGH PORIKA"
assert result[0]["grade"] == "E5"
assert result[0]["current_location"] == "ABU ROAD"
assert result[0]["new_location"] == "VIZAG"
assert result[1]["sn"] == "2"
assert result[1]["name"] == "RAMASHISH KUMAR"
assert result[1]["grade"] == "E3"
assert result[1]["new_function"] == "CGD"
print("ALL ASSERTIONS PASSED")
