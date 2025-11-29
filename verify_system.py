#!/usr/bin/env python3
"""
Quick system verification and setup
"""
import sqlite3
from pathlib import Path

print("\n" + "="*60)
print("SYSTEM VERIFICATION")
print("="*60 + "\n")

# Check database
db_path = Path("database/iot_warehouse.db")
if not db_path.exists():
    print("❌ Database not found!")
else:
    print("✅ Database exists")
    
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    # Get tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    
    print(f"\n📋 Tables found: {len(tables)}")
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  • {table}: {count} rows")
    
    conn.close()

# Check if files exist
print("\n📁 Data Files:")
csv_path = Path("output/sensor_data.csv")
if csv_path.exists():
    lines = len(open(csv_path).readlines())
    print(f"  ✅ sensor_data.csv: {lines} lines")
else:
    print("  ❌ sensor_data.csv not found")

jsonl_path = Path("output/sensor_data.jsonl")
if jsonl_path.exists():
    lines = len(open(jsonl_path).readlines())
    print(f"  ✅ sensor_data.jsonl: {lines} lines")
else:
    print("  ❌ sensor_data.jsonl not found")

print("\n" + "="*60)
print("RECOMMENDATIONS:")
print("="*60)
print("1. Run control panel: python control_panel.py")
print("2. Click 'Run All' to start complete pipeline")
print("3. ETL will populate database automatically")
print("4. Dashboard will be available at http://127.0.0.1:8050")
print("="*60 + "\n")
