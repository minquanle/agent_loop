import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage

from loop_core import run_agent
from offline_demo import ScriptedModel, tool_reply


def words(cid="w1"):
    return ("count_words", {"text": "Hoc AI rat vui"}, cid)


class LoopTests(unittest.TestCase):
    def test_final_without_tool(self):
        result = run_agent(ScriptedModel([AIMessage(content="Chào!")]), "Chào")
        self.assertEqual((result.status, result.steps, result.tool_calls), ("final", 1, 0))

    def test_multi_tool_pairing_and_order(self):
        first = tool_reply(words(), ("calculator", {"a": 2, "b": 3, "operation": "add"}, "c1"))
        model = ScriptedModel([first, AIMessage(content="4 và 5")])
        result = run_agent(model, "Tính và đếm")
        history = model.inputs[1]
        self.assertIs(history[2], first)
        self.assertEqual([m.tool_call_id for m in history if isinstance(m, ToolMessage)], ["w1", "c1"])
        self.assertEqual(result.tool_calls, 2)

    def test_dependent_round_uses_previous_result(self):
        second = tool_reply(("calculator", {"a": 4, "b": 25000, "operation": "multiply"}, "c2"))
        model = ScriptedModel([tool_reply(words()), second, AIMessage(content="100000")])
        result = run_agent(model, "Đếm rồi nhân")
        self.assertIn('"count": 4', model.inputs[1][-1].content)
        self.assertEqual(result.steps, 3)

    def test_last_step_executes_tool_but_no_extra_model_call(self):
        model = ScriptedModel([tool_reply(words()), AIMessage(content="Không được gọi")])
        result = run_agent(model, "Đếm", 1)
        self.assertEqual((result.status, result.steps, result.tool_calls), ("max_steps", 1, 1))
        self.assertEqual(len(model.inputs), 1)
        self.assertIsInstance(result.messages[-1], ToolMessage)

    def test_tool_errors_are_returned_to_model(self):
        cases = [("missing", {}, "u1"), ("calculator", {"a": 1, "b": 0, "operation": "divide"}, "d1"),
                 ("calculator", {"a": 1}, "v1"), ("count_words", {"text": "a" * 4001}, "l1")]
        for call in cases:
            with self.subTest(call=call[0]):
                model = ScriptedModel([tool_reply(call), AIMessage(content="Có lỗi tool")])
                result = run_agent(model, "Thử")
                self.assertEqual(result.status, "final")
                self.assertEqual(model.inputs[1][-1].status, "error")

    def test_invalid_id_stops_before_any_tool(self):
        with patch("loop_core.execute_call") as execute:
            result = run_agent(ScriptedModel([tool_reply(words(""))]), "Thử")
            self.assertEqual(result.status, "protocol_error")
            execute.assert_not_called()

    def test_reused_id_stops_on_next_round(self):
        result = run_agent(ScriptedModel([tool_reply(words()), tool_reply(words())]), "Thử")
        self.assertEqual((result.status, result.tool_calls), ("protocol_error", 1))

    def test_oversized_batch_runs_no_tool_and_pairs_all_results(self):
        model = ScriptedModel([tool_reply(*(words(f"w{i}") for i in range(5))), AIMessage(content="Dừng")])
        with patch("loop_core.execute_call") as execute:
            result = run_agent(model, "Thử")
            execute.assert_not_called()
        self.assertEqual(result.tool_calls, 0)
        self.assertEqual(len([m for m in model.inputs[1] if isinstance(m, ToolMessage)]), 5)

    def test_model_error_counts_attempt(self):
        result = run_agent(ScriptedModel([RuntimeError("secret details")]), "Thử")
        self.assertEqual((result.status, result.steps), ("model_error", 1))
        self.assertNotIn("secret details", str(result.trace))

    def test_empty_and_invalid_tool_response(self):
        for reply, expected in [(AIMessage(content=""), "empty_response"),
            (AIMessage(content="", invalid_tool_calls=[{"name": "calculator", "args": "bad json", "id": "x", "error": "bad"}]), "protocol_error")]:
            self.assertEqual(run_agent(ScriptedModel([reply]), "Thử").status, expected)

    def test_budget_and_question_validation(self):
        for budget in (0, -1, 21, True, 1.5):
            with self.assertRaises(ValueError):
                run_agent(None, "Thử", budget)
        for question in ("", "  ", "a" * 4001):
            with self.assertRaises(ValueError):
                run_agent(None, question)
        for limit in (0, -1, 9, True, 1.5):
            with self.assertRaises(ValueError):
                run_agent(None, "Thử", max_calls_per_step=limit)


    def test_duplicate_ids_within_batch(self):
        with patch("loop_core.execute_call") as execute:
            result = run_agent(ScriptedModel([tool_reply(words(), words())]), "Thử")
            self.assertEqual(result.status, "protocol_error")
            self.assertEqual(result.tool_calls, 0)
            execute.assert_not_called()

    def test_changing_requests_stop_at_budget(self):
        replies = [tool_reply(("count_words", {"text": f"input {i}"}, f"w{i}")) for i in range(5)]
        replies.append(AIMessage(content="Không được gọi bước 6"))
        model = ScriptedModel(replies)
        result = run_agent(model, "Thử", max_steps=5)
        self.assertEqual((result.status, result.steps, result.tool_calls),
                         ("max_steps", 5, 5))
        self.assertEqual(len(model.inputs), 5)

    def test_final_at_exact_budget(self):
        model = ScriptedModel([tool_reply(words()), AIMessage(content="4")])
        result = run_agent(model, "Đếm", max_steps=2)
        self.assertEqual((result.status, result.steps), ("final", 2))

    def test_invalid_arguments_can_be_corrected(self):
        bad = ("calculator", {"a": 1, "b": 0, "operation": "divide"}, "c1")
        good = ("calculator", {"a": 1, "b": 2, "operation": "divide"}, "c2")
        model = ScriptedModel([tool_reply(bad), tool_reply(good),
                               AIMessage(content="1 / 2 = 0.5")])
        result = run_agent(model, "Thử")
        self.assertEqual((result.status, result.steps), ("final", 3))
        self.assertEqual(model.inputs[1][-1].status, "error")
        self.assertIn('"value": 0.5', model.inputs[2][-1].content)

    def test_unexpected_tool_error_is_sanitized(self):
        from unittest.mock import Mock
        broken = Mock()
        broken.invoke.side_effect = RuntimeError("sensitive tool details")
        with patch.dict("loop_core.TOOL_MAP", {"count_words": broken}):
            result = run_agent(ScriptedModel([tool_reply(words())]), "Thử", 1)
        self.assertIn('"tool_error"', result.messages[-1].content)
        self.assertNotIn("sensitive tool details", str(result.trace))

    def test_calculator_rejects_nonfinite_input_and_overflow(self):
        from loop_core import execute_call
        for a, b in ((float("inf"), 1), (float("nan"), 1), (1e308, 1e308)):
            call = {"name": "calculator", "args": {"a": a, "b": b, "operation": "multiply"}}
            self.assertEqual(execute_call(call),
                             {"ok": False, "error": "invalid_arguments"})

    def test_non_ai_response_is_protocol_error(self):
        result = run_agent(ScriptedModel(["Wrong response type"]), "Thử")
        self.assertEqual((result.status, result.tool_calls), ("protocol_error", 0))

    def test_text_with_tool_calls_is_not_final(self):
        first = tool_reply(words())
        first.content = "Tôi sẽ dùng công cụ."
        result = run_agent(ScriptedModel([first]), "Đếm", 1)
        self.assertEqual((result.status, result.tool_calls), ("max_steps", 1))

    def test_text_content_blocks_can_be_final(self):
        reply = AIMessage(content=[{"type": "text", "text": "Xin chào!"}])
        result = run_agent(ScriptedModel([reply]), "Chào")
        self.assertEqual((result.status, result.answer), ("final", "Xin chào!"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
