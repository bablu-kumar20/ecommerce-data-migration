import unittest
from types import SimpleNamespace

from google.adk.models import LlmRequest
from google.genai import types

from python.src.agents.ecommerce_data_agent import agent_callbacks


def _request(message: str) -> LlmRequest:
    return LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text=message)],
            )
        ]
    )


class AgentCallbacksTests(unittest.TestCase):
    def tearDown(self):
        agent_callbacks._MODEL_CALL_STARTS.clear()

    def test_general_knowledge_question_is_blocked_before_model_call(self):
        callback_context = SimpleNamespace(invocation_id="blocked-request")

        response = agent_callbacks.enforce_data_scope(
            callback_context,
            _request("Who is the prime minister of India?"),
        )

        self.assertIsNotNone(response)
        self.assertEqual(
            response.content.parts[0].text,
            agent_callbacks.OUT_OF_SCOPE_MESSAGE,
        )
        self.assertNotIn(
            callback_context.invocation_id,
            agent_callbacks._MODEL_CALL_STARTS,
        )

    def test_ecommerce_question_is_allowed_to_reach_model(self):
        callback_context = SimpleNamespace(invocation_id="data-request")

        response = agent_callbacks.enforce_data_scope(
            callback_context,
            _request("Show the top five products by revenue."),
        )

        self.assertIsNone(response)
        self.assertIn(
            callback_context.invocation_id,
            agent_callbacks._MODEL_CALL_STARTS,
        )

    def test_unrelated_coding_question_is_out_of_scope(self):
        self.assertFalse(
            agent_callbacks.is_ecommerce_data_question(
                "Write a Python program that sorts a list."
            )
        )


if __name__ == "__main__":
    unittest.main()
