import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from python.src.agent_tools import remediation_tools


class RemediationToolsTests(unittest.TestCase):
    def test_proposal_requires_approval_before_script_is_available(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store_path = Path(temporary_directory) / "proposals.json"
            with patch.object(
                remediation_tools,
                "PROPOSAL_STORE_PATH",
                store_path,
            ):
                created = remediation_tools.create_remediation_proposal(
                    source_table="products",
                    record_id="P100",
                    field_name="price",
                    proposed_value="49.99",
                    reason="Silver flagged the existing price as invalid.",
                )
                proposal_id = created["proposal"]["proposal_id"]

                before_approval = (
                    remediation_tools.get_approved_remediation_script(proposal_id)
                )
                missing_confirmation = (
                    remediation_tools.approve_remediation_proposal(
                        proposal_id,
                        approved_by="trainer",
                        confirmation=False,
                    )
                )
                approved = remediation_tools.approve_remediation_proposal(
                    proposal_id,
                    approved_by="trainer",
                    confirmation=True,
                )
                script = remediation_tools.get_approved_remediation_script(
                    proposal_id
                )

        self.assertEqual(created["status"], "success")
        self.assertEqual(before_approval["status"], "error")
        self.assertEqual(missing_confirmation["status"], "error")
        self.assertEqual(approved["proposal"]["status"], "approved")
        self.assertEqual(script["execution"], "manual_only")
        self.assertEqual(
            script["sql"],
            "UPDATE products SET price = %s WHERE product_id = %s;",
        )
        self.assertEqual(script["parameters"], ["49.99", "P100"])

    def test_non_allowlisted_field_is_rejected(self):
        result = remediation_tools.create_remediation_proposal(
            source_table="products",
            record_id="P100",
            field_name="admin_password",
            proposed_value="secret",
            reason="Not a valid data-quality correction.",
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("not allowlisted", result["message"])


if __name__ == "__main__":
    unittest.main()
