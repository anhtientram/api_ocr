from app.services.heuristic_extract import heuristic_extract
from app.services.pii import redact_pii
from app.services.postfilter import strip_clinical_advice


def test_heuristic_extracts_amh():
    text = "KẾT QUẢ XÉT NGHIỆM\nAMH: 1.27 ng/mL\nFSH: 6.5 mIU/mL\n"
    params = {p.key: p for p in heuristic_extract(text, "lab")}
    assert "amh" in params
    assert params["amh"].value == 1.27
    assert params["amh"].unit.lower().replace(" ", "") in {"ng/ml"}
    assert params["fsh"].value == 6.5


def test_redact_phone():
    text, found = redact_pii("LH: 5.1 — liên hệ 0912345678 giúp")
    assert found is True
    assert "0912345678" not in text
    assert "091***678" in text


def test_strip_diagnosis_lines():
    text = "AMH thấp.\nChẩn đoán: suy buồng trứng.\nChỉ số FSH 12."
    cleaned = strip_clinical_advice(text)
    assert "Chẩn đoán" not in cleaned
    assert "FSH" in cleaned
