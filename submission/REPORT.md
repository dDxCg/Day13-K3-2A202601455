# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: VGO
- Repository URL: https://github.com/dDxCg/Day13-K3-2A202601455
- Commit SHA cuối: 902b47f2bc0624e9e8d604dfc6741ec3fa9fb6a8

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

- Challenge ID: config/challange.json
- Triệu chứng từ metrics: latency p95/p99 tăng mạnh từ ~500ms lên 2500 - 3000ms
- Trace ID liên quan: e918f5bc9c2c19432dc6f5495c02db2a
- Log line/correlation ID liên quan: req-1eb04b3f
- Root cause: incident rag_slow bật STATE["rag_slow"], khiến retrieve() trong app/mock_rag.py sleep đồng bộ 2.5s mỗi request feature=refund; log response_sent khớp latency_ms ~2500-2900, không kèm error_type, trace xác nhận span retrieval/generation chiếm gần hết thời gian
- Fix action: inject_incident.py --disable để khôi phục baseline; về lâu dài thêm timeout cho vector store call + cache kết quả retrieval hay dùng, tránh block đồng bộ toàn request
- Preventive measure: Tách riêng span đo thời gian retrieval trong trace (hiện gộp chung GENERATION), thêm alert theo span-level latency thay vì chỉ tổng latency, và thêm timeout cứng ở tầng retrieve() để lỗi fail-fast thay vì treo 2.5s

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR |
|---|---|---|---|
| Nguyễn Thanh Hoàn | PII mask và Structured log | https://github.com/dDxCg/Day13-K3-2A202601455/pull/1 |
| Lương Thanh Trang | Dashboard, SLO | https://github.com/dDxCg/Day13-K3-2A202601455/pull/2 |
| Đỗ Tuấn Kiệt | tracing and prompt version | 7b1506b8e2cbd31ad7a7607129a522094a0c26bb | 
| Đỗ Đức Cường | trace incident | 0aad354d97ba1094954a0e09267662298da0126d |
