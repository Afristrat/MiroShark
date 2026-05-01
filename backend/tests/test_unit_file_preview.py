"""Tests for POST /api/simulation/file-preview."""
import io
import pytest
from unittest.mock import patch, MagicMock
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _make_upload(filename, content, content_type="application/octet-stream"):
    return (io.BytesIO(content), filename)


class TestFilePreviewMissingFile:
    def test_missing_file_field(self, client):
        res = client.post("/api/simulation/file-preview", data={})
        assert res.status_code == 400
        assert res.get_json()["error_code"] == "MISSING_FILE"

    def test_empty_filename(self, client):
        data = {"file": (io.BytesIO(b"hello"), "")}
        res = client.post(
            "/api/simulation/file-preview",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 400
        assert res.get_json()["error_code"] == "MISSING_FILENAME"

    def test_unsupported_extension(self, client):
        data = {"file": (io.BytesIO(b"data"), "file.docx")}
        res = client.post(
            "/api/simulation/file-preview",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 400
        assert res.get_json()["error_code"] == "UNSUPPORTED_FORMAT"


class TestFilePreviewTxt:
    def test_txt_extraction(self, client):
        content = b"Hello world. This is a test document.\n" * 20
        data = {"file": (io.BytesIO(content), "test.txt")}
        res = client.post(
            "/api/simulation/file-preview",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "Hello world" in body["data"]["text"]
        assert body["data"]["filename"] == "test.txt"
        assert body["data"]["char_count"] > 0

    def test_md_extraction(self, client):
        content = b"# Title\n\nSome **markdown** content.\n"
        data = {"file": (io.BytesIO(content), "doc.md")}
        res = client.post(
            "/api/simulation/file-preview",
            data=data,
            content_type="multipart/form-data",
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "Title" in body["data"]["text"]


class TestFilePreviewPdf:
    def test_pdf_extraction_success(self, client):
        """Mock FileParser to avoid needing a real PDF in tests."""
        with patch(
            "app.api.simulation.FileParser.extract_text",
            return_value="Extracted PDF content. Key actors: Alice, Bob.",
        ):
            data = {"file": (io.BytesIO(b"%PDF-1.4 fake"), "report.pdf")}
            res = client.post(
                "/api/simulation/file-preview",
                data=data,
                content_type="multipart/form-data",
            )
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "Extracted PDF content" in body["data"]["text"]
        assert body["data"]["filename"] == "report.pdf"

    def test_pdf_extraction_failure_returns_422(self, client):
        with patch(
            "app.api.simulation.FileParser.extract_text",
            side_effect=Exception("corrupt PDF"),
        ):
            data = {"file": (io.BytesIO(b"garbage"), "bad.pdf")}
            res = client.post(
                "/api/simulation/file-preview",
                data=data,
                content_type="multipart/form-data",
            )
        assert res.status_code == 422
        assert res.get_json()["error_code"] == "EXTRACTION_FAILED"

    def test_pdf_text_truncated_to_4000_chars(self, client):
        long_text = "A" * 10000
        with patch(
            "app.api.simulation.FileParser.extract_text",
            return_value=long_text,
        ):
            data = {"file": (io.BytesIO(b"%PDF fake"), "big.pdf")}
            res = client.post(
                "/api/simulation/file-preview",
                data=data,
                content_type="multipart/form-data",
            )
        body = res.get_json()
        assert body["data"]["char_count"] == 4000
        assert len(body["data"]["text"]) == 4000
