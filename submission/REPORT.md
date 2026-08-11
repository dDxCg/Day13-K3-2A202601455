# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (xem `submission/evidence/validate_logs_output.txt`)
- Tổng số traces: 24 unique correlation ID trong `data/logs.jsonl` (>= 10 yêu cầu), tracing_enabled=true
- Số PII leak còn lại: 0
- Link/đường dẫn dashboard: chạy local `streamlit run scripts/dashboard_app.py` (đọc `data/logs.jsonl`), screenshot tại `submission/evidence/dashboard_baseline.png`

## 3. Logging và tracing

- Evidence correlation ID: mỗi request có `correlation_id` dạng `req-xxxxxxxx` xuyên suốt `request_received` và `response_sent` (xem `data/logs.jsonl`)
- Evidence PII redaction: `validate_logs.py` báo 0 PII leak trên 53 record
- Evidence trace waterfall: traces gửi lên Langfuse (tracing_enabled=true qua `/health`), 24 trace tương ứng correlation ID
- Giải thích một span đáng chú ý: span `response_sent` mang `latency_ms`, `tokens_in/out`, `cost_usd`, `quality_score` — dùng trực tiếp cho 6 panel dashboard

## 4. Prompt versioning

- Prompt name: `day13-chat`
- Version/label baseline: version 1, labels `baseline` + `production`
- Version/label candidate: version 2, labels `candidate` (thêm câu "Answer in at most 3 sentences.")
- Trace ID của mỗi version:
  - label=baseline → `req-50b7f2db` (tokens_out=150)
  - label=candidate → `req-6f9818a9` (tokens_out=96)
- Bằng chứng đổi label hoặc rollback: xem `submission/evidence/prompt_versioning_evidence.txt`
  - Đổi `production` sang v2 → request `req-44f73187`
  - Rollback `production` về v1 → request `req-03922c3c`
  - Thực hiện qua Langfuse SDK (`scripts/setup_prompt_versions.py`, `scripts/swap_prompt_label.py`), xác nhận labels trước/sau mỗi bước

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.` (xem `submission/evidence/validate_dashboard_output.txt`)
- Evidence dashboard: `submission/evidence/dashboard_baseline.png` — 6 panel (latency P50/95/99, traffic, error, cost, tokens, quality), time range 60 phút, refresh 30s, mỗi panel có dòng SLO
- SLO đã chọn và lý do: theo `config/slo.yaml` — P95 latency ≤ 3000ms, error rate ≤ 2%, cost ngày ≤ 2.5 USD, quality mean ≥ 0.75 (giữ nguyên baseline mặc định của repo, phù hợp fake-LLM traffic thấp)
- Alert rules và runbook: xem `config/alert_rules.yaml` và `docs/alerts.md`

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| | | | |
