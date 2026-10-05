from unittest.mock import patch

from app.processors.pdf_processor import process_pdf


def test_pdf_extracts_actual_text_before_scoring(tmp_path):
    stream = b"BT /F1 12 Tf 20 20 Td (fixture text) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(content)
    content.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010} 00000 n \n".encode())
    content.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path = tmp_path / "fixture.pdf"
    path.write_bytes(content)
    with patch("app.processors.pdf_processor.process_text", return_value={"type": "text", "scores": {}, "meta": {}}) as score:
        result = process_pdf(str(path))
    score.assert_called_once_with("fixture text")
    assert result["type"] == "pdf"
    assert result["meta"]["page_count"] == 1
