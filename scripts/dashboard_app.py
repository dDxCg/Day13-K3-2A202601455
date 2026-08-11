"""Runtime dashboard for Day 13 observability lab.

Renders the 6 panels required by config/dashboard.yaml, reading from
data/logs.jsonl. Run with: streamlit run scripts/dashboard_app.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASHBOARD_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"

st.set_page_config(page_title="Day 13 AI Observability", layout="wide")


@st.cache_data(ttl=15)
def load_config() -> dict:
    return yaml.safe_load(DASHBOARD_CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]


@st.cache_data(ttl=15)
def load_logs(_mtime: float) -> pd.DataFrame:
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    df = pd.DataFrame(records)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def panel_by_id(config: dict, panel_id: str) -> dict:
    return next(p for p in config["panels"] if p["id"] == panel_id)


def threshold_line(panel: dict) -> str:
    t = panel["threshold"]
    op = "<=" if t["operator"] == "lte" else ">="
    return f"SLO: {t['aggregation']} {op} {t['value']} {panel['unit']}"


def main() -> None:
    config = load_config()
    mtime = LOG_PATH.stat().st_mtime if LOG_PATH.exists() else 0.0
    df = load_logs(mtime)

    now = pd.Timestamp.utcnow()
    window_start = now - pd.Timedelta(minutes=config["time_range_minutes"])

    st.title(config["title"])
    st.caption(
        f"Time range: last {config['time_range_minutes']} min "
        f"| refresh: {config['refresh_seconds']}s "
        f"| now: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    if df.empty:
        st.warning("data/logs.jsonl is empty. Run the API and load_test.py first.")
        return

    windowed = df[df["ts"] >= window_start]
    responses = windowed[windowed["event"] == "response_sent"].copy()
    requests_recv = windowed[windowed["event"] == "request_received"].copy()
    failed = windowed[windowed["event"] == "request_failed"].copy()

    row1 = st.columns(3)
    row2 = st.columns(3)

    # 1. Latency P50/P95/P99
    with row1[0]:
        panel = panel_by_id(config, "latency")
        st.subheader(panel["title"])
        if not responses.empty:
            p50, p95, p99 = responses["latency_ms"].quantile([0.5, 0.95, 0.99])
            st.metric("P50 (ms)", f"{p50:.0f}")
            st.metric("P95 (ms)", f"{p95:.0f}")
            st.metric("P99 (ms)", f"{p99:.0f}")
            st.caption(threshold_line(panel))
            if p95 > panel["threshold"]["value"]:
                st.error(f"P95 {p95:.0f}ms breaches SLO")
        else:
            st.info("No response_sent events in window")

    # 2. Traffic
    with row1[1]:
        panel = panel_by_id(config, "traffic")
        st.subheader(panel["title"])
        st.metric("Total requests", len(requests_recv))
        if not requests_recv.empty:
            per_min = requests_recv.set_index("ts").resample("1min").size()
            st.bar_chart(per_min, x_label="minute", y_label="requests/min")
        st.caption(threshold_line(panel))

    # 3. Errors
    with row1[2]:
        panel = panel_by_id(config, "errors")
        st.subheader(panel["title"])
        total_req = len(requests_recv)
        total_fail = len(failed)
        error_rate = (total_fail / total_req * 100) if total_req else 0.0
        st.metric("Error rate (%)", f"{error_rate:.2f}")
        if not failed.empty and "error_type" in failed:
            st.bar_chart(failed["error_type"].value_counts())
        else:
            st.caption("No errors in window")
        st.caption(threshold_line(panel))
        if error_rate > panel["threshold"]["value"]:
            st.error(f"Error rate {error_rate:.2f}% breaches SLO")

    # 4. Cost
    with row2[0]:
        panel = panel_by_id(config, "cost")
        st.subheader(panel["title"])
        total_cost = responses["cost_usd"].sum() if not responses.empty else 0.0
        st.metric("Total cost (USD)", f"{total_cost:.4f}")
        if not responses.empty:
            per_min_cost = responses.set_index("ts")["cost_usd"].resample("1min").sum()
            st.line_chart(per_min_cost, x_label="minute", y_label="USD")
        st.caption(threshold_line(panel))
        if total_cost > panel["threshold"]["value"]:
            st.error(f"Cost {total_cost:.4f} USD breaches SLO")

    # 5. Tokens
    with row2[1]:
        panel = panel_by_id(config, "tokens")
        st.subheader(panel["title"])
        tokens_in = int(responses["tokens_in"].sum()) if not responses.empty else 0
        tokens_out = int(responses["tokens_out"].sum()) if not responses.empty else 0
        st.metric("Tokens in", tokens_in)
        st.metric("Tokens out", tokens_out)
        st.caption(threshold_line(panel))

    # 6. Quality
    with row2[2]:
        panel = panel_by_id(config, "quality")
        st.subheader(panel["title"])
        mean_q = responses["quality_score"].mean() if not responses.empty else 0.0
        st.metric("Mean quality score", f"{mean_q:.3f}")
        st.caption(threshold_line(panel))
        if mean_q < panel["threshold"]["value"]:
            st.error(f"Quality {mean_q:.3f} breaches SLO")

    st.divider()
    st.caption(f"Source: {LOG_PATH.relative_to(REPO_ROOT)} | records in window: {len(windowed)}")

    time.sleep(config["refresh_seconds"])
    st.rerun()


if __name__ == "__main__":
    main()
