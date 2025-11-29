#!/usr/bin/env python3
"""Batch ETL pipeline for the real-time IoT data project.

This script performs the classic Extract -> Transform -> Load workflow expected by
Milestone 2 of the project brief:

1. Extract sensor readings from the generated CSV/JSONL files.
2. Transform the data (cleansing + anomaly flagging).
3. Load the curated records into the SQLite data warehouse and publish
   hourly aggregates for downstream analytics.

Running the script is idempotent: previously loaded readings are skipped, so it
can be executed repeatedly without duplicating data.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.schema import (
    DimLocation,
    DimSensor,
    DimStatus,
    DimTime,
    FactWeatherReading,
    create_database,
    get_database_url,
    get_session,
    initialize_status_dimension,
)
DEFAULT_CSV = PROJECT_ROOT / "output" / "sensor_data.csv"
DEFAULT_JSONL = PROJECT_ROOT / "output" / "sensor_data.jsonl"
AGGREGATE_PATH = PROJECT_ROOT / "processed" / "hourly_aggregates.csv"
LOG_PATH = PROJECT_ROOT / "etl_pipeline.log"

# Thresholds reused by the streaming consumer so alerts line up in batch/streaming
ALERT_THRESHOLDS = {
    "HIGH_TEMP": ("temperature", ">", 40.0),
    "LOW_TEMP": ("temperature", "<", 0.0),
    "LOW_HUMIDITY": ("humidity", "<", 20.0),
    "HIGH_HUMIDITY": ("humidity", ">", 90.0),
    "HIGH_WIND": ("wind_speed", ">", 50.0),
    "LOW_PRESSURE": ("pressure", "<", 980.0),
    "HIGH_PRESSURE": ("pressure", ">", 1040.0),
}


def configure_logging(verbose: bool = False) -> logging.Logger:
    """Configure application logging (console + file)."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("batch_etl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the batch ETL pipeline")
    parser.add_argument(
        "--input-csv",
        type=str,
        default=str(DEFAULT_CSV),
        help="Path to the flattened CSV produced by sensor_generator.py",
    )
    parser.add_argument(
        "--input-jsonl",
        type=str,
        default=str(DEFAULT_JSONL),
        help="Optional JSONL fallback if the CSV is unavailable",
    )
    parser.add_argument(
        "--output-aggregates",
        type=str,
        default=str(AGGREGATE_PATH),
        help="Destination for hourly aggregate metrics",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for debugging",
    )
    return parser.parse_args()


def safe_float(value: Optional[object], default: float = 0.0) -> float:
    """Convert values to float while handling blanks and NaNs."""
    if value is None:
        return default
    try:
        if isinstance(value, str) and not value.strip():
            return default
        result = float(value)
        if math.isnan(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_str(value: Optional[object], default: str = "") -> str:
    """Convert values to safe ASCII strings."""
    if value is None:
        return default
    if isinstance(value, float) and math.isnan(value):
        return default
    return str(value)


def parse_timestamp(value: str) -> Optional[datetime]:
    """Parse ISO-8601 timestamps with or without timezone offsets."""
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def detect_anomaly(record: Dict[str, object]) -> Tuple[bool, Optional[str]]:
    """Run simple rule-based anomaly detection consistent with streaming alerts."""
    for label, (metric, op, threshold) in ALERT_THRESHOLDS.items():
        metric_value = safe_float(record.get(metric))
        if op == ">" and metric_value > threshold:
            return True, label
        if op == "<" and metric_value < threshold:
            return True, label
    return False, None


def load_source_records(csv_path: Path, jsonl_path: Path) -> Iterable[Dict[str, object]]:
    """Yield records from CSV (preferred) or JSONL files."""
    if csv_path.exists():
        for chunk in pd.read_csv(csv_path, chunksize=1000):
            for record in chunk.to_dict(orient="records"):
                yield record
    elif jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def ensure_status(session, status_code: str) -> DimStatus:
    status = (
        session.query(DimStatus)
        .filter(DimStatus.status_code == status_code)
        .first()
    )
    if status:
        return status

    status = DimStatus(status_code=status_code, description=status_code.title())
    session.add(status)
    session.flush()
    return status


def upsert_dimensions(
    session, record: Dict[str, object], timestamp: datetime
) -> Tuple[DimTime, DimSensor, DimLocation, DimStatus]:
    # Time dimension
    time_row = session.query(DimTime).filter(DimTime.ts == timestamp).first()
    if not time_row:
        time_row = DimTime(
            ts=timestamp,
            date=timestamp.date(),
            year=timestamp.year,
            month=timestamp.month,
            day=timestamp.day,
            hour=timestamp.hour,
            minute=timestamp.minute,
            second=timestamp.second,
            day_of_week=timestamp.strftime("%A"),
            is_weekend=timestamp.weekday() >= 5,
        )
        session.add(time_row)
        session.flush()

    # Sensor dimension
    sensor_id = safe_str(record.get("sensor_id"), "unknown_sensor")
    sensor_row = session.query(DimSensor).filter(DimSensor.sensor_id == sensor_id).first()
    if not sensor_row:
        sensor_row = DimSensor(
            sensor_id=sensor_id,
            sensor_type=safe_str(record.get("sensor_type"), "weather_station"),
            sensor_model=safe_str(record.get("sensor_model"), "unknown"),
            manufacturer=safe_str(record.get("manufacturer"), "unknown"),
            firmware_version=safe_str(record.get("firmware_version"), "unknown"),
            is_active=True,
        )
        session.add(sensor_row)
        session.flush()

    # Location dimension
    city = safe_str(record.get("city"), "Unknown")
    location_row = session.query(DimLocation).filter(DimLocation.city_name == city).first()
    if not location_row:
        location_row = DimLocation(
            city_name=city,
            region=safe_str(record.get("region"), city),
            country=safe_str(record.get("country"), "Egypt"),
            lat=safe_float(record.get("lat")),
            lon=safe_float(record.get("lon")),
            altitude=safe_float(record.get("altitude")),
            location_code=city[:3].upper() or "UNK",
        )
        session.add(location_row)
        session.flush()

    # Status dimension
    requested_status = safe_str(record.get("status"), "OK").upper() or "OK"
    status_row = ensure_status(session, requested_status)

    return time_row, sensor_row, location_row, status_row


def insert_fact(
    session,
    timestamp: datetime,
    dims: Tuple[DimTime, DimSensor, DimLocation, DimStatus],
    record: Dict[str, object],
    anomaly: Tuple[bool, Optional[str]],
) -> bool:
    time_row, sensor_row, location_row, status_row = dims

    existing = (
        session.query(FactWeatherReading)
        .filter(
            FactWeatherReading.time_id == time_row.time_id,
            FactWeatherReading.sensor_id == sensor_row.sensor_id,
        )
        .first()
    )
    if existing:
        return False

    is_anomaly, anomaly_code = anomaly
    if is_anomaly:
        status_row = ensure_status(session, "DEGRADED")

    fact = FactWeatherReading(
        time_id=time_row.time_id,
        sensor_id=sensor_row.sensor_id,
        location_id=location_row.location_id,
        status_id=status_row.status_id,
        temperature=safe_float(record.get("temperature")),
        humidity=safe_float(record.get("humidity")),
        pressure=safe_float(record.get("pressure"), 1013.0),
        wind_speed=safe_float(record.get("wind_speed")),
        wind_direction=safe_str(record.get("wind_direction"), "N"),
        rainfall=safe_float(record.get("rainfall")),
        unit=safe_str(record.get("unit"), "C/%/hPa"),
        is_anomaly=is_anomaly,
        anomaly_type=anomaly_code,
        ingestion_ts=datetime.now(timezone.utc).astimezone(),
        processing_latency_ms=0,
        signal_strength=safe_float(record.get("signal_strength"), -70.0),
        reading_quality=safe_float(record.get("reading_quality"), 1.0),
    )
    session.add(fact)
    return True


def refresh_hourly_aggregates(engine, destination: Path, logger: logging.Logger) -> None:
    query = text(
        """
        SELECT
            dl.city_name AS city,
            dt.year,
            dt.month,
            dt.day,
            dt.hour,
            COUNT(*) AS readings_count,
            AVG(f.temperature) AS avg_temperature,
            MIN(f.temperature) AS min_temperature,
            MAX(f.temperature) AS max_temperature,
            AVG(f.humidity) AS avg_humidity,
            SUM(CASE WHEN f.is_anomaly = 1 THEN 1 ELSE 0 END) AS anomaly_count
        FROM fact_weather_reading f
        JOIN dim_time dt ON f.time_id = dt.time_id
        JOIN dim_location dl ON f.location_id = dl.location_id
        GROUP BY dl.city_name, dt.year, dt.month, dt.day, dt.hour
        ORDER BY dt.year, dt.month, dt.day, dt.hour, dl.city_name
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    destination.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destination, index=False)
    logger.info("Saved aggregates to: %s", destination)


def main() -> None:
    args = parse_args()
    logger = configure_logging(args.verbose)

    csv_path = Path(args.input_csv)
    jsonl_path = Path(args.input_jsonl)

    if not csv_path.exists() and not jsonl_path.exists():
        logger.warning(
            "No source files found. Expected either %s or %s.", csv_path, jsonl_path
        )
        return

    logger.info("Starting batch ETL job")
    logger.info("Input CSV: %s", csv_path if csv_path.exists() else "<missing>")
    logger.info("Input JSONL: %s", jsonl_path if jsonl_path.exists() else "<missing>")

    db_url = get_database_url()
    engine = create_database(db_url)
    session = get_session(engine)
    initialize_status_dimension(session)

    inserted = 0
    skipped = 0

    try:
        for idx, record in enumerate(load_source_records(csv_path, jsonl_path), 1):
            timestamp = parse_timestamp(safe_str(record.get("timestamp")))
            if not timestamp:
                skipped += 1
                continue

            dims = upsert_dimensions(session, record, timestamp)
            anomaly = detect_anomaly(record)
            if insert_fact(session, timestamp, dims, record, anomaly):
                inserted += 1
            else:
                skipped += 1

            if idx % 500 == 0:
                session.commit()
                logger.debug("Processed %d records so far", idx)

        session.commit()
    finally:
        session.close()

    logger.info("Records inserted: %d", inserted)
    logger.info("Records skipped (duplicates/invalid): %d", skipped)

    refresh_hourly_aggregates(engine, Path(args.output_aggregates), logger)
    logger.info("Batch ETL pipeline complete")


if __name__ == "__main__":
    main()
