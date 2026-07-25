#!/usr/bin/env python3
"""PrusaSlicer post-processing script: wrap gcode as .gcode.3mf and upload to BamBuddy."""

from __future__ import annotations

import base64
import binascii
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# --- config ---
BAMBUDDY_URL = os.environ.get("BAMBUDDY_URL", "http://localhost:8000")
BAMBUDDY_API_KEY = os.environ.get("BAMBUDDY_API_KEY", "").strip()
ADD_TO_QUEUE = os.environ.get("BAMBUDDY_ADD_TO_QUEUE", "0") == "1"
FOLDER_ID = os.environ.get("BAMBUDDY_FOLDER_ID")  # optional, e.g. "3"
# --------------


def _auth_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build request headers, optionally including BamBuddy API key auth."""
    headers = dict(extra or {})
    if BAMBUDDY_API_KEY:
        headers["X-API-Key"] = BAMBUDDY_API_KEY
    return headers


def derive_upload_name(gcode_path: Path) -> str:
    """Build a clean .gcode.3mf filename for BamBuddy.

    PrusaSlicer passes a temp path in argv[1] (e.g. ``.69975_0.gcode``).
    The intended export name is in ``SLIC3R_PP_OUTPUT_NAME``.
    """
    output_name = os.environ.get("SLIC3R_PP_OUTPUT_NAME", "").strip()
    if output_name:
        base = Path(output_name).name
    else:
        base = gcode_path.name

    stem = base
    while stem.lower().endswith(".gcode"):
        stem = stem[: -len(".gcode")]
    stem = stem.lstrip(".")
    if not stem:
        stem = "print"

    return f"{stem}.gcode.3mf"


def extract_gcode_thumbnail(gcode_path: Path) -> bytes | None:
    """Extract the largest embedded PNG/JPEG thumbnail from PrusaSlicer gcode.

    PrusaSlicer format (Printer Settings → General → Firmware → G-code thumbnails):
      ; thumbnail begin 220x220 12345
      ; <base64 lines>
      ; thumbnail end

    Use PNG (e.g. ``220x220/PNG``) — QOI thumbnails are skipped.
    """
    try:
        with open(gcode_path, errors="ignore") as f:
            content = f.read(50000)

        best = None
        in_thumbnail = False
        thumbnail_lines = []
        current_width = 0

        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("; thumbnail begin"):
                in_thumbnail = True
                thumbnail_lines = []
                match = re.search(r"(\d+)x(\d+)", line)
                current_width = int(match.group(1)) if match else 0
                continue

            if line.startswith("; thumbnail end"):
                if in_thumbnail and thumbnail_lines:
                    try:
                        decoded = base64.b64decode("".join(thumbnail_lines))
                        is_png = decoded.startswith(b"\x89PNG\r\n\x1a\n")
                        is_jpeg = decoded.startswith(b"\xff\xd8\xff")
                        if is_png or is_jpeg:
                            if best is None or current_width > best[0]:
                                best = (current_width, decoded)
                    except (binascii.Error, ValueError):
                        pass
                in_thumbnail = False
                thumbnail_lines = []
                continue

            if in_thumbnail and line.startswith(";"):
                data_line = line[1:].strip()
                if data_line:
                    thumbnail_lines.append(data_line)

        return best[1] if best else None
    except Exception:
        # Missing, QOI-only, or malformed thumbnails — upload without preview.
        return None


def wrap_gcode_3mf(gcode_path: Path) -> tuple[bytes, str, bool]:
    """Package plain gcode into a minimal Bambu-compatible .gcode.3mf zip."""
    gcode_bytes = gcode_path.read_bytes()
    upload_name = derive_upload_name(gcode_path)

    thumbnail = None
    try:
        thumbnail = extract_gcode_thumbnail(gcode_path)
    except Exception:
        thumbnail = None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Metadata/plate_1.gcode", gcode_bytes)
        zf.writestr(
            "Metadata/slice_info.config",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<config><plate><metadata key="index" value="1"/></plate></config>',
        )
        if thumbnail:
            try:
                # BamBuddy ThreeMFParser checks Metadata/plate_1.png first.
                zf.writestr("Metadata/plate_1.png", thumbnail)
            except Exception:
                pass  # zip without thumbnail is still valid for BamBuddy

    return buf.getvalue(), upload_name, bool(thumbnail)


def upload_file(content: bytes, filename: str) -> dict:
    boundary = "----BamBuddyUploadBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

    url = f"{BAMBUDDY_URL.rstrip('/')}/api/v1/library/files"
    if FOLDER_ID:
        url += f"?folder_id={FOLDER_ID}"

    req = urllib.request.Request(
        url,
        data=body,
        headers=_auth_headers(
            {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        ),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def add_to_queue(file_id: int) -> dict:
    url = f"{BAMBUDDY_URL.rstrip('/')}/api/v1/library/files/add-to-queue"
    req = urllib.request.Request(
        url,
        data=json.dumps({"file_ids": [file_id]}).encode(),
        headers=_auth_headers({"Content-Type": "application/json"}),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: prusaslicer-to-bambuddy.py <path-to-exported.gcode>", file=sys.stderr)
        return 1

    gcode_path = Path(sys.argv[1])
    if not gcode_path.is_file():
        print(f"File not found: {gcode_path}", file=sys.stderr)
        return 1

    try:
        content, upload_name, has_thumbnail = wrap_gcode_3mf(gcode_path)
        result = upload_file(content, upload_name)
        msg = f"Uploaded to BamBuddy: {result['filename']} (id={result['id']})"
        if has_thumbnail:
            msg += ", with thumbnail"
        print(msg)

        if ADD_TO_QUEUE:
            queue_result = add_to_queue(result["id"])
            added = queue_result.get("added", [])
            errors = queue_result.get("errors", [])
            if added:
                print(f"Added to print queue: item {added[0]['queue_item_id']}")
            if errors:
                print(f"Queue error: {errors[0]['error']}", file=sys.stderr)
                return 1

        return 0
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"BamBuddy HTTP {e.code}: {detail}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
