# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: VGO
- Repository URL: [github.com/dDxCg/Day13-K3-Observability.git](https://github.com/dDxCg/Day13-K3-Observability.git)
- Commit SHA cuối:
- Thành viên và vai trò:| Tên                | Vai trò                 | Phạm vi chính                                 | Evidence phải bàn giao                     |
  | ------------------- | ------------------------ | ----------------------------------------------- | -------------------------------------------- |
  | Nguyễn Thanh Hoàn | Logging & PII            | correlation ID, metadata, JSON log, redaction   | log hợp lệ và bằng chứng không lộ PII |
  | Đỗ Tuấn Kiệt    | Tracing & Prompt Version | traces, metadata, prompt v1/v2, label/rollback  | trace gắn đúng prompt version             |
  | Lương Thanh Trang | Dashboard, SLO & Alert   | 6 panel, threshold, SLO, alert và runbook      | validator + ảnh dashboard                   |
  | Đỗ Đức Cường  | Incident, Report & Demo  | chạy challenge, nối metrics → traces → logs | root cause, fix và demo cuối               |

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
- Evidence dashboard: `submission/evidence/dashboard_baseline.png` — 6 panel (latency P50/95/99, traffic, error, cost, tokens, quality), time range 60 phút, refresh 30s, mỗi panel có dòng threshold/SLO
- SLO đã chọn và lý do (`config/slo.yaml`):
  - `latency_p95_ms` ≤ 3000ms (target 99.5%): baseline thực đo P50=584ms/P95=644ms/P99=668ms trên 24 request `response_sent` trong `data/logs.jsonl`; đặt 3000ms để có headroom phát hiện incident kiểu `rag_slow` mà không quá lỏng.
  - `error_rate_pct` ≤ 2% (target 99.0%): baseline 0/24 request lỗi; ngưỡng 2% là chuẩn phổ biến cho API, đủ nhạy để bắt `ElevatedErrorRate`.
  - `daily_cost_usd` ≤ 2.5 USD (target 100%): baseline 24 request tốn 0.048 USD; 2.5 USD/ngày để dư biên khi load test tăng concurrency mà vẫn cảnh báo được trước khi vượt ngân sách.
  - `quality_score_avg` ≥ 0.75 (target 95%): baseline trung bình 0.88; đặt 0.75 làm sàn cảnh báo sớm khi chất lượng suy giảm rõ rệt so với baseline.
- Alert rules và runbook: `config/alert_rules.yaml` (HighLatencyP95, ElevatedErrorRate, DailyCostBudgetBreach — cả 3 dựa trên triệu chứng/SLO, không dựa tên implementation nội bộ) với chi tiết điều kiện, user impact, 3 bước kiểm tra đầu, mitigation và owner tại `docs/alerts.md`.

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

| Thành viên        | Phần việc                                                                            | Commit/PR                                                                                     | Điều đã học                                                                                                                       |
| ------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Nguyễn Thanh Hoàn | Logging & PII: correlation ID, metadata, JSON log, redaction                           | `032f11b` loggin and pII                                                                    | Cách chuẩn hoá log JSON có correlation ID xuyên suốt request và redact PII (email, số điện thoại, thẻ) trước khi ghi log |
| Đỗ Tuấn Kiệt    | Tracing & Prompt Version: tạo traces, metadata, prompt v1/v2, đổi label/rollback    | `7b1506b` Tracing & Prompt Version                                                          | Cách gắn prompt_name/prompt_label/prompt_version vào trace trên Langfuse và quy trình promote/rollback prompt an toàn           |
| Lương Thanh Trang | Dashboard, SLO & Alert: dựng 6 panel, threshold, SLO, alert và runbook               | `c7e6ed1` checkpoint 2                                                                      | Cách xác định SLO dựa trên baseline thực đo và viết alert rule theo triệu chứng thay vì theo tên implementation nội bộ |
| Đỗ Đức Cường  | Incident, Report & Demo: merge nhánh, chạy challenge, nối metrics → traces → logs | `8702c4e` Merge pull request #1 from dDxCg/hoan, `d874629` Merge branch 'main' into trang | Cách khoanh vùng root cause bằng cách nối dữ liệu giữa metrics, trace và log                                                  |
