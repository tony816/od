import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    TextResourceContents,
    BlobResourceContents,
)

# 기본 경로: C:\Users\tony960816\OneDrive - 특허법인무한 (환경변수 ONEDRIVE_ROOT로 재정의 가능)
ONE_DRIVE_ROOT = Path(
    os.environ.get("ONEDRIVE_ROOT", r"C:\Users\tony960816\OneDrive - 특허법인무한")
).resolve()

MAX_LIST = int(os.environ.get("ONEDRIVE_MAX_LIST", "200"))        # 한 번에 나열할 최대 파일 수
MAX_BYTES = int(os.environ.get("ONEDRIVE_MAX_BYTES", str(256_000)))  # 읽기 한도 (바이트)

server = Server("onedrive-local")


def _ensure_within_root(path: Path) -> Path:
    path = path.resolve()
    if not str(path).startswith(str(ONE_DRIVE_ROOT)):
        raise ValueError("Requested path is outside the OneDrive root")
    return path


@server.list_resources()
async def list_resources() -> list[Resource]:
    resources: list[Resource] = []
    for entry in ONE_DRIVE_ROOT.rglob("*"):
        if not entry.is_file():
            continue
        rel = entry.relative_to(ONE_DRIVE_ROOT)
        uri = entry.resolve().as_uri()  # file:///C:/...
        size = entry.stat().st_size
        resources.append(
            Resource(
                uri=uri,
                name=str(rel),
                description=f"OneDrive file ({size} bytes)",
                mimeType="application/octet-stream",
            )
        )
        if len(resources) >= MAX_LIST:
            break
    return resources


@server.read_resource()
async def read_resource(uri: str):
    parsed = urlparse(uri)
    if parsed.scheme not in ("file", ""):
        raise ValueError("Only file:// URIs are supported")

    # 윈도우 file://C:/... 형태 처리
    if parsed.scheme == "file":
        if parsed.netloc:
            # file://C:/path or file:///C:/path
            path = Path(f"{parsed.netloc}{parsed.path}")
        else:
            path = Path(parsed.path)
    else:
        path = Path(uri)

    path = _ensure_within_root(Path(unquote(path.as_posix())))

    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        data = data[:MAX_BYTES]

    try:
        text = data.decode("utf-8")
        return [TextResourceContents(text=text, mimeType="text/plain")]
    except UnicodeDecodeError:
        return [BlobResourceContents(data=data, mimeType="application/octet-stream")]


if __name__ == "__main__":
    import anyio

    async def main():
        print(f"Serving OneDrive from: {ONE_DRIVE_ROOT}")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    anyio.run(main)
