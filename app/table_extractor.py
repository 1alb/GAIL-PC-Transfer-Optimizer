from typing import Any, Dict, List

TOP_TOLERANCE = 3.0


def cluster_words_into_rows(words: List[Dict[str, Any]], tolerance: float = TOP_TOLERANCE) -> List[List[Dict[str, Any]]]:
    rows: List[List[Dict[str, Any]]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if not rows or abs(word["top"] - rows[-1][0]["top"]) > tolerance:
            rows.append([word])
        else:
            rows[-1].append(word)
    return rows


def _is_data_row(words: List[Dict[str, Any]]) -> bool:
    if len(words) < 5:
        return False
    sorted_words = sorted(words, key=lambda word: float(word.get("x0", 0)))
    first_text = str(sorted_words[0].get("text", "")).strip()
    return first_text.isdigit() and 1 <= len(first_text) <= 3
