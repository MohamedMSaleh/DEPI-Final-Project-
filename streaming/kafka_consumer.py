#!/usr/bin/env python3
"""
kafka_consumer.py
Real-time Kafka Streaming Consumer for IoT Weather Data

Project: DEPI Final Project - Real-time IoT Data Pipeline
Team: Data Rangers

This script implements a Kafka-based streaming consumer that:
- Consumes sensor data from Kafka topics in real-time
- Detects threshold breaches and anomalies
- Generates alerts for critical conditions
- Logs alerts to database
- Provides production-grade message queue architecture

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
from typing import Dict, List
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from database.schema import (
    create_database, get_session, get_database_url, 
    AlertLog, FactWeatherReading, DimTime, DimSensor, 
    DimLocation, DimStatus
)
from streaming.kafka_broker import get_broker
from datetime import datetime as dt_parser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('kafka_streaming.log')
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

# Define alert rules (same as original streaming_consumer.py)
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
# KAFKA STREAMING CONSUMER
# ============================

class KafkaStreamingConsumer:
    """
    Real-time Kafka streaming consumer for sensor data.
    Demonstrates production-grade message queue architecture.
    """
    
    def __init__(self, topic: str = "sensor_data", db_url: str = None):
        """
        Initialize Kafka streaming consumer.
        
        Args:
            topic: Kafka topic to consume from
            db_url: Database URL (optional)
        """
        self.topic = topic
        self.db_url = db_url or get_database_url()
        self.engine = create_database(self.db_url)
        self.alert_rules = ALERT_RULES
        self.kafka_broker = get_broker()
        self.processed_count = 0
        self.alert_count = 0
        self.readings_saved = 0
        
        logger.info(f"[OK] Kafka streaming consumer initialized")
        logger.info(f"   Topic: {self.topic}")
        logger.info(f"   Alert rules: {len(self.alert_rules)}")
        logger.info(f"   Saving readings to database: ENABLED")
    
    def process_message(self, message: Dict):
        """
        Process a single message from Kafka and check for alerts.
        
        Args:
            message: Sensor data message from Kafka
        """
        try:
            self.processed_count += 1
            
            sensor_id = message.get('sensor_id', 'unknown')
            timestamp = message.get('timestamp', datetime.now().isoformat())
            
            # Extract weather values
            if 'value' in message and isinstance(message['value'], dict):
                values = message['value']
            else:
                values = message
            
            # Check each alert rule
            alerts_triggered = []
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
                            timestamp=timestamp,
                            message=message
                        )
                        alerts_triggered.append(rule.name)
                        self.alert_count += 1
            
            # Save reading to database
            self.save_reading_to_database(message)
            
            # Log processing (only show alerts or every 50th message)
            if alerts_triggered:
                logger.info(f"[STATS] Processed {self.processed_count} messages | "
                           f"Saved: {self.readings_saved} | Alerts: {self.alert_count} | "
                           f"Current: {', '.join(alerts_triggered)}")
            elif self.processed_count % 50 == 0:
                logger.info(f"[STATS] Processed {self.processed_count} messages | "
                           f"Saved: {self.readings_saved} | Alerts: {self.alert_count}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def save_reading_to_database(self, message: Dict):
        """
        Save sensor reading to the data warehouse.
        
        Args:
            message: Full sensor message from Kafka
        """
        try:
            session = get_session(self.engine)
            
            # Extract data from message
            sensor_id = message.get('sensor_id', 'unknown')
            timestamp_str = message.get('timestamp', datetime.now().isoformat())
            
            # Parse timestamp
            ts = dt_parser.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Get or create dimension records
            # Time dimension
            time_record = session.query(DimTime).filter_by(
                year=ts.year, month=ts.month, day=ts.day,
                hour=ts.hour, minute=ts.minute, second=ts.second
            ).first()
            
            if not time_record:
                time_record = DimTime(
                    ts=ts,
                    date=ts.date(),
                    year=ts.year,
                    month=ts.month,
                    day=ts.day,
                    hour=ts.hour,
                    minute=ts.minute,
                    second=ts.second,
                    day_of_week=ts.strftime('%A'),
                    is_weekend=(ts.weekday() >= 5)
                )
                session.add(time_record)
                session.flush()
            
            # Sensor dimension
            sensor_record = session.query(DimSensor).filter_by(sensor_id=sensor_id).first()
            if not sensor_record:
                sensor_record = DimSensor(
                    sensor_id=sensor_id,
                    sensor_type=message.get('sensor_type', 'weather_station'),
                    sensor_model=message.get('sensor_model', 'unknown'),
                    manufacturer=message.get('manufacturer', 'unknown'),
                    firmware_version=message.get('firmware_version', 'unknown'),
                    is_active=True
                )
                session.add(sensor_record)
                session.flush()
            
            # Location dimension
            metadata = message.get('metadata', {})
            city_name = metadata.get('city', 'Unknown')
            location_record = session.query(DimLocation).filter_by(city_name=city_name).first()
            
            if not location_record:
                location_record = DimLocation(
                    city_name=city_name,
                    region=metadata.get('region', 'Unknown'),
                    country=metadata.get('country', 'Egypt'),
                    lat=metadata.get('lat', 0.0),
                    lon=metadata.get('lon', 0.0),
                    altitude=metadata.get('altitude', 0),
                    location_code=f"{city_name[:3].upper()}"
                )
                session.add(location_record)
                session.flush()
            
            # Status dimension
            status_code = message.get('status', 'OK')
            status_record = session.query(DimStatus).filter_by(status_code=status_code).first()
            
            if not status_record:
                status_record = DimStatus(
                    status_code=status_code,
                    description=f"Status: {status_code}"
                )
                session.add(status_record)
                session.flush()
            
            # Extract values
            values = message.get('value', {})
            
            # Create fact record
            fact_record = FactWeatherReading(
                time_id=time_record.time_id,
                sensor_id=sensor_record.sensor_id,
                location_id=location_record.location_id,
                status_id=status_record.status_id,
                temperature=values.get('temperature', 0.0),
                humidity=values.get('humidity', 0.0),
                pressure=values.get('pressure', 0.0),
                wind_speed=values.get('wind_speed', 0.0),
                wind_direction=values.get('wind_direction', 'N'),
                rainfall=values.get('rainfall', 0.0),
                is_anomaly=(status_code != 'OK'),
                anomaly_type=status_code if status_code != 'OK' else None,
                ingestion_ts=datetime.now(),
                processing_latency_ms=0,
                signal_strength=message.get('signal_strength', -70.0),
                reading_quality=message.get('reading_quality', 1.0)
            )
            
            session.add(fact_record)
            session.commit()
            session.close()
            
            self.readings_saved += 1
            
        except Exception as e:
            logger.error(f"Failed to save reading to database: {e}")
            if session:
                session.rollback()
                session.close()
    
    def create_alert(self, sensor_id: str, alert_type: str, severity: str,
                     metric_name: str, metric_value: float, threshold: float,
                     timestamp: str, message: Dict):
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
            message: Full message that triggered the alert
        """
        # Create message
        alert_message = (
            f"{alert_type}: Sensor {sensor_id} reported {metric_name}={metric_value:.2f} "
            f"(threshold: {threshold:.2f}) at {timestamp}"
        )
        
        # Log to console
        if severity == 'CRITICAL':
            logger.critical(f"[CRITICAL ALERT] {alert_message}")
        else:
            logger.warning(f"[WARNING] {alert_message}")
        
        # Log to database
        try:
            session = get_session(self.engine)
            
            alert = AlertLog(
                alert_ts=datetime.now(),
                sensor_id=sensor_id,
                alert_type=alert_type,
                alert_severity=severity,
                message=alert_message,
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
    
    def start(self):
        """
        Start consuming messages from Kafka topic.
        This runs in a continuous loop processing messages.
        """
        logger.info("="*70)
        logger.info("[START] Kafka Real-time Streaming Pipeline")
        logger.info("="*70)
        logger.info(f"[TOPIC] Consuming from: {self.topic}")
        logger.info(f"[RULES] Alert rules active: {len(self.alert_rules)}")
        logger.info(f"[DATABASE] {self.db_url}")
        logger.info("="*70)
        logger.info("[RUNNING] Consumer is active. Press Ctrl+C to stop.")
        logger.info("")
        
        try:
            while True:
                # Consume message from Kafka broker
                message = self.kafka_broker.consume(self.topic, timeout=0.5)
                
                if message:
                    self.process_message(message)
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            logger.info("\n[STOP] Stopping Kafka streaming consumer...")
            logger.info(f"[FINAL] Messages: {self.processed_count} | Saved to DB: {self.readings_saved} | Alerts: {self.alert_count}")
        
        except Exception as e:
            logger.error(f"[ERROR] Fatal error in consumer: {e}")
        
        finally:
            self.kafka_broker.stop()
            logger.info("[STOPPED] Kafka consumer stopped.")

# ============================
# MAIN
# ============================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kafka Streaming Consumer for IoT Weather Data")
    parser.add_argument("--topic", type=str, default="sensor_data", help="Kafka topic to consume from")
    parser.add_argument("--db-url", type=str, default=None, help="Database URL (optional)")
    
    args = parser.parse_args()
    
    # Create and start consumer
    consumer = KafkaStreamingConsumer(topic=args.topic, db_url=args.db_url)
    consumer.start()

if __name__ == "__main__":
    main()
