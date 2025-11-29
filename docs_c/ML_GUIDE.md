# 🧠 Machine Learning Temperature Prediction - Complete Guide

## 📋 **Overview**

This ML system uses **Facebook Prophet** to predict next-day temperatures for all cities in your IoT pipeline. Prophet is specifically designed for time series forecasting and handles seasonality patterns automatically.

---

## 🎯 **Features**

- ✅ **Automated Predictions**: Generates 24-hour hourly temperature forecasts
- ✅ **Multi-City Support**: Predictions for all cities (Cairo, Alexandria, Giza, Luxor, Aswan)
- ✅ **Confidence Intervals**: Upper/lower bounds for prediction accuracy
- ✅ **Dashboard Integration**: Visual comparison of actual vs predicted temperatures
- ✅ **Control Panel Integration**: One-click model execution
- ✅ **Database Storage**: Predictions saved to `ml_temperature_predictions` table

---

## 📦 **Step 1: Install ML Dependencies**

### **Option A: Install All Requirements**
```powershell
cd "C:\Users\mahmo\OneDrive\Desktop\DEPI\DEPI-Final-Project-"
pip install -r requirements.txt
```

### **Option B: Install Only ML Packages**
```powershell
pip install prophet scikit-learn
```

**Note:** Prophet requires `pystan` which may take 5-10 minutes to compile on first install.

---

## 🚀 **Step 2: Run ML Predictions**

### **Method 1: Control Panel (Recommended)**

1. Open the Control Panel:
   ```powershell
   python control_panel.py
   ```

2. Find "🧠 ML Temperature Predictor" in the components list

3. Click **"▶ Start"** button

4. Watch the **Activity Log** for progress:
   - ✓ "Loaded X data points for [City]"
   - ✓ "Model trained successfully for [City]"
   - ✓ "Generated 24 predictions for [City]"
   - ✓ "Saved X predictions to database"

### **Method 2: Direct Python Execution**
```powershell
python ml/temperature_predictor.py
```

**Expected Output:**
```
============================================================
🌡️ TEMPERATURE PREDICTION SYSTEM
============================================================

============================================================
🔮 TEMPERATURE PREDICTION FOR 5 CITIES
============================================================

📍 Processing Cairo...
✓ Loaded 456 data points for Cairo
🔄 Training model for Cairo...
✅ Model trained successfully for Cairo
✅ Generated 24 predictions for Cairo
   Average predicted temp: 18.5°C

📍 Processing Alexandria...
[... similar output for other cities ...]

============================================================
✅ PREDICTIONS COMPLETE
============================================================
Total predictions: 120
Cities: 5
Time range: 2025-11-30 09:00:00 to 2025-12-01 08:00:00

✅ Saved 120 predictions to database

📊 PREDICTION SUMMARY
============================================================
Cairo           | Avg:  18.5°C | Range: 16.2°C - 20.8°C
Alexandria      | Avg:  17.8°C | Range: 15.5°C - 19.3°C
Giza            | Avg:  18.2°C | Range: 16.0°C - 20.5°C
Luxor           | Avg:  22.1°C | Range: 19.8°C - 24.5°C
Aswan           | Avg:  24.3°C | Range: 22.0°C - 26.7°C

✅ Prediction process complete!
```

---

## 📊 **Step 3: View Predictions in Dashboard**

1. **Start the Dashboard:**
   ```powershell
   python dashboard/advanced_dashboard.py
   ```
   Or use Control Panel → Start "📊 Dashboard"

2. **Open Browser:**
   Navigate to: http://127.0.0.1:8050

3. **New ML Section Added:**
   - **"🧠 AI Temperature Predictions"** chart showing:
     - Solid lines = Actual temperatures (last 48 hours)
     - Dashed lines = Predicted temperatures (next 24 hours)
     - Gray shaded area = Confidence intervals
   
   - **"Model Performance"** panel showing:
     - Total predictions count
     - Model version (Prophet v1)
     - Last run timestamp
     - Per-city statistics (avg, min, max temperatures)

4. **Filter by City:**
   Use the city dropdown to focus on specific locations

---

## 🗄️ **Step 4: Database Schema**

New table created automatically: `ml_temperature_predictions`

```sql
CREATE TABLE ml_temperature_predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_timestamp DATETIME NOT NULL,
    city_name TEXT NOT NULL,
    predicted_temp REAL NOT NULL,
    lower_bound REAL NOT NULL,
    upper_bound REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT DEFAULT 'prophet_v1'
);
```

**Query Latest Predictions:**
```sql
SELECT 
    city_name,
    prediction_timestamp,
    predicted_temp,
    lower_bound,
    upper_bound
FROM ml_temperature_predictions
WHERE created_at = (SELECT MAX(created_at) FROM ml_temperature_predictions)
ORDER BY city_name, prediction_timestamp;
```

---

## 🔧 **How It Works**

### **1. Data Collection**
```python
# Fetches last 30 days of temperature data
SELECT 
    t.ts as ds,
    AVG(f.temperature) as y
FROM fact_weather_reading f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_location l ON f.location_id = l.location_id
WHERE l.city_name = 'Cairo'
    AND t.ts >= datetime('now', '-30 days')
GROUP BY DATE(t.ts), CAST(strftime('%H', t.ts) AS INTEGER)
ORDER BY t.ts
```

### **2. Model Training (Per City)**
```python
from prophet import Prophet

model = Prophet(
    daily_seasonality=True,      # Captures day/night patterns
    weekly_seasonality=True,      # Captures weekly trends
    yearly_seasonality=False,     # Not enough data
    changepoint_prior_scale=0.05, # Flexibility to trends
    seasonality_mode='additive'
)

model.fit(historical_data)
```

### **3. Prediction Generation**
```python
# Create future dataframe for next 24 hours
future = model.make_future_dataframe(periods=24, freq='H')

# Generate predictions
forecast = model.predict(future)

# Extract: yhat (prediction), yhat_lower, yhat_upper
```

### **4. Database Storage**
```python
predictions_df.to_sql(
    'ml_temperature_predictions',
    conn,
    if_exists='append',
    index=False
)
```

---

## 📈 **Prediction Accuracy**

The model includes a built-in accuracy calculator (future implementation):

```python
from ml.temperature_predictor import TemperaturePredictor

predictor = TemperaturePredictor()
accuracy = predictor.get_prediction_accuracy('Cairo', hours_back=24)

print(f"MAE: {accuracy['mae']:.2f}°C")
print(f"RMSE: {accuracy['rmse']:.2f}°C")
print(f"Accuracy: {accuracy['accuracy_percent']:.1f}%")
```

---

## 🔄 **Automation Options**

### **Option 1: Scheduled Task (Windows)**
Create a Windows Task Scheduler task to run daily:

```powershell
# Run at 6:00 AM daily
schtasks /create /tn "ML Temperature Prediction" /tr "python C:\Users\mahmo\OneDrive\Desktop\DEPI\DEPI-Final-Project-\ml\temperature_predictor.py" /sc daily /st 06:00
```

### **Option 2: Python Scheduler**
Add to a monitoring script:

```python
import schedule
import time
from ml.temperature_predictor import TemperaturePredictor

def run_predictions():
    predictor = TemperaturePredictor()
    predictions = predictor.predict_all_cities()
    if predictions is not None:
        predictor.save_predictions_to_db(predictions)

# Run every 6 hours
schedule.every(6).hours.do(run_predictions)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🛠️ **Troubleshooting**

### **Issue: Prophet Not Installing**
```powershell
# Try these steps:
pip install --upgrade pip
pip install pystan
pip install prophet
```

### **Issue: "No data available"**
**Solution:** Ensure database has at least 10 data points per city:
```sql
SELECT city_name, COUNT(*) as count
FROM fact_weather_reading f
JOIN dim_location l ON f.location_id = l.location_id
GROUP BY city_name;
```

### **Issue: Predictions not showing in dashboard**
1. Verify predictions exist:
   ```sql
   SELECT COUNT(*) FROM ml_temperature_predictions;
   ```
2. Check timestamps:
   ```sql
   SELECT MAX(created_at) FROM ml_temperature_predictions;
   ```
3. Restart dashboard

---

## 📚 **API Reference**

### **TemperaturePredictor Class**

```python
from ml.temperature_predictor import TemperaturePredictor

predictor = TemperaturePredictor()

# Train and predict for one city
predictions = predictor.predict_next_day('Cairo', periods=24)

# Train and predict for all cities
all_predictions = predictor.predict_all_cities()

# Save to database
predictor.save_predictions_to_db(all_predictions)

# Get latest predictions
latest = predictor.get_latest_predictions(city_name='Cairo')

# Check accuracy
accuracy = predictor.get_prediction_accuracy('Cairo', hours_back=24)
```

---

## 🎓 **Understanding Prophet**

**Why Prophet?**
- ✅ Handles hourly, daily, weekly seasonality automatically
- ✅ Robust to missing data and outliers
- ✅ Provides confidence intervals
- ✅ Fast training and prediction
- ✅ Industry-proven (developed by Meta/Facebook)

**Key Components:**
1. **Trend**: Overall upward/downward temperature movement
2. **Seasonality**: Daily (day/night), weekly patterns
3. **Holidays**: Special events (future enhancement)

**Model Formula:**
```
y(t) = g(t) + s(t) + h(t) + εt
where:
  g(t) = trend
  s(t) = seasonality
  h(t) = holidays effect
  εt  = error term
```

---

## 🚀 **Next Steps**

### **Enhancements You Can Add:**

1. **Multiple Models:**
   - Add Random Forest for comparison
   - Implement ensemble methods

2. **Feature Engineering:**
   - Add humidity, pressure as predictors
   - Include wind speed correlation

3. **Alert System:**
   - Notify if predicted temp exceeds thresholds
   - Compare actual vs predicted for anomalies

4. **Model Versioning:**
   - Track model improvements over time
   - A/B testing different configurations

5. **Hyperparameter Tuning:**
   - Optimize `changepoint_prior_scale`
   - Adjust seasonality parameters

---

## 📞 **Support**

**Files Added:**
- `ml/temperature_predictor.py` - Main prediction engine
- `docs_c/ML_GUIDE.md` - This guide
- Updated `dashboard/advanced_dashboard.py` - ML visualization
- Updated `control_panel.py` - ML component integration
- Updated `requirements.txt` - ML dependencies

**Quick Test:**
```powershell
# Test Prophet installation
python -c "from prophet import Prophet; print('Prophet OK')"

# Test prediction module
python -c "from ml.temperature_predictor import TemperaturePredictor; print('Module OK')"
```

---

## ✅ **Verification Checklist**

- [ ] Prophet installed successfully
- [ ] ML module runs without errors
- [ ] Predictions saved to database
- [ ] Dashboard shows ML section
- [ ] Control panel shows ML component
- [ ] At least 10 data points per city
- [ ] Predictions cover next 24 hours
- [ ] Confidence intervals displayed

---

**🎉 Congratulations!** Your IoT pipeline now includes AI-powered temperature forecasting!

---

**Project:** DEPI Final Project - IoT Data Pipeline  
**Team:** Data Rangers  
**ML Model:** Facebook Prophet v1.1.5  
**Last Updated:** 2025-01-27
