"""
Simple Real-Time Data Injector
Continuously adds new sensor readings to the database so the dashboard updates
WITH REALISTIC GRADUAL CHANGES (no wild jumps!)
"""
import time
import random
import math
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from database.schema import (
    create_database, get_session, get_database_url,
    FactWeatherReading, DimTime, DimSensor, DimLocation, DimStatus
)

# Egyptian cities with realistic climate profiles
CITIES_CONFIG = {
    "Cairo": {
        "avg_temp_day": 28.0, "avg_temp_night": 18.0,
        "temp_variation": 3.0, "humidity_avg": 55.0,
        "lat": 30.0444, "lon": 31.2357, "alt": 23
    },
    "Alexandria": {
        "avg_temp_day": 26.0, "avg_temp_night": 20.0,
        "temp_variation": 2.5, "humidity_avg": 68.0,
        "lat": 31.2001, "lon": 29.9187, "alt": 5
    },
    "Giza": {
        "avg_temp_day": 29.0, "avg_temp_night": 19.0,
        "temp_variation": 3.0, "humidity_avg": 50.0,
        "lat": 29.9753, "lon": 31.1376, "alt": 19
    },
    "Luxor": {
        "avg_temp_day": 35.0, "avg_temp_night": 22.0,
        "temp_variation": 4.0, "humidity_avg": 35.0,
        "lat": 25.6872, "lon": 32.6396, "alt": 76
    },
    "Aswan": {
        "avg_temp_day": 38.0, "avg_temp_night": 24.0,
        "temp_variation": 5.0, "humidity_avg": 30.0,
        "lat": 24.0889, "lon": 32.8998, "alt": 85
    }
}

# Store previous values for each city (for smooth transitions)
previous_readings = {}

def get_time_of_day_factor(ts: datetime) -> float:
    """Calculate temperature factor based on time of day (0=night, 1=day peak)"""
    hour = ts.hour + ts.minute / 60.0
    coldest_hour = 5.0  # 5 AM coldest
    warmest_hour = 14.0  # 2 PM warmest
    
    hours_since_coldest = (hour - coldest_hour) % 24
    
    if hours_since_coldest <= (warmest_hour - coldest_hour):
        factor = hours_since_coldest / (warmest_hour - coldest_hour)
    else:
        hours_to_coldest = 24 - hours_since_coldest
        factor = hours_to_coldest / (24 - (warmest_hour - coldest_hour))
    
    return 0.5 * (1 + math.sin(math.pi * (factor - 0.5)))

def inject_reading():
    """Inject a single REALISTIC reading with smooth transitions"""
    db_url = get_database_url()
    engine = create_database(db_url)
    session = get_session(engine)
    
    try:
        # Get current time
        now = datetime.now()
        
        # Get or create time record
        time_record = session.query(DimTime).filter_by(
            year=now.year, month=now.month, day=now.day,
            hour=now.hour, minute=now.minute, second=now.second
        ).first()
        
        if not time_record:
            time_record = DimTime(
                ts=now,
                date=now.date(),
                year=now.year,
                month=now.month,
                day=now.day,
                hour=now.hour,
                minute=now.minute,
                second=now.second,
                day_of_week=now.strftime('%A'),
                is_weekend=(now.weekday() >= 5)
            )
            session.add(time_record)
            session.flush()
        
        # Pick random city
        city = random.choice(list(CITIES_CONFIG.keys()))
        city_config = CITIES_CONFIG[city]
        
        # Get sensor and location
        sensor_id = f"ws_{city.lower()}_demo"
        sensor = session.query(DimSensor).filter_by(sensor_id=sensor_id).first()
        if not sensor:
            sensor = DimSensor(
                sensor_id=sensor_id,
                sensor_type="weather_station",
                sensor_model="DEMO",
                manufacturer="Demo",
                firmware_version="1.0",
                is_active=True
            )
            session.add(sensor)
            session.flush()
        
        location = session.query(DimLocation).filter_by(city_name=city).first()
        if not location:
            location = DimLocation(
                city_name=city,
                region=city,
                country="Egypt",
                lat=city_config["lat"],
                lon=city_config["lon"],
                altitude=city_config["alt"],
                location_code=city[:3].upper()
            )
            session.add(location)
            session.flush()
        
        # Get OK status
        status = session.query(DimStatus).filter_by(status_code="OK").first()
        
        # === REALISTIC VALUE GENERATION WITH SMOOTH TRANSITIONS ===
        
        # Get time factor for daily temperature cycle
        time_factor = get_time_of_day_factor(now)
        
        # Base temperature from time of day
        temp_range = city_config["avg_temp_day"] - city_config["avg_temp_night"]
        base_temp = city_config["avg_temp_night"] + (temp_range * time_factor)
        
        # Get previous values for this city
        prev = previous_readings.get(city, {})
        
        # Temperature: smooth transition (only change by ±0.3°C max per reading)
        if "temperature" in prev:
            temp_delta = random.gauss(0, 0.15)  # Very small random change
            temp = prev["temperature"] + temp_delta
            # Slowly drift toward expected base temperature
            temp = temp * 0.9 + base_temp * 0.1
        else:
            # First reading for this city
            temp = base_temp + random.gauss(0, city_config["temp_variation"] * 0.3)
        
        # Bound temperature to realistic range
        min_temp = city_config["avg_temp_night"] - 5
        max_temp = city_config["avg_temp_day"] + 8
        temp = max(min_temp, min(max_temp, temp))
        temp = round(temp, 2)
        
        # Humidity: inversely related to temperature + smooth transition
        base_humidity = city_config["humidity_avg"]
        temp_diff = temp - city_config["avg_temp_night"]
        humidity_delta = -1.0 * temp_diff
        
        if "humidity" in prev:
            humidity = prev["humidity"] + random.gauss(0, 0.8)  # Small change
            target_humidity = base_humidity + humidity_delta
            humidity = humidity * 0.85 + target_humidity * 0.15
        else:
            humidity = base_humidity + humidity_delta + random.gauss(0, 3.0)
        
        humidity = max(20.0, min(85.0, humidity))
        humidity = round(humidity, 2)
        
        # Pressure: very stable, small changes
        base_pressure = 1013.0 - (city_config["alt"] / 10.0)
        if "pressure" in prev:
            pressure = prev["pressure"] + random.gauss(0, 0.2)  # Tiny change
            pressure = pressure * 0.95 + base_pressure * 0.05
        else:
            pressure = base_pressure + random.gauss(0, 1.5)
        
        pressure = round(max(1005.0, min(1020.0, pressure)), 2)
        
        # Wind speed: gradual changes
        base_wind = 8.0 + 7.0 * time_factor
        if "wind_speed" in prev:
            wind_speed = prev["wind_speed"] + random.gauss(0, 0.5)
            wind_speed = wind_speed * 0.85 + base_wind * 0.15
        else:
            wind_speed = base_wind + random.gauss(0, 2.0)
        
        wind_speed = round(max(0.0, min(25.0, wind_speed)), 2)
        
        # Wind direction: mostly stays the same
        wind_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        if "wind_direction" in prev and random.random() < 0.85:
            wind_direction = prev["wind_direction"]
        else:
            wind_direction = random.choice(wind_directions)
        
        # Rainfall: rare
        rainfall = 0.0
        if random.random() < 0.02:  # 2% chance
            rainfall = round(random.uniform(0.1, 1.5), 2)
        
        # Store current values for next iteration
        previous_readings[city] = {
            "temperature": temp,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction
        }
        
        # Create reading
        reading = FactWeatherReading(
            time_id=time_record.time_id,
            sensor_id=sensor.sensor_id,
            location_id=location.location_id,
            status_id=status.status_id,
            temperature=temp,
            humidity=humidity,
            pressure=pressure,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            rainfall=rainfall,
            is_anomaly=False,
            anomaly_type=None,
            ingestion_ts=datetime.now(),
            processing_latency_ms=10,
            signal_strength=-70.0,
            reading_quality=0.95
        )
        
        session.add(reading)
        session.commit()
        
        print(f"[{now.strftime('%H:%M:%S')}] {city}: {temp}°C (Δ{temp-prev.get('temperature', temp):+.2f}°C), {humidity:.1f}% humidity")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

def main():
    print("="*60)
    print("Real-Time Data Injector")
    print("="*60)
    print("Continuously adding sensor readings to database")
    print("Dashboard will now show LIVE updates!")
    print("Press Ctrl+C to stop")
    print("="*60)
    print()
    
    count = 0
    try:
        while True:
            inject_reading()
            count += 1
            
            if count % 10 == 0:
                print(f"\n[INFO] {count} readings injected. Dashboard should show changes!\n")
            
            time.sleep(3)  # Every 3 seconds
    
    except KeyboardInterrupt:
        print(f"\n\nStopped after injecting {count} readings.")
        print("Dashboard now has fresh data!")

if __name__ == "__main__":
    main()
