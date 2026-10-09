from langchain_core.messages import AIMessage
from loop_core import run_agent
class ScriptedModel:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.inputs = []
    def invoke(self, messages):
        self.inputs.append(list(messages))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply
def tool_reply(*specs):
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": cid, "type": "tool_call"}
        for name, args, cid in specs])
def scenarios():
    calc = ("calculator", {"a": 123, "b": 456, "operation": "multiply"}, "c1")
    words = ("count_words", {"text": "Hoc AI rat vui"}, "w1")
    yield "A - no tool", [AIMessage(content="Xin chào!")], 5
    yield "B - one tool", [tool_reply(calc), AIMessage(content="123 x 456 = 56088.")], 5
    yield "C - two tools", [tool_reply(calc, words),
                           AIMessage(content="56088; 4 đơn vị cách trắng.")], 5
    yield "D - dependent tools", [tool_reply(words),
        tool_reply(("calculator", {"a": 4, "b": 25000, "operation": "multiply"}, "c2")),
        AIMessage(content="4 x 25000 = 100000.")], 5
    yield "E - max_steps", [tool_reply(words)], 1
    yield "F - tool error", [tool_reply(("calculator",
        {"a": 1, "b": 0, "operation": "divide"}, "e1")),
        AIMessage(content="Không thể chia cho 0.")], 5
def main():
    for title, replies, budget in scenarios():
        result = run_agent(ScriptedModel(replies), "Kiểm tra vòng lặp.", budget)
        print(f"{title}: status={result.status}; steps={result.steps}; tool_calls={result.tool_calls}")
        for event in result.trace:
            if event["event"] == "tool":
                print(f"  {event['name']}: {event['payload']}")
        print(f"  {result.answer}")
if __name__ == "__main__":
    main()
