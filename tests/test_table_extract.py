from app.services.table_extract import recover_decimal, _result_number, extract_from_rows
from app.services.bbox import WordBox


def test_recover_triglycerid_decimal():
    v, fixed = recover_decimal("triglycerid", 487.0)
    assert fixed is True
    assert abs(v - 4.87) < 0.001


def test_recover_cholesterol_decimal():
    v, fixed = recover_decimal("cholesterol", 62.0)
    assert fixed is True
    assert abs(v - 6.2) < 0.001


def test_result_number_skips_reference_range():
    line = "Triglycerid 4.87 Tăng 0.46 — 1.88 mmol/L"
    assert _result_number(line) == 4.87


def test_result_number_strips_parenthetical_ranges():
    line = "Số lượng HC nam (3,9 - 5,4x10) 3.87"
    assert _result_number(line) == 3.87


def test_extract_row_boxes_merges_decimal_tokens():
    boxes = [
        WordBox("Triglycerid", 0.9, 0, 10, 100, 80, 14),
        WordBox("4", 0.9, 0, 120, 100, 10, 14),
        WordBox(".", 0.9, 0, 132, 100, 5, 14),
        WordBox("87", 0.9, 0, 140, 100, 20, 14),
        WordBox("Tăng", 0.9, 0, 180, 100, 40, 14),
        WordBox("0.46", 0.9, 0, 240, 100, 30, 14),
        WordBox("-", 0.9, 0, 275, 100, 8, 14),
        WordBox("1.88", 0.9, 0, 290, 100, 30, 14),
    ]
    params = {p.key: p for p in extract_from_rows(boxes, "", "lab")}
    assert "triglycerid" in params
    assert abs(float(params["triglycerid"].value) - 4.87) < 0.001


def test_column_extract_pairs_dual_layout():
    from app.services import column_extract as ce

    labels = [
        "Số lượng HC: nam (4,0 - 5,8)",
        "Hematocrit nam (0,38 - 0,50)",
        "MCH (27 - 32 pg)",
        "Số lượng tiểu cầu (150 - 400)",
    ]
    results = ["3.87", "0.384", "35.1", "198"]
    params = {p.key: p for p in ce._pair_side(labels, results)}
    assert abs(params["rbc"].value - 3.87) < 0.001
    assert abs(params["hct"].value - 0.384) < 0.001
    assert abs(params["mch"].value - 35.1) < 0.001
    assert abs(params["plt"].value - 198) < 0.001


def test_lexicon_scan_known_alphabet():
    from app.services.lexicon_extract import lexicon_extract

    text = "Triglycerid 4.87 Tăng\nCholesterol 6.2\nSố lượng HC: 3.87\nHuyết sắc tố 136"
    params = {p.key: p for p in lexicon_extract(text, [], "lab")}
    assert abs(params["triglycerid"].value - 4.87) < 0.001
    assert abs(params["rbc"].value - 3.87) < 0.001
    assert abs(params["hgb"].value - 136) < 0.001
