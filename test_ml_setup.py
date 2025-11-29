"""
Quick ML System Test
====================
Verifies ML integration is working correctly
"""

import sys
from pathlib import Path

print("\n" + "="*60)
print("🧪 ML SYSTEM TEST")
print("="*60 + "\n")

# Test 1: Check Prophet installation
print("1️⃣ Testing Prophet installation...")
try:
    from prophet import Prophet
    print("   ✅ Prophet installed successfully")
except ImportError as e:
    print(f"   ❌ Prophet not found: {e}")
    print("   📦 Install with: pip install prophet")
    sys.exit(1)

# Test 2: Check module import
print("\n2️⃣ Testing temperature_predictor module...")
try:
    sys.path.append(str(Path(__file__).parent))
    from ml.temperature_predictor import TemperaturePredictor
    print("   ✅ Module imported successfully")
except Exception as e:
    print(f"   ❌ Module import failed: {e}")
    sys.exit(1)

# Test 3: Check database
print("\n3️⃣ Testing database connection...")
try:
    import sqlite3
    db_path = Path(__file__).parent / "database" / "iot_warehouse.db"
    
    if not db_path.exists():
        print(f"   ❌ Database not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM fact_weather_reading")
    count = cursor.fetchone()[0]
    print(f"   ✅ Database connected: {count} readings")
    
    # Check cities
    cursor.execute("""
        SELECT city_name, COUNT(*) as count
        FROM fact_weather_reading f
        JOIN dim_location l ON f.location_id = l.location_id
        GROUP BY city_name
    """)
    cities = cursor.fetchall()
    
    print("\n   📍 Data by city:")
    for city, city_count in cities:
        print(f"      {city:15} {city_count:6} readings")
    
    conn.close()
    
    if count < 10:
        print("\n   ⚠️ Warning: Less than 10 readings. ML model needs more data.")
        
except Exception as e:
    print(f"   ❌ Database error: {e}")
    sys.exit(1)

# Test 4: Test predictor initialization
print("\n4️⃣ Testing predictor initialization...")
try:
    predictor = TemperaturePredictor()
    print("   ✅ Predictor initialized")
except Exception as e:
    print(f"   ❌ Initialization failed: {e}")
    sys.exit(1)

# Test 5: Test data retrieval
print("\n5️⃣ Testing data retrieval for one city...")
try:
    import pandas as pd
    df = predictor.get_training_data('Cairo', days=30)
    
    if df is not None and len(df) > 0:
        print(f"   ✅ Retrieved {len(df)} data points for Cairo")
        print(f"   📅 Date range: {df['ds'].min()} to {df['ds'].max()}")
        print(f"   🌡️ Temp range: {df['y'].min():.1f}°C - {df['y'].max():.1f}°C")
    else:
        print("   ⚠️ No data available for Cairo")
except Exception as e:
    print(f"   ❌ Data retrieval failed: {e}")

# Summary
print("\n" + "="*60)
print("✅ ML SYSTEM TEST COMPLETE")
print("="*60)
print("\n🚀 Next steps:")
print("   1. Run: python ml/temperature_predictor.py")
print("   2. Open Control Panel and start ML component")
print("   3. View predictions in Dashboard (port 8050)")
print("\n")
