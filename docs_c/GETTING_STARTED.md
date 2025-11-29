# Getting Started - IoT Weather Monitoring System

**Quick start guide to get your system running in minutes!**

---

## 📋 Prerequisites

- **Python 3.14** (recommended) or 3.10+
- **Windows 10/11** with PowerShell
- **4GB RAM minimum** (8GB recommended)
- **Internet connection** for package installation

---

## 🚀 Installation

### Step 1: Install Dependencies

```powershell
cd C:\Users\mahmo\OneDrive\Desktop\DEPI\DEPI-Final-Project-
pip install -r requirements.txt
```

**Key packages installed:**
- `dash>=3.3.0` - Web dashboard framework
- `pandas>=2.3.3` - Data processing
- `prophet>=1.1.6` - ML forecasting
- `sqlalchemy` - Database ORM
- `kafka-python` - Message queue (optional)

### Step 2: Initialize Database

```powershell
python database\schema.py
```

✅ **Success**: You'll see "✅ Database initialization complete!"

---

## 🎮 Using the Control Panel (Recommended)

The **Control Panel** is the easiest way to manage all pipeline components.

### Start Control Panel

```powershell
python control_panel.py
```

### Control Panel Features

The GUI provides:

1. **Component Management**
   - ✅ Sensor Generator (auto-starts)
   - ✅ Batch ETL (auto-starts, runs every 60s)
   - ✅ Kafka Broker (auto-starts)
   - ✅ Kafka Consumer (alerts only)
   - ✅ Advanced Dashboard (port 8050)
   - ✅ ML Temperature Predictor (on-demand)

2. **Action Buttons**
   - **Run All** - Starts all auto-start components + ML predictor
   - **Stop All** - Gracefully stops everything
   - **Restart All** - Full system restart
   - Individual start/stop/restart for each component

3. **Monitoring**
   - Real-time output logs for each process
   - System resource usage (CPU, Memory, Disk)
   - Database statistics
   - Pipeline flow visualization

4. **Database Tools**
   - View database statistics
   - Backup database
   - Clean old data
   - Verify system integrity

### Quick Start Workflow

1. Click **"Run All"** button
2. Wait 5-10 seconds for initialization
3. Open browser to **http://127.0.0.1:8050**
4. View real-time dashboard

**That's it! Your complete pipeline is now running.**

---

## 🔧 Manual Operation (Advanced)

If you prefer command-line control:

### Terminal 1: Generate Data
```powershell
python sensor_generator.py --num-sensors 20 --interval 5
```

### Terminal 2: Batch ETL (Continuous)
```powershell
python etl\batch_etl.py
```
*Runs automatically every 60 seconds*

### Terminal 3: Kafka Consumer (Optional)
```powershell
python streaming\kafka_consumer.py
```
*Monitors for alerts in real-time*

### Terminal 4: Dashboard
```powershell
python dashboard\advanced_dashboard.py
```
*Opens at http://127.0.0.1:8050*

### Terminal 5: ML Predictions (On-demand)
```powershell
python ml\temperature_predictor.py
```
*Generates next-day temperature forecasts*

---

## 🌐 Accessing the Dashboard

### Advanced Dashboard (Primary)
- **URL**: http://127.0.0.1:8050
- **Port**: 8050
- **Auto-refresh**: Every 10 seconds
- **Features**:
  - Real-time KPI cards
  - Temperature trends chart
  - Current readings by city
  - ML predictions visualization
  - Interactive gauges
  - City comparison
  - Recent alerts
  - Data quality metrics

### Dashboard V2 (Alternative)
- **URL**: http://127.0.0.1:8051
- **Port**: 8051
- **Style**: Glassmorphism design
- **Features**: Similar to Advanced Dashboard

**Tip**: Use the Advanced Dashboard (port 8050) as your primary interface.

---

## 📊 What You'll See

### After Starting Sensor Generator:
- Console shows readings every 5 seconds
- Files created in `output/`:
  - `sensor_data.csv`
  - `sensor_data.jsonl`

### After ETL Runs:
- Database populated: `database/iot_warehouse.db`
- Aggregates created: `processed/hourly_aggregates.csv`
- Console shows:
  ```
  [CYCLE 1] Starting ETL at HH:MM:SS
  [CYCLE 1] Complete in 1.23s | Inserted: 120 | Skipped: 0
  ```

### In the Dashboard:
- **Total Readings**: Growing counter
- **Active Sensors**: 20 sensors
- **Anomalies**: Flagged unusual readings
- **Recent Alerts**: Temperature/humidity warnings
- **Temperature Trends**: Line chart per city
- **ML Predictions**: Next 24 hours forecast

---

## 🧪 Testing Your Setup

### Quick Verification

```powershell
python verify_system.py
```

This shows:
- ✅ Database tables and row counts
- ✅ Data files and sizes
- ✅ System status

### Expected Output:
```
📊 IoT PIPELINE SYSTEM VERIFICATION
====================================

DATABASE STATUS:
- fact_weather_reading: 16,168 rows
- ml_predictions: 120 rows
- alert_log: 16 alerts

FILES:
- sensor_data.csv: 14,593 lines
- sensor_data.jsonl: exists

✅ System Ready!
```

---

## 🎯 Common Tasks

### Generate Sample Data
```powershell
# 5 minutes of data
python sensor_generator.py --duration 300

# 10 sensors instead of 20
python sensor_generator.py --num-sensors 10
```

### Run ML Prediction
```powershell
python ml\temperature_predictor.py
```
*Predictions appear in dashboard within 10 seconds*

### View Database Content
```powershell
# Using SQLite browser
sqlite3 database\iot_warehouse.db
.tables
SELECT COUNT(*) FROM fact_weather_reading;
```

### Check System Resources
Open Control Panel → View resource monitor in real-time

---

## ⚠️ Troubleshooting

### Issue: "Module not found"
```powershell
pip install <module-name>
# or reinstall all
pip install -r requirements.txt
```

### Issue: Dashboard shows old data
**Solution**: Dashboard caches are cleared automatically every 10s. Just wait.

### Issue: ETL stops after one run
**Solution**: This is fixed! ETL now runs continuously. Use Control Panel to start it.

### Issue: Can't see dropdown options
**Solution**: Hard refresh browser (Ctrl+Shift+R) after restarting dashboard.

### Issue: "Database is locked"
**Solution**: Use Control Panel to manage processes. It handles this automatically.

### Issue: High CPU usage
**Solution**: 
- Reduce sensor count: `--num-sensors 10`
- Increase interval: `--interval 10`

---

## 🔐 Important Notes

### Data Architecture

The system uses **TWO PARALLEL PATHS**:

**Path 1: Batch ETL (Primary)**
```
Sensor → CSV/JSONL Files → ETL → Data Warehouse → Dashboard
```

**Path 2: Streaming (Alerts Only)**
```
Sensor → Kafka → Consumer → Alert Database
```

**Key Principle**: Only ETL writes to the data warehouse. Kafka Consumer only creates alerts.

### Auto-Start Components

When you click "Run All":
1. ✅ Sensor Generator starts
2. ✅ ETL starts (continuous mode)
3. ✅ Kafka Broker starts
4. ✅ Kafka Consumer starts
5. ✅ Dashboard starts
6. ✅ ML Predictor runs once

### Database Tables

- **fact_weather_reading**: All sensor readings
- **dim_time**: Time dimension
- **dim_sensor**: Sensor metadata
- **dim_location**: City information
- **dim_status**: Reading status codes
- **alert_log**: Real-time alerts
- **ml_predictions**: Temperature forecasts

---

## 📚 Next Steps

1. ✅ **Read** [USER_GUIDE.md](USER_GUIDE.md) for detailed features
2. ✅ **Check** [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. ✅ **See** [API_REFERENCE.md](API_REFERENCE.md) for customization
4. ✅ **Review** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions

---

## 🎉 Success Checklist

- [ ] Dependencies installed
- [ ] Database initialized
- [ ] Control Panel opens
- [ ] "Run All" works
- [ ] Dashboard accessible at port 8050
- [ ] Data flowing (check dashboard counters)
- [ ] ML predictions generated

**All checked? Congratulations! Your IoT pipeline is operational! 🚀**

---

**Need Help?** Check the troubleshooting section or review the log files in the Control Panel.

**Version**: 2.0  
**Last Updated**: November 2025  
**Status**: Production Ready
