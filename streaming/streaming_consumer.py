#!/usr/bin/env python3
"""
streaming_consumer.py
Real-time Streaming Pipeline for IoT Weather Data

Project: DEPI Final Project - Real-time IoT Data Pipeline
Team: Data Rangers

This script implements a real-time streaming consumer that:
- Monitors new sensor data in real-time
- Detects threshold breaches and anomalies
- Generates alerts for critical conditions
- Logs alerts to database

Alert Rules:
- High Temperature: temperature > 40°C
- Low Temperature: temperature < 0°C  
- Low Humidity: humidity < 20%
- High Humidity: humidity > 90%
- High Wind Speed: wind_speed > 50 km/h
- Unusual Pressure: pressure < 980 or pressure > 1040 hPa
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.schema import create_database, get_session, get_database_url, AlertLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('streaming_pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# ============================
# ALERT RULES & THRESHOLDS
# ============================

class AlertRule:
    """Defines an alert rule with thresholds."""
    
    def __init__(self, name: str, metric: str, condition: str, threshold: float, severity: str):
        self.name = name
        self.metric = metric
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
    
    def check(self, value: float) -> bool:
        """Check if value triggers the alert."""
        if self.condition == '>':
            return value > self.threshold
        elif self.condition == '<':
            return value < self.threshold
        elif self.condition == '>=':
            return value >= self.threshold
        elif self.condition == '<=':
            return value <= self.threshold
        return False

# Define alert rules
ALERT_RULES = [
    AlertRule('HIGH_TEMP', 'temperature', '>', 40.0, 'CRITICAL'),
    AlertRule('LOW_TEMP', 'temperature', '<', 0.0, 'WARNING'),
    AlertRule('LOW_HUMIDITY', 'humidity', '<', 20.0, 'WARNING'),
    AlertRule('HIGH_HUMIDITY', 'humidity', '>', 90.0, 'WARNING'),
    AlertRule('HIGH_WIND', 'wind_speed', '>', 50.0, 'WARNING'),
    AlertRule('LOW_PRESSURE', 'pressure', '<', 980.0, 'WARNING'),
    AlertRule('HIGH_PRESSURE', 'pressure', '>', 1040.0, 'WARNING'),
]

# ============================
# STREAMING CONSUMER
# ============================

class StreamingConsumer:
    """
    Real-time streaming consumer for sensor data.
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize streaming consumer.
        
        Args:
            db_url: Database URL (optional)
        """
        self.db_url = db_url or get_database_url()
        self.engine = create_database(self.db_url)
        self.alert_rules = ALERT_RULES
        self.processed_lines = set()  # Track processed lines to avoid duplicates
        logger.info("Streaming consumer initialized")
    
    def process_record(self, record: Dict):
        """
        Process a single sensor record and check for alerts.
        
        Args:
            record: Sensor data record
        """
        sensor_id = record.get('sensor_id', 'unknown')
        timestamp = record.get('timestamp', datetime.now().isoformat())
        
        # Extract weather values
        if 'value' in record and isinstance(record['value'], dict):
            values = record['value']
        else:
            # Flat structure (CSV)
            values = record
        
        # Check each alert rule
        for rule in self.alert_rules:
            if rule.metric in values:
                metric_value = values[rule.metric]
                
                if rule.check(metric_value):
                    self.create_alert(
                        sensor_id=sensor_id,
                        alert_type=rule.name,
                        severity=rule.severity,
                        metric_name=rule.metric,
                        metric_value=metric_value,
                        threshold=rule.threshold,
                        timestamp=timestamp
                    )
    
    def create_alert(self, sensor_id: str, alert_type: str, severity: str,
                     metric_name: str, metric_value: float, threshold: float,
                     timestamp: str):
        """
        Create and log an alert.
        
        Args:
            sensor_id: Sensor identifier
            alert_type: Type of alert
            severity: Alert severity (WARNING, CRITICAL)
            metric_name: Name of the metric that triggered the alert
            metric_value: Current value of the metric
            threshold: Threshold value
            timestamp: Timestamp of the reading
        """
        # Create message
        message = (
            f"{alert_type}: Sensor {sensor_id} reported {metric_name}={metric_value:.2f} "
            f"(threshold: {threshold:.2f}) at {timestamp}"
        )
        
        # Log to console
        if severity == 'CRITICAL':
            logger.critical(message)
        else:
            logger.warning(message)
        
        # Log to database
        try:
            session = get_session(self.engine)
            
            alert = AlertLog(
                alert_ts=datetime.now(),
                sensor_id=sensor_id,
                alert_type=alert_type,
                alert_severity=severity,
                message=message,
                metric_name=metric_name,
                metric_value=metric_value,
                threshold_value=threshold,
                is_resolved=False
            )
            
            session.add(alert)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Failed to log alert to database: {e}")
    
    def process_file(self, file_path: Path):
        """
        Process a JSONL or CSV file.
        
        Args:
            file_path: Path to the file
        """
        logger.info(f"Processing file: {file_path}")
        
        try:
            if file_path.suffix == '.jsonl':
                self.process_jsonl(file_path)
            elif file_path.suffix == '.csv':
                self.process_csv(file_path)
            else:
                logger.warning(f"Unsupported file type: {file_path.suffix}")
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def process_jsonl(self, file_path: Path):
        """Process JSONL file line by line."""
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line_key = f"{file_path}:{line_num}"
                
                # Skip if already processed
                if line_key in self.processed_lines:
                    continue
                
                try:
                    record = json.loads(line.strip())
                    self.process_record(record)
                    self.processed_lines.add(line_key)
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON on line {line_num}: {e}")
    
    def process_csv(self, file_path: Path):
        """Process CSV file row by row."""
        import pandas as pd
        
        try:
            df = pd.read_csv(file_path)
            
            for idx, row in df.iterrows():
                row_key = f"{file_path}:{idx}"
                
                # Skip if already processed
                if row_key in self.processed_lines:
                    continue
                
                record = row.to_dict()
                self.process_record(record)
                self.processed_lines.add(row_key)
        
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")

# ============================
# FILE WATCHER
# ============================

class DataFileHandler(FileSystemEventHandler):
    """Watches for new data files and processes them."""
    
    def __init__(self, consumer: StreamingConsumer):
        super().__init__()
        self.consumer = consumer
        self.last_modified = {}
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process sensor data files
        if file_path.name in ['sensor_data.jsonl', 'sensor_data.csv']:
            # Debounce: only process if not modified in last 2 seconds
            now = time.time()
            last_time = self.last_modified.get(str(file_path), 0)
            
            if now - last_time > 2:
                logger.info(f"File modified: {file_path}")
                self.consumer.process_file(file_path)
                self.last_modified[str(file_path)] = now

# ============================
# MAIN
# ============================

def run_streaming_consumer(watch_dir: Path, db_url: str = None):
    """
    Run the streaming consumer with file watching.
    
    Args:
        watch_dir: Directory to watch for data files
        db_url: Database URL (optional)
    """
    logger.info("="*60)
    logger.info("Starting Real-time Streaming Pipeline")
    logger.info("="*60)
    logger.info(f"Watching directory: {watch_dir}")
    logger.info(f"Alert rules: {len(ALERT_RULES)}")
    logger.info("="*60)
    
    # Create consumer
    consumer = StreamingConsumer(db_url)
    
    # Process existing files first
    for file_name in ['sensor_data.jsonl', 'sensor_data.csv']:
        file_path = watch_dir / file_name
        if file_path.exists():
            consumer.process_file(file_path)
    
    # Set up file watcher
    event_handler = DataFileHandler(consumer)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    observer.start()
    
    logger.info("Streaming consumer is running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping streaming consumer...")
        observer.stop()
    
    observer.join()
    logger.info("Streaming consumer stopped.")

if __name__ == "__main__":
    # Default paths
    project_root = Path(__file__).parent.parent
    watch_directory = project_root / 'output'
    
    # Run streaming consumer
    run_streaming_consumer(watch_directory)
