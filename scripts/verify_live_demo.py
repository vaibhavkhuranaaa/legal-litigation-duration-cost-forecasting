from __future__ import annotations

import json
import re
import urllib.request
from urllib.parse import urljoin

BASE_URL = "https://vaibhavkhuranaaa.github.io/legal-litigation-duration-cost-forecasting/"
ROW_BASE_URL = (
    "https://legal-litigation-row-data.gp-access-planner.workers.dev/"
    "row-data/fjc-civil-2026-03-31.v1/"
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "project-kit-demo-drive"})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return response.read()


def verify_row_origin() -> None:
    manifest = json.loads(fetch(urljoin(ROW_BASE_URL, "manifest.json")))
    if manifest["total_records"] != 5_008_334:
        raise RuntimeError("live row population total drifted")
    partition = manifest["partitions"][0]
    request = urllib.request.Request(
        urljoin(ROW_BASE_URL, partition["path"]),
        headers={
            "Origin": "https://vaibhavkhuranaaa.github.io",
            "Range": "bytes=0-3",
            "User-Agent": "project-kit-demo-drive",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 206 or response.read() != b"PAR1":
            raise RuntimeError("live row partition range contract failed")
        if (
            response.headers.get("Access-Control-Allow-Origin")
            != "https://vaibhavkhuranaaa.github.io"
        ):
            raise RuntimeError("live row partition CORS contract failed")


def main() -> int:
    html = fetch(BASE_URL).decode("utf-8")
    if "Federal Civil Portfolio Intelligence" not in html:
        raise RuntimeError("live shell title missing")
    script_path = re.search(r'<script[^>]+src="([^"]+\.js)"', html)
    if not script_path:
        raise RuntimeError("live application bundle missing")
    script_url = urljoin(BASE_URL, script_path.group(1))
    bundle = fetch(script_url).decode("utf-8", errors="ignore")
    if ROW_BASE_URL not in bundle:
        raise RuntimeError("production row-data origin missing from live application bundle")
    asset = re.search(r"full-population\.v1-[A-Za-z0-9_-]+\.json", bundle)
    if not asset:
        raise RuntimeError("full-population asset reference missing")
    population = json.loads(fetch(urljoin(script_url, asset.group(0))))
    if population["population"]["statistical_records"] != 5_008_334:
        raise RuntimeError("live population total drifted")
    if population["publication_policy"]["matter_level_rows"] != 0:
        raise RuntimeError("live aggregate boundary failed")
    verify_row_origin()
    print("live demo drive: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
