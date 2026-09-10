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


def test_result_number_skips_digit_inside_ocr_word():
    # "đói" OCR'd as "d6i" must not yield 6 before real result 5.1
    line = "Glucose mauluc d6i 5.1 3.9 -6.4 mmol/L Binh thuong"
    assert _result_number(line) == 5.1


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


def test_parse_thousands_separator():
    from app.services.table_extract import parse_number_token, _result_number

    assert parse_number_token("1,320.0") == 1320.0
    assert parse_number_token("6.52") == 6.52
    assert parse_number_token("6,52") == 6.52
    line = "NT-proBNP (Dau an suy tim) 1,320.0 <300.0 pg/mL"
    assert _result_number(line) == 1320.0


def test_lexicon_cardiac_panel_tim_mach():
    from app.services.lexicon_extract import lexicon_extract

    text = """
HO SO KHAM TIM MACH
Huyet ap / Mach:
145/90 mmHg
NT-proBNP (Dau an suy tim) 1,320.0 <300.0 pg/mL Tang ro
Troponin T sieu nhay (hs-cTnT) 11.8 <14.0 ng/L
CK-MB (Men co tim) 16.4 <25.0 U/L
Cholesterol toan phan 6.52 3.90 - 5.20 mmol/L
LDL-Cholesterol (Lipid xovura) 4.24 < 2.60 mmol/L
Triglyceride 2.75 0.40 - 1.88 mmol/L
HDL-Cholesterol (Lipid bao ve) 0.92 >1.00 mmol/L
Dien giai do (K+ / Na+) 4.35/139 3.5-5.0/135-145 mmol/L
EF(SimpsonBiplane):46%
Duong kinh that trai tam truong (LVDd) 55mm 35-52mm
Duong kinh that trai tam thu (LVDs) 39 mm 25-36mm
Do day vach lien that (IVSd) 12.5 mm 6-10 mm
Kich thuoc nhi trai (LA) 41 mm 28-40 mm
Ap luc DM phoi (PAPs):34mmHg
"""
    params = {p.key: p for p in lexicon_extract(text, [], "lab")}
    assert abs(params["nt_probnp"].value - 1320.0) < 0.1
    assert abs(params["troponin_t"].value - 11.8) < 0.1
    assert abs(params["ck_mb"].value - 16.4) < 0.1
    assert abs(params["cholesterol"].value - 6.52) < 0.01
    assert abs(params["ldl"].value - 4.24) < 0.01
    assert abs(params["hdl"].value - 0.92) < 0.01
    assert abs(params["triglycerid"].value - 2.75) < 0.01
    assert abs(params["potassium"].value - 4.35) < 0.01
    assert abs(params["sodium"].value - 139) < 0.1
    assert abs(params["bp_systolic"].value - 145) < 0.1
    assert abs(params["bp_diastolic"].value - 90) < 0.1
    assert abs(params["ef_pct"].value - 46) < 0.1
    assert abs(params["lvdd_mm"].value - 55) < 0.1
    assert abs(params["lvds_mm"].value - 39) < 0.1
    assert abs(params["ivsd_mm"].value - 12.5) < 0.1
    assert abs(params["la_mm"].value - 41) < 0.1
    assert abs(params["paps_mmhg"].value - 34) < 0.1


def test_lexicon_scan_known_alphabet():
    from app.services.lexicon_extract import lexicon_extract

    text = "Triglycerid 4.87 Tăng\nCholesterol 6.2\nSố lượng HC: 3.87\nHuyết sắc tố 136"
    params = {p.key: p for p in lexicon_extract(text, [], "lab")}
    assert abs(params["triglycerid"].value - 4.87) < 0.001
    assert abs(params["rbc"].value - 3.87) < 0.001
    assert abs(params["hgb"].value - 136) < 0.001


def test_lexicon_total_t_not_confused_with_alt():
    from app.services.lexicon_extract import lexicon_extract

    text = (
        "Testosterone toan phan (Total T) 18.60 9.90 - 27.80 nmol/L Binh thuong\n"
        "Testosterone ty do (Free T) 425.5 170.0-700.0 pmol/L Binh thuong\n"
        "LH (Luteinizing Hormone) 4.20 1.70 -8.60 mlU/mL Binh thuong\n"
        "FSH (Follicle Stimulating Hormone) 3.85 1.50 - 12.40 mlU/mL Binh thuong\n"
        "Prolactin 168.0 86.0-324.0 mIU/L Binh thuong\n"
        "Estradiol (E2) 88.5 28.0 - 156.0 pmol/L Binh thuong\n"
        "Glucose mauluc d6i 5.1 3.9 -6.4 mmol/L Binh thuong\n"
    )
    params = {p.key: p for p in lexicon_extract(text, [], "lab")}
    assert "alt" not in params
    assert "amh" not in params
    assert "mch" not in params
    assert abs(params["total_t"].value - 18.6) < 0.01
    assert abs(params["free_t"].value - 425.5) < 0.1
    assert abs(params["prolactin"].value - 168.0) < 0.1
    assert abs(params["lh"].value - 4.2) < 0.01
    assert abs(params["fsh"].value - 3.85) < 0.01
    assert abs(params["e2"].value - 88.5) < 0.1
    assert abs(params["glucose"].value - 5.1) < 0.01
