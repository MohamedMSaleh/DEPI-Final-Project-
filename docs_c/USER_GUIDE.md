# User Guide - IoT Weather Monitoring System

**Comprehensive guide to using all system features**

---

## Table of Contents

1. [Control Panel Overview](#control-panel-overview)
2. [Dashboard Features](#dashboard-features)
3. [Data Generation](#data-generation)
4. [Machine Learning Predictions](#machine-learning-predictions)
5. [Alert System](#alert-system)
6. [Database Management](#database-management)
7. [Best Practices](#best-practices)

---

## Control Panel Overview

### Main Interface

The Control Panel is your central command center with 4 main tabs:

#### 1. **Components Tab**

**Component List:**
- **Sensor Generator**: Simulates weather data every 5 seconds
- **Batch ETL**: Processes data every 60 seconds (continuous)
- **Kafka Broker**: In-memory message queue
- **Kafka Consumer**: Real-time alert monitoring
- **Advanced Dashboard**: Web dashboard on port 8050
- **ML Predictor**: Temperature forecasting (on-demand)

**Status Indicators:**
- 🟢 **Green**: Running
- 🔴 **Red**: Stopped
- 🟡 **Yellow**: Starting/Stopping

**Actions per Component:**
- **Start**: Launch the component
- **Stop**: Gracefully shut down
- **Restart**: Stop and start again
- **View Logs**: See output in real-time

**Global Actions:**
- **Run All**: Starts all auto-start components
- **Stop All**: Stops everything
- **Restart All**: Full system restart

#### 2. **System Monitor Tab**

**Resource Metrics:**
- **CPU Usage**: Real-time percentage
- **Memory Usage**: RAM consumption
- **Disk Usage**: Storage space
- **Network I/O**: (if applicable)

**Process Information:**
- PID (Process ID)
- Uptime
- Memory per process
- CPU per process

#### 3. **Database Tab**

**Statistics Panel:**
- Total readings
- Total predictions
- Total alerts
- Active sensors
- Data freshness (last reading time)

**Management Actions:**
- **View Stats**: Refresh database counts
- **Backup Database**: Create timestamped backup
- **Clean Old Data**: Remove data older than N days
- **Verify System**: Run integrity checks

#### 4. **Pipeline Flow Tab**

**Visual Diagram:**
Shows the complete data flow from sensor to dashboard with color-coded stages:

```
[Sensor Gen] → [Files] → [ETL] → [Warehouse] → [ML] → [Dashboard]
                   ↓
              [Kafka] → [Alerts]
```

**Stage Colors:**
- 🟢 Green: Component running
- ⚪ Gray: Component stopped
- 🔵 Blue: Data storage
- 🔴 Red: Error state

---

## Dashboard Features

### Accessing the Dashboard

**URL**: http://127.0.0.1:8050

**Auto-refresh**: Every 10 seconds (real-time data)

### Dashboard Panels

#### 1. **Header Section**
- **System Title**: "IoT Weather Monitoring System"
- **Active Sensors**: Green badge showing count
- **Open Alerts**: Yellow badge showing unresolved alerts
- **Auto-refresh indicator**: Updates every 10 seconds

#### 2. **Control Panel**
- **Select City**: Dropdown to filter by city (Cairo, Alexandria, etc.)
- **Time Range**: Filter data (Last Hour, 6 Hours, 24 Hours, 7 Days, All Time)
- **Refresh Button**: Manual refresh trigger

#### 3. **KPI Cards** (Top Row)
Six metrics cards showing:
- **Total Readings**: Count of all sensor readings
- **Anomalies**: Number of flagged unusual readings
- **Observed Range**: Min to max temperature
- **Avg Humidity**: Average humidity percentage
- **Avg Wind Speed**: Average wind in km/h
- **Avg Pressure**: Average pressure in hPa

#### 4. **Temperature Trends Chart**
- **Type**: Line chart
- **X-axis**: Time
- **Y-axis**: Temperature (°C)
- **Legend**: One line per city
- **Interactivity**: Hover for exact values, zoom, pan

#### 5. **Current Readings Panel**
Shows latest reading for selected city:
- **Large temperature display**: Current temp in °C
- **Humidity**: With icon
- **Wind Speed**: With icon
- **Pressure**: With icon
- **Last updated**: Timestamp

#### 6. **ML Predictions Chart**
- **Blue line**: Historical actual temperatures
- **Orange line**: AI predictions for next 24 hours
- **X-axis**: Date and time
- **Y-axis**: Temperature (°C)
- **Shows**: Past data + future forecast

#### 7. **Model Performance Panel**
- **MAE (Mean Absolute Error)**: Prediction accuracy
- **Predictions Count**: Number of forecasts
- **Last Prediction**: Timestamp
- **Model Info**: Prophet algorithm details

#### 8. **Gauge Charts** (4 gauges)
- **Temperature Gauge**: Average temp with color zones
- **Humidity Gauge**: Average humidity
- **Wind Speed Gauge**: Average wind
- **Pressure Gauge**: Average pressure

#### 9. **City Comparison Chart**
- **Type**: Bar chart
- **Shows**: Average temperature per city
- **Purpose**: Compare cities at a glance

#### 10. **Temperature Distribution**
- **Type**: Histogram
- **Shows**: Frequency distribution of temperatures
- **Purpose**: Identify temperature patterns

#### 11. **Recent Alerts Table**
Displays last 10 alerts with:
- **Time**: When alert occurred
- **Severity**: CRITICAL, WARNING, INFO
- **Type**: HIGH_TEMP, LOW_HUMIDITY, etc.
- **Sensor ID**: Which sensor triggered
- **Message**: Alert description

#### 12. **Recent Readings Table**
Shows last 20 readings:
- Timestamp
- Sensor ID
- City
- Temperature
- Humidity
- Wind Speed
- Status

### Dashboard Interactions

**Filtering:**
1. Select a city from dropdown
2. Choose time range
3. Data updates automatically

**Refreshing:**
- Auto-refresh: Every 10 seconds
- Manual: Click "Refresh Now" button
- Browser: Ctrl+Shift+R for hard refresh

**Responsive Design:**
- Works on desktop (recommended)
- Tablets (partial support)
- Mobile (limited, not optimized)

---

## Data Generation

### Sensor Generator Configuration

**Command-line options:**

```powershell
python sensor_generator.py [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--num-sensors` | 20 | Number of sensors (1-100) |
| `--interval` | 5 | Seconds between readings |
| `--duration` | unlimited | Run duration in seconds |
| `--output-dir` | output | Output directory path |
| `--seed` | random | Random seed for reproducibility |
| `--use-kafka` | False | Publish to Kafka broker |

**Examples:**

```powershell
# Generate data for 10 minutes with 15 sensors
python sensor_generator.py --num-sensors 15 --duration 600

# Fast generation (every 2 seconds)
python sensor_generator.py --interval 2

# Reproducible data (same seed = same data)
python sensor_generator.py --seed 42
```

### Data Output

**Files created:**
- `output/sensor_data.csv`: CSV format
- `output/sensor_data.jsonl`: JSON Lines format
- `logs/sensor_generator.log`: Generation logs

**Data format (CSV):**
```csv
timestamp,sensor_id,temperature,humidity,pressure,wind_speed,wind_direction,rainfall,city,lat,lon
2025-11-29T14:30:00,ws_cairo_001,25.3,48.2,1012.5,12.3,NE,0.0,Cairo,30.0444,31.2357
```

**Data format (JSONL):**
```json
{
  "timestamp": "2025-11-29T14:30:00+02:00",
  "sensor_id": "ws_cairo_001",
  "value": {
    "temperature": 25.3,
    "humidity": 48.2,
    "pressure": 1012.5,
    "wind_speed": 12.3,
    "wind_direction": "NE",
    "rainfall": 0.0
  },
  "metadata": {
    "city": "Cairo",
    "lat": 30.0444,
    "lon": 31.2357
  }
}
```

### Weather Simulation

**Cities covered:**
- **Cairo**: 30.04°N, 31.24°E (Day: 28°C, Night: 18°C)
- **Alexandria**: 31.20°N, 29.92°E (Day: 26°C, Night: 20°C)
- **Giza**: 30.01°N, 31.21°E (Day: 29°C, Night: 19°C)
- **Luxor**: 25.69°N, 32.64°E (Day: 35°C, Night: 22°C)
- **Aswan**: 24.09°N, 32.90°E (Day: 38°C, Night: 24°C)

**Realistic features:**
- **Daily cycles**: Coldest at 5 AM, warmest at 2 PM
- **Geographic accuracy**: Hotter in south (Luxor, Aswan)
- **Humidity correlation**: Inverse to temperature
- **Smooth transitions**: No sudden jumps
- **Wind patterns**: Gradual direction changes

---

## Machine Learning Predictions

### Temperature Predictor

**Purpose**: Forecast next 24 hours of temperature per city

**Algorithm**: Facebook Prophet
- Time-series forecasting
- Handles seasonality
- Robust to missing data
- Confidence intervals included

### Running Predictions

**Via Control Panel:**
1. Click "ML Predictor" in Components tab
2. Click "Start" or "Run Once"
3. Wait 30-60 seconds
4. Check dashboard for predictions

**Via Command Line:**
```powershell
python ml\temperature_predictor.py
```

**Output:**
```
🧠 TEMPERATURE PREDICTION SYSTEM
================================
✅ Prophet library available

Training model for Cairo...
✅ Model trained: 45 historical readings
📊 Predictions generated: 24 hours ahead
💾 Saved to database: 24 predictions

Training model for Alexandria...
...

🎯 PREDICTION SUMMARY
Total Cities: 5
Total Predictions: 120
Timestamp: 2025-11-29 14:30:00

✅ All predictions saved to database
```

### Viewing Predictions

**In Dashboard:**
- **ML Predictions Chart**: Orange line shows forecasts
- **Model Performance Panel**: Shows accuracy metrics

**In Database:**
```sql
SELECT * FROM ml_predictions 
WHERE city_name = 'Cairo' 
ORDER BY prediction_time DESC 
LIMIT 24;
```

### Prediction Accuracy

**Metrics:**
- **MAE (Mean Absolute Error)**: Average prediction error in °C
- **Typical MAE**: 1-2°C for good models
- **Updates**: Run predictor daily for best results

---

## Alert System

### Alert Rules

The system monitors 7 conditions:

| Alert Type | Metric | Condition | Threshold | Severity |
|-----------|--------|-----------|-----------|----------|
| HIGH_TEMP | Temperature | > | 40°C | CRITICAL |
| LOW_TEMP | Temperature | < | 0°C | WARNING |
| HIGH_HUMIDITY | Humidity | > | 90% | WARNING |
| LOW_HUMIDITY | Humidity | < | 20% | WARNING |
| HIGH_WIND | Wind Speed | > | 50 km/h | WARNING |
| UNUSUAL_PRESSURE | Pressure | < or > | 980-1040 hPa | WARNING |
| ANOMALY | Statistical | Z-score | > 3σ | INFO |

### Alert Processing

**Kafka Consumer (Real-time):**
- Monitors Kafka message stream
- Checks each reading against rules
- Creates alerts in database
- Runs continuously

**Start Consumer:**
```powershell
python streaming\kafka_consumer.py
```

**Console output:**
```
🔔 ALERT: HIGH_TEMP
Sensor: ws_luxor_003
Value: 42.5°C > 40.0°C
Severity: CRITICAL
```

### Viewing Alerts

**In Dashboard:**
- **Recent Alerts Panel**: Shows last 10 alerts
- **Header Badge**: Shows count of unresolved alerts

**In Database:**
```sql
SELECT * FROM alert_log 
WHERE is_resolved = FALSE 
ORDER BY alert_ts DESC;
```

**Via Control Panel:**
- Database tab shows total alert count
- View logs for real-time alerts

### Customizing Alert Rules

Edit `streaming/kafka_consumer.py`:

```python
ALERT_RULES = [
    AlertRule('HIGH_TEMP', 'temperature', '>', 45.0, 'CRITICAL'),  # Changed to 45°C
    AlertRule('LOW_TEMP', 'temperature', '<', -5.0, 'WARNING'),   # Changed to -5°C
    # Add new rules here
]
```

---

## Database Management

### Database Schema

**Location**: `database/iot_warehouse.db` (SQLite)

**Tables:**

1. **fact_weather_reading** (Fact Table)
   - reading_id (PK)
   - time_id, sensor_id, location_id, status_id (FKs)
   - temperature, humidity, pressure, wind_speed, etc.
   - is_anomaly, anomaly_type

2. **dim_time** (Time Dimension)
   - time_id (PK)
   - ts, date, year, month, day, hour, minute
   - day_of_week, is_weekend

3. **dim_sensor** (Sensor Dimension)
   - sensor_id (PK)
   - sensor_type, model, manufacturer
   - is_active

4. **dim_location** (Location Dimension)
   - location_id (PK)
   - city_name, region, country
   - lat, lon, altitude

5. **dim_status** (Status Dimension)
   - status_id (PK)
   - status_code, description

6. **alert_log** (Alerts)
   - alert_id (PK)
   - alert_ts, sensor_id, alert_type
   - severity, message
   - is_resolved

7. **ml_predictions** (ML Forecasts)
   - prediction_id (PK)
   - city_name, prediction_time
   - predicted_temperature
   - created_at

### Database Operations

**View Statistics (Control Panel):**
1. Go to Database tab
2. Click "View Stats"
3. See table row counts

**Backup Database:**
1. Database tab → "Backup Database"
2. Creates: `database/backups/iot_warehouse_YYYYMMDD_HHMMSS.db`

**Clean Old Data:**
1. Database tab → "Clean Old Data"
2. Enter number of days to keep
3. Removes readings older than specified

**Direct SQL Access:**
```powershell
sqlite3 database\iot_warehouse.db

# Example queries
.schema fact_weather_reading
SELECT COUNT(*) FROM fact_weather_reading;
SELECT city_name, AVG(temperature) FROM fact_weather_reading 
  JOIN dim_location ON fact_weather_reading.location_id = dim_location.location_id
  GROUP BY city_name;
```

---

## Best Practices

### System Operation

1. **Use Control Panel** for all operations (recommended)
2. **Run All** at startup for quick launch
3. **Monitor logs** for errors
4. **Check database stats** periodically
5. **Backup database** before major changes

### Data Generation

1. **Start with defaults** (20 sensors, 5-second interval)
2. **Use reproducible seeds** for testing (`--seed 42`)
3. **Monitor disk space** (data grows ~1MB/hour)
4. **Limit duration** for testing (`--duration 300`)

### ETL Processing

1. **Let ETL run continuously** (every 60 seconds)
2. **Don't manually stop ETL** (use Control Panel)
3. **Check processed/** folder for aggregates
4. **Monitor ETL logs** for errors

### Dashboard Usage

1. **Filter by city** for focused analysis
2. **Use time ranges** to zoom in/out
3. **Refresh browser** if data seems stale (Ctrl+Shift+R)
4. **Check auto-refresh** is working (10-second updates)

### ML Predictions

1. **Run predictor daily** for freshest forecasts
2. **Verify sufficient history** (need 30+ days for best results)
3. **Check MAE** to evaluate accuracy
4. **Retrain after system changes**

### Alert Management

1. **Keep Kafka Consumer running** for real-time alerts
2. **Review alerts regularly** in dashboard
3. **Adjust thresholds** based on your needs
4. **Mark alerts resolved** when addressed

### Performance Optimization

1. **Reduce sensor count** if CPU high (`--num-sensors 10`)
2. **Increase interval** if disk I/O high (`--interval 10`)
3. **Clean old data** monthly (keep last 30 days)
4. **Close unused dashboard tabs**

### Troubleshooting

1. **Check logs first** (Control Panel or log files)
2. **Check Control Panel** status indicators
3. **Restart components** individually before "Restart All"
4. **Hard refresh browser** for dashboard issues
5. **Reinstall packages** if import errors

---

## Advanced Features

### Custom Sensor Types

Edit `sensor_generator.py` to add new sensor types:

```python
SENSOR_TYPES = {
    'weather_station': {...},
    'air_quality': {  # New type
        'temperature': (15, 35),
        'pm25': (0, 150),
        'co2': (400, 1000)
    }
}
```

### Custom Visualizations

Create new dashboard panels by editing `dashboard/advanced_dashboard.py`:

```python
# Add new callback
@app.callback(
    Output('my-custom-chart', 'figure'),
    [Input('interval-update', 'n_intervals')]
)
def update_custom_chart(n):
    # Your visualization logic
    return figure
```

### Kafka Topics

Default topic: `sensor_data`

Add new topics in `streaming/kafka_broker.py`:

```python
TOPICS = ['sensor_data', 'alerts', 'predictions']  # Add more topics
```

### Scheduled Tasks

ETL runs automatically every 60 seconds (continuous mode).

To change interval, edit `etl/batch_etl.py`:

```python
time.sleep(60)  # Change to desired seconds
```

---

## Quick Reference

### Essential Commands

```powershell
# Start Control Panel
python control_panel.py

# Generate data
python sensor_generator.py

# Run ETL manually
python etl\batch_etl.py

# Start dashboard
python dashboard\advanced_dashboard.py

# Run ML predictor
python ml\temperature_predictor.py

# Open Control Panel
python control_panel.py
```

### Important URLs

- **Dashboard**: http://127.0.0.1:8050
- **Dashboard V2**: http://127.0.0.1:8051

### Key File Locations

- **Database**: `database/iot_warehouse.db`
- **Data files**: `output/sensor_data.csv` and `.jsonl`
- **Aggregates**: `processed/hourly_aggregates.csv`
- **Logs**: `logs/` directory
- **Backups**: `database/backups/`

### Status Codes

- **OK**: Normal reading
- **SPIKE**: Anomalous value (z-score > 3)
- **STUCK**: Sensor reporting identical values
- **DROPOUT**: Missing data
- **RECOVERED**: Sensor back online

---

**Version**: 2.0  
**Last Updated**: November 2025  
**Status**: Production Ready

**Need more help?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or [ARCHITECTURE.md](ARCHITECTURE.md)
