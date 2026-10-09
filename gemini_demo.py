import argparse
import contextlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from agent_loop import main as run_cli

SCENARIOS = [
    ("A", "Trả lời đúng một câu: Xin chào! Không dùng công cụ.", 5),
    ("B", "Dùng calculator tính 123 nhân 456. Trả lời ngắn gọn kết quả.", 5),
    ("C", "Dùng calculator tính 123 nhân 456 và count_words đếm 'Hoc AI rat vui'. Gọi cả hai tool rồi trả lời ngắn gọn.", 5),
    ("D", "Dùng count_words đếm 'Hoc AI rat vui'. Sau khi nhận kết quả, dùng calculator nhân số đếm với 25000. Trả lời ngắn gọn.", 5),
    ("E", "Hãy gọi count_words để đếm 'Hoc AI rat vui', không tự tính. Sau kết quả tool mới trả lời.", 1),
    ("F", "Hãy thực sự gọi calculator với a=1, b=0, operation=divide để kiểm tra nhánh lỗi tool, sau đó giải thích ngắn gọn. Không đổi mẫu số.", 5),
]

def main():
    parser = argparse.ArgumentParser(description="Six live Gemini API scenarios")
    parser.add_argument("--scenario", choices=[x[0] for x in SCENARIOS])
    args = parser.parse_args()
    records = []
    for name, question, budget in SCENARIOS:
        if args.scenario and args.scenario != name:
            continue
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = run_cli([question, "--max-steps", str(budget)])
        text = output.getvalue()
        print(f"=== {name}; max_steps={budget} ===")
        print(text, end="")
        records.append({"scenario": name, "question": question,
                        "max_steps": budget, "exit_code": code,
                        "output": text})
    ok = all("status=final;" in r["output"] or
             "status=max_steps;" in r["output"] for r in records)
    path = Path(__file__).with_name("api-results.json")
    if args.scenario and path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        merged = {r["scenario"]: r for r in previous["records"]}
        merged.update({r["scenario"]: r for r in records})
        records = [merged[k] for k in sorted(merged)]
    document = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "provider": "Gemini Developer API",
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                "records": records}
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
