import os
import sys
import unittest

from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import app


class TestBackendRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "healthy")

    def test_optimize_endpoint_accepts_transfer_only_payload(self):
        payload = {
            "transfers": [
                {
                    "employee_id": "EMP-1",
                    "employee_name": "Alice",
                    "from_location": "New York",
                    "to_location": "New York",
                }
            ]
        }

        response = self.client.post("/optimize", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "OPTIMAL")
        self.assertIn("two_way_swaps", body)
        self.assertIn("three_way_swaps", body)
        self.assertIn("surplus_transfers", body)
        self.assertIn("unresolved_transfers", body)
        self.assertIn("total_shipments_saved", body)

    def test_optimize_endpoint_accepts_missing_employee_id(self):
        payload = {
            "transfers": [
                {
                    "employee_name": "Alice",
                    "from_location": "New York",
                    "to_location": "Chicago",
                }
            ]
        }

        response = self.client.post("/optimize", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "OPTIMAL")
        self.assertEqual(body["unresolved_transfers"][0]["employee_id"], "unnamed-0")
        self.assertEqual(body["unresolved_transfers"][0]["employee_name"], "Alice")

    def test_two_way_swap_is_resolved_without_shipments(self):
        payload = {
            "transfers": [
                {
                    "employee_id": "EMP-1",
                    "employee_name": "Alice",
                    "from_location": "New York",
                    "to_location": "Chicago",
                },
                {
                    "employee_id": "EMP-2",
                    "employee_name": "Bob",
                    "from_location": "Chicago",
                    "to_location": "New York",
                },
            ]
        }

        response = self.client.post("/optimize", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "OPTIMAL")
        self.assertEqual(len(body["two_way_swaps"]), 1)
        self.assertEqual(body["total_shipments_saved"], 2)
        self.assertEqual(body["surplus_transfers"], [])

    def test_docs_endpoint_is_available(self):
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
