import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from loop_core import run_agent
from tools import TOOLS
def main(argv=None):
    parser = argparse.ArgumentParser(description="Bounded tool-calling loop")
    parser.add_argument("question")
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args(argv)
    load_dotenv(Path(__file__).with_name(".env"), override=False)
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key:
        parser.error("Missing GOOGLE_API_KEY in environment or .env")
    try:
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            api_key=key, vertexai=False, temperature=0.0,
            timeout=60, max_retries=0)
        result = run_agent(llm.bind_tools(TOOLS), args.question, args.max_steps)
    except Exception as exc:
        print(f"Không khởi chạy được Agent ({type(exc).__name__}).")
        return 2
    for event in result.trace:
        if event["event"] == "tool":
            print(f"[step {event['step']}] {event['name']}: "
                  f"{event['payload']}")
    print(f"status={result.status}; steps={result.steps}; "
          f"tool_calls={result.tool_calls}")
    print(result.answer)
    return 0 if result.status == "final" else 1
if __name__ == "__main__":
    raise SystemExit(main())
