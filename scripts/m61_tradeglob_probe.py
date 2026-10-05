from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from tradeglob import TradeGlobFetcher

COHORT = ["COMI", "EGAL", "SWDY", "ETEL", "EAST", "TMGH", "PHDC", "FWRY", "EFID", "HRHO"]
START = date(2021, 1, 1)
END = date(2025, 12, 31)
OUT = Path("artifacts/m61_tradeglob_probe")
OUT.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    fetcher = TradeGlobFetcher()
    summary = {
        "provider": "TradeGlob/TradingView",
        "authenticated": bool(fetcher.authenticated),
        "exchange": "EGX",
        "interval": "Daily",
        "start": START.isoformat(),
        "end": END.isoformat(),
        "symbols": {},
    }

    for symbol in COHORT:
        item = {"status": "FAILED"}
        try:
            df = fetcher.get_ohlcv(
                symbol=symbol,
                exchange="EGX",
                interval="Daily",
                n_bars=5000,
                use_cache=False,
                validate=True,
            )
            raw_path = OUT / f"{symbol}.csv"
            df.to_csv(raw_path)
            item.update(
                {
                    "status": "OK",
                    "rows": int(len(df)),
                    "first": str(df.index.min()),
                    "last": str(df.index.max()),
                    "columns": [str(c) for c in df.columns],
                    "sha256": sha256(raw_path),
                }
            )
        except Exception as exc:
            item["error_type"] = type(exc).__name__
            item["error"] = str(exc)
        summary["symbols"][symbol] = item

    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
