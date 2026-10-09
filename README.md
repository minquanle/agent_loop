# Agent Loop — Gemini 2.5 Flash qua API thật

Mã thực hành cho bài **Xây dựng vòng lặp Agent gọi công cụ có giới hạn số bước** của AI Guru x TiniX. Agent gọi Gemini Developer API, dùng calculator và count_words, lưu lịch sử tin nhắn và dừng theo max_steps.

## Thiết lập trên Windows / PowerShell

Cần Python 3.11, Git, kết nối mạng và Google API key có quyền/quota cho Gemini 2.5 Flash.

```powershell
git clone https://github.com/minquanle/agent_loop.git
cd agent_loop
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
Copy-Item .env.example .env
```

Chỉ sao chép file mẫu nếu chưa có `.env`; mở `.env` và điền key của bạn:

```dotenv
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Key thật chỉ ở `.env`, được gitignore loại trừ. CLI đọc `.env` cạnh file Python; biến môi trường có sẵn được ưu tiên. Model được kiểm tra theo [tài liệu Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash); quyền truy cập còn phụ thuộc tài khoản. Google hiện giới hạn truy cập model 2.5 cho các tài khoản đã dùng trước đó.

Trên macOS/Linux: `python3.11 -m venv .venv`, dùng `.venv/bin/python` thay `.\.venv\Scripts\python.exe`, và `cp .env.example .env` nếu chưa có cấu hình.

## Chạy Agent

```powershell
.\.venv\Scripts\python.exe agent_loop.py "Dùng calculator tính 123 nhân 456." --max-steps 5
```

Gemini quyết định tool/tham số. CLI in kết quả tool, trạng thái, số bước, số yêu cầu đưa qua dispatcher và câu trả lời. `final` trả exit code 0; trạng thái dừng/lỗi trả 1; lỗi khởi chạy trả 2. `final` không bảo đảm câu trả lời đúng.

## Sáu tình huống gọi API

```powershell
.\.venv\Scripts\python.exe gemini_demo.py
.\.venv\Scripts\python.exe gemini_demo.py --scenario D
```

Lệnh đầu chạy A–F; lệnh sau chỉ chạy D. Mỗi lần chạy gọi API thật và có thể phát sinh phí. Cần key có quyền/quota. `api-results.json` ghi lại câu hỏi, ngân sách, exit code và output thực tế. Khi chỉ chạy một tình huống, kết quả đó được cập nhật và các tình huống còn lại được giữ. File kết quả đi kèm là một lần chạy đã ghi nhận; kết quả chạy mới có thể khác câu chữ, thứ tự hoặc số bước.

| Tình huống | Nội dung | Kết quả API đã ghi nhận |
|---|---|---|
| A | Chào hỏi, không cần tool | final, 1 bước, 0 tool call |
| B | Tính 123 × 456 | final, 2 bước, 1 call; value 56088.0 |
| C | Tính và đếm cùng yêu cầu | final, 2 bước, 2 call ở bước đầu; value 56088.0, count 4 |
| D | Đếm trước, nhân sau | final, 3 bước, 2 call; value 100000.0 |
| E | Ngân sách một bước | max_steps, 1 bước, 1 call; count 4 |
| F | Gọi tool chia cho 0 rồi giải thích | final, 2 bước, 1 call; invalid_arguments |

Tình huống F yêu cầu thử lỗi chia 0; chương trình không tự đổi mẫu số. Câu trả lời API có thể gọi kết quả đếm là “từ”, nhưng count_words chỉ đếm đơn vị cách trắng, không phân tích từ tiếng Việt theo nghĩa ngôn ngữ học.

## Cấu trúc

- `tools.py`: calculator với số hữu hạn và count_words giới hạn 4000 ký tự.
- `loop_core.py`: điều phối, dispatcher, lịch sử và trace.
- `agent_loop.py`: CLI với Gemini 2.5 Flash, temperature=0.0, timeout=60 giây, max_retries=0.
- `gemini_demo.py`: sáu tình huống gọi cùng CLI qua API.
- `api-results.json`: output API đã ghi nhận.
- `requirements.txt`, `.env.example`, `.gitignore`: cài đặt và cấu hình.

Kiểm tra cú pháp:

```powershell
.\.venv\Scripts\python.exe -m py_compile tools.py loop_core.py agent_loop.py gemini_demo.py
```

Một bước là một lần thử gọi mô hình, kể cả lỗi. Lượt trả lời cuối cũng tính bước. Mặc định tối đa 5 bước và 4 call mỗi bước; nhóm quá lớn bị từ chối cả nhóm và nhận đủ ToolMessage lỗi. Tool chạy tuần tự; giữ AIMessage và ghép kết quả theo ID. Bước cuối vẫn chạy tool nhưng không có lượt tổng kết thêm ngoài ngân sách.

`tool_calls` và `trace.executed` đếm yêu cầu qua dispatcher, gồm cả sai tên/tham số; đọc payload.ok để biết thành công. `max_steps` từ 1–20, `max_calls_per_step` từ 1–8; giới hạn thứ hai truyền qua Python. Mỗi câu hỏi có lịch sử riêng. Mẫu chưa có bộ nhớ nhiều lượt, deadline tổng, timeout cho tool dài hoặc phát hiện lặp cùng tên/tham số.

Temperature thấp giảm độ ngẫu nhiên, không bảo đảm tham số đúng. Timeout áp dụng từng lời gọi mô hình. Khi xác minh đã gặp timeout, lần gọi tiếp theo thành công; mẫu không tự retry. Mỗi lần chạy có thể khác do model, quyền tài khoản, quota và tình trạng dịch vụ.

## Dữ liệu và lỗi thường gặp

Câu hỏi, mô tả tool và kết quả được gửi qua API cho nhà cung cấp. CLI và api-results.json lưu output; chỉ dùng dữ liệu mẫu, kiểm tra nội dung trước khi chia sẻ. Không commit key hoặc log chứa thông tin nhạy cảm.

- Thiếu key: tạo `.env` từ mẫu và điền GOOGLE_API_KEY; `.env.example` không được đọc tự động.
- 401/403: kiểm tra key và quyền truy cập model; 429: kiểm tra quota, chờ rồi chạy lại khi đủ hạn mức.
- model_error/504: kiểm tra dịch vụ/kết nối; timeout 60 giây không đảm bảo mọi yêu cầu sẽ thành công.
- max_steps: xem kết quả từng phần; tăng ngân sách chỉ khi có nhu cầu. Giảm bước không ngắt hàm tool đang chạy.
- protocol_error: kiểm tra ID/phản hồi và phiên bản thư viện; không tự tạo ID để tiếp tục.

Đã gọi Gemini 2.5 Flash qua API trên Windows/Python 3.11.9 ngày 09/10/2026, nhận đủ sáu kết quả nêu trên. Đây là bằng chứng cho các yêu cầu cụ thể, không bảo đảm mọi lần chạy hoặc câu hỏi khác đều đạt.
