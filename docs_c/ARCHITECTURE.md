# System Architecture - IoT Weather Monitoring System

**Technical architecture documentation and design decisions**

---

## Table of Contents

1. [Overview](#overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Database Design](#database-design)
5. [Technology Stack](#technology-stack)
6. [Design Decisions](#design-decisions)
7. [Scalability](#scalability)

---

## Overview

### Architecture Style

**Type**: Layered Architecture with Event-Driven Components

**Key Characteristics:**
- ✅ Separation of concerns
- ✅ Loosely coupled components
- ✅ Event-driven real-time processing
- ✅ Batch processing for analytics
- ✅ Star schema data warehouse

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Control    │  │  Dashboard   │  │ Dashboard V2 │     │
│  │    Panel     │  │   (Port      │  │   (Port      │     │
│  │   (Tkinter)  │  │    8050)     │  │    8051)     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Batch ETL  │  │   Kafka      │  │  ML Predict  │     │
│  │ (Continuous) │  │  Consumer    │  │   (Prophet)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   INTEGRATION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │    Kafka     │  │    File      │                        │
│  │   Broker     │  │   System     │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   SQLite     │  │     CSV      │  │    JSONL     │     │
│  │  Warehouse   │  │    Files     │  │    Files     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     SOURCE LAYER                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │            Sensor Generator (Simulated)          │      │
│  │         Generates weather data every 5s           │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Sensor Generator

**Purpose**: Simulate realistic IoT weather sensors

**Technology**: Python 3.14

**Key Features:**
- Generates data for 5 Egyptian cities
- Realistic daily temperature cycles
- Smooth temporal transitions
- Configurable anomaly injection
- Dual output (CSV + JSONL)
- Optional Kafka publishing

**Output Rate**: Every 5 seconds (configurable)

**Data Volume**: ~70KB/hour for 20 sensors

**Location**: `sensor_generator.py`

---

### 2. Batch ETL Pipeline

**Purpose**: Extract, Transform, Load data into warehouse

**Technology**: Python + Pandas + SQLAlchemy

**Mode**: Continuous (runs every 60 seconds)

**ETL Stages:**

**Extract:**
- Read CSV files from `output/`
- Read JSONL files from `output/`
- Parse JSON structures
- Combine data sources
- Deduplicate by (timestamp, sensor_id)

**Transform:**
- **Data Cleaning**:
  - Convert timestamps to datetime
  - Validate numeric ranges
  - Handle missing values
  - Remove invalid records

- **Anomaly Detection**:
  - Z-score analysis (3σ threshold)
  - Stuck sensor detection
  - Status code assignment

- **Aggregation**:
  - Hourly metrics per sensor/location
  - Mean, min, max, stddev
  - Anomaly counts

**Load:**
- Populate dimension tables (SCD Type 1)
- Insert fact records
- Batch commit (every 100 records)
- Update processing metadata

**Performance**: ~104 records/second

**Location**: `etl/batch_etl.py`

---

### 3. Kafka Message Broker

**Purpose**: In-memory message queue for real-time streaming

**Technology**: Custom Python implementation

**Features:**
- Topic-based pub/sub
- Multiple consumer support
- Thread-safe operations
- Memory-efficient queues

**Topics:**
- `sensor_data`: Primary data stream

**Location**: `streaming/kafka_broker.py`

---

### 4. Kafka Consumer

**Purpose**: Real-time alert monitoring ONLY

**Technology**: Python + Threading

**Role**: **ALERTS ONLY** (does NOT write to warehouse)

**Alert Rules (7 total):**
1. HIGH_TEMP: > 40°C
2. LOW_TEMP: < 0°C
3. HIGH_HUMIDITY: > 90%
4. LOW_HUMIDITY: < 20%
5. HIGH_WIND: > 50 km/h
6. UNUSUAL_PRESSURE: < 980 or > 1040 hPa
7. ANOMALY: Statistical outlier

**Process:**
1. Subscribe to Kafka topic
2. Receive reading
3. Check against alert rules
4. Create alert if threshold breached
5. Log to `alert_log` table

**Latency**: < 100ms

**Location**: `streaming/kafka_consumer.py`

---

### 5. Machine Learning Predictor

**Purpose**: Forecast next 24 hours of temperature

**Technology**: Facebook Prophet

**Algorithm Details:**
- Time-series forecasting
- Additive model: y(t) = g(t) + s(t) + h(t) + ε
  - g(t): trend
  - s(t): seasonality
  - h(t): holidays/events
  - ε: error term

**Training:**
- Uses last 30 days of data (minimum)
- Trains one model per city
- Generates 24-hour forecast
- Includes confidence intervals

**Output:** Saves to `ml_predictions` table

**Accuracy:** Typical MAE: 1-2°C

**Location**: `ml/temperature_predictor.py`

---

### 6. Advanced Dashboard

**Purpose**: Real-time data visualization

**Technology**: Dash (Plotly) + Flask

**Port**: 8050

**Architecture:**
- **Frontend**: React (via Dash)
- **Backend**: Flask server
- **Data**: SQLite queries via SQLAlchemy

**Auto-Refresh**: 10 seconds

**Components:**
- Header with system status
- KPI cards (6 metrics)
- Temperature trends (line chart)
- Current readings (city-specific)
- ML predictions (forecast chart)
- Model performance (MAE, accuracy)
- Gauges (4 indicators)
- City comparison (bar chart)
- Temperature distribution (histogram)
- Recent alerts (table)
- Recent readings (table)

**Styling**: Custom CSS with dark theme

**Location**: `dashboard/advanced_dashboard.py`

---

### 7. Dashboard V2

**Purpose**: Alternative dashboard with modern UI

**Technology**: Dash with glassmorphism design

**Port**: 8051

**Features**: Similar to Advanced Dashboard with different styling

**Location**: `dashboard/dashboard_v2.py`

---

### 8. Control Panel

**Purpose**: Central management interface

**Technology**: Tkinter (Python GUI)

**Features:**
- Process lifecycle management
- Real-time log viewing
- System resource monitoring
- Database management tools
- Pipeline flow visualization
- One-click operations

**Architecture:**
- **ProcessManager**: Subprocess control
- **GUI Tabs**: Components, Monitor, Database, Pipeline
- **Threading**: Non-blocking operations

**Location**: `control_panel.py`

---

## Data Flow

### Path 1: Batch ETL Pipeline (Primary Data Path)

```
┌────────────────┐
│     Sensor     │ Generates data every 5s
│   Generator    │
└────────┬───────┘
         │
         ▼ Writes to files
┌────────────────┐
│   CSV/JSONL    │
│     Files      │ output/sensor_data.*
└────────┬───────┘
         │
         ▼ Reads every 60s
┌────────────────┐
│   Batch ETL    │ Extract → Transform → Load
└────────┬───────┘
         │
         ▼ Inserts to database
┌────────────────┐
│      Data      │ Star schema tables
│   Warehouse    │
└────────┬───────┘
         │
         ├──────────────────┐
         ▼                  ▼
┌────────────────┐  ┌────────────────┐
│  ML Predictor  │  │   Dashboard    │
│  (Prophet)     │  │   (Dash)       │
└────────┬───────┘  └────────────────┘
         │
         ▼ Saves predictions
┌────────────────┐
│  ml_predictions│
│     table      │
└────────────────┘
```

### Path 2: Streaming Alert Pipeline

```
┌────────────────┐
│     Sensor     │ Generates data every 5s
│   Generator    │
└────────┬───────┘
         │
         ▼ Publishes to Kafka
┌────────────────┐
│     Kafka      │ In-memory message queue
│     Broker     │
└────────┬───────┘
         │
         ▼ Consumes messages
┌────────────────┐
│     Kafka      │ Check alert rules
│    Consumer    │
└────────┬───────┘
         │
         ▼ If threshold breached
┌────────────────┐
│   alert_log    │ Store alerts only
│     table      │ (NO warehouse writes)
└────────────────┘
```

### Data Flow Principles

1. **ETL is Primary**: All warehouse data comes from ETL
2. **Kafka for Alerts**: Streaming path only creates alerts
3. **No Dual Writes**: Single source of truth per table
4. **Clear Separation**: Batch vs. real-time responsibilities

---

## Database Design

### Star Schema Architecture

```
             ┌──────────────┐
             │   dim_time   │
             │──────────────│
             │  time_id PK  │
             │  ts          │
             │  date        │
             │  year        │
             │  month       │
             │  ...         │
             └──────┬───────┘
                    │
                    │ 1:N
                    ▼
┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│  dim_sensor  │   │ fact_weather_    │   │ dim_location │
│──────────────│   │    reading       │   │──────────────│
│ sensor_id PK │   │──────────────────│   │ location_id  │
│ sensor_type  │◄──│ reading_id PK    │──►│ city_name    │
│ model        │1:N│ time_id FK       │N:1│ region       │
│ ...          │   │ sensor_id FK     │   │ lat/lon      │
└──────────────┘   │ location_id FK   │   │ ...          │
                   │ status_id FK     │   └──────────────┘
                   │ temperature      │
┌──────────────┐   │ humidity         │
│  dim_status  │   │ pressure         │
│──────────────│   │ wind_speed       │
│ status_id PK │   │ is_anomaly       │
│ status_code  │◄──│ ...              │
│ description  │1:N└──────────────────┘
└──────────────┘
```

### Additional Tables

**alert_log:**
- Not part of star schema
- Operational table for alerts
- Separate from analytical data

**ml_predictions:**
- Stores ML forecasts
- Links to dim_location conceptually
- Time-series prediction data

### Indexing Strategy

**Primary Keys**: All tables
**Foreign Keys**: fact_weather_reading (4 FKs)
**Additional Indexes**:
- `dim_time.ts`: Query by timestamp
- `dim_location.location_code`: City lookups
- `dim_status.status_code`: Status filtering
- `alert_log.alert_ts`: Recent alerts
- `alert_log.sensor_id`: Sensor-specific alerts

### Data Types

**Timestamps**: `DATETIME` (UTC+2 for Egypt)
**Temperatures**: `FLOAT` (°C)
**Humidity**: `FLOAT` (percentage 0-100)
**Pressure**: `FLOAT` (hPa)
**Wind Speed**: `FLOAT` (km/h)
**Wind Direction**: `VARCHAR(10)` (N, NE, E, etc.)
**Rainfall**: `FLOAT` (mm)

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.14 | Primary development |
| **Data Processing** | Pandas | 2.3.3 | Data manipulation |
| **Database** | SQLite | 3.x | Data warehousing |
| **ORM** | SQLAlchemy | 2.x | Database abstraction |
| **Dashboard** | Dash | 3.3.0 | Web visualization |
| **ML** | Prophet | 1.1.6 | Time-series forecasting |
| **GUI** | Tkinter | Built-in | Control panel |

### Supporting Libraries

| Library | Purpose |
|---------|---------|
| NumPy | Numerical computations |
| Plotly | Interactive charts |
| psutil | System monitoring |
| threading | Concurrent operations |
| subprocess | Process management |
| pathlib | Path handling |
| json | JSON parsing |
| csv | CSV parsing |

### Development Tools

- **IDE**: VS Code
- **Version Control**: Git
- **Terminal**: PowerShell 5.1
- **OS**: Windows 11

---

## Design Decisions

### 1. Why SQLite?

**Pros:**
- ✅ Zero configuration
- ✅ File-based (portable)
- ✅ Fast for read-heavy workloads
- ✅ ACID compliant
- ✅ Perfect for development

**Cons:**
- ⚠️ Limited concurrent writes
- ⚠️ Not distributed

**Decision**: SQLite is perfect for this project's scale (< 1M records). For production, consider PostgreSQL.

### 2. Why Continuous ETL?

**Before**: ETL ran once and exited
**After**: ETL runs every 60 seconds in a loop

**Reason**: 
- Aligns with DEPI requirements
- Automatic processing
- No manual intervention
- Fresh data always available

### 3. Why Two Dashboards?

**Advanced Dashboard** (Port 8050):
- Production-ready
- Complete features
- Optimized performance

**Dashboard V2** (Port 8051):
- Modern glassmorphism UI
- Experimental features
- User preference

**Decision**: Provide options, recommend Advanced Dashboard

### 4. Why In-Memory Kafka?

**Alternative**: Apache Kafka (full installation)

**Chosen**: Custom Python implementation

**Reasons:**
- ✅ No external dependencies
- ✅ Easier setup
- ✅ Sufficient for project scale
- ✅ Educational value

### 5. Why Prophet for ML?

**Alternatives**: ARIMA, LSTM, XGBoost

**Chosen**: Prophet

**Reasons:**
- ✅ Designed for time-series
- ✅ Handles seasonality well
- ✅ Robust to missing data
- ✅ Easy to interpret
- ✅ Production-ready (Facebook)

### 6. Why Separate Alert Path?

**Design**: Kafka Consumer does NOT write to warehouse

**Reason**:
- Follows strict ETL principles
- Single source of truth (ETL only)
- Clear separation of concerns
- Kafka for real-time, ETL for analytics

### 7. Why Star Schema?

**Alternative**: Normalized OLTP schema

**Chosen**: Star schema

**Reasons:**
- ✅ Optimized for analytics (OLAP)
- ✅ Simple joins
- ✅ Fast aggregations
- ✅ Easy to understand
- ✅ Industry standard for DWH

---

## Scalability

### Current Capacity

**Data Volume:**
- 20 sensors × 5 sec = 14,400 readings/day
- ~500KB/day data files
- ~1.5MB/day database growth
- Sustainable for 1+ year

**Performance:**
- ETL: 104 records/sec
- Dashboard: < 100ms queries
- Kafka: < 100ms latency
- ML: ~60 seconds for 5 cities

### Scaling Strategies

#### Vertical Scaling (Scale Up)

**Hardware Improvements:**
- More CPU cores → Parallel ETL processing
- More RAM → Larger in-memory caches
- SSD → Faster file I/O

**Code Improvements:**
- Optimize SQL queries
- Add database indexes
- Implement caching (Redis)
- Use connection pooling

#### Horizontal Scaling (Scale Out)

**For 100+ Sensors:**

**Option 1: Distributed Kafka**
- Apache Kafka cluster (Zookeeper)
- Multiple consumer instances
- Load balancing

**Option 2: Cloud Migration**
- Azure Event Hubs for streaming
- Azure SQL Database for warehouse
- Azure Functions for ETL
- Azure ML for predictions

**Option 3: Microservices**
- Separate services per city
- API gateway for coordination
- Kubernetes orchestration

### Cloud Architecture (Future)

```
┌───────────────────────────────────────────────────┐
│                  AZURE CLOUD                      │
│                                                   │
│  ┌─────────────┐        ┌─────────────┐         │
│  │  Event Hubs │────────│ Stream      │         │
│  │  (Kafka)    │        │ Analytics   │         │
│  └─────────────┘        └─────────────┘         │
│         │                        │               │
│         ▼                        ▼               │
│  ┌─────────────┐        ┌─────────────┐         │
│  │  Blob       │────────│ Data        │         │
│  │  Storage    │        │ Factory     │         │
│  │  (Data Lake)│        │ (ETL)       │         │
│  └─────────────┘        └─────────────┘         │
│                                │                  │
│                                ▼                  │
│                        ┌─────────────┐           │
│                        │  Synapse    │           │
│                        │  Analytics  │           │
│                        │  (DWH)      │           │
│                        └─────────────┘           │
│                                │                  │
│                                ▼                  │
│                        ┌─────────────┐           │
│                        │  Power BI   │           │
│                        │  Dashboard  │           │
│                        └─────────────┘           │
└───────────────────────────────────────────────────┘
```

---

## Performance Optimization

### Current Optimizations

1. **Batch Commits**: ETL commits every 100 records
2. **Session Management**: Proper open/close cycles
3. **Indexes**: All FK and timestamp columns
4. **Cache Clearing**: Dashboard expires SQLAlchemy cache
5. **Query Limits**: Dashboard queries only recent data

### Future Optimizations

1. **Partitioning**: Partition fact table by date
2. **Aggregates**: Pre-compute common queries
3. **Compression**: Compress old data
4. **Archival**: Move old data to cold storage
5. **Caching**: Redis for hot data

---

## Security Considerations

### Current Security

**Database:**
- File-based (local access only)
- No network exposure
- No authentication required

**Dashboard:**
- Localhost only (127.0.0.1)
- No authentication
- No HTTPS

**Files:**
- Local file system
- No encryption

### Production Security (Recommendations)

1. **Authentication**: Add user login to dashboard
2. **Authorization**: Role-based access control
3. **Encryption**: TLS for network traffic, encrypt database
4. **Audit Logs**: Track all data access
5. **Input Validation**: Sanitize all inputs
6. **Secrets Management**: Use environment variables

---

## Monitoring & Observability

### Current Monitoring

**Control Panel:**
- Process status (running/stopped)
- CPU and memory usage
- Database row counts
- Log file viewers

**Logs:**
- `logs/sensor_generator.log`
- `logs/etl_pipeline.log`
- `logs/kafka_streaming.log`
- `logs/ml_predictions.log`

### Future Monitoring

**Metrics (Prometheus):**
- Data ingestion rate
- ETL processing time
- Alert frequency
- Query latency
- Error rates

**Dashboards (Grafana):**
- System health overview
- Resource utilization
- Data quality metrics
- SLA compliance

**Alerting:**
- PagerDuty for critical alerts
- Email for warnings
- Slack notifications

---

## Disaster Recovery

### Current Backup Strategy

**Manual Backups:**
- Control Panel → Database → Backup Database
- Creates timestamped copy in `database/backups/`

**Frequency**: On-demand

### Production DR Plan

1. **Automated Backups**: Daily, weekly, monthly
2. **Offsite Storage**: Azure Blob Storage
3. **Point-in-Time Recovery**: Transaction logs
4. **Replication**: Read replicas for failover
5. **Testing**: Quarterly DR drills

**RTO (Recovery Time Objective)**: < 1 hour
**RPO (Recovery Point Objective)**: < 5 minutes

---

## Compliance & Governance

### Data Retention

**Current**: Unlimited (all data kept)

**Recommended**:
- Hot data: Last 90 days (online)
- Warm data: 90-365 days (compressed)
- Cold data: 1-7 years (archived)
- Delete: > 7 years

### Data Quality

**Validation Rules:**
- Temperature: -50°C to 60°C
- Humidity: 0% to 100%
- Pressure: 900 to 1100 hPa
- Timestamps: Not in future

**Quality Metrics:**
- Completeness: % of non-null values
- Accuracy: % within valid ranges
- Consistency: Duplicate detection
- Timeliness: Data freshness

---

**Version**: 2.0  
**Last Updated**: November 2025  
**Status**: Production Ready
