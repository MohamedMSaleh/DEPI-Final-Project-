#!/usr/bin/env python3
"""
sensor_generator.py
Real-time IoT Data Pipeline -- Sensor Data Generator

Project: DEPI Final Project
Team: Data Rangers
Members:
- Mustafa Elsebaey Mohamed
- Mohamed Mahmoud Saleh
- Yossef Mohamed Abdelhady
- Anas Ahmed Taha
- Nermeen Ayman Mosbah
- Farah Ayman Ahmed

Description:
This script simulates REALISTIC IoT sensor data for temperature, humidity, CO2, and other weather metrics
specific to Egyptian climate patterns. The data is suitable for machine learning weather prediction models.

Features:
- Emits realistic, geographically accurate sensor readings for Egyptian cities
- Supports multiple output formats and destinations (JSONL, CSV, Azure Event Hubs)
- Maintains temporal continuity with smooth transitions between readings
- Simulates realistic daily temperature cycles and weather patterns
- Configurable via command-line arguments for flexible operation
- Structured logging for monitoring and debugging

Usage:
    # Run with default settings (writes to local 'output' folder)
    python sensor_generator.py --num-sensors 10 --duration 60

    # Run and send data to Azure Event Hubs
    python sensor_generator.py --event-hubs-conn-str "YOUR_CONN_STR" --event-hub-name "your_hub"

Install required libraries:
    pip install azure-eventhub
"""

from __future__ import annotations
import argparse
import csv
import json
import logging
import math
import os
import random
import signal
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional Azure Event Hubs import
try:
    from azure.eventhub import EventData, EventHubProducerClient
    EVENT_HUBS_AVAILABLE = True
except ImportError:
    EVENT_HUBS_AVAILABLE = False

# ---------------------------
# Configuration dataclasses
# ---------------------------
@dataclass
class SensorSpec:
    """Defines the static properties of a single sensor."""
    sensor_id: str
    sensor_type: str
    sensor_model: str
    manufacturer: str
    firmware_version: str
    city: str
    region: str
    country: str
    lat: float
    lon: float
    altitude: float

@dataclass
class AnomalyConfig:
    """Configuration for injecting anomalies into the data."""
    spike_rate: float
    stuck_rate: float
    dropout_rate: float
    max_spike_multiplier: float
    stuck_duration_mean_s: float

# ---------------------------
# Constants / Defaults
# ---------------------------
DEFAULT_INTERVAL = 5.0
DEFAULT_NUM_SENSORS = 20
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_JSONL_FILE = "sensor_data.jsonl"
DEFAULT_CSV_FILE = "sensor_data.csv"
DEFAULT_LOGFILE = "sensor_generator.log"

# Predefined locations for realistic sensor placement with realistic climate data for Egypt
# Note: Egyptian cities have hot desert climate with significant temperature variations
LOCATIONS = [
    {
        "city": "Cairo", "region": "Greater Cairo", "country": "Egypt",
        "lat": 30.0444, "lon": 31.2357, "alt": 23,
        "avg_temp_day": 28.0, "avg_temp_night": 18.0,  # Moderate temperatures
        "temp_variation": 3.0, "humidity_avg": 55.0
    },
    {
        "city": "Alexandria", "region": "Alexandria", "country": "Egypt",
        "lat": 31.2001, "lon": 29.9187, "alt": 5,
        "avg_temp_day": 26.0, "avg_temp_night": 20.0,  # Coastal, more moderate
        "temp_variation": 2.5, "humidity_avg": 68.0    # Higher humidity (coastal)
    },
    {
        "city": "Giza", "region": "Giza", "country": "Egypt",
        "lat": 29.9753, "lon": 31.1376, "alt": 19,
        "avg_temp_day": 29.0, "avg_temp_night": 19.0,  # Similar to Cairo
        "temp_variation": 3.0, "humidity_avg": 50.0
    },
    {
        "city": "Luxor", "region": "Luxor", "country": "Egypt",
        "lat": 25.6872, "lon": 32.6396, "alt": 76,
        "avg_temp_day": 35.0, "avg_temp_night": 22.0,  # HOT - Southern Egypt!
        "temp_variation": 4.0, "humidity_avg": 35.0    # Lower humidity (desert)
    },
    {
        "city": "Aswan", "region": "Aswan", "country": "Egypt",
        "lat": 24.0889, "lon": 32.8998, "alt": 85,
        "avg_temp_day": 38.0, "avg_temp_night": 24.0,  # HOTTEST - Far South!
        "temp_variation": 5.0, "humidity_avg": 30.0    # Very low humidity (desert)
    },
]

# ---------------------------
# Utility functions
# ---------------------------
def now_iso_local() -> str:
    """Return a timezone-aware ISO8601 string for the current time."""
    return datetime.now(timezone.utc).astimezone().isoformat()

def seed_random(seed: Optional[int]) -> None:
    """Seed the random number generator for reproducibility."""
    if seed is not None:
        random.seed(seed)

# ---------------------------
# Sensor Value Generation with REALISTIC patterns
# ---------------------------
def get_time_of_day_factor(ts: datetime) -> float:
    """
    Calculate time-of-day factor (0 to 1) for temperature variation.
    0 = coldest (sunrise ~5 AM)
    1 = warmest (afternoon ~2-3 PM)
    Returns a value between 0 and 1 based on hour of day
    """
    hour = ts.hour + ts.minute / 60.0
    
    # Temperature cycle: coldest at 5 AM, warmest at 14:00 (2 PM)
    # Using a sinusoidal function shifted appropriately
    coldest_hour = 5.0
    warmest_hour = 14.0
    
    # Calculate angle for smooth temperature cycle
    hours_since_coldest = (hour - coldest_hour) % 24
    
    # Temperature increases from coldest to warmest, then decreases
    if hours_since_coldest <= (warmest_hour - coldest_hour):
        # Warming phase (5 AM to 2 PM) - 9 hours
        factor = hours_since_coldest / (warmest_hour - coldest_hour)
    else:
        # Cooling phase (2 PM to 5 AM next day) - 15 hours
        hours_to_coldest = 24 - hours_since_coldest
        factor = hours_to_coldest / (24 - (warmest_hour - coldest_hour))
    
    # Apply smoothing with sine function for more natural curve
    return 0.5 * (1 + math.sin(math.pi * (factor - 0.5)))

def generate_weather_reading(
    sensor: SensorSpec, 
    ts: datetime, 
    location_data: Dict,
    prev_values: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Generate a REALISTIC composite weather reading for a sensor at a given time.
    
    Key improvements:
    - Uses actual Egyptian climate data per city
    - Smooth transitions between readings (no wild jumps)
    - Realistic daily temperature cycles
    - Proper humidity-temperature inverse correlation
    - Geographically accurate patterns (southern cities are hotter!)
    
    Args:
        sensor: The sensor specification
        ts: Current timestamp
        location_data: Climate data for the sensor's location
        prev_values: Previous reading values for smooth transitions
    
    Returns:
        Dictionary with realistic weather measurements
    """
    # Get time of day factor (0 = night, 1 = day peak)
    time_factor = get_time_of_day_factor(ts)
    
    # Calculate base temperature using location-specific data
    temp_range = location_data["avg_temp_day"] - location_data["avg_temp_night"]
    base_temp = location_data["avg_temp_night"] + (temp_range * time_factor)
    
    # Add small random variation (weather changes gradually!)
    if prev_values:
        # Smooth transition: new value close to previous value
        temp_delta = random.gauss(0, 0.15)  # Very small change per reading
        temperature = prev_values.get("temperature", base_temp) + temp_delta
        # Slowly drift toward the expected base temperature
        temperature = temperature * 0.9 + base_temp * 0.1
    else:
        # First reading: use base with small variation
        temperature = base_temp + random.gauss(0, location_data["temp_variation"] * 0.3)
    
    # Ensure temperature stays within realistic bounds
    min_temp = location_data["avg_temp_night"] - 5
    max_temp = location_data["avg_temp_day"] + 8
    temperature = max(min_temp, min(max_temp, temperature))
    temperature = round(temperature, 2)
    
    # Humidity: inversely related to temperature + location average
    # Hot afternoon = low humidity, cool night = higher humidity
    base_humidity = location_data["humidity_avg"]
    temp_diff = temperature - location_data["avg_temp_night"]
    humidity_delta = -1.0 * temp_diff  # Decrease 1% humidity per degree increase
    
    if prev_values:
        # Smooth humidity transition
        humidity = prev_values.get("humidity", base_humidity) + random.gauss(0, 0.8)
        target_humidity = base_humidity + humidity_delta
        humidity = humidity * 0.85 + target_humidity * 0.15
    else:
        humidity = base_humidity + humidity_delta + random.gauss(0, 3.0)
    
    # Bound humidity to realistic range
    humidity = max(20.0, min(85.0, humidity))
    humidity = round(humidity, 2)
    
    # Atmospheric pressure: realistic for Egypt with small daily variation
    base_pressure = 1013.0 - (location_data["alt"] / 10.0)  # Altitude effect
    if prev_values:
        pressure = prev_values.get("pressure", base_pressure) + random.gauss(0, 0.2)
        pressure = pressure * 0.95 + base_pressure * 0.05
    else:
        pressure = base_pressure + random.gauss(0, 1.5)
    
    pressure = round(max(1005.0, min(1020.0, pressure)), 2)
    
    # Wind speed: varies by time of day (calmer at night)
    base_wind = 8.0 + 7.0 * time_factor  # 8-15 km/h range
    if prev_values:
        wind_speed = prev_values.get("wind_speed", base_wind) + random.gauss(0, 0.5)
        wind_speed = wind_speed * 0.85 + base_wind * 0.15
    else:
        wind_speed = base_wind + random.gauss(0, 2.0)
    
    wind_speed = round(max(0.0, min(25.0, wind_speed)), 2)
    
    # Wind direction: changes slowly
    wind_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    if prev_values and "wind_direction" in prev_values:
        # 80% chance to keep same direction, 20% to shift
        if random.random() < 0.8:
            wind_direction = prev_values["wind_direction"]
        else:
            current_idx = wind_directions.index(prev_values["wind_direction"])
            # Shift by one position (clockwise or counterclockwise)
            shift = random.choice([-1, 1])
            wind_direction = wind_directions[(current_idx + shift) % len(wind_directions)]
    else:
        wind_direction = random.choice(wind_directions)
    
    # Rainfall: rare in Egypt (5% chance of any rain)
    if random.random() < 0.05:
        rainfall = round(random.uniform(0.1, 2.0), 2)  # Light rain only
    else:
        rainfall = 0.0
    
    return {
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "rainfall": rainfall,
    }

# ---------------------------
# File I/O
# ---------------------------
class OutputWriter:
    """Manages writing events to JSONL and flattened CSV files."""
    def __init__(self, outdir: Path, jsonl_name: str, csv_name: str, logger: logging.Logger):
        self.outdir = outdir
        self.jsonl_path = outdir / jsonl_name
        self.csv_path = outdir / csv_name
        self.logger = logger
        self.csv_writer = None
        self.jsonl_file = None
        self.csv_file = None

        outdir.mkdir(parents=True, exist_ok=True)
        self._open_files()

    def _open_files(self):
        """Open files and prepare CSV writer."""
        self.jsonl_file = open(self.jsonl_path, "a", encoding="utf-8")
        
        is_new_file = not self.csv_path.exists() or os.stat(self.csv_path).st_size == 0
        self.csv_file = open(self.csv_path, "a", newline="", encoding="utf-8")
        
        # Define the flattened CSV header based on the new JSON structure
        header = [
            "timestamp", "sensor_id", "sensor_type", "status", "seq", "is_simulated",
            "firmware_version", "sensor_model", "manufacturer", "signal_strength", "reading_quality", "event_type",
            "temperature", "humidity", "pressure", "wind_speed", "wind_direction", "rainfall", "unit",
            "city", "region", "country", "lat", "lon", "altitude"
        ]
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=header)
        
        if is_new_file:
            self.csv_writer.writeheader()
            self.csv_file.flush()

    def write(self, event: Dict):
        """Write event to JSONL and a flattened row to CSV."""
        # 1. Write to JSONL
        self.jsonl_file.write(json.dumps(event) + "\n")
        self.jsonl_file.flush()

        # 2. Flatten the event and write to CSV
        flat_row = {
            "timestamp": event["timestamp"],
            "sensor_id": event["sensor_id"],
            "sensor_type": event["sensor_type"],
            "status": event["status"],
            "seq": event["seq"],
            "is_simulated": event["is_simulated"],
            "firmware_version": event["firmware_version"],
            "sensor_model": event["sensor_model"],
            "manufacturer": event["manufacturer"],
            "signal_strength": event["signal_strength"],
            "reading_quality": event["reading_quality"],
            "event_type": event["event_type"],
            "temperature": event["value"]["temperature"],
            "humidity": event["value"]["humidity"],
            "pressure": event["value"]["pressure"],
            "wind_speed": event["value"]["wind_speed"],
            "wind_direction": event["value"]["wind_direction"],
            "rainfall": event["value"]["rainfall"],
            "unit": event["unit"],
            "city": event["metadata"]["city"],
            "region": event["metadata"]["region"],
            "country": event["metadata"]["country"],
            "lat": event["metadata"]["lat"],
            "lon": event["metadata"]["lon"],
            "altitude": event["metadata"]["altitude"],
        }
        self.csv_writer.writerow(flat_row)
        self.csv_file.flush()

    def close(self):
        """Close all open file handles."""
        if self.jsonl_file:
            self.jsonl_file.close()
        if self.csv_file:
            self.csv_file.close()

# ---------------------------
# Main Generator Logic
# ---------------------------
class SensorGenerator:
    """
    The main class for generating and emitting REALISTIC sensor data.
    It orchestrates sensor creation, data generation, anomaly injection, and publishing.
    """
    def __init__(
        self,
        sensors: List[SensorSpec],
        location_map: Dict[str, Dict],
        writer: Optional[OutputWriter] = None,
        interval_s: float = DEFAULT_INTERVAL,
        anomaly_cfg: Optional[AnomalyConfig] = None,
        event_hub_producer: Optional[EventHubProducerClient] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.sensors = sensors
        self.location_map = location_map
        self.writer = writer
        self.interval = interval_s
        self.anomaly_cfg = anomaly_cfg or AnomalyConfig(0.002, 0.001, 0.001, 1.5, 60.0)
        self.event_hub_producer = event_hub_producer
        self.logger = logger or logging.getLogger("sensor_gen")
        
        # State for maintaining continuity
        self._previous_values: Dict[str, Dict] = {}
        
        # State for anomalies
        self._stuck_until: Dict[str, float] = {}
        self._stuck_value: Dict[str, Dict] = {}
        
        self._seq = 0
        self._running = False

    def _inject_stuck_state(self, sensor_id: str, now_ts: float) -> bool:
        """Determine if a sensor should be in a 'stuck' state."""
        if sensor_id in self._stuck_until and now_ts < self._stuck_until[sensor_id]:
            return True  # Already stuck
        
        if random.random() < self.anomaly_cfg.stuck_rate / len(self.sensors):
            duration = random.expovariate(1.0 / self.anomaly_cfg.stuck_duration_mean_s)
            self._stuck_until[sensor_id] = now_ts + duration
            self.logger.info(f"Sensor {sensor_id} will be stuck for {duration:.1f}s.")
            return True
            
        self._stuck_until.pop(sensor_id, None)
        self._stuck_value.pop(sensor_id, None)
        return False

    def _get_spike_multiplier(self) -> Optional[float]:
        """Return a REALISTIC spike multiplier if a spike anomaly should occur."""
        if random.random() < self.anomaly_cfg.spike_rate:
            # Reduced spike range for realism (10-50% spike, not 300%)
            multiplier = 1.0 + random.uniform(0.1, 0.5)
            return random.choice([-1, 1]) * multiplier
        return None

    def _should_dropout(self) -> bool:
        """Determine if the current reading should be dropped."""
        return random.random() < self.anomaly_cfg.dropout_rate

    async def _publish_to_event_hubs(self, event: Dict):
        """Asynchronously send an event to Azure Event Hubs."""
        if not self.event_hub_producer:
            return
        try:
            event_data_batch = await self.event_hub_producer.create_batch()
            event_data_batch.add(EventData(json.dumps(event)))
            await self.event_hub_producer.send_batch(event_data_batch)
        except Exception as e:
            self.logger.error(f"Failed to send event to Azure Event Hubs: {e}")

    def start(self, duration_s: Optional[float] = None):
        """Start the generator loop."""
        self._running = True
        end_time = time.time() + duration_s if duration_s else None
        self.logger.info(
            f"Starting generator: {len(self.sensors)} sensors, "
            f"{self.interval:.1f}s interval, duration: {duration_s or 'unlimited'}s"
        )
        self.logger.info("Generating REALISTIC Egyptian weather data suitable for ML models...")

        try:
            while self._running:
                batch_start_time = time.time()
                if end_time and batch_start_time >= end_time:
                    self.logger.info("Specified duration reached. Stopping.")
                    break
                
                self._emit_batch()

                elapsed = time.time() - batch_start_time
                sleep_time = max(0, self.interval - elapsed)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            self.logger.info("Ctrl-C received. Shutting down gracefully.")
        finally:
            self.stop()

    def stop(self):
        """Stop the generator and clean up resources."""
        self._running = False
        self.logger.info("Stopping generator and closing resources.")
        if self.writer:
            self.writer.close()
        if self.event_hub_producer:
            self.event_hub_producer.close()

    def _emit_batch(self):
        """Generate and emit a batch of sensor readings."""
        now_dt = datetime.now(timezone.utc).astimezone()
        now_ts = time.time()

        for sensor in self.sensors:
            self._seq += 1
            
            if self._should_dropout():
                self.logger.debug(f"Dropping out reading for {sensor.sensor_id}")
                continue
            
            location_data = self.location_map[sensor.city]
            prev_values = self._previous_values.get(sensor.sensor_id)
            
            is_stuck = self._inject_stuck_state(sensor.sensor_id, now_ts)
            if is_stuck:
                if sensor.sensor_id not in self._stuck_value:
                    # First time it's stuck in this period, generate and store the value
                    self._stuck_value[sensor.sensor_id] = generate_weather_reading(
                        sensor, now_dt, location_data, prev_values
                    )
                value = self._stuck_value[sensor.sensor_id]
                status = "STUCK"
            else:
                value = generate_weather_reading(sensor, now_dt, location_data, prev_values)
                status = "OK"
                # Store for next iteration
                self._previous_values[sensor.sensor_id] = value.copy()

            # Inject REALISTIC spikes into non-stuck values
            spike_multiplier = self._get_spike_multiplier()
            if spike_multiplier and not is_stuck:
                # Apply spike to temperature (realistic range)
                original_temp = value["temperature"]
                if spike_multiplier < 0:
                    # Negative spike: 10-30% decrease
                    value["temperature"] = round(original_temp * (1 + spike_multiplier * 0.3), 2)
                else:
                    # Positive spike: 10-30% increase
                    value["temperature"] = round(original_temp * (1 + spike_multiplier * 0.3), 2)
                
                status = "SPIKE"
                self.logger.info(
                    f"Spike injected for {sensor.sensor_id}: "
                    f"temp changed from {original_temp}°C to {value['temperature']}°C"
                )

            # Construct the final event object according to the new schema
            event = {
                "timestamp": now_dt.isoformat(),
                "sensor_id": sensor.sensor_id,
                "sensor_type": sensor.sensor_type,
                "value": value,
                "unit": "C/%/hPa",
                "metadata": {
                    "city": sensor.city,
                    "region": sensor.region,
                    "country": sensor.country,
                    "lat": sensor.lat,
                    "lon": sensor.lon,
                    "altitude": sensor.altitude,
                },
                "status": status,
                "is_simulated": True,
                "seq": self._seq,
                "firmware_version": sensor.firmware_version,
                "sensor_model": sensor.sensor_model,
                "manufacturer": sensor.manufacturer,
                "signal_strength": round(random.uniform(-80, -50), 1),
                "reading_quality": round(random.uniform(0.90, 1.0), 3) if status == "OK" else round(random.uniform(0.60, 0.85), 3),
                "event_type": "measurement",
            }

            if self.writer:
                self.writer.write(event)
            
            if self.event_hub_producer:
                # This should be run in an async context if we were to use the async producer
                # For simplicity, we'll use the sync producer's send_batch method in a blocking way
                try:
                    with self.event_hub_producer:
                        batch = self.event_hub_producer.create_batch()
                        batch.add(EventData(json.dumps(event)))
                        self.event_hub_producer.send_batch(batch)
                except Exception as e:
                    self.logger.error(f"Error sending to Event Hub: {e}")

# ---------------------------
# Setup and CLI
# ---------------------------
def setup_logging(log_level: str, logfile: Optional[Path]) -> logging.Logger:
    """Configure logging to console and optionally to a file."""
    logger = logging.getLogger("sensor_gen")
    logger.setLevel(log_level.upper())
    
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
        
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        if logfile:
            fh = RotatingFileHandler(logfile, maxBytes=5*1024*1024, backupCount=3)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
            
    return logger

def build_sensors(num_sensors: int) -> Tuple[List[SensorSpec], Dict[str, Dict]]:
    """Create a list of sensor specifications and location mapping."""
    sensors = []
    location_map = {loc["city"]: loc for loc in LOCATIONS}
    
    for i in range(num_sensors):
        loc = LOCATIONS[i % len(LOCATIONS)]
        sensor_id = f"ws_{loc['city'].lower()}_{i+1:03d}"
        sensors.append(SensorSpec(
            sensor_id=sensor_id,
            sensor_type="weather_station",
            sensor_model=random.choice(["WST-5000", "WST-5001", "Atmo-Tracker-Pro"]),
            manufacturer=random.choice(["AcmeWeather", "GlobalSensors", "AtmoCorp"]),
            firmware_version=random.choice(["v2.0.1", "v2.1.0", "v2.1.1"]),
            city=loc["city"],
            region=loc["region"],
            country=loc["country"],
            lat=round(loc["lat"] + random.uniform(-0.05, 0.05), 6),
            lon=round(loc["lon"] + random.uniform(-0.05, 0.05), 6),
            altitude=loc["alt"]
        ))
    return sensors, location_map

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="IoT Sensor Data Generator for the DEPI Project - Generates REALISTIC Egyptian weather data.")
    
    # General settings
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Interval in seconds between readings.")
    parser.add_argument("--num-sensors", type=int, default=DEFAULT_NUM_SENSORS, help="Number of sensors to simulate.")
    parser.add_argument("--duration", type=float, default=None, help="Run duration in seconds (default: runs indefinitely).")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")
    
    # Output settings
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory for local file outputs.")
    parser.add_argument("--jsonl-file", type=str, default=DEFAULT_JSONL_FILE, help="Name of the JSONL output file.")
    parser.add_argument("--csv-file", type=str, default=DEFAULT_CSV_FILE, help="Name of the CSV output file.")
    parser.add_argument("--logfile", type=str, default=DEFAULT_LOGFILE, help="Path for the generator's log file.")
    
    # Azure Event Hubs settings
    parser.add_argument("--event-hubs-conn-str", type=str, default=None, help="Azure Event Hubs connection string.")
    parser.add_argument("--event-hub-name", type=str, default=None, help="Name of the Azure Event Hub.")
    
    # Anomaly settings
    parser.add_argument("--anomaly-spike-rate", type=float, default=0.002, help="Rate of spike anomalies (reduced for realism).")
    parser.add_argument("--anomaly-stuck-rate", type=float, default=0.001, help="Rate of stuck sensor anomalies.")
    parser.add_argument("--anomaly-dropout-rate", type=float, default=0.001, help="Rate of dropped readings.")

    return parser.parse_args()

def main():
    """Main entry point of the script."""
    args = parse_args()
    
    seed_random(args.seed)
    logger = setup_logging("INFO", Path(args.logfile) if args.logfile else None)

    # --- Configure Outputs ---
    writer = None
    event_hub_producer = None

    # Local file writer
    if not args.event_hubs_conn_str:
        logger.info(f"No Event Hubs connection string provided. Writing to local directory: {args.output_dir}")
        outdir = Path(args.output_dir)
        writer = OutputWriter(outdir, args.jsonl_file, args.csv_file, logger)
    
    # Azure Event Hubs producer
    elif args.event_hubs_conn_str and args.event_hub_name:
        if not EVENT_HUBS_AVAILABLE:
            logger.error("Azure Event Hubs arguments provided, but 'azure-eventhub' is not installed.")
            logger.error("Please install it: pip install azure-eventhub")
            sys.exit(1)
        try:
            event_hub_producer = EventHubProducerClient.from_connection_string(
                conn_str=args.event_hubs_conn_str,
                eventhub_name=args.event_hub_name
            )
            logger.info(f"Successfully connected to Azure Event Hub: {args.event_hub_name}")
        except Exception as e:
            logger.error(f"Failed to create Event Hub producer: {e}")
            sys.exit(1)
    else:
        logger.error("If using Event Hubs, both connection string and hub name must be provided.")
        sys.exit(1)

    # --- Create Sensors and Anomaly Config ---
    sensors, location_map = build_sensors(args.num_sensors)
    anomaly_cfg = AnomalyConfig(
        spike_rate=args.anomaly_spike_rate,
        stuck_rate=args.anomaly_stuck_rate,
        dropout_rate=args.anomaly_dropout_rate,
        max_spike_multiplier=1.5,  # Reduced for realism
        stuck_duration_mean_s=180.0
    )

    # --- Initialize and Run Generator ---
    generator = SensorGenerator(
        sensors=sensors,
        location_map=location_map,
        writer=writer,
        interval_s=args.interval,
        anomaly_cfg=anomaly_cfg,
        event_hub_producer=event_hub_producer,
        logger=logger
    )

    # Set up graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} received. Initiating shutdown...")
        generator.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    generator.start(duration_s=args.duration)
    
    logger.info("Generator has finished execution.")

if __name__ == "__main__":
    main()
