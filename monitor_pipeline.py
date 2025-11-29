"""
Real-Time Pipeline Monitor
Shows LIVE status of all pipeline components in an easy-to-read format
"""
import time
import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from database.schema import get_database_url
from streaming.kafka_broker import get_broker

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_database_stats():
    """Get current database statistics"""
    try:
        db_url = get_database_url()
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Total readings
            total_readings = conn.execute(text("SELECT COUNT(*) FROM fact_weather_reading")).scalar()
            
            # Latest reading time
            latest_reading = conn.execute(text(
                "SELECT dt.ts FROM fact_weather_reading f "
                "JOIN dim_time dt ON f.time_id = dt.time_id "
                "ORDER BY dt.ts DESC LIMIT 1"
            )).scalar()
            
            # Total alerts
            total_alerts = conn.execute(text("SELECT COUNT(*) FROM alert_log")).scalar()
            
            # Recent alerts (last 5 minutes)
            recent_alerts = conn.execute(text(
                "SELECT COUNT(*) FROM alert_log "
                "WHERE alert_ts > datetime('now', '-5 minutes')"
            )).scalar()
            
            # Anomalies count
            anomalies = conn.execute(text(
                "SELECT COUNT(*) FROM fact_weather_reading WHERE is_anomaly = 1"
            )).scalar()
            
            # Readings by city (last hour)
            city_counts = conn.execute(text(
                "SELECT dl.city_name, COUNT(*) as count "
                "FROM fact_weather_reading f "
                "JOIN dim_location dl ON f.location_id = dl.location_id "
                "JOIN dim_time dt ON f.time_id = dt.time_id "
                "WHERE dt.ts > datetime('now', '-1 hour') "
                "GROUP BY dl.city_name "
                "ORDER BY count DESC"
            )).fetchall()
            
            return {
                'total_readings': total_readings,
                'latest_reading': latest_reading,
                'total_alerts': total_alerts,
                'recent_alerts': recent_alerts,
                'anomalies': anomalies,
                'city_counts': city_counts
            }
    except Exception as e:
        return {'error': str(e)}

def get_kafka_stats():
    """Get Kafka broker statistics"""
    try:
        broker = get_broker()
        return broker.get_stats()
    except Exception as e:
        return {'error': str(e)}

def get_file_stats():
    """Get output file statistics"""
    try:
        output_dir = Path(__file__).parent / 'output'
        jsonl_file = output_dir / 'sensor_data.jsonl'
        csv_file = output_dir / 'sensor_data.csv'
        
        stats = {}
        
        if jsonl_file.exists():
            # Count lines
            with open(jsonl_file, 'r') as f:
                line_count = sum(1 for _ in f)
            # Get file size
            size_mb = jsonl_file.stat().st_size / (1024 * 1024)
            # Get last modified
            last_mod = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
            
            stats['jsonl'] = {
                'lines': line_count,
                'size_mb': round(size_mb, 2),
                'last_modified': last_mod.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        if csv_file.exists():
            with open(csv_file, 'r') as f:
                line_count = sum(1 for _ in f) - 1  # Exclude header
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            last_mod = datetime.fromtimestamp(csv_file.stat().st_mtime)
            
            stats['csv'] = {
                'lines': line_count,
                'size_mb': round(size_mb, 2),
                'last_modified': last_mod.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        return stats
    except Exception as e:
        return {'error': str(e)}

def display_status():
    """Display comprehensive pipeline status"""
    clear_screen()
    
    print("=" * 80)
    print(" " * 25 + "IOT PIPELINE MONITOR")
    print("=" * 80)
    print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Kafka Status
    print("[1] KAFKA MESSAGE BROKER")
    print("-" * 80)
    kafka_stats = get_kafka_stats()
    if 'error' in kafka_stats:
        print(f"   Status: ERROR - {kafka_stats['error']}")
    elif kafka_stats:
        for topic, stats in kafka_stats.items():
            print(f"   Topic: {topic}")
            print(f"      Messages Pending: {stats['messages_pending']}")
            print(f"      Active Subscribers: {stats['subscribers']}")
            if stats['messages_pending'] > 0:
                print(f"      [WARNING] Messages are piling up! Consumer may be slow.")
            elif stats['subscribers'] > 0:
                print(f"      [OK] Consumer is active and processing messages")
            else:
                print(f"      [INFO] No active consumers")
    else:
        print("   Status: NOT RUNNING - No topics found")
    print()
    
    # Database Status
    print("[2] DATABASE (SQLite Data Warehouse)")
    print("-" * 80)
    db_stats = get_database_stats()
    if 'error' in db_stats:
        print(f"   Status: ERROR - {db_stats['error']}")
    else:
        print(f"   Total Readings: {db_stats['total_readings']:,}")
        print(f"   Latest Reading: {db_stats['latest_reading'] or 'No data yet'}")
        print(f"   Total Alerts: {db_stats['total_alerts']:,}")
        print(f"   Recent Alerts (5 min): {db_stats['recent_alerts']}")
        print(f"   Anomalies Detected: {db_stats['anomalies']:,}")
        
        if db_stats['city_counts']:
            print(f"   Readings by City (Last Hour):")
            for city, count in db_stats['city_counts']:
                print(f"      {city}: {count} readings")
        
        # Status indicators
        if db_stats['total_readings'] == 0:
            print(f"   [WARNING] No data in database. Run ETL pipeline!")
        elif db_stats['recent_alerts'] > 0:
            print(f"   [ALERT] {db_stats['recent_alerts']} new alerts in last 5 minutes!")
        else:
            print(f"   [OK] Database is healthy")
    print()
    
    # File Output Status
    print("[3] FILE OUTPUT")
    print("-" * 80)
    file_stats = get_file_stats()
    if 'error' in file_stats:
        print(f"   Status: ERROR - {file_stats['error']}")
    else:
        if 'jsonl' in file_stats:
            print(f"   JSONL File:")
            print(f"      Lines: {file_stats['jsonl']['lines']:,}")
            print(f"      Size: {file_stats['jsonl']['size_mb']} MB")
            print(f"      Last Updated: {file_stats['jsonl']['last_modified']}")
        
        if 'csv' in file_stats:
            print(f"   CSV File:")
            print(f"      Lines: {file_stats['csv']['lines']:,}")
            print(f"      Size: {file_stats['csv']['size_mb']} MB")
            print(f"      Last Updated: {file_stats['csv']['last_modified']}")
        
        if not file_stats:
            print(f"   [WARNING] No output files found. Start sensor generator!")
    print()
    
    # Instructions
    print("[4] PIPELINE COMPONENTS STATUS")
    print("-" * 80)
    print("   Expected Running Components:")
    print("   [1] Sensor Generator   -> python sensor_generator.py --use-kafka --num-sensors 10")
    print("   [2] Kafka Consumer     -> python streaming/kafka_consumer.py")
    print("   [3] ETL Pipeline       -> python etl/batch_etl.py (run periodically)")
    print("   [4] Dashboard          -> python dashboard/advanced_dashboard.py")
    print()
    print("=" * 80)
    print("Press Ctrl+C to stop monitoring")
    print("=" * 80)

def main():
    """Run continuous monitoring"""
    print("Starting IoT Pipeline Monitor...")
    print("Updating every 3 seconds...")
    time.sleep(2)
    
    try:
        while True:
            display_status()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        print("Goodbye!")

if __name__ == "__main__":
    main()
