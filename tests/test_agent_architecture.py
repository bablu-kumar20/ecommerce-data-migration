import subprocess
import sys
import unittest
from pathlib import Path

from google.adk.evaluation.eval_set import EvalSet

from python.src.agents.ecommerce_data_agent.agent import root_agent
from python.src.agents.ecommerce_data_agent.sub_agents import remediation_agent


def _tool_name(tool):
    return getattr(tool, "name", getattr(tool, "__name__", ""))


class AgentArchitectureTests(unittest.TestCase):
    def test_root_has_expected_specialists(self):
        self.assertEqual(
            {agent.name for agent in root_agent.sub_agents},
            {
                "data_quality_agent",
                "pipeline_monitor_agent",
                "anomaly_forecast_agent",
                "remediation_agent",
            },
        )

    def test_root_has_advanced_business_tools(self):
        tool_names = {_tool_name(tool) for tool in root_agent.tools}
        self.assertIn("compare_sales_periods", tool_names)
        self.assertIn("get_top_products_for_date_range", tool_names)
        self.assertIn("get_top_customers_for_date_range", tool_names)
        self.assertIn("get_category_sales_for_date_range", tool_names)

    def test_remediation_agent_has_no_database_execution_tool(self):
        tool_names = {_tool_name(tool) for tool in remediation_agent.tools}
        self.assertIn("get_approved_remediation_script", tool_names)
        self.assertFalse(
            any(name.startswith(("execute_", "update_", "delete_")) for name in tool_names)
        )

    def test_official_eval_set_schema_and_case_count(self):
        path = Path(
            "python/src/agents/ecommerce_data_agent/"
            "advanced_behaviors.evalset.json"
        )
        eval_set = EvalSet.model_validate_json(path.read_text(encoding="utf-8"))

        self.assertEqual(eval_set.eval_set_id, "advanced_behaviors")
        self.assertEqual(len(eval_set.eval_cases), 7)

    def test_adk_style_package_import_does_not_attach_subagents_twice(self):
        command = (
            "import sys; "
            "sys.path.insert(0, r'python/src/agents'); "
            "from ecommerce_data_agent.agent import root_agent; "
            "print(root_agent.name)"
        )
        result = subprocess.run(
            [sys.executable, "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ecommerce_data_agent")


if __name__ == "__main__":
    unittest.main()
