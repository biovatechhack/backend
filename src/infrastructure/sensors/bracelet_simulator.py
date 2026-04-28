from dataclasses import dataclass
from datetime import datetime
import random
from domain.entities.sensor_reading import SensorReading

@dataclass
class BraceletReading:
    glucose_mg_dl: float
    heart_rate_bpm: int
    spo2_pct: int
    steps_today: int
    sleep_hours: float

class BraceletSimulator:
    """Simulates real-time bracelet data (as per your description)"""

    @staticmethod
    def get_current_reading(patient_id: str) -> BraceletReading:
        """Return realistic simulated sensor data"""
        # Base values with small random variation
        glucose = round(110 + random.gauss(0, 30), 1)          # normal range with variance
        hr = int(75 + random.gauss(0, 12))
        spo2 = int(97 + random.gauss(0, 2))
        steps = random.randint(800, 12000)
        sleep = round(random.uniform(5.5, 8.5), 1)

        # Simulate risk correlation (for testing HIGH cases)
        if random.random() < 0.15:   # 15% chance of critical reading
            glucose = round(random.choice([45.0, 320.0]), 1)   # hypo or hyper
            hr = 125 if glucose < 70 else 105

        return BraceletReading(
            glucose_mg_dl=glucose,
            heart_rate_bpm=hr,
            spo2_pct=spo2,
            steps_today=steps,
            sleep_hours=sleep
        )

    @staticmethod
    def to_sensor_reading(patient_id: str, reading: BraceletReading) -> SensorReading:
        return SensorReading(
            patient_id=patient_id,
            recorded_at=datetime.utcnow(),
            glucose_mg_dl=reading.glucose_mg_dl,
            heart_rate_bpm=reading.heart_rate_bpm,
            spo2_pct=reading.spo2_pct,
            steps_today=reading.steps_today,
            sleep_hours=reading.sleep_hours,
        )