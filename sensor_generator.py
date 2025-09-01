#!/usr/bin/env python3
"""
sensor_generator_pro.py
Professional IoT sensor data simulator for DEPI Graduation Project (Real-time IoT Pipeline).

Features:
- Emits synthetic readings for multiple sensors at a configurable interval (default 5s).
- JSONL + CSV outputs (keeps files open for efficient writes, flushes per write).
- Optional Kafka publishing (uses kafka-python if available).
- Realistic patterns: diurnal component, spatial correlation, Gaussian noise, drift.
- Controlled anomaly injection: spikes, stuck values, dropouts.
- Graceful shutdown, structured logging, command-line options, reproducible with seed.
- Lightweight dependencies by default (kafka-python only needed for Kafka mode).

Save & run:
    python sensor_generator_pro.py --interval 5 --num-sensors 50 --duration 3600

Install optional Kafka lib:
    pip install kafka-python

Author: Generated for you (DEPI project)
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
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Optional Kafka import (lazy)
try:
    from kafka import KafkaProducer  # type: ignore
    KAFKA_AVAILABLE = True
except Exception:
    KAFKA_AVAILABLE = False

# ---------------------------
# Configuration dataclasses
# ---------------------------
@dataclass
class SensorSpec:
    sensor_id: str
    sensor_type: str  # 'temperature' | 'humidity' | 'co2' etc
    unit: str
    lat: float
    lon: float
    location: str

@dataclass
class AnomalyConfig:
    spike_rate: float         # fraction of readings that are spikes
    stuck_rate: float         # fraction of sensors that get 'stuck' at a value for a duration
    dropout_rate: float       # fraction of readings dropped/missing
    max_spike_multiplier: float
    stuck_duration_mean_s: float # average seconds of stuck state

# ---------------------------
# Constants / Defaults
# ---------------------------
DEFAULT_INTERVAL = 5.0  # seconds between emission batches
DEFAULT_NUM_SENSORS = 50
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_JSONL = "sensor_data.jsonl"
DEFAULT_CSV = "sensor_data.csv"
DEFAULT_LOGFILE = "sensor_generator.log"

# ---------------------------
# Utility functions
# ---------------------------
def now_iso_local() -> str:
    """Return timezone-aware ISO8601 string (local tz if available)."""
    # .astimezone() will convert to local timezone
    return datetime.now(timezone.utc).astimezone().isoformat()

def seed_random(seed: Optional[int]) -> None:
    if seed is not None:
        random.seed(seed)
        # If using numpy in future, set that seed as well.

# ---------------------------
# Sensor value models
# ---------------------------
def diurnal_component(ts: datetime, amplitude: float = 3.0) -> float:
    """Return a diurnal periodic component (-amplitude..+amplitude)."""
    # minute of day -> angle
    minute = ts.hour * 60 + ts.minute + ts.second / 60.0
    angle = 2 * math.pi * (minute / (24 * 60))
    return amplitude * math.sin(angle)  # simple daily sine

def spatial_base(lat: float, lon: float) -> float:
    """Create a simple base temperature value from lat/lon to add spatial variation."""
    # Map lat/lon to deterministic base (not physically accurate, just variation)
    return 20.0 + (lat % 5) * 0.6 + (lon % 5) * 0.3

def generate_reading(sensor: SensorSpec, ts: datetime, drift: float) -> float:
    """Produce a synthetic sensor reading depending on type, time, and drift."""
    base = spatial_base(sensor.lat, sensor.lon)
    diurnal = diurnal_component(ts, amplitude=3.0)
    noise = random.gauss(0, 0.4)
    if sensor.sensor_type == "temperature":
        return round(base + diurnal + drift + noise, 3)
    if sensor.sensor_type == "humidity":
        # humidity around 35..70
        hum_base = 45.0 + (sensor.lat % 3) * 2.0
        return round(hum_base + diurnal * 0.6 + drift + random.gauss(0, 1.0), 3)
    if sensor.sensor_type == "co2":
        return round(400 + 20 * math.sin(ts.minute / 60.0 * 2*math.pi) + drift + random.gauss(0, 5.0), 3)
    # fallback
    return round(base + diurnal + drift + noise, 3)

# ---------------------------
# File writers
# ---------------------------
class OutputWriter:
    """Manages JSONL + CSV file handles and writing events efficiently."""
    def __init__(self, outdir: Path, jsonl_name: str, csv_name: str, logger: logging.Logger):
        self.outdir = outdir
        self.jsonl_path = outdir / jsonl_name
        self.csv_path = outdir / csv_name
        self.logger = logger
        outdir.mkdir(parents=True, exist_ok=True)
        # Open files in append mode and keep handles
        self.jsonl_f = open(self.jsonl_path, "a", encoding="utf-8")
        self.csv_f = open(self.csv_path, "a", newline="", encoding="utf-8")
        # Ensure CSV header exists
        if os.stat(self.csv_path).st_size == 0:
            self._write_csv_header()
        self.csv_writer = csv.writer(self.csv_f)

    def _write_csv_header(self):
        writer = csv.writer(self.csv_f)
        writer.writerow(["timestamp", "sensor_id", "sensor_type", "value", "unit", "lat", "lon", "location", "status", "seq"])
        self.csv_f.flush()

    def write(self, event: Dict):
        # JSONL
        self.jsonl_f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.jsonl_f.flush()
        # CSV row
        row = [
            event.get("timestamp"),
            event.get("sensor_id"),
            event.get("sensor_type"),
            event.get("value"),
            event.get("unit"),
            event.get("metadata", {}).get("lat"),
            event.get("metadata", {}).get("lon"),
            event.get("metadata", {}).get("location"),
            event.get("status"),
            event.get("seq")
        ]
        self.csv_writer.writerow(row)
        self.csv_f.flush()

    def close(self):
        try:
            self.jsonl_f.close()
        except Exception:
            pass
        try:
            self.csv_f.close()
        except Exception:
            pass

# ---------------------------
# Main Generator
# ---------------------------
class SensorGenerator:
    def __init__(
        self,
        sensors: List[SensorSpec],
        writer: OutputWriter,
        interval_s: float = DEFAULT_INTERVAL,
        anomaly_cfg: Optional[AnomalyConfig] = None,
        kafka_producer: Optional[KafkaProducer] = None,
        kafka_topic: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.sensors = sensors
        self.writer = writer
        self.interval = float(interval_s)
        self.anomaly_cfg = anomaly_cfg or AnomalyConfig(0.01, 0.005, 0.005, 3.0, 60.0)
        self.kafka_producer = kafka_producer
        self.kafka_topic = kafka_topic
        self.logger = logger or logging.getLogger("sensor_gen")
        # maintain per-sensor drift and stuck state
        self._drifts: Dict[str, float] = {s.sensor_id: random.uniform(-0.5, 0.5) for s in sensors}
        self._stuck_until: Dict[str, float] = {}  # sensor_id -> timestamp until stuck
        self._stuck_value: Dict[str, float] = {}
        self._seq = 0
        self._running = False

    def _maybe_inject_stuck(self, sensor_id: str, now_ts: float):
        # If currently stuck, keep it. Otherwise, maybe start a stuck period.
        if sensor_id in self._stuck_until and now_ts < self._stuck_until[sensor_id]:
            return True  # still stuck
        # start new stuck period?
        if random.random() < self.anomaly_cfg.stuck_rate:
            duration = max(1.0, random.expovariate(1.0 / self.anomaly_cfg.stuck_duration_mean_s))
            self._stuck_until[sensor_id] = now_ts + duration
            return True
        # not stuck
        self._stuck_until.pop(sensor_id, None)
        self._stuck_value.pop(sensor_id, None)
        return False

    def _maybe_spike(self, cfg: AnomalyConfig) -> Optional[float]:
        if random.random() < cfg.spike_rate:
            # spike multiplier between 1..max_spike_multiplier
            m = 1.0 + random.random() * (cfg.max_spike_multiplier - 1.0)
            # make it positive or negative
            sign = 1 if random.random() < 0.8 else -1
            return sign * m
        return None

    def _should_dropout(self, cfg: AnomalyConfig) -> bool:
        return random.random() < cfg.dropout_rate

    def _publish_kafka(self, event: Dict):
        if not self.kafka_producer or not self.kafka_topic:
            return
        try:
            payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
            self.kafka_producer.send(self.kafka_topic, payload)
            # optionally flush occasionally (left to kafka config)
        except Exception as e:
            self.logger.exception("Kafka publish error: %s", e)

    def start(self, duration_s: Optional[float] = None):
        """Start emitting data until duration expires (if provided) or until stopped."""
        self._running = True
        stopped_at = time.time() + duration_s if duration_s else None
        self.logger.info("Starting generator. Sensors=%d interval=%.2fs duration=%s", len(self.sensors), self.interval, duration_s)
        try:
            while self._running:
                batch_start = time.time()
                if stopped_at and time.time() >= stopped_at:
                    self.logger.info("Reached requested duration. Stopping.")
                    break
                self._emit_batch()
                # adaptive sleep to maintain roughly the configured interval between batches
                elapsed = time.time() - batch_start
                to_sleep = max(0.0, self.interval - elapsed)
                time.sleep(to_sleep)
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received. Stopping generator.")
        except Exception as e:
            self.logger.exception("Generator error: %s", e)
        finally:
            # flush and close writer and kafka producer
            self.logger.info("Shutting down writer and producer.")
            try:
                self.writer.close()
            except Exception:
                pass
            if self.kafka_producer:
                try:
                    self.kafka_producer.flush()
                    self.kafka_producer.close()
                except Exception:
                    pass

    def stop(self):
        self._running = False

    def _emit_batch(self):
        now_dt = datetime.now(timezone.utc).astimezone()
        now_ts = time.time()
        for s in self.sensors:
            self._seq += 1
            sensor_id = s.sensor_id

            # update drift slowly
            self._drifts[sensor_id] += random.gauss(0, 0.002)

            # Maybe simulate dropout
            if self._should_dropout(self.anomaly_cfg):
                # dropout: skip emitting this reading
                if random.random() < 0.5:
                    self.logger.debug("Dropout for sensor %s (simulated)", sensor_id)
                    continue

            # maybe stuck
            stuck = False
            if self._maybe_inject_stuck(sensor_id, now_ts):
                stuck = True
                if sensor_id not in self._stuck_value:
                    # pick the current reading as stuck baseline
                    val = generate_reading(s, now_dt, self._drifts[sensor_id])
                    self._stuck_value[sensor_id] = val
                    self.logger.info("Sensor %s entered stuck state at value %.3f", sensor_id, val)
                value = self._stuck_value[sensor_id]
            else:
                # normal reading
                value = generate_reading(s, now_dt, self._drifts[sensor_id])
                # possible spike
                spike_mult = self._maybe_spike(self.anomaly_cfg)
                if spike_mult is not None:
                    # apply relative spike e.g. +200%
                    old_value = value
                    value = round(value * spike_mult, 3) if abs(value) > 0.001 else round(value + spike_mult, 3)
                    self.logger.info("Spike injected on %s: %s -> %s", sensor_id, old_value, value)

            # build event
            event = {
                "timestamp": now_dt.isoformat(),
                "sensor_id": sensor_id,
                "sensor_type": s.sensor_type,
                "value": value,
                "unit": s.unit,
                "metadata": {"lat": s.lat, "lon": s.lon, "location": s.location},
                "status": "OK" if not stuck else "STUCK",
                "seq": self._seq
            }
            # write locally
            try:
                self.writer.write(event)
            except Exception:
                self.logger.exception("Failed to write event for %s", sensor_id)

            # publish to Kafka (if configured)
            if self.kafka_producer and self.kafka_topic:
                self._publish_kafka(event)

            # small intra-batch jitter so timestamps not identical across sensors
            time.sleep(random.uniform(0.01, 0.06))

# ---------------------------
# CLI / Setup
# ---------------------------
def setup_logging(log_level: str = "INFO", logfile: Optional[Path] = None) -> logging.Logger:
    logger = logging.getLogger("sensor_gen")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    # avoid duplicate handlers
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        if logfile is not None:
            fh = RotatingFileHandler(logfile, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger

def build_sensors_auto(num_sensors: int, center: Tuple[float, float] = (30.0, 31.0)) -> List[SensorSpec]:
    """Auto-generate num_sensors sensors around a center lat/lon."""
    sensors: List[SensorSpec] = []
    lat0, lon0 = center
    types = ["temperature", "humidity", "co2"]
    units = {"temperature": "°C", "humidity": "%", "co2": "ppm"}
    for i in range(num_sensors):
        # place sensors on a small grid / jitter
        jitter_lat = (i % 10) * 0.01 + random.uniform(-0.005, 0.005)
        jitter_lon = (i // 10) * 0.01 + random.uniform(-0.005, 0.005)
        lat = lat0 + jitter_lat
        lon = lon0 + jitter_lon
        s_type = types[i % len(types)]
        s_id = f"{s_type[:4]}_{i:03d}"
        loc = f"site/zone{(i//10)+1}"
        sensors.append(SensorSpec(sensor_id=s_id, sensor_type=s_type, unit=units[s_type], lat=lat, lon=lon, location=loc))
    return sensors

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Professional IoT sensor data generator (JSONL + CSV, optional Kafka).")
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Seconds between emission batches (default 5.0).")
    ap.add_argument("--num-sensors", type=int, default=DEFAULT_NUM_SENSORS, help="Number of sensors to generate (default 50).")
    ap.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory for JSONL/CSV logs.")
    ap.add_argument("--jsonl", type=str, default=DEFAULT_JSONL, help="JSONL filename (in output dir).")
    ap.add_argument("--csv", type=str, default=DEFAULT_CSV, help="CSV filename (in output dir).")
    ap.add_argument("--logfile", type=str, default=DEFAULT_LOGFILE, help="Optional rotating logfile path.")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducible runs.")
    ap.add_argument("--duration", type=float, default=None, help="Optional run duration in seconds (default: run until ctrl-c).")
    ap.add_argument("--anomaly-spike-rate", type=float, default=0.01, help="Fraction of readings that are spikes (default 0.01).")
    ap.add_argument("--anomaly-stuck-rate", type=float, default=0.002, help="Fraction of sensors that occasionally stuck (default 0.002).")
    ap.add_argument("--anomaly-dropout-rate", type=float, default=0.001, help="Fraction of readings dropped (default 0.001).")
    ap.add_argument("--kafka-bootstrap", type=str, default=None, help="Kafka bootstrap servers (e.g. localhost:9092). Optional.")
    ap.add_argument("--kafka-topic", type=str, default=None, help="Kafka topic to publish to (requires --kafka-bootstrap).")
    return ap.parse_args()

def main():
    args = parse_args()
    seed_random(args.seed)
    outdir = Path(args.output_dir)
    logfile = Path(args.logfile) if args.logfile else None
    logger = setup_logging(log_level="INFO", logfile=logfile)

    # create writer
    writer = OutputWriter(outdir, args.jsonl, args.csv, logger)

    # build sensors
    sensors = build_sensors_auto(args.num_sensors)

    # anomaly config
    anomaly_cfg = AnomalyConfig(
        spike_rate=args.anomaly_spike_rate,
        stuck_rate=args.anomaly_stuck_rate,
        dropout_rate=args.anomaly_dropout_rate,
        max_spike_multiplier=4.0,
        stuck_duration_mean_s=120.0
    )

    # optional Kafka setup
    kafka_producer = None
    if args.kafka_bootstrap:
        if not KAFKA_AVAILABLE:
            logger.error("Kafka bootstrap configured but kafka-python is not installed. Install with `pip install kafka-python`")
            sys.exit(2)
        try:
            kafka_producer = KafkaProducer(bootstrap_servers=args.kafka_bootstrap.split(","), linger_ms=5)
            logger.info("Kafka producer initialized for %s", args.kafka_bootstrap)
        except Exception as e:
            logger.exception("Failed to initialize Kafka producer: %s", e)
            kafka_producer = None

    gen = SensorGenerator(
        sensors=sensors,
        writer=writer,
        interval_s=args.interval,
        anomaly_cfg=anomaly_cfg,
        kafka_producer=kafka_producer,
        kafka_topic=args.kafka_topic,
        logger=logger
    )

    # graceful shutdown
    def _signal_handler(signum, frame):
        logger.info("Signal %s received, stopping generator...", signum)
        gen.stop()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        gen.start(duration_s=args.duration)
    finally:
        logger.info("Generator terminated. Outputs in: %s", outdir.resolve())

if __name__ == "__main__":
    main()
