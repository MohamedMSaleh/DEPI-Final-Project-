# Real-time IoT Data Pipeline

**DEPI Final Project - Data Rangers Team**

A complete end-to-end real-time IoT data pipeline for weather sensor data, featuring data simulation, batch ETL processing, real-time streaming analytics, alerting, and visualization.

## Team Members

- Mustafa Elsebaey Mohamed
- Mohamed Mahmoud Saleh
- Yossef Mohamed Abdelhady
- Anas Ahmed Taha
- Nermeen Ayman Mosbah
- Farah Ayman Ahmed

## Project Overview

This project implements a production-ready IoT data pipeline that simulates weather sensor data from Egyptian cities and processes it through multiple stages:

1. **Data Simulation**: Realistic weather sensor data generation
2. **Batch ETL**: Extract, Transform, Load pipeline with data warehousing
3. **Streaming Analytics**: Real-time monitoring and alerting
4. **Visualization**: Interactive dashboard for insights

## Architecture

**✅ Corrected Architecture - Follows Strict ETL Requirements**

The project implements **TWO PARALLEL DATA PATHS**:

### **Path 1: Batch ETL Pipeline (Primary Data Path)**
```
📡 Sensor Generator → 📄 CSV/JSONL Files → ⚙️ Batch ETL → 💾 Data Warehouse → 📊 Dashboard
                                              ↓
                                    (Extract, Transform, Load)
                                    - Read raw files
                                    - Clean & aggregate
                                    - Flag anomalies
                                    - Load to warehouse
```

### **Path 2: Streaming Pipeline (Real-time Alerts)**
```
📡 Sensor Generator → 🔄 Kafka Broker → 💬 Kafka Consumer → 🚨 Alert Database
                                              ↓
                                    (Monitor & Alert ONLY)
                                    - Real-time monitoring
                                    - Threshold detection
                                    - Alert generation
                                    - NO warehouse writes
```

### **Complete Flow Diagram**
```
                    📡 SENSOR GENERATOR
                           |
                    Writes to BOTH paths
                    ┌──────┴──────┐
                    ↓             ↓
            📄 CSV FILES    🔄 KAFKA BROKER
                    ↓             ↓
            ⚙️ BATCH ETL   💬 KAFKA CONSUMER
         (Extract/Transform     (Monitor &
              /Load)            Alert Only)
                    ↓             ↓
            💾 DATA WAREHOUSE  🚨 ALERTS DB
         (sensor_readings,    (alert_log
          hourly_aggregates)   table only)
                    ↓
            ┌───────┴───────┐
            ↓               ↓
        🧠 ML PREDICTOR  📊 DASHBOARD
      (ml_predictions)  (Visualizations)
                    ↓
            📊 DASHBOARD
        (Shows predictions)
```

### **Key Architectural Principles**

1. **Batch ETL is Primary**: All data warehouse population via ETL
2. **Streaming for Alerts**: Kafka path monitors and alerts only
3. **No Dual Writes**: Only ETL writes to fact tables
4. **Clear Separation**: Batch vs. Streaming responsibilities
   │    - Dims: Time, Sensor, Location  │
   │    - Alerts Log                    │
   └──────────────┬─────────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │    Dashboard    │
         │    (Phase 4)    │
         └─────────────────┘
```

## Features

### Phase 1: Data Simulation ✅
- **Realistic Egyptian weather data** for 5 major cities (Cairo, Alexandria, Giza, Luxor, Aswan)
- **Temporal continuity** with smooth transitions between readings
- **Configurable anomaly injection** (spikes, stuck sensors, dropouts)
- **Multiple output formats**: JSONL and CSV
- **Optional Azure Event Hubs integration**
- Generates data every 5 seconds by default

### Phase 2: Batch ETL Pipeline ✅
- **Extract**: Reads from JSONL/CSV files
- **Transform**: 
  - Data cleaning and validation
  - Anomaly detection using statistical methods
  - Hourly aggregate computation
- **Load**: Populates star schema data warehouse
- **Star Schema Design**:
  - Fact table: `fact_weather_reading`
  - Dimensions: `dim_time`, `dim_sensor`, `dim_location`, `dim_status`
- Idempotent processing (can run multiple times safely)

### Phase 3: Streaming Analytics ✅
- **Apache Kafka Message Broker**: Production-grade message queue for real-time streaming
- **Dual monitoring modes**:
  - **Kafka Consumer**: Real-time message processing from Kafka topics
  - **File Watcher**: Monitors JSONL/CSV files for changes
- **Alert rules**:
  - High Temperature (> 40°C) - CRITICAL
  - Low Temperature (< 0°C) - WARNING
  - Low Humidity (< 20%) - WARNING
  - High Humidity (> 90%) - WARNING
  - High Wind Speed (> 50 km/h) - WARNING
  - Abnormal Pressure (< 980 or > 1040 hPa) - WARNING
- **Alert logging** to database
- **Pub/Sub architecture** with topic-based messaging

### Phase 4: Dashboard & Visualization ✅
- **Real-time dashboard** with auto-refresh
- **Metrics displayed**:
  - System statistics (total readings, sensors, anomalies, alerts)
  - Temperature trends over time
  - Latest sensor readings table
  - Temperature distribution histogram
  - Recent alerts log
  - Readings by city
  - Data quality status (pie chart)
- Auto-refreshes every 5 seconds

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Step 1: Clone Repository

```bash
cd DEPI-Final-Project-
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- pandas >= 2.0.0
- numpy >= 1.24.0
- matplotlib >= 3.7.0
- seaborn >= 0.12.0
- sqlalchemy >= 2.0.0
- python-dotenv >= 1.0.0
- pytz >= 2023.3
- schedule >= 1.2.0
- watchdog >= 6.0.0

### Step 3: Initialize Database

```bash
python database\schema.py
```

This creates:
- SQLite database at `database/iot_warehouse.db`
- All dimension and fact tables
- Pre-populated status codes

## Usage

### 1. Generate Sensor Data

Run the sensor data generator:

```bash
python sensor_generator.py --num-sensors 20 --duration 300 --interval 5
```

**Arguments:**
- `--num-sensors`: Number of sensors to simulate (default: 20)
- `--duration`: Run duration in seconds (default: unlimited)
- `--interval`: Interval between readings in seconds (default: 5)
- `--output-dir`: Output directory for files (default: `output`)
- `--seed`: Random seed for reproducibility

**Output:**
- `output/sensor_data.jsonl`: JSONL format
- `output/sensor_data.csv`: CSV format
- `sensor_generator.log`: Generator logs

### 2. Run Batch ETL Pipeline

Process the generated data:

```bash
python etl\batch_etl.py
```

**What it does:**
1. Extracts data from JSONL and CSV files
2. Cleans and validates data
3. Detects anomalies using z-score analysis
4. Computes hourly aggregates
5. Loads data into data warehouse

**Output:**
- Data loaded into `database/iot_warehouse.db`
- Hourly aggregates saved to `processed/hourly_aggregates.csv`
- ETL logs in `etl_pipeline.log`

### 3. Start Streaming Consumer

#### Option A: Kafka Message Queue (Recommended)

Start Kafka consumer for real-time streaming:

```bash
python streaming\kafka_consumer.py
```

**What it does:**
1. Connects to in-memory Kafka broker
2. Consumes messages from `sensor_data` topic in real-time
3. Checks readings against 7 alert rules
4. Logs alerts to database with full context
5. Runs continuously until stopped (Ctrl+C)

**Benefits:**
- Production-grade message queue architecture
- Decoupled producer/consumer design
- Better scalability and fault tolerance
- Demonstrates enterprise streaming patterns

#### Option B: File Watcher (Alternative)

Monitor file changes for real-time alerts:

```bash
python streaming\streaming_consumer.py
```

**What it does:**
1. Monitors `output/` directory for new data
2. Processes JSONL/CSV files as they're modified
3. Checks readings against alert rules
4. Logs alerts to database and console

**Output:**
- Alerts logged to database `alert_log` table
- Console output with alert notifications
- Streaming logs in `kafka_streaming.log` or `streaming_pipeline.log`

### 4. Launch Dashboard

View visualizations:

```bash
python dashboard\simple_dashboard.py
```

**What it does:**
1. Queries data warehouse for latest metrics
2. Generates interactive visualizations
3. Auto-refreshes every 5 seconds
4. Press Ctrl+C to exit

### Complete Workflow Example

#### Kafka-Based Real-Time Pipeline (Recommended)

Run all components in separate terminals:

**Terminal 1** - Generate data with Kafka:
```bash
python sensor_generator.py --use-kafka --num-sensors 10 --interval 5
```

**Terminal 2** - Consume from Kafka:
```bash
python streaming\kafka_consumer.py
```

**Terminal 3** - Run ETL periodically:
```bash
python etl\batch_etl.py
```

**Terminal 4** - View dashboard:
```bash
python dashboard\advanced_dashboard.py
```

#### File-Based Pipeline (Alternative)

**Terminal 1** - Generate data to files:
```bash
python sensor_generator.py --num-sensors 10 --interval 5
```

**Terminal 2** - Monitor files for alerts:
```bash
python streaming\streaming_consumer.py
```

**Terminal 3** - Run ETL periodically:
```bash
python etl\batch_etl.py
```

**Terminal 4** - View dashboard:
```bash
python dashboard\advanced_dashboard.py
```

## Project Structure

```
DEPI-Final-Project-/
│
├── sensor_generator.py          # Phase 1: Data generation
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
├── database/
│   ├── schema.py               # Star schema definition
│   ├── __init__.py
│   └── iot_warehouse.db        # SQLite database (created at runtime)
│
├── etl/
│   ├── batch_etl.py            # Phase 2: ETL pipeline
│   ├── __init__.py
│   └── etl_pipeline.log        # ETL logs
│
├── streaming/
│   ├── streaming_consumer.py   # Phase 3: Real-time monitoring
│   └── streaming_pipeline.log  # Streaming logs
│
├── dashboard/
│   └── simple_dashboard.py     # Phase 4: Visualization
│
├── output/                      # Generated sensor data
│   ├── sensor_data.jsonl
│   ├── sensor_data.csv
│   └── sensor_generator.log
│
├── processed/                   # Processed data
│   └── hourly_aggregates.csv
│
└── docs/
    └── PROJECT_DOCUMENTATION.md # Detailed documentation
```

## Data Warehouse Schema

### Star Schema Design

**Fact Table: fact_weather_reading**
- reading_id (PK)
- time_id (FK)
- sensor_id (FK)
- location_id (FK)
- status_id (FK)
- temperature, humidity, pressure, wind_speed, wind_direction, rainfall
- is_anomaly, anomaly_type
- ingestion_ts, processing_latency_ms
- signal_strength, reading_quality

**Dimension Tables:**

1. **dim_time**: Temporal analysis
   - time_id (PK), ts, date, year, month, day, hour, minute, second, day_of_week, is_weekend

2. **dim_sensor**: Sensor metadata
   - sensor_id (PK), sensor_type, sensor_model, manufacturer, firmware_version, is_active

3. **dim_location**: Geographic data
   - location_id (PK), city_name, region, country, lat, lon, altitude, location_code

4. **dim_status**: Reading status
   - status_id (PK), status_code, description

**Additional Table: alert_log**
- Stores real-time alerts with timestamps, severity, and resolution status

## Sample Queries

### Get Latest Readings by City

```sql
SELECT 
    dt.ts,
    ds.sensor_id,
    dl.city_name,
    f.temperature,
    f.humidity,
    f.is_anomaly
FROM fact_weather_reading f
JOIN dim_time dt ON f.time_id = dt.time_id
JOIN dim_sensor ds ON f.sensor_id = ds.sensor_id
JOIN dim_location dl ON f.location_id = dl.location_id
ORDER BY dt.ts DESC
LIMIT 10;
```

### Get Hourly Average Temperature by City

```sql
SELECT 
    dl.city_name,
    dt.hour,
    AVG(f.temperature) as avg_temp,
    COUNT(*) as reading_count
FROM fact_weather_reading f
JOIN dim_time dt ON f.time_id = dt.time_id
JOIN dim_location dl ON f.location_id = dl.location_id
GROUP BY dl.city_name, dt.hour
ORDER BY dl.city_name, dt.hour;
```

### Get Alert Summary

```sql
SELECT 
    alert_type,
    alert_severity,
    COUNT(*) as alert_count
FROM alert_log
WHERE alert_ts >= datetime('now', '-24 hours')
GROUP BY alert_type, alert_severity
ORDER BY alert_count DESC;
```

## Configuration

### Modifying Alert Thresholds

Edit `streaming/streaming_consumer.py`:

```python
ALERT_RULES = [
    AlertRule('HIGH_TEMP', 'temperature', '>', 40.0, 'CRITICAL'),
    AlertRule('LOW_TEMP', 'temperature', '<', 0.0, 'WARNING'),
    # Add or modify rules as needed
]
```

### Changing Data Generation Settings

Edit sensor_generator.py or use command-line arguments:

```bash
# Change interval to 10 seconds
python sensor_generator.py --interval 10

# Generate for 1 hour (3600 seconds)
python sensor_generator.py --duration 3600

# Use specific random seed
python sensor_generator.py --seed 42
```

## Troubleshooting

### Issue: Database locked error

**Solution**: Make sure only one process is writing to the database at a time. Close the dashboard before running ETL, or use separate database connections.

### Issue: No data in dashboard

**Solution**: 
1. Ensure data has been generated: check `output/sensor_data.jsonl`
2. Run ETL pipeline: `python etl\batch_etl.py`
3. Verify database has data: check `database/iot_warehouse.db`

### Issue: Streaming consumer not detecting changes

**Solution**: 
1. Make sure watchdog is installed: `pip install watchdog`
2. Verify the output directory path is correct
3. Check file permissions

### Issue: Import errors

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# If still failing, install individually
pip install pandas numpy matplotlib seaborn sqlalchemy watchdog schedule
```

## Performance Considerations

- **Batch Size**: ETL commits every 100 records for optimal performance
- **Dashboard Refresh**: Default 5 seconds; increase for slower systems
- **Data Retention**: Implement data archival for large datasets
- **Indexing**: Key columns are indexed for fast queries

## Future Enhancements

- [ ] Azure Event Hubs integration for cloud streaming
- [ ] Apache Airflow DAG for scheduled ETL
- [ ] Machine learning for anomaly prediction
- [ ] Web-based dashboard (Flask/Streamlit)
- [ ] Docker containerization
- [ ] Kubernetes deployment
- [ ] Advanced analytics with time-series forecasting

## License

This project is part of the DEPI Final Project curriculum.

## Acknowledgments

- Egyptian climate data references
- SQLAlchemy documentation
- Python data engineering best practices

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review log files for errors
3. Contact team members

---

**Built with ❤️ by Data Rangers Team**
