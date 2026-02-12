"""
Custom load shape classes for enterprise testing scenarios.

These shapes are selectable from the Locust Web UI when using --class-picker.
Each shape defines a time-based user ramp profile.

See: https://docs.locust.io/en/stable/custom-load-shape.html
"""

from locust import LoadTestShape


class EnterpriseRampShape(LoadTestShape):
    """
    Staged enterprise ramp-up simulating a workday traffic pattern.

    Stages:
      0-2 min:   Ramp 0 → 50 users   (morning login wave)
      2-5 min:   Hold at 50           (steady state — light)
      5-8 min:   Ramp 50 → 200        (peak hours)
      8-15 min:  Hold at 200          (sustained peak)
      15-18 min: Ramp 200 → 100       (afternoon drop-off)
      18-20 min: Hold at 100          (steady state)
      20+ min:   Ramp down to 0       (end of day)

    Total duration: ~22 minutes
    """

    stages = [
        {"duration": 120,  "users": 50,  "spawn_rate": 1},    # 0-2 min
        {"duration": 300,  "users": 50,  "spawn_rate": 1},    # 2-5 min
        {"duration": 480,  "users": 200, "spawn_rate": 5},    # 5-8 min
        {"duration": 900,  "users": 200, "spawn_rate": 5},    # 8-15 min
        {"duration": 1080, "users": 100, "spawn_rate": 3},    # 15-18 min
        {"duration": 1200, "users": 100, "spawn_rate": 3},    # 18-20 min
        {"duration": 1320, "users": 0,   "spawn_rate": 5},    # 20-22 min
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None  # Test complete


class SpikeTestShape(LoadTestShape):
    """
    Spike test — sudden traffic burst to test system resilience.

    Pattern:
      0-1 min:   Baseline 20 users
      1-1.5 min: SPIKE to 300 users (instant burst)
      1.5-3 min: Hold spike at 300
      3-4 min:   Drop back to 20
      4-5 min:   Recovery at 20
      5-5.5 min: Second SPIKE to 500
      5.5-7 min: Hold at 500
      7-8 min:   Ramp down to 0

    Total duration: ~8 minutes
    """

    stages = [
        {"duration": 60,   "users": 20,  "spawn_rate": 5},
        {"duration": 90,   "users": 300, "spawn_rate": 100},  # SPIKE
        {"duration": 180,  "users": 300, "spawn_rate": 100},
        {"duration": 240,  "users": 20,  "spawn_rate": 50},   # Drop
        {"duration": 300,  "users": 20,  "spawn_rate": 5},
        {"duration": 330,  "users": 500, "spawn_rate": 150},  # SPIKE 2
        {"duration": 420,  "users": 500, "spawn_rate": 150},
        {"duration": 480,  "users": 0,   "spawn_rate": 50},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None


class SoakTestShape(LoadTestShape):
    """
    Soak test — sustained moderate load over a long period.

    Ramps to 100 users over 5 minutes, holds for 55 minutes,
    then ramps down. Tests for memory leaks, connection exhaustion,
    and degradation over time.

    Total duration: ~65 minutes
    """

    stages = [
        {"duration": 300,  "users": 100, "spawn_rate": 1},    # 0-5 min: ramp
        {"duration": 3600, "users": 100, "spawn_rate": 1},    # 5-60 min: soak
        {"duration": 3900, "users": 0,   "spawn_rate": 5},    # 60-65 min: drain
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None
