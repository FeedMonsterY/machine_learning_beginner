import json
import os
import tempfile
import unittest
from unittest import mock

from pypdf import PdfWriter

import analyze_pdf


class AnalyzePdfTests(unittest.TestCase):
    def test_analyze_blank_pdf_reports_page_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = os.path.join(temp_dir, "blank.pdf")
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            writer.add_blank_page(width=72, height=72)
            with open(pdf_path, "wb") as pdf_file:
                writer.write(pdf_file)

            result = analyze_pdf.analyze_pdf(pdf_path)

        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["text_statistics"]["pages_with_text"], 0)
        self.assertEqual(result["text_statistics"]["total_characters"], 0)
        self.assertEqual(result["file_name"], "blank.pdf")

    def test_analyze_pdf_collects_page_text_statistics(self) -> None:
        page_one = mock.Mock()
        page_one.extract_text.return_value = "Hello world"
        page_two = mock.Mock()
        page_two.extract_text.return_value = "第二页 内容"
        metadata = {"/Author": "Copilot"}

        with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf:
            with mock.patch.object(analyze_pdf, "PdfReader") as mock_reader:
                reader = mock.Mock()
                reader.is_encrypted = False
                reader.metadata = metadata
                reader.pages = [page_one, page_two]
                mock_reader.return_value = reader

                result = analyze_pdf.analyze_pdf(temp_pdf.name)

        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["metadata"], {"Author": "Copilot"})
        self.assertEqual(result["text_statistics"]["pages_with_text"], 2)
        self.assertEqual(result["text_statistics"]["total_words"], 4)
        self.assertIn("Hello world", result["document_preview"])
        self.assertEqual(result["pages"][0]["word_count"], 2)

    def test_encrypted_pdf_requires_password(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_pdf:
            with mock.patch.object(analyze_pdf, "PdfReader") as mock_reader:
                reader = mock.Mock()
                reader.is_encrypted = True
                mock_reader.return_value = reader

                with self.assertRaisesRegex(ValueError, "该 PDF 已加密"):
                    analyze_pdf.analyze_pdf(temp_pdf.name)

    def test_main_supports_json_output(self) -> None:
        fake_analysis = {
            "file_name": "sample.pdf",
            "file_path": "/tmp/sample.pdf",
            "file_size_bytes": 10,
            "page_count": 1,
            "is_encrypted": False,
            "metadata": {},
            "text_statistics": {
                "pages_with_text": 1,
                "total_characters": 5,
                "non_whitespace_characters": 5,
                "total_words": 1,
                "average_words_per_text_page": 1.0,
            },
            "document_preview": "hello",
            "pages": [],
        }

        with mock.patch.object(analyze_pdf, "analyze_pdf", return_value=fake_analysis):
            with mock.patch("sys.stdout.write") as mock_write:
                exit_code = analyze_pdf.main(["/tmp/sample.pdf", "--json"])

        written = "".join(call.args[0] for call in mock_write.call_args_list)
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(written), fake_analysis)


if __name__ == "__main__":
    unittest.main()
