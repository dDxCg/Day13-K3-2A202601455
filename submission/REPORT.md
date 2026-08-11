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
- Version/label baseline: version 3, label `baseline` (giữ nguyên template gốc `Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}`)
- Version/label candidate: version 4, label `candidate` (đổi format: hướng dẫn trả lời tối đa 3 câu, thêm system framing)
- Trace ID của mỗi version:
  - label=baseline (v3): trace `8e8f65f7a0fe16652887aa4af376be7d` (session `role2-baseline-02`)
  - label=candidate (v4): trace `e9cb90002499b2e474da1592221691e1` (session `role2-candidate-02`)
- Bằng chứng đổi label hoặc rollback:
  - Đổi `production` từ v3 → v4: trace `83954cee5dfe63a7d1bf512123b1cbdd` (session `role2-promoted-01`), metadata xác nhận `prompt_label=production, prompt_version=4`
  - Rollback `production` từ v4 → v3: trace `850c46ddf7cf947cc5d15b19c27ea361` (session `role2-rollback-02`), metadata xác nhận `prompt_label=production, prompt_version=3`
  - [Cần bổ sung: ảnh chụp màn hình Langfuse UI cho 2 trace trên và danh sách prompt version — evidence dạng ảnh vẫn bắt buộc theo SUBMISSION.md]

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
