import os
import sys
import unittest

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.models.request_models import Transfer
from app.utils.solver import TransferResolutionSolver


class TestTransferResolutionSolver(unittest.TestCase):
    def test_aggregates_net_flow_into_a_single_shipment(self):
        transfers = [
            Transfer(employee_id="EMP-1", employee_name="Alice", from_location="A", to_location="B"),
            Transfer(employee_id="EMP-2", employee_name="Bob", from_location="B", to_location="C"),
        ]

        solver = TransferResolutionSolver(transfers)
        shipments = solver.solve()

        self.assertEqual(len(shipments), 1)
        self.assertEqual(shipments[0].from_location, "A")
        self.assertEqual(shipments[0].to_location, "C")
        self.assertEqual(shipments[0].quantity, 1)


if __name__ == "__main__":
    unittest.main()
