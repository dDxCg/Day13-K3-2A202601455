# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: warning
- SLI/SLO liên quan: `latency_p95_ms` ≤ 3000ms (config/slo.yaml)
- Điều kiện và thời gian duy trì: P95 latency > 3000ms, duy trì liên tục 5 phút
- Ảnh hưởng tới người dùng: câu trả lời chậm, người dùng chờ lâu hoặc bỏ ngang phiên chat
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency trên dashboard, xác nhận P95/P99 tăng và khoảng thời gian bắt đầu
  2. Mở trace chậm nhất trong khoảng thời gian đó trên Langfuse, tìm span chiếm nhiều thời gian nhất (ví dụ RAG retrieval, tool call)
  3. Tra log theo `correlation_id` của trace để xem chi tiết field liên quan (feature, model, payload)
- Mitigation tạm thời: tắt/giảm concurrency của incident đang chạy (`python scripts/inject_incident.py --scenario rag_slow --disable`) hoặc route feature bị chậm sang fallback đơn giản hơn
- Owner: dashboard-team

## Alert 2

- Tên: ElevatedErrorRate
- Severity: critical
- SLI/SLO liên quan: `error_rate_pct` ≤ 2% (config/slo.yaml)
- Điều kiện và thời gian duy trì: error rate > 2%, duy trì liên tục 5 phút
- Ảnh hưởng tới người dùng: request thất bại, người dùng nhận lỗi thay vì câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Errors, xem breakdown theo `error_type` để biết loại lỗi chiếm đa số
  2. Lọc log `event == "request_failed"` theo `error_type` và `feature` để khoanh vùng
  3. Mở trace tương ứng để xem span nào raise exception
- Mitigation tạm thời: rollback prompt/version gần nhất nếu lỗi bắt đầu ngay sau khi đổi label, hoặc bật circuit breaker cho dependency đang lỗi
- Owner: dashboard-team

## Alert 3

- Tên: DailyCostBudgetBreach
- Severity: warning
- SLI/SLO liên quan: `daily_cost_usd` ≤ 2.5 USD (config/slo.yaml)
- Điều kiện và thời gian duy trì: tổng cost trong cửa sổ hiện tại > 2.5 USD, duy trì 15 phút
- Ảnh hưởng tới người dùng: không ảnh hưởng trực tiếp trải nghiệm, nhưng rủi ro vượt ngân sách vận hành
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Cost, xem xu hướng tăng theo phút và tổng cộng
  2. Đối chiếu panel Tokens để xác nhận cost tăng do tokens_out tăng hay do tần suất request tăng
  3. Lọc log theo `feature`/`model` để tìm nguồn phát sinh chi phí bất thường
- Mitigation tạm thời: giới hạn concurrency hoặc tạm ngắt feature gây chi phí cao, xem lại prompt/response length
- Owner: dashboard-team
