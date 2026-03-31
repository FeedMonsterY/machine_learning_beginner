#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


PYPDF_INSTALL_HINT = "请先安装 pypdf：python -m pip install pypdf==6.9.2"


def read_pdf_text(pdf_path: Path, password: str | None = None) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(PYPDF_INSTALL_HINT) from exc

    if not pdf_path.is_file():
        raise FileNotFoundError(f"未找到 PDF 文件：{pdf_path}")

    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        if not password:
            raise ValueError("PDF 已加密，请使用 --password 提供密码。")
        if reader.decrypt(password) == 0:
            raise ValueError("无法解密 PDF，请确认密码是否正确。")

    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            text = "[该页未提取到文本]"
        pages.append(f"--- 第 {page_number} 页 ---\n{text}")

    return "\n\n".join(pages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="读取 PDF 文件中的文本内容。")
    parser.add_argument("pdf_path", type=Path, help="PDF 文件路径")
    parser.add_argument("--password", help="加密 PDF 的密码")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="将提取出的文本写入指定文件，不提供时直接打印到终端",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        text = read_pdf_text(args.pdf_path, password=args.password)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
