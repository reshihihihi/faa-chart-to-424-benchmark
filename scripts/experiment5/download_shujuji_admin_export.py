from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "http://43.135.12.254"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "downloads" / "experiment5_admin"


def get_json(url: str, token: str, *, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"x-shujuji-admin-token": token}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, token: str, output_path: Path, *, timeout: int) -> None:
    request = urllib.request.Request(url, headers={"x-shujuji-admin-token": token}, method="GET")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with output_path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)


def latest_formal300_export(exports: list[dict[str, Any]]) -> dict[str, Any]:
    complete = []
    for item in exports:
        formal = ((item.get("summary") or {}).get("formal300") or {})
        if formal.get("final_json_count") == 300 and formal.get("submission_json_count", 0) >= 300:
            complete.append(item)
    candidates = complete or exports
    if not candidates:
        raise RuntimeError("No admin exports returned by /api/admin/exports.")
    return sorted(candidates, key=lambda item: str(item.get("created_at") or ""))[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a shujuji admin annotation export without committing tokens.")
    parser.add_argument("--base-url", default=os.environ.get("SHUJUJI_ADMIN_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token-env", default="SHUJUJI_ADMIN_TOKEN")
    parser.add_argument("--file-name", default="latest")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"Missing admin token. Set ${args.token_env} before running this script.")

    base_url = args.base_url.rstrip("/")
    exports_payload = get_json(f"{base_url}/api/admin/exports", token, timeout=args.timeout)
    exports = exports_payload.get("exports") or []
    selected = latest_formal300_export(exports) if args.file_name == "latest" else {"file_name": args.file_name}
    file_name = selected.get("file_name")
    if not file_name:
        raise RuntimeError("Selected export has no file_name.")

    encoded_file_name = urllib.parse.quote(str(file_name), safe="")
    output_path = args.output_dir / str(file_name)
    download_file(
        f"{base_url}/api/admin/export/download?file={encoded_file_name}",
        token,
        output_path,
        timeout=args.timeout,
    )

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "file_name": file_name,
        "output_path": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "selected_export_meta": selected,
    }
    summary_path = args.output_dir / "latest_download_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
