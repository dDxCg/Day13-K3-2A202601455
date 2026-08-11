"""Generate a static, hand-editable HTML dashboard for Day 13 observability lab.

Reads config/dashboard.yaml (contract) and data/logs.jsonl (data), writes a
single self-contained HTML file. Unlike the Streamlit app, this output is a
plain file: open it in any browser, or edit the HTML/CSS by hand.

Run with: python scripts/generate_dashboard_html.py [--out reports/dashboard.html]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from statistics import mean

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_OUT = REPO_ROOT / "reports" / "dashboard.html"

TERM_HELP = {
    "P50 (ms)": "Trung vị (median): một nửa request nhanh hơn giá trị này.",
    "P95 (ms)": "95% request nhanh hơn giá trị này. Dùng để phát hiện độ trễ đuôi (tail latency).",
    "P99 (ms)": "99% request nhanh hơn giá trị này. Nhạy với vài request rất chậm.",
    "SLO": "Service Level Objective: mức mục tiêu cam kết. Vượt ngưỡng = vi phạm chất lượng dịch vụ.",
    "QPS": "Queries per second: số request xử lý mỗi giây.",
    "Error rate (%)": "Tỷ lệ request thất bại trên tổng số request nhận được, trong khoảng thời gian hiển thị.",
    "Cost (USD)": "Tổng chi phí gọi model, tính bằng USD, cộng dồn trong khoảng thời gian hiển thị.",
    "Tokens in/out": "Số token gửi vào (prompt) và nhận về (completion) từ model.",
    "Quality score": "Điểm chất lượng proxy (0-1) tự động chấm cho câu trả lời; không thay thế đánh giá con người.",
}


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]


def load_logs() -> list[dict]:
    records = []
    if not LOG_PATH.exists():
        return records
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "ts" in rec:
            rec["_ts"] = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
        records.append(rec)
    return records


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, round(pct / 100 * (len(s) - 1))))
    return s[idx]


def panel_by_id(config: dict, panel_id: str) -> dict:
    return next(p for p in config["panels"] if p["id"] == panel_id)


def term(label: str) -> str:
    help_text = TERM_HELP.get(label, "")
    if not help_text:
        return escape(label)
    return (
        f'<span class="term" tabindex="0">{escape(label)}'
        f'<span class="tooltip">{escape(help_text)}</span></span>'
    )


def threshold_text(panel: dict) -> str:
    t = panel["threshold"]
    op = "≤" if t["operator"] == "lte" else "≥"
    return f"{term('SLO')}: {t['aggregation']} {op} {t['value']} {panel['unit']}"


def stat_card(label: str, value: str, breach: bool = False) -> str:
    cls = "stat breach" if breach else "stat"
    return f'<div class="{cls}"><div class="stat-value">{value}</div><div class="stat-label">{term(label)}</div></div>'


def bucket_per_minute(items: list[dict], value_fn=None) -> list[tuple[datetime, float]]:
    """Group items by minute; value_fn(item)->float sums per bucket, else counts."""
    buckets: dict[datetime, float] = {}
    for r in items:
        ts = r.get("_ts")
        if not ts:
            continue
        minute = ts.replace(second=0, microsecond=0)
        buckets[minute] = buckets.get(minute, 0.0) + (value_fn(r) if value_fn else 1.0)
    return sorted(buckets.items())


def svg_bar_chart(data: list[tuple[str, float]], *, width=520, height=140, color="var(--accent)") -> str:
    if not data:
        return '<p class="empty">Không có dữ liệu để vẽ biểu đồ.</p>'
    pad_l, pad_b, pad_t = 30, 20, 10
    plot_w = width - pad_l - 10
    plot_h = height - pad_b - pad_t
    max_v = max(v for _, v in data) or 1.0
    n = len(data)
    bar_w = plot_w / n
    bars = []
    labels = []
    show_every = max(1, n // 8)
    for i, (label, v) in enumerate(data):
        bar_h = (v / max_v) * plot_h
        x = pad_l + i * bar_w
        y = pad_t + (plot_h - bar_h)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(bar_w - 2, 1):.1f}" height="{bar_h:.1f}" '
            f'fill="{color}" rx="2"><title>{escape(label)}: {v:g}</title></rect>'
        )
        if i % show_every == 0:
            labels.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{height - 4}" font-size="9" '
                f'fill="var(--muted)" text-anchor="middle">{escape(label)}</text>'
            )
    axis = f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{width - 10}" y2="{pad_t + plot_h}" stroke="var(--border)"/>'
    max_label = f'<text x="{pad_l - 4}" y="{pad_t + 8}" font-size="9" fill="var(--muted)" text-anchor="end">{max_v:g}</text>'
    return (
        f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="bar chart">'
        f"{axis}{max_label}{''.join(bars)}{''.join(labels)}</svg>"
    )


def svg_line_chart(data: list[tuple[str, float]], *, width=520, height=140, color="var(--accent)") -> str:
    if not data:
        return '<p class="empty">Không có dữ liệu để vẽ biểu đồ.</p>'
    pad_l, pad_b, pad_t = 34, 20, 10
    plot_w = width - pad_l - 10
    plot_h = height - pad_b - pad_t
    max_v = max(v for _, v in data) or 1.0
    n = len(data)
    step = plot_w / max(n - 1, 1)
    points = []
    for i, (_, v) in enumerate(data):
        x = pad_l + i * step
        y = pad_t + (plot_h - (v / max_v) * plot_h)
        points.append((x, y))
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}"><title>{escape(data[i][0])}: {data[i][1]:g}</title></circle>'
        for i, (x, y) in enumerate(points)
    )
    axis = f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{width - 10}" y2="{pad_t + plot_h}" stroke="var(--border)"/>'
    max_label = f'<text x="{pad_l - 4}" y="{pad_t + 8}" font-size="9" fill="var(--muted)" text-anchor="end">{max_v:g}</text>'
    return (
        f'<svg viewBox="0 0 {width} {height}" class="chart" role="img" aria-label="line chart">'
        f'{axis}{max_label}<path d="{path}" fill="none" stroke="{color}" stroke-width="2"/>{dots}</svg>'
    )


def build_html(config: dict, records: list[dict]) -> str:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=config["time_range_minutes"])
    windowed = [r for r in records if r.get("_ts") and r["_ts"] >= window_start]
    responses = [r for r in windowed if r.get("event") == "response_sent"]
    requests_recv = [r for r in windowed if r.get("event") == "request_received"]
    failed = [r for r in windowed if r.get("event") == "request_failed"]

    # --- latency ---
    lat_panel = panel_by_id(config, "latency")
    lat_values = [r["latency_ms"] for r in responses if "latency_ms" in r]
    p50 = percentile(lat_values, 50)
    p95 = percentile(lat_values, 95)
    p99 = percentile(lat_values, 99)
    lat_breach = bool(lat_values) and p95 > lat_panel["threshold"]["value"]
    latency_html = (
        stat_card("P50 (ms)", f"{p50:.0f}") if lat_values else ""
    ) + (
        stat_card("P95 (ms)", f"{p95:.0f}", breach=lat_breach) if lat_values else ""
    ) + (
        stat_card("P99 (ms)", f"{p99:.0f}") if lat_values else ""
    )
    if lat_values:
        responses_sorted = sorted(responses, key=lambda r: r["_ts"])
        latency_html += svg_line_chart(
            [(r["_ts"].strftime("%H:%M:%S"), r["latency_ms"]) for r in responses_sorted if "latency_ms" in r]
        )
    else:
        latency_html = '<p class="empty">Không có event response_sent trong khoảng thời gian này.</p>'

    # --- traffic ---
    traffic_panel = panel_by_id(config, "traffic")
    traffic_html = stat_card("QPS", f"{len(requests_recv)} request")
    per_min_req = bucket_per_minute(requests_recv)
    traffic_html += svg_bar_chart([(m.strftime("%H:%M"), v) for m, v in per_min_req])

    # --- errors ---
    err_panel = panel_by_id(config, "errors")
    total_req = len(requests_recv)
    total_fail = len(failed)
    error_rate = (total_fail / total_req * 100) if total_req else 0.0
    err_breach = error_rate > err_panel["threshold"]["value"]
    error_types: dict[str, int] = {}
    for r in failed:
        et = r.get("error_type", "unknown")
        error_types[et] = error_types.get(et, 0) + 1
    err_breakdown = "".join(
        f"<li>{escape(str(k))}: {v}</li>" for k, v in sorted(error_types.items(), key=lambda kv: -kv[1])
    ) or "<li>Không có lỗi trong khoảng thời gian này.</li>"
    errors_html = stat_card("Error rate (%)", f"{error_rate:.2f}", breach=err_breach)
    if error_types:
        errors_html += svg_bar_chart(
            sorted(error_types.items(), key=lambda kv: -kv[1]), color="var(--danger)"
        )
    errors_html += f'<ul class="breakdown">{err_breakdown}</ul>'

    # --- cost ---
    cost_panel = panel_by_id(config, "cost")
    total_cost = sum(r.get("cost_usd", 0.0) for r in responses)
    cost_breach = total_cost > cost_panel["threshold"]["value"]
    cost_html = stat_card("Cost (USD)", f"${total_cost:.4f}", breach=cost_breach)
    per_min_cost = bucket_per_minute(responses, value_fn=lambda r: r.get("cost_usd", 0.0))
    cost_html += svg_line_chart([(m.strftime("%H:%M"), round(v, 4)) for m, v in per_min_cost])

    # --- tokens ---
    tok_panel = panel_by_id(config, "tokens")
    tokens_in = sum(r.get("tokens_in", 0) for r in responses)
    tokens_out = sum(r.get("tokens_out", 0) for r in responses)
    tokens_html = stat_card("Tokens in/out", f"{tokens_in} / {tokens_out}")

    # --- quality ---
    qual_panel = panel_by_id(config, "quality")
    q_scores = [r["quality_score"] for r in responses if "quality_score" in r]
    mean_q = mean(q_scores) if q_scores else 0.0
    qual_breach = bool(q_scores) and mean_q < qual_panel["threshold"]["value"]
    quality_html = stat_card("Quality score", f"{mean_q:.3f}", breach=qual_breach)

    sections = [
        {
            "group": "Hiệu năng & Lưu lượng",
            "audience": "Kỹ sư vận hành, SRE",
            "panels": [
                (lat_panel, latency_html),
                (traffic_panel, traffic_html),
            ],
        },
        {
            "group": "Độ tin cậy",
            "audience": "Kỹ sư, quản lý sản phẩm",
            "panels": [
                (err_panel, errors_html),
            ],
        },
        {
            "group": "Chi phí & Sử dụng",
            "audience": "Quản lý, tài chính",
            "panels": [
                (cost_panel, cost_html),
                (tok_panel, tokens_html),
            ],
        },
        {
            "group": "Chất lượng đầu ra",
            "audience": "Sản phẩm, QA",
            "panels": [
                (qual_panel, quality_html),
            ],
        },
    ]

    section_blocks = []
    for sec in sections:
        panel_blocks = []
        for panel, body in sec["panels"]:
            panel_blocks.append(
                f'''<div class="panel">
  <div class="panel-head">
    <h3>{escape(panel["title"])}</h3>
    <span class="unit">đơn vị: {escape(panel["unit"])}</span>
  </div>
  <div class="panel-body">{body}</div>
  <div class="panel-threshold">{threshold_text(panel)}</div>
</div>'''
            )
        section_blocks.append(
            f'''<section class="group">
  <div class="group-head">
    <h2>{escape(sec["group"])}</h2>
  </div>
  <div class="panel-grid">
    {''.join(panel_blocks)}
  </div>
</section>'''
        )

    generated_at = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    return f'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{escape(config["title"])}</title>
<style>
  :root {{
    --bg: #f5f6f9; --panel-bg: #ffffff; --border: #d9dce3;
    --text: #1a1d24; --muted: #6b7280; --accent: #3b6fd6; --danger: #d1373d;
    --group-tint: rgba(0,0,0,0.02);
    --tooltip-bg: #1a1d24; --tooltip-text: #f5f6f9;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #0f1117; --panel-bg: #171a23; --border: #2a2f3d;
      --text: #e6e8ee; --muted: #9aa2b1; --accent: #5b8def; --danger: #e5484d;
      --group-tint: rgba(255,255,255,0.02);
      --tooltip-bg: #f5f6f9; --tooltip-text: #1a1d24;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #0f1117; --panel-bg: #171a23; --border: #2a2f3d;
    --text: #e6e8ee; --muted: #9aa2b1; --accent: #5b8def; --danger: #e5484d;
    --group-tint: rgba(255,255,255,0.02);
    --tooltip-bg: #f5f6f9; --tooltip-text: #1a1d24;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px; background: var(--bg); color: var(--text);
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
  }}
  header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; gap: 16px; }}
  h1 {{ margin: 0 0 4px; font-size: 22px; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .settings {{ position: relative; flex-shrink: 0; }}
  .settings-btn {{
    display: flex; align-items: center; justify-content: center; width: 34px; height: 34px;
    border: 1px solid var(--border); border-radius: 8px; background: var(--panel-bg); color: var(--text);
    cursor: pointer;
  }}
  .settings-btn svg {{ width: 18px; height: 18px; }}
  .settings-panel {{
    display: none; position: absolute; right: 0; top: 42px; z-index: 20; min-width: 190px;
    border: 1px solid var(--border); border-radius: 8px; background: var(--panel-bg);
    padding: 8px; box-shadow: 0 6px 16px rgba(0,0,0,0.15);
  }}
  .settings-panel.open {{ display: block; }}
  .settings-panel .label {{ font-size: 11px; color: var(--muted); padding: 4px 6px; }}
  .theme-choice {{
    display: flex; align-items: center; gap: 8px; width: 100%; padding: 6px 8px; margin: 2px 0;
    border: 1px solid transparent; border-radius: 6px; background: none; color: var(--text);
    font-size: 13px; cursor: pointer; text-align: left;
  }}
  .theme-choice svg {{ width: 16px; height: 16px; flex-shrink: 0; }}
  .theme-choice:hover {{ background: var(--group-tint); }}
  .theme-choice.active {{ border-color: var(--accent); color: var(--accent); }}
  .group {{
    margin-bottom: 28px; border: 1px solid var(--border); border-radius: 10px;
    padding: 16px; background: var(--group-tint);
  }}
  .group-head {{ display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }}
  .group-head h2 {{ margin: 0; font-size: 16px; color: var(--accent); }}
  .audience {{ font-size: 12px; color: var(--muted); }}
  .panel-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
  .panel {{ border: 1px solid var(--border); border-radius: 8px; padding: 14px; background: var(--panel-bg); }}
  .panel-head {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }}
  .panel-head h3 {{ margin: 0; font-size: 14px; }}
  .unit {{ font-size: 11px; color: var(--muted); }}
  .panel-body {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .stat {{ min-width: 90px; }}
  .stat-value {{ font-size: 22px; font-weight: 600; }}
  .stat-label {{ font-size: 11px; color: var(--muted); margin-top: 2px; }}
  .stat.breach .stat-value {{ color: var(--danger); }}
  .panel-threshold {{ margin-top: 10px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--border); padding-top: 8px; }}
  .breakdown {{ list-style: none; margin: 6px 0 0; padding: 0; font-size: 12px; color: var(--muted); }}
  .empty {{ color: var(--muted); font-size: 13px; }}
  .term {{ position: relative; border-bottom: 1px dotted var(--muted); cursor: help; }}
  .tooltip {{
    display: none; position: absolute; bottom: 130%; left: 0; z-index: 10;
    width: 220px; padding: 8px 10px; background: var(--tooltip-bg); border: 1px solid var(--border);
    border-radius: 6px; font-size: 11px; color: var(--tooltip-text); line-height: 1.4; font-weight: normal;
  }}
  .term:hover .tooltip, .term:focus .tooltip {{ display: block; }}
  .chart {{ width: 100%; height: auto; margin-top: 8px; display: block; }}
  footer {{ margin-top: 20px; font-size: 12px; color: var(--muted); }}
</style>
</head>
<body>
<header>
  <div>
    <h1>{escape(config["title"])}</h1>
    <div class="meta">Khoảng thời gian: {config["time_range_minutes"]} phút gần nhất | tạo lúc: {generated_at} | số bản ghi trong cửa sổ: {len(windowed)}</div>
  </div>
  <div class="settings">
    <button class="settings-btn" id="settings-btn" aria-label="Cài đặt giao diện" title="Cài đặt giao diện">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </svg>
    </button>
    <div class="settings-panel" id="settings-panel">
      <div class="label">Giao diện</div>
      <button class="theme-choice" data-theme-choice="light">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
        Sáng
      </button>
      <button class="theme-choice" data-theme-choice="dark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>
        Tối
      </button>
      <button class="theme-choice" data-theme-choice="system">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
        Hệ thống
      </button>
    </div>
  </div>
</header>
{''.join(section_blocks)}
<script>
(function() {{
  var root = document.documentElement;
  var KEY = "day13-dashboard-theme";
  function apply(choice) {{
    if (choice === "light" || choice === "dark") {{
      root.setAttribute("data-theme", choice);
    }} else {{
      root.removeAttribute("data-theme");
    }}
    document.querySelectorAll(".theme-choice").forEach(function(btn) {{
      btn.classList.toggle("active", btn.getAttribute("data-theme-choice") === choice);
    }});
  }}
  var saved = localStorage.getItem(KEY) || "system";
  apply(saved);
  document.querySelectorAll(".theme-choice").forEach(function(btn) {{
    btn.addEventListener("click", function() {{
      var choice = btn.getAttribute("data-theme-choice");
      localStorage.setItem(KEY, choice);
      apply(choice);
    }});
  }});
  var settingsBtn = document.getElementById("settings-btn");
  var panel = document.getElementById("settings-panel");
  settingsBtn.addEventListener("click", function(e) {{
    e.stopPropagation();
    panel.classList.toggle("open");
  }});
  document.addEventListener("click", function(e) {{
    if (!panel.contains(e.target) && e.target !== settingsBtn) {{
      panel.classList.remove("open");
    }}
  }});
}})();
</script>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static HTML dashboard")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    config = load_config()
    records = load_logs()
    html = build_html(config, records)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"Da ghi dashboard tinh vao: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
