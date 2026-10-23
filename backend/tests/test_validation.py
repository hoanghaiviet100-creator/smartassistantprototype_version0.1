from app.core.validation import check_type_consistency, detect_type, sanitize_filename, supported_features
from app.schemas import Feature


def test_detect_by_magic_not_extension():
    assert detect_type(b"%PDF-1.4 ...") == "pdf"
    assert detect_type(b"\x89PNG\r\n\x1a\n....") == "png"
    assert detect_type(b"\xff\xd8\xff\xe0....") == "jpeg"
    assert detect_type(b"MZ\x90\x00") == "exe"
    assert detect_type("xin chào, đây là text".encode()) == "text"
    assert detect_type(b"\x00\x01\x02\xfe\xff") == "unknown"


def test_text_detection_tolerates_cut_multibyte_char():
    data = ("đ" * 3000).encode()[:4095]  # cắt giữa ký tự 2 byte
    assert detect_type(data) == "text"


def test_sanitize_filename_strips_paths_and_control_chars():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\a\\cv.pdf") == "cv.pdf"
    assert sanitize_filename("a\x00b\nc.pdf") == "abc.pdf"
    assert sanitize_filename("...") == "upload"
    assert sanitize_filename(None) == "upload"
    assert len(sanitize_filename("a" * 500 + ".pdf")) <= 120


def test_consistency_flags():
    assert check_type_consistency("cv.pdf", "application/pdf", "pdf") == []
    assert check_type_consistency("cv.pdf", "application/pdf", "png") == ["extension_mismatch", "mime_mismatch"]
    assert check_type_consistency("a.docx", None, "zip") == []  # OOXML là zip
    assert check_type_consistency("x.bin", "application/octet-stream", "unknown") == []
    assert "double_extension" in check_type_consistency("invoice.pdf.exe", None, "exe")


def test_supported_features_policy():
    assert supported_features("pdf", []) == [Feature.SENSITIVE, Feature.FILE_SCAN]
    assert supported_features("png", []) == [Feature.SCAM, Feature.SENSITIVE, Feature.FILE_SCAN]
    assert supported_features("zip", []) == [Feature.FILE_SCAN]
    assert supported_features("pdf", ["extension_mismatch"]) == [Feature.FILE_SCAN]  # mismatch => chỉ F3
