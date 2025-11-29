# Quick Start Guide - IoT Data Pipeline

**Get up and running in 5 minutes!**

## Prerequisites

- Python 3.10+ installed
- Windows PowerShell or Command Prompt

## Step 1: Install Dependencies (2 minutes)

```powershell
cd C:\Users\mahmo\OneDrive\Desktop\DEPI\DEPI-Final-Project-
pip install pandas numpy matplotlib seaborn sqlalchemy python-dotenv pytz schedule watchdog
```

## Step 2: Initialize Database (30 seconds)

```powershell
python database\schema.py
```

✅ You should see: "Database initialization complete!"

## Step 3: Generate Sample Data (1 minute)

```powershell
# Generate data for 1 minute with 10 sensors
python sensor_generator.py --num-sensors 10 --duration 60 --interval 5
```

✅ You should see data being generated in real-time.

## Step 4: Run ETL Pipeline (10 seconds)

```powershell
python etl\batch_etl.py
```

✅ You should see: "ETL Pipeline Complete! Records loaded: XXX"

## Step 5: View Dashboard (immediate)

```powershell
python dashboard\simple_dashboard.py
```

✅ A matplotlib window will open showing your dashboard!

## Optional: Run Streaming Alerts

Open a new terminal:

```powershell
python streaming\streaming_consumer.py
```

Now if you generate more data (Step 3), you'll see real-time alerts!

## What You Should See

### After Step 3 (Data Generation):
- Files created: `output/sensor_data.jsonl` and `output/sensor_data.csv`
- Console showing sensor readings every 5 seconds

### After Step 4 (ETL):
- Database file: `database/iot_warehouse.db`
- Aggregates file: `processed/hourly_aggregates.csv`
- Log file: `etl_pipeline.log`

### After Step 5 (Dashboard):
- 7-panel dashboard with:
  - System statistics
  - Temperature trends
  - Latest readings table
  - Temperature distribution
  - Recent alerts
  - Readings by city
  - Data quality pie chart

## Troubleshooting

### "Module not found" error
```powershell
pip install <missing-module>
```

### "Database is locked" error
Close the dashboard before running ETL.

### Dashboard not showing
Make sure ETL has been run at least once to populate the database.

## Next Steps

1. Read the full [README.md](../README.md) for detailed documentation
2. Check [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for technical details
3. Modify alert thresholds in `streaming/streaming_consumer.py`
4. Customize dashboard refresh rate (default: 5 seconds)

## Quick Commands Cheat Sheet

```powershell
# Full workflow
python sensor_generator.py --num-sensors 10 --duration 300    # 5 minutes of data
python etl\batch_etl.py                                        # Process data
python streaming\streaming_consumer.py                         # Monitor alerts (Ctrl+C to stop)
python dashboard\simple_dashboard.py                           # View dashboard (Ctrl+C to stop)
```

## Tips

- **For continuous operation**: Run sensor generator in one terminal, streaming consumer in another, and dashboard in a third.
- **For batch processing**: Generate data once, run ETL, then view dashboard.
- **Performance**: Reduce sensor count or increase interval if your system is slow.

---

**Have fun exploring your IoT data pipeline! 🚀**
