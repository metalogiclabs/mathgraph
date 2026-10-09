"""Immutable, source-URL-keyed PDF reuse for the authorized WattBot corpus.

The only cache key is the exact pinned URL (including its arXiv version).
Cached bytes are rehashed and parsed before use. An altered source or an
invalid cached PDF is a failure, never a silent substitute. The caller still
compares the complete corpus SHA-256 manifest to prior qualification.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import tempfile

import fitz
from pdf_probe import download_one, pinned_pdf_url


def cached_download(url: str, destination: Path, cache_root: Path | None):
    pinned_pdf_url(url)
    if cache_root is None:
        digest, info = download_one(url, destination)
        return digest, info, False
    cache_root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    cached_file = cache_root / (key + ".pdf")
    digest_file = cache_root / (key + ".sha256")
    if cached_file.exists() or digest_file.exists():
        if not (cached_file.is_file() and digest_file.is_file()):
            raise ValueError("Incomplete cached source pair")
        if cached_file.stat().st_size > 18 * 1024 * 1024:
            raise ValueError("Cached PDF exceeds finite source size limit")
        observed = hashlib.sha256(cached_file.read_bytes()).hexdigest()
        if observed != digest_file.read_text(encoding="ascii").strip():
            raise ValueError("Cached PDF digest mismatch")
        if not cached_file.read_bytes().startswith(b"%PDF"):
            raise ValueError("Cached source is not a PDF")
        with fitz.open(str(cached_file)) as pdf:
            pages = len(pdf)
            text_chars = sum(len(page.get_text()) for page in pdf)
        if pages < 1 or text_chars < 1:
            raise ValueError("Cached PDF has no usable text")
        shutil.copyfile(cached_file, destination)
        return observed, f"pages={pages};text_chars={text_chars}", True
    with tempfile.TemporaryDirectory(prefix="wattbot_pdf_new_") as td:
        stage = Path(td) / "source.pdf"
        digest, info = download_one(url, stage)
        shutil.copyfile(stage, destination)
        temporary = cache_root / (key + ".tmp")
        shutil.copyfile(stage, temporary)
        temporary.replace(cached_file)
        digest_file.write_text(digest + "\n", encoding="ascii")
    return digest, info, False


def self_test(tmp: Path):
    url = "https://arxiv.org/abs/2601.01234v2"
    assert pinned_pdf_url(url) == "https://arxiv.org/pdf/2601.01234v2"
    key = hashlib.sha256(url.encode()).hexdigest()
    root = tmp / "cache"
    root.mkdir()
    pdf_path = root / (key + ".pdf")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Training power was 45 MW.")
    document.save(pdf_path)
    document.close()
    pdf_digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    (root / (key + ".sha256")).write_text(pdf_digest+"\n")
    destination = tmp / "out.pdf"
    observed, _, cache_hit = cached_download(url, destination, root)
    assert observed == pdf_digest and cache_hit
    assert destination.read_bytes() == pdf_path.read_bytes()
    (root / (key + ".sha256")).write_text("0" * 64)
    try:
        cached_download(url, destination, root)
    except ValueError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("Poisoned cache accepted")
