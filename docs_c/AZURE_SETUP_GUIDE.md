# Azure Integration Setup Guide

## Overview
This guide will help you migrate your IoT Data Pipeline to Azure cloud services for a production-ready implementation.

## Azure Architecture

```
┌─────────────────────┐
│  Sensor Generator   │
│    (Python)         │
└──────────┬──────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
    ┌────────────┐              ┌──────────────────┐
    │ Azure      │              │ Azure Blob       │
    │ Event Hubs │              │ Storage          │
    │ (Streaming)│              │ (Data Lake)      │
    └──────┬─────┘              └────────┬─────────┘
           │                             │
           │                             │
           ▼                             ▼
    ┌──────────────────┐        ┌──────────────────┐
    │ Azure Stream     │        │ Azure Data       │
    │ Analytics        │        │ Factory          │
    │ (Real-time)      │        │ (Batch ETL)      │
    └────────┬─────────┘        └────────┬─────────┘
             │                           │
             │                           │
             └──────────┬────────────────┘
                        │
                        ▼
                ┌─────────────────┐
                │ Azure SQL DB    │
                │ or Synapse      │
                │ (Data Warehouse)│
                └────────┬────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  Dashboard  │
                  │  (Power BI/ │
                  │   Dash)     │
                  └─────────────┘
```

## Prerequisites

1. **Azure Subscription** (Free tier available)
2. **Azure CLI** installed
3. **Python 3.10+** with required packages
4. **Azure SDK for Python** packages

## Part 1: Azure Resources Setup

### Step 1: Install Azure CLI

Download and install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

Verify installation:
```bash
az --version
```

### Step 2: Login to Azure

```bash
az login
```

### Step 3: Set Default Subscription

```bash
# List subscriptions
az account list --output table

# Set default subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### Step 4: Create Resource Group

```bash
az group create \
  --name iot-pipeline-rg \
  --location eastus
```

### Step 5: Create Storage Account (Data Lake)

```bash
az storage account create \
  --name iotpipelinestorage \
  --resource-group iot-pipeline-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true
```

Get connection string:
```bash
az storage account show-connection-string \
  --name iotpipelinestorage \
  --resource-group iot-pipeline-rg \
  --output tsv
```

Create containers:
```bash
# For raw data
az storage container create \
  --name raw-data \
  --account-name iotpipelinestorage

# For processed data
az storage container create \
  --name processed-data \
  --account-name iotpipelinestorage
```

### Step 6: Create Event Hubs Namespace

```bash
az eventhubs namespace create \
  --name iot-pipeline-eventhub \
  --resource-group iot-pipeline-rg \
  --location eastus \
  --sku Standard
```

Create Event Hub:
```bash
az eventhubs eventhub create \
  --name sensor-events \
  --namespace-name iot-pipeline-eventhub \
  --resource-group iot-pipeline-rg \
  --partition-count 4 \
  --message-retention 1
```

Get connection string:
```bash
az eventhubs namespace authorization-rule keys list \
  --resource-group iot-pipeline-rg \
  --namespace-name iot-pipeline-eventhub \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString \
  --output tsv
```

### Step 7: Create Azure SQL Database

```bash
# Create SQL Server
az sql server create \
  --name iot-pipeline-sqlserver \
  --resource-group iot-pipeline-rg \
  --location eastus \
  --admin-user sqladmin \
  --admin-password "YourStrongPassword123!"

# Create Database
az sql db create \
  --resource-group iot-pipeline-rg \
  --server iot-pipeline-sqlserver \
  --name iot-warehouse \
  --service-objective S0 \
  --compute-model Serverless \
  --auto-pause-delay 60

# Configure firewall (allow Azure services)
az sql server firewall-rule create \
  --resource-group iot-pipeline-rg \
  --server iot-pipeline-sqlserver \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Add your IP
az sql server firewall-rule create \
  --resource-group iot-pipeline-rg \
  --server iot-pipeline-sqlserver \
  --name AllowMyIP \
  --start-ip-address YOUR_PUBLIC_IP \
  --end-ip-address YOUR_PUBLIC_IP
```

Get connection string:
```bash
az sql db show-connection-string \
  --client ado.net \
  --server iot-pipeline-sqlserver \
  --name iot-warehouse
```

### Step 8: Create Azure Stream Analytics Job

```bash
az stream-analytics job create \
  --resource-group iot-pipeline-rg \
  --name iot-stream-analytics \
  --location eastus \
  --output-error-policy Drop \
  --events-outoforder-policy Adjust \
  --events-outoforder-max-delay 10 \
  --events-late-arrival-max-delay 5
```

## Part 2: Configuration Files

### Create `.env` file

Create a file named `.env` in your project root:

```env
# Azure Event Hubs
EVENTHUB_CONNECTION_STRING=Endpoint=sb://...
EVENTHUB_NAME=sensor-events

# Azure Storage Account
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
STORAGE_ACCOUNT_NAME=iotpipelinestorage
STORAGE_ACCOUNT_KEY=your-storage-key
RAW_CONTAINER_NAME=raw-data
PROCESSED_CONTAINER_NAME=processed-data

# Azure SQL Database
SQL_SERVER=iot-pipeline-sqlserver.database.windows.net
SQL_DATABASE=iot-warehouse
SQL_USERNAME=sqladmin
SQL_PASSWORD=YourStrongPassword123!
SQL_CONNECTION_STRING=Driver={ODBC Driver 17 for SQL Server};Server=tcp:iot-pipeline-sqlserver.database.windows.net,1433;Database=iot-warehouse;Uid=sqladmin;Pwd=YourStrongPassword123!;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;

# Azure Resource Group
AZURE_RESOURCE_GROUP=iot-pipeline-rg
AZURE_LOCATION=eastus
```

## Part 3: Install Required Python Packages

Update `requirements.txt`:

```bash
pip install azure-eventhub
pip install azure-storage-blob
pip install azure-identity
pip install pyodbc
pip install python-dotenv
```

## Part 4: Updated Python Scripts

### 1. Update Sensor Generator with Event Hubs

The sensor generator already supports Event Hubs via `--eventhub-connection-string` parameter.

Run with Event Hubs:
```bash
python sensor_generator.py \
  --num-sensors 10 \
  --interval 5 \
  --eventhub-connection-string "$EVENTHUB_CONNECTION_STRING" \
  --eventhub-name sensor-events
```

### 2. Create Azure Blob ETL Script

See `azure_etl.py` (to be created)

### 3. Azure Stream Analytics Query

In Azure Portal, configure Stream Analytics with this query:

```sql
-- Input: sensor-events (Event Hub)
-- Output: alerts-output (SQL Database)

SELECT
    sensor_id,
    city,
    temperature,
    humidity,
    wind_speed,
    pressure,
    timestamp,
    CASE 
        WHEN temperature > 40 THEN 'High Temperature Alert'
        WHEN temperature < 0 THEN 'Low Temperature Alert'
        WHEN humidity < 20 THEN 'Low Humidity Alert'
        WHEN humidity > 90 THEN 'High Humidity Alert'
        WHEN wind_speed > 50 THEN 'High Wind Speed Alert'
        WHEN pressure < 980 OR pressure > 1040 THEN 'Abnormal Pressure Alert'
        ELSE NULL
    END AS alert_type
INTO
    [alerts-output]
FROM
    [sensor-events]
WHERE
    temperature > 40 OR temperature < 0 OR
    humidity < 20 OR humidity > 90 OR
    wind_speed > 50 OR
    pressure < 980 OR pressure > 1040
```

## Part 5: Testing the Pipeline

### Test 1: Generate Data to Event Hubs

```bash
# Load environment variables
source .env  # Linux/Mac
# or
$env:EVENTHUB_CONNECTION_STRING = "..."  # Windows PowerShell

# Run generator
python sensor_generator.py \
  --num-sensors 5 \
  --interval 5 \
  --duration 300 \
  --eventhub-connection-string "$EVENTHUB_CONNECTION_STRING" \
  --eventhub-name sensor-events
```

### Test 2: Run Batch ETL with Azure Storage

```bash
python azure_etl.py
```

### Test 3: Verify Stream Analytics

1. Start Stream Analytics Job in Azure Portal
2. Monitor for alerts in SQL Database
3. Check metrics in Azure Portal

### Test 4: Update Dashboard for Azure SQL

Update dashboard connection to use Azure SQL instead of SQLite.

## Part 6: Monitoring & Management

### View Event Hub Metrics

```bash
az monitor metrics list \
  --resource iot-pipeline-eventhub \
  --resource-group iot-pipeline-rg \
  --resource-type Microsoft.EventHub/namespaces \
  --metric IncomingMessages
```

### Query Azure SQL

```bash
sqlcmd -S iot-pipeline-sqlserver.database.windows.net \
  -d iot-warehouse \
  -U sqladmin \
  -P "YourStrongPassword123!" \
  -Q "SELECT COUNT(*) FROM fact_weather_reading"
```

### View Stream Analytics Job Status

```bash
az stream-analytics job show \
  --resource-group iot-pipeline-rg \
  --name iot-stream-analytics \
  --query provisioningState
```

## Cost Management

### Estimated Monthly Costs (Free Tier / Low Usage)

- Event Hubs Standard: ~$10-20/month
- Storage Account: ~$1-5/month
- Azure SQL Database (Serverless S0): ~$5-15/month
- Stream Analytics: ~$80/month (1 streaming unit)

### Cost Optimization Tips

1. Use Azure Free Tier where possible
2. Enable auto-pause for SQL Database
3. Use Azure Student subscription (free $100 credit)
4. Delete resources when not in use

## Cleanup

To delete all resources:

```bash
az group delete --name iot-pipeline-rg --yes --no-wait
```

## Next Steps

1. ✅ Set up all Azure resources
2. ✅ Update environment variables
3. ✅ Run sensor generator with Event Hubs
4. ✅ Execute Azure ETL pipeline
5. ✅ Configure Stream Analytics
6. ✅ Update dashboard for Azure SQL
7. ✅ Test end-to-end pipeline
8. ✅ Create Power BI dashboard (optional)
9. ✅ Document results in final report

## Troubleshooting

### Connection Issues

- Verify firewall rules for SQL Server
- Check Event Hub connection string format
- Ensure storage account access keys are correct

### Authentication Errors

```bash
# Re-login to Azure
az login

# Verify subscription
az account show
```

### Performance Issues

- Increase Event Hub partitions
- Scale up SQL Database tier
- Add more Stream Analytics streaming units

## Support Resources

- [Azure Event Hubs Documentation](https://docs.microsoft.com/en-us/azure/event-hubs/)
- [Azure Stream Analytics Documentation](https://docs.microsoft.com/en-us/azure/stream-analytics/)
- [Azure SQL Database Documentation](https://docs.microsoft.com/en-us/azure/sql-database/)
- [Azure Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/)
