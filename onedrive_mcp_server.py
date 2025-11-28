import json
import os
from pathlib import Path
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP

# 기본 경로: C:\Users\tony960816\OneDrive - 특허법인무한 (환경변수 ONEDRIVE_ROOT로 재정의 가능)
ONE_DRIVE_ROOT = Path(
    os.environ.get("ONEDRIVE_ROOT", r"C:\Users\tony960816\OneDrive - 특허법인무한")
).resolve()

MAX_LIST = int(os.environ.get("ONEDRIVE_MAX_LIST", "200"))        # 한 번에 나열할 최대 파일 수
MAX_BYTES = int(os.environ.get("ONEDRIVE_MAX_BYTES", str(256_000)))  # 읽기 한도 (바이트)

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))  # Render는 PORT 환경변수를 사용

server = FastMCP(
    "onedrive-local",
    host=HOST,
    port=PORT,
    instructions="Expose local OneDrive files via MCP (OneDrive sync folder only).",
)


def _ensure_within_root(path: Path) -> Path:
    path = path.resolve()
    if not str(path).startswith(str(ONE_DRIVE_ROOT)):
        raise ValueError("Requested path is outside the OneDrive root")
    return path


@server.resource(
    "resource://onedrive/index",
    name="OneDrive index",
    description="List of OneDrive files (truncated by MAX_LIST)",
    mime_type="application/json",
)
def list_resources():
    items: list[dict] = []
    for entry in ONE_DRIVE_ROOT.rglob("*"):
        if not entry.is_file():
            continue
        rel = entry.relative_to(ONE_DRIVE_ROOT)
        size = entry.stat().st_size
        items.append({"path": str(rel), "bytes": size})
        if len(items) >= MAX_LIST:
            break
    return json.dumps({"root": str(ONE_DRIVE_ROOT), "items": items}, ensure_ascii=False)


@server.resource(
    "resource://onedrive/{rel_path}",
    name="OneDrive file",
    description="Read a OneDrive file by relative path",
)
def read_resource(rel_path: str):
    rel_path = Path(unquote(rel_path))
    path = _ensure_within_root(ONE_DRIVE_ROOT / rel_path)

    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        data = data[:MAX_BYTES]

    try:
        text = data.decode("utf-8")
        return text
    except UnicodeDecodeError:
        return data


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "sse")  # sse | streamable-http | stdio
    print(f"Serving OneDrive from: {ONE_DRIVE_ROOT}")
    print(f"Transport: {transport} host={HOST} port={PORT}")
    server.run(transport=transport)
