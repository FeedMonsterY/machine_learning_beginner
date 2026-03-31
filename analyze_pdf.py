import argparse
import json
import os
import sys
from typing import Any

from pypdf import PdfReader


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def analyze_pdf(file_path: str, password: str | None = None) -> dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到 PDF 文件：{file_path}")

    reader = PdfReader(file_path)
    if reader.is_encrypted:
        if not password:
            raise ValueError("该 PDF 已加密，请使用 --password 提供密码。")
        if not reader.decrypt(password):
            raise ValueError("PDF 密码错误，无法完成分析。")

    page_analyses: list[dict[str, Any]] = []
    combined_text_parts: list[str] = []

    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        normalized_text = _normalize_text(text)
        combined_text_parts.append(normalized_text)
        words = normalized_text.split()
        page_analyses.append(
            {
                "page_number": index,
                "character_count": len(normalized_text),
                "word_count": len(words),
                "preview": _preview_text(normalized_text),
            }
        )

    combined_text = " ".join(part for part in combined_text_parts if part).strip()
    metadata = {
        key.lstrip("/"): value
        for key, value in (reader.metadata or {}).items()
        if value is not None
    }
    text_pages = [page for page in page_analyses if page["character_count"] > 0]

    return {
        "file_name": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "file_size_bytes": os.path.getsize(file_path),
        "page_count": len(page_analyses),
        "is_encrypted": bool(reader.is_encrypted),
        "metadata": metadata,
        "text_statistics": {
            "pages_with_text": len(text_pages),
            "total_characters": len(combined_text),
            "non_whitespace_characters": len(combined_text.replace(" ", "")),
            "total_words": len(combined_text.split()),
            "average_words_per_text_page": round(
                len(combined_text.split()) / len(text_pages), 2
            )
            if text_pages
            else 0.0,
        },
        "document_preview": _preview_text(combined_text, limit=240),
        "pages": page_analyses,
    }


def format_report(analysis: dict[str, Any]) -> str:
    stats = analysis["text_statistics"]
    lines = [
        f"文件：{analysis['file_name']}",
        f"路径：{analysis['file_path']}",
        f"大小：{analysis['file_size_bytes']} 字节",
        f"页数：{analysis['page_count']}",
        f"是否加密：{'是' if analysis['is_encrypted'] else '否'}",
        f"含文字页数：{stats['pages_with_text']}",
        f"总字符数：{stats['total_characters']}",
        f"非空白字符数：{stats['non_whitespace_characters']}",
        f"总词数：{stats['total_words']}",
        f"平均每个含文字页词数：{stats['average_words_per_text_page']}",
    ]

    if analysis["metadata"]:
        lines.append("元数据：")
        for key, value in sorted(analysis["metadata"].items()):
            lines.append(f"  - {key}: {value}")

    if analysis["document_preview"]:
        lines.append(f"全文预览：{analysis['document_preview']}")

    if analysis["pages"]:
        lines.append("逐页概览：")
        for page in analysis["pages"]:
            lines.append(
                "  - 第 {page_number} 页：{character_count} 个字符，{word_count} 个词".format(
                    **page
                )
            )
            if page["preview"]:
                lines.append(f"    预览：{page['preview']}")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="分析 PDF 文件的基础信息和文本统计。")
    parser.add_argument("file", help="要分析的 PDF 文件路径")
    parser.add_argument("--password", help="PDF 密码（仅加密文件需要）")
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出分析结果",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        analysis = analyze_pdf(args.file, password=args.password)
    except Exception as exc:
        print(f"PDF 分析失败：{exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(analysis, ensure_ascii=False, indent=2))
    else:
        print(format_report(analysis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
