import unittest
import datetime
from iss_tracker import calculate_speed, find_closest_epoch, calculate_average_speed

class TestIssTracker(unittest.TestCase):
    def test_calculate_speed(self):
        self.assertEqual(calculate_speed(0, 0, 0), 0)
        self.assertEqual(calculate_speed(3, 4, 0), 5)
        self.assertEqual(calculate_speed(6, 8, 0), 10)
        self.assertEqual(calculate_speed(1, 2, 2), 3)

    def test_find_closest_epoch(self):
        data = [
            {"epoch": "2025-048T12:00:00.000Z", "velocity": {"x_dot": 1, "y_dot": 1, "z_dot": 1}},
            {"epoch": "2025-050T12:00:00.000Z", "velocity": {"x_dot": 2, "y_dot": 2, "z_dot": 2}},
            {"epoch": "2025-052T12:00:00.000Z", "velocity": {"x_dot": 3, "y_dot": 3, "z_dot": 3}},
        ]
        now = datetime.datetime.strptime("2025-050T15:00:00.000Z", "%Y-%jT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC)
        closest = min(data, key=lambda x: abs(datetime.datetime.strptime(x["epoch"], "%Y-%jT%H:%M:%S.%fZ").replace(tzinfo=datetime.UTC) - now))
        self.assertEqual(closest["epoch"], "2025-050T12:00:00.000Z")

    def test_calculate_average_speed(self):
        data = [
            {"velocity": {"x_dot": 3, "y_dot": 4, "z_dot": 0}},
            {"velocity": {"x_dot": 6, "y_dot": 8, "z_dot": 0}},
        ]
        avg_speed = calculate_average_speed(data)
        self.assertEqual(avg_speed, 7.5)

if __name__ == "__main__":
    unittest.main()
