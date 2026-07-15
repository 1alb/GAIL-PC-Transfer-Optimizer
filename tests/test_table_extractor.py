import unittest

from app.table_extractor import extract_records_from_rows


class TestTableExtractor(unittest.TestCase):
    def test_extract_records_from_rows_keeps_numeric_first_word_rows(self):
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

        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0],
            {
                "sn": "1",
                "emp_no": "15086",
                "name": "RAJKUMAR SINGH PORIKA",
                "grade": "E5",
                "current_location": "ABU ROAD",
                "new_location": "VIZAG",
                "new_function": "",
                "remarks": "",
            },
        )
        self.assertEqual(
            result[1],
            {
                "sn": "2",
                "emp_no": "17426",
                "name": "RAMASHISH KUMAR",
                "grade": "E3",
                "current_location": "ABU ROAD",
                "new_location": "PATNA-CGD",
                "new_function": "CGD",
                "remarks": "",
            },
        )


if __name__ == "__main__":
    unittest.main()
