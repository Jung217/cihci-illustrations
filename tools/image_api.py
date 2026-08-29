#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兩支生圖腳本共用的 OpenAI 影像 API 薄層。

只負責四件事：組 multipart、送出請求、把回傳的 base64 存成檔案，
以及幾個 CLI 都要用的小工具。提示詞與 shot list 是各腳本自己的事，不放這裡。
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
REF_IMAGE = REPO / "assets" / "ip" / "cihci.png"

ENDPOINT = "https://api.openai.com/v1/images/edits"
DEFAULT_MODEL = "gpt-image-2"
QUALITY_CHOICES = ("low", "medium", "high")
API_KEY_ENV = "OPENAI_API_KEY"
IMAGES_PER_REQUEST = "1"

REQUEST_TIMEOUT_SECONDS = 600
ERROR_SNIPPET_CHARS = 400
BYTES_PER_KIB = 1024

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_BAD_USAGE = 2


class MissingApiKey(RuntimeError):
    """未設定 API 金鑰的環境變數。"""


@dataclass(frozen=True)
class GeneratedImage:
    """一次成功請求的產物。"""

    data: bytes
    usage: dict[str, Any]

    @property
    def size_in_kib(self) -> int:
        return len(self.data) // BYTES_PER_KIB

    @property
    def total_tokens(self) -> Any:
        return self.usage.get("total_tokens")


def enable_utf8_output() -> None:
    """把 stdout/stderr 轉成 UTF-8，否則 Windows 主控台的中文會變亂碼。

    必須早於 argparse：`--help` 和參數錯誤都在 parse_args() 內部就印完並結束，
    晚一步設定就來不及了。
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def require_api_key() -> str:
    """讀取 API 金鑰，沒有就拋 MissingApiKey。"""
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise MissingApiKey(f"缺少 {API_KEY_ENV} 環境變數。")
    return api_key


def encode_multipart(
    fields: dict[str, str], files: list[tuple[str, Path]]
) -> tuple[bytes, str]:
    """把表單欄位與檔案編成 multipart/form-data，回傳 (body, boundary)。"""
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode()
    for name, path in files:
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        body += path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), boundary


def request_image(
    *,
    prompt: str,
    size: str,
    quality: str,
    model: str,
    reference_image: Path,
    api_key: str,
) -> GeneratedImage:
    """呼叫 images/edits 產生一張圖。HTTP 與連線錯誤原樣往外拋。"""
    fields = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": IMAGES_PER_REQUEST,
    }
    body, boundary = encode_multipart(fields, [("image[]", reference_image)])
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    return GeneratedImage(
        data=base64.b64decode(payload["data"][0]["b64_json"]),
        usage=payload.get("usage", {}),
    )


def http_error_detail(exc: urllib.error.HTTPError) -> str:
    """把 HTTP 錯誤壓成一行，只留開頭一段回應內容。"""
    return f"HTTP {exc.code}: {exc.read().decode()[:ERROR_SNIPPET_CHARS]}"


def save_image(image: GeneratedImage, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image.data)


def display_path(path: Path) -> Path:
    """倉庫內的路徑印相對路徑；--out 指到倉庫外時原樣印出。"""
    try:
        return path.relative_to(REPO)
    except ValueError:
        return path
