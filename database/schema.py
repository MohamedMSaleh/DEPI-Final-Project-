#!/usr/bin/env python3
"""
schema.py
Data Warehouse Schema Definition - Star Schema for IoT Weather Data

Project: DEPI Final Project - Real-time IoT Data Pipeline
Team: Data Rangers

This module defines the database schema for the data warehouse using SQLAlchemy ORM.
The schema follows a star schema design with one fact table and four dimension tables.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, create_engine, Text, Date
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# ============================
# DIMENSION TABLES
# ============================

class DimTime(Base):
    """Time dimension table for temporal analysis."""
    __tablename__ = 'dim_time'
    
    time_id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, nullable=False, unique=True, index=True)
    date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, nullable=False)
    second = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    is_weekend = Column(Boolean, nullable=False)
    
    # Relationship
    readings = relationship("FactWeatherReading", back_populates="time")

class DimSensor(Base):
    """Sensor dimension table for sensor metadata."""
    __tablename__ = 'dim_sensor'
    
    sensor_id = Column(String(50), primary_key=True)
    sensor_type = Column(String(50), nullable=False)
    sensor_model = Column(String(50))
    manufacturer = Column(String(50))
    install_date = Column(Date)
    firmware_version = Column(String(20))
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    
    # Relationship
    readings = relationship("FactWeatherReading", back_populates="sensor")

class DimLocation(Base):
    """Location dimension table for geographical data."""
    __tablename__ = 'dim_location'
    
    location_id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String(100), nullable=False)
    region = Column(String(100))
    country = Column(String(100), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    altitude = Column(Float)
    location_code = Column(String(50), unique=True, index=True)  # city_lat_lon hash
    
    # Relationship
    readings = relationship("FactWeatherReading", back_populates="location")

class DimStatus(Base):
    """Status dimension table for sensor reading status."""
    __tablename__ = 'dim_status'
    
    status_id = Column(Integer, primary_key=True, autoincrement=True)
    status_code = Column(String(20), nullable=False, unique=True, index=True)
    description = Column(String(200))
    
    # Relationship
    readings = relationship("FactWeatherReading", back_populates="status")

# ============================
# FACT TABLE
# ============================

class FactWeatherReading(Base):
    """Fact table for weather sensor readings."""
    __tablename__ = 'fact_weather_reading'
    
    reading_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    time_id = Column(Integer, ForeignKey('dim_time.time_id'), nullable=False, index=True)
    sensor_id = Column(String(50), ForeignKey('dim_sensor.sensor_id'), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey('dim_location.location_id'), nullable=False, index=True)
    status_id = Column(Integer, ForeignKey('dim_status.status_id'), nullable=False, index=True)
    
    # Measures (weather metrics)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    pressure = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=False)
    wind_direction = Column(String(10), nullable=False)
    rainfall = Column(Float, nullable=False, default=0.0)
    unit = Column(String(20), nullable=False, default='C/%/hPa')
    
    # Anomaly flags
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String(50))  # 'SPIKE', 'STUCK', 'DROPOUT', NULL
    
    # Pipeline metadata
    ingestion_ts = Column(DateTime, nullable=False, default=datetime.utcnow)
    processing_latency_ms = Column(Integer)  # Time taken to process this reading
    
    # Additional metadata
    signal_strength = Column(Float)
    reading_quality = Column(Float)
    
    # Relationships
    time = relationship("DimTime", back_populates="readings")
    sensor = relationship("DimSensor", back_populates="readings")
    location = relationship("DimLocation", back_populates="readings")
    status = relationship("DimStatus", back_populates="readings")

# ============================
# ALERT TABLE (for streaming alerts)
# ============================

class AlertLog(Base):
    """Table for storing real-time alerts."""
    __tablename__ = 'alert_log'
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    alert_ts = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    sensor_id = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # 'HIGH_TEMP', 'LOW_HUMIDITY', etc.
    alert_severity = Column(String(20), nullable=False)  # 'WARNING', 'CRITICAL'
    message = Column(Text, nullable=False)
    metric_name = Column(String(50))
    metric_value = Column(Float)
    threshold_value = Column(Float)
    is_resolved = Column(Boolean, default=False)
    resolved_ts = Column(DateTime)

# ============================
# DATABASE UTILITIES
# ============================

def get_database_url(db_path=None):
    """
    Get database URL for SQLite.
    
    Args:
        db_path: Path to SQLite database file. If None, uses default in 'database' folder.
    
    Returns:
        Database URL string
    """
    if db_path is None:
        # Default: create database in 'database' folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, 'iot_warehouse.db')
    
    return f'sqlite:///{db_path}'

def create_database(db_url=None):
    """
    Create all tables in the database.
    
    Args:
        db_url: Database URL. If None, uses default SQLite database.
    
    Returns:
        SQLAlchemy engine
    """
    if db_url is None:
        db_url = get_database_url()
    
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    
    print(f"Database created successfully at: {db_url}")
    print(f"Tables created: {', '.join(Base.metadata.tables.keys())}")
    
    return engine

def get_session(engine):
    """
    Create a new database session.
    
    Args:
        engine: SQLAlchemy engine
    
    Returns:
        SQLAlchemy Session
    """
    Session = sessionmaker(bind=engine)
    return Session()

def initialize_status_dimension(session):
    """
    Initialize the status dimension table with predefined statuses.
    
    Args:
        session: SQLAlchemy session
    """
    statuses = [
        {'status_code': 'OK', 'description': 'Normal reading - no issues detected'},
        {'status_code': 'SPIKE', 'description': 'Anomalous spike detected in reading'},
        {'status_code': 'STUCK', 'description': 'Sensor appears to be stuck on same value'},
        {'status_code': 'DROPOUT', 'description': 'Reading dropout or missing data'},
        {'status_code': 'DEGRADED', 'description': 'Poor signal quality or degraded reading'},
    ]
    
    for status_data in statuses:
        # Check if status already exists
        exists = session.query(DimStatus).filter_by(status_code=status_data['status_code']).first()
        if not exists:
            status = DimStatus(**status_data)
            session.add(status)
    
    session.commit()
    print(f"Initialized {len(statuses)} status codes in dim_status table.")

if __name__ == "__main__":
    """Initialize database when run as main script."""
    print("=== IoT Data Warehouse Schema Initialization ===")
    print()
    
    # Create database and tables
    engine = create_database()
    
    # Create session and initialize status dimension
    session = get_session(engine)
    initialize_status_dimension(session)
    session.close()
    
    print()
    print("Database initialization complete!")
    print(f"Database location: {os.path.join(os.path.dirname(__file__), 'iot_warehouse.db')}")
