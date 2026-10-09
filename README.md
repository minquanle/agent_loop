# Agent Loop: vòng lặp gọi công cụ có giới hạn bước

Mã thực hành đi kèm bài **Xây dựng vòng lặp Agent gọi công cụ có giới hạn số bước** của AI Guru x TiniX. Agent dùng Gemini và LangChain với hai tool: `calculator` và `count_words`.

## Yêu cầu

- Python 3.11 và Git.
- Demo và kiểm thử offline không cần API key.
- Chạy Gemini cần kết nối mạng, Google API key và quyền/quota cho model đã chọn.

## Tải và cài đặt trên Windows (PowerShell)

```powershell
git clone https://github.com/minquanle/agent_loop.git
cd agent_loop
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Dùng trực tiếp Python của venv trong các lệnh dưới, không cần kích hoạt venv hay thay đổi ExecutionPolicy.

Trên macOS/Linux:

```bash
git clone https://github.com/minquanle/agent_loop.git
cd agent_loop
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

## Kiểm tra trước khi gọi API

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_loop
.\.venv\Scripts\python.exe offline_demo.py
```

Bộ kiểm thử gồm 20 test. Demo có sáu kịch bản A–F: trả lời trực tiếp, một tool, nhiều tool cùng lượt, tool phụ thuộc kết quả trước, hết bước và lỗi tool. Các phản hồi mô hình đã chuẩn bị sẵn; phép tính và số đếm do tool thật thực hiện. Không gọi API hoặc phát sinh chi phí API khi chạy hai lệnh này.

Trên macOS/Linux, thay `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`.

## Cấu hình và chạy Gemini

1. Tạo key ở [Google AI Studio](https://aistudio.google.com/apikey).
2. Sao chép file mẫu và mở `.env` để điền key của bạn:

```powershell
Copy-Item .env.example .env
```

Trên macOS/Linux: `cp .env.example .env`.

```dotenv
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

`your_google_api_key_here` là chỗ cần thay bằng key thật. Model có thể đổi qua `GEMINI_MODEL`; chọn model hỗ trợ Function Calling và được tài khoản cho phép. Cấu hình mặc định được đối chiếu với [tài liệu Google](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite). Biến môi trường có sẵn được ưu tiên hơn `.env`; CLI đọc `.env` cạnh `agent_loop.py`.

3. Chạy một yêu cầu:

```powershell
.\.venv\Scripts\python.exe agent_loop.py "Dùng calculator tính 123 nhân 456." --max-steps 5
```

CLI in payload của tool, trạng thái, số bước, số yêu cầu đưa qua dispatcher và câu trả lời. Có văn bản cuối trả exit code 0; các trạng thái dừng khác trả 1; lỗi khởi chạy trả 2. Kết quả mô hình thực tế có thể khác demo offline. Cần đọc trace/kết quả tool để kiểm tra việc thực hiện yêu cầu.

## File và quy tắc vòng lặp

| File | Vai trò |
|---|---|
| `tools.py` | Hai tool và registry cho phép. |
| `loop_core.py` | Dispatcher, lịch sử tin nhắn, trace và `run_agent`. |
| `agent_loop.py` | CLI Gemini Developer API. |
| `offline_demo.py` | Sáu kịch bản A–F dùng mô hình giả. |
| `test_loop.py` | Kiểm thử logic và nhánh lỗi. |
| `requirements.txt` | Phiên bản thư viện trực tiếp được ghim. |
| `.env.example` | Cấu hình mẫu để người dùng điền key/model. |
| `.gitignore` | Loại trừ key thật, môi trường và cache. |

- Một bước là một lần thử `model.invoke`, kể cả khi lỗi; lượt trả lời cuối cũng tính bước.
- Mặc định tối đa 5 bước (cho phép 1–20) và 4 call mỗi bước (cho phép 1–8). Nhóm vượt giới hạn bị chặn cả nhóm nhưng vẫn nhận đủ ToolMessage lỗi.
- Giữ nguyên AIMessage, ghép kết quả theo ID. Tool chạy tuần tự.
- Bước cuối vẫn xử lý tool, sau đó dừng; không gọi thêm lượt tổng kết ngoài ngân sách.
- `tool_calls` và `trace.executed` đếm yêu cầu chuyển qua dispatcher, gồm cả sai tên/tham số. Đọc `payload.ok` để biết tool thành công.
- `status=final` chỉ xác nhận có văn bản cuối, không bảo đảm câu trả lời đúng.
- CLI đặt `temperature=1.0`, `timeout=30`, `max_retries=0`. Timeout áp dụng từng lời gọi mô hình, không phải deadline toàn tác vụ.

`run_agent` nhận `max_calls_per_step` qua Python; CLI chỉ có tùy chọn `--max-steps`. `calculator` dùng float, cần quy tắc số/làm tròn riêng cho tài chính. `count_words` đếm đơn vị cách trắng, không phân tích từ tiếng Việt theo nghĩa ngôn ngữ học; giới hạn văn bản 4000 ký tự.

## Dữ liệu và phạm vi mẫu

Khi chạy Gemini, câu hỏi, mô tả tool và kết quả tool được gửi qua API cho nhà cung cấp. CLI in kết quả tool ra terminal; dùng dữ liệu mẫu, tránh thông tin nhạy cảm và kiểm tra log trước khi chia sẻ. `.env` chứa key thật không được commit.

Mỗi câu hỏi có lịch sử riêng. Mẫu chưa có bộ nhớ nhiều lượt, deadline tổng, timeout cho tool dài hoặc phát hiện lặp cùng tên/tham số. Tool ghi dữ liệu, gửi email hay tạo tác động bên ngoài cần thêm phân quyền, duyệt và chống thực hiện trùng.

## Khắc phục lỗi

- Thiếu key: tạo `.env` từ `.env.example`, điền `GOOGLE_API_KEY`; file mẫu không được đọc tự động.
- `401`/`403`: kiểm tra key và quyền truy cập; `429`: kiểm tra quota. Mẫu không tự retry.
- Không tìm thấy module: cài requirements bằng đúng Python của venv, chạy ở thư mục chứa các file trên.
- `max_steps`: xem kết quả tool và chọn ngân sách phù hợp; giảm bước không ngắt một hàm tool đang chạy.
- `protocol_error`: kiểm tra ID, phản hồi và bộ phiên bản; không tự tạo ID để tiếp tục.

## Phạm vi xác minh

Đã kiểm tra offline trên Windows với Python 3.11.9 ngày 09/10/2026: 20 test và sáu demo đạt, `pip check` đạt, khởi tạo tích hợp và bind_tools đạt. Chưa gọi Gemini API thật; quyền/quota và hành vi chọn tool/tổng hợp cần kiểm tra bằng tài khoản người chạy.

Tham khảo [LangChain Google integration](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai) và [Google Function Calling](https://ai.google.dev/gemini-api/docs/function-calling).
