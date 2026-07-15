import os
import sys
import unittest
from datetime import date

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.models.request_models import EmployeeTransfer, PCType
from app.utils.transfer_cycle_preprocessor import preprocess_transfer_cycles


class TestTransferCyclePreprocessing(unittest.TestCase):
    def _make_transfer(self, transfer_id, source, destination):
        return EmployeeTransfer(
            transfer_id=transfer_id,
            employee_id=f"EMP-{transfer_id}",
            name=f"Employee {transfer_id}",
            department="IT",
            source_plant_id=source,
            destination_plant_id=destination,
            required_pc_type=PCType.STANDARD,
            transfer_date=date(2026, 8, 1),
        )

    def test_detects_direct_mutual_swap(self):
        transfers = [
            self._make_transfer("TR-1", "Delhi", "Kolkata"),
            self._make_transfer("TR-2", "Kolkata", "Delhi"),
        ]

        active, resolved = preprocess_transfer_cycles(transfers)

        self.assertEqual(len(active), 0)
        self.assertEqual(len(resolved), 2)
        self.assertTrue(all(item["reason"] == "Mutual employee swap" for item in resolved))

    def test_detects_longer_transfer_cycle(self):
        transfers = [
            self._make_transfer("TR-1", "Delhi", "Kolkata"),
            self._make_transfer("TR-2", "Kolkata", "Pune"),
            self._make_transfer("TR-3", "Pune", "Delhi"),
        ]

        active, resolved = preprocess_transfer_cycles(transfers)

        self.assertEqual(len(active), 0)
        self.assertEqual(len(resolved), 3)
        self.assertTrue(all(item["reason"] == "Transfer cycle detected" for item in resolved))

    def test_leaves_non_cycle_transfers_active(self):
        transfers = [
            self._make_transfer("TR-1", "Delhi", "Kolkata"),
            self._make_transfer("TR-2", "Kolkata", "Delhi"),
            self._make_transfer("TR-3", "Delhi", "Pune"),
        ]

        active, resolved = preprocess_transfer_cycles(transfers)

        self.assertEqual([t.transfer_id for t in active], ["TR-3"])
        self.assertEqual([t.transfer_id for t in resolved], ["TR-1", "TR-2"])


if __name__ == "__main__":
    unittest.main()
