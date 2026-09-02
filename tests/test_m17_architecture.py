from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from litigation_planner.publication_contract import PublicationContractError
from scripts.build_representative_partition import _select_sql, _sql_string, build_partition
from scripts.serve_range_origin import RangeOriginServer


def test_representative_select_is_bounded_to_one_year_and_escapes_version() -> None:
    sql = _select_sql("dataset'v1", 2019)
    assert "extract(year from records.filed_date) = 2019" in sql
    assert "dataset''v1" in sql
    assert _sql_string("safe") == "'safe'"
    assert "records.office_code" not in sql
    assert "records.docket_number" not in sql


def test_representative_build_refuses_output_inside_public_repository(tmp_path: Path) -> None:
    with pytest.raises(PublicationContractError, match="outside tracked Git"):
        build_partition(
            warehouse=tmp_path / "missing.duckdb",
            output=Path("data/filing-year-2019.parquet"),
            secret_path=tmp_path / "missing.key",
            contract_path=Path("config/public-row-mart-v1.toml"),
        )


def test_range_origin_serves_single_ranges_with_cache_and_exact_cors(tmp_path: Path) -> None:
    payload = b"PAR1-private-representative-fixture"
    (tmp_path / "fixture.parquet").write_bytes(payload)
    log_path = tmp_path / "requests.ndjson"
    allowed_origin = "http://127.0.0.1:4175"
    server = RangeOriginServer(("127.0.0.1", 0), tmp_path, log_path, frozenset({allowed_origin}))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/fixture.parquet"
        request = Request(url, headers={"Origin": allowed_origin, "Range": "bytes=5-11"})
        with urlopen(request) as response:
            assert response.status == 206
            assert response.read() == payload[5:12]
            assert response.headers["Content-Range"] == f"bytes 5-11/{len(payload)}"
            assert response.headers["Accept-Ranges"] == "bytes"
            assert response.headers["Access-Control-Allow-Origin"] == allowed_origin
            assert response.headers["Access-Control-Allow-Headers"] == "Range"
            assert response.headers["Vary"] == "Origin"
            assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
            assert response.headers["Content-Type"] == "application/vnd.apache.parquet"

        bad_request = Request(url, headers={"Origin": allowed_origin, "Range": "bytes=999-1000"})
        with pytest.raises(HTTPError) as error:
            urlopen(bad_request)
        assert error.value.code == 416

        attacker_request = Request(
            url,
            method="HEAD",
            headers={"Origin": "https://attacker.example", "Range": "bytes=0-"},
        )
        with pytest.raises(HTTPError) as attacker_error:
            urlopen(attacker_request)
        assert attacker_error.value.code == 403
        assert attacker_error.value.headers.get("Access-Control-Allow-Origin") is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["status"] == 206
    assert entries[0]["bytes_sent"] == 7
    assert entries[1]["status"] == 416
