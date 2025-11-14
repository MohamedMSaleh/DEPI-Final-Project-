Real-time IoT Data Pipeline — Proposal
Executive summary
We will build a real-time IoT data pipeline that simulates sensor data for temperature, humidity, and CO2. The pipeline will ingest events in real time, process data in batch for cleaning and aggregation, and run streaming checks to generate alerts. A simple dashboard will show live metrics and recent alerts. The generator will write logs in JSONL and CSV and can send events to Azure Event Hubs or to local files.
Objectives
• Simulate realistic IoT sensor data.
• Provide reliable ingestion using files or Azure Event Hubs.
• Clean and aggregate data in batch.
• Detect and alert on simple anomalies in streaming.
• Provide a simple dashboard for monitoring.
Scope
In scope:
• Sensor generator in Python that writes JSONL and CSV and can publish to Event Hubs.
• Batch ETL that cleans data, computes aggregates, and flags anomalies.
• Streaming consumer that evaluates alerts.
• Streamlit dashboard to view live metrics and alerts.
Out of scope:
• Full enterprise deployment and advanced production hardening.
• Advanced machine learning models.
Deliverables
1. sensor_generator.py with command line options for interval, number of sensors, duration, output folder, and Event Hubs connection.
2. Batch ETL scripts and a notebook that clean data, compute hourly aggregates, and mark anomalies.
3. Streaming consumer that reads events and emits alerts.
4. Streamlit dashboard that shows live metrics and recent alerts.
5. README with run instructions and how to switch between Azure and local modes.
3-week timeline
Week 1 — Generator and ingestion: Implement the Python generator, produce sample JSONL and CSV files, and add Event Hubs option.
Week 2 — Batch ETL and storage: Implement data cleaning, compute aggregates, flag anomalies, and store cleaned data in Azure Blob or local files.
Week 3 — Streaming and dashboard: Implement streaming alerts and build a Streamlit dashboard that displays live metrics and recent alerts.
Tools and how we will use them
• Python 3.10 or higher for the generator, ETL, and streaming code.
• Azure Event Hubs for streaming ingestion.
• Azure Stream Analytics or Azure Functions for streaming rules and alerts.
• Azure Blob Storage or Azure Data Lake to store raw and processed data.
• Pandas and Jupyter for batch ETL and data exploration.
• Streamlit for a lightweight dashboard.
• Git and GitHub for source control.
Fallback options: local files for ingestion, or local Kafka for streaming if Azure is not available.
Success criteria
• The generator produces valid JSONL and CSV files with timestamps and sensor identifiers.
• The ETL produces cleaned tables and hourly aggregates.
• The streaming job detects threshold breaches and writes alert logs.
• The dashboard shows current metrics and recent alerts.
Data warehouse design — Star schema
We will use a star schema with one fact table for sensor readings and four dimension tables for time, sensor, location, and status.
ERD diagram (simple):
    DIM_TIME
       |
DIM_LOCATION ---< FACT_SENSOR_READING >--- DIM_SENSOR
       |
    DIM_STATUS
Fact table: fact_sensor_reading
Columns:
• reading_id INT
• time_id INT
• sensor_id VARCHAR
• location_id INT
• status_id INT
• value FLOAT
• unit VARCHAR
• seq BIGINT
• is_anomaly BOOLEAN
• anomaly_type VARCHAR
• ingestion_ts TIMESTAMP
• processing_latency_ms INT
Dimension table: dim_time
Columns:
• time_id INT
• ts TIMESTAMP
• date DATE
• year INT
• month INT
• day INT
• hour INT
• minute INT
• second INT
• day_of_week INT
• is_weekend BOOLEAN
Dimension table: dim_sensor
Columns:
• sensor_id VARCHAR
• sensor_type VARCHAR
• sensor_model VARCHAR
• manufacturer VARCHAR
• install_date DATE
• firmware_version VARCHAR
• is_active BOOLEAN
• notes TEXT
Dimension table: dim_location
Columns:
• location_id INT
• site VARCHAR
• zone VARCHAR
• lat FLOAT
• lon FLOAT
• floor VARCHAR
• building VARCHAR
• location_code VARCHAR
Dimension table: dim_status
Columns:
• status_id INT
• status_code VARCHAR
• description VARCHAR
Mapping from JSON/CSV to warehouse
timestamp -> dim_time.ts and fact_sensor_reading.time_id
sensor_id -> dim_sensor.sensor_id and fact_sensor_reading.sensor_id
sensor_type -> dim_sensor.sensor_type
value -> fact_sensor_reading.value
unit -> fact_sensor_reading.unit
metadata.location -> dim_location.location_code and fact_sensor_reading.location_id
metadata.lat -> dim_location.lat
metadata.lon -> dim_location.lon
status -> dim_status.status_code and fact_sensor_reading.status_id
seq -> fact_sensor_reading.seq
ingestion timestamp -> fact_sensor_reading.ingestion_ts (added by pipeline)
Example JSON event
{
 "timestamp": "2025-09-01T17:37:42.379229+03:00",
 "sensor_id": "temp_000",
 "sensor_type": "temperature",
 "value": 20.886,
 "unit": "C",
 "metadata": {"lat": 29.9986278, "lon": 31.0047304, "location": "site/zone1", "site_id": 1, "zone_id": 1},
 "status": "OK",
 "seq": 1,
 "battery_level": 94,
 "firmware_version": "v1.2.0",
 "sensor_model": "T1000",
 "manufacturer": "AcmeSensors",
 "signal_strength": -65,
 "reading_quality": 0.98,
 "is_simulated": true,
 "event_type": "measurement"
}

