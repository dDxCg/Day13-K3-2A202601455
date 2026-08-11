# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`:
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

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

- Kết quả `validate_dashboard.py`:
- Evidence dashboard:
- SLO đã chọn và lý do:
- Alert rules và runbook:

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
