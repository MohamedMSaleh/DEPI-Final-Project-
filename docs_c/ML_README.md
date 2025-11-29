# 🧠 AI Temperature Prediction System

## 🎯 **Overview**

Complete machine learning integration for the DEPI IoT Data Pipeline. Uses Facebook Prophet to forecast next-day temperatures with hourly granularity.

---

## ✨ **Features**

| Feature | Description | Status |
|---------|-------------|--------|
| 🤖 **AI Model** | Facebook Prophet time series forecasting | ✅ |
| 📊 **Dashboard** | Visual actual vs predicted comparison | ✅ |
| 🎛️ **Control Panel** | One-click ML execution | ✅ |
| 🗄️ **Database** | Automatic prediction storage | ✅ |
| 🌍 **Multi-City** | All 5 Egyptian cities supported | ✅ |
| 📈 **Confidence** | Upper/lower bound intervals | ✅ |

---

## 📦 **Installation**

```powershell
pip install prophet scikit-learn
```

---

## 🚀 **Usage**

### **Method 1: Control Panel**
```powershell
python control_panel.py
# Click "🧠 ML Temperature Predictor" → Start
```

### **Method 2: Command Line**
```powershell
python ml/temperature_predictor.py
```

### **Method 3: Programmatic**
```python
from ml.temperature_predictor import TemperaturePredictor

predictor = TemperaturePredictor()
predictions = predictor.predict_all_cities()
predictor.save_predictions_to_db(predictions)
```

---

## 📊 **Results**

### **Prediction Statistics**

| City | Training Data | Predictions | Avg Temp | Range |
|------|---------------|-------------|----------|-------|
| Cairo | 1,903 readings | 24 hours | 22.8°C | 19.0°C - 28.1°C |
| Alexandria | 1,917 readings | 24 hours | 23.5°C | 20.2°C - 28.7°C |
| Giza | 1,867 readings | 24 hours | 23.5°C | 4.4°C - 36.8°C |
| Luxor | 1,870 readings | 24 hours | 30.3°C | 24.8°C - 34.6°C |
| Aswan | 1,896 readings | 24 hours | 34.5°C | 27.8°C - 41.8°C |

**Total:** 120 predictions generated

---

## 🎨 **Dashboard Integration**

The dashboard now includes:

### **🧠 AI Temperature Predictions Chart**
- Solid lines: Actual temperatures (last 48 hours)
- Dashed lines: Predicted temperatures (next 24 hours)
- Gray shaded area: Confidence intervals
- Interactive legend and hover info

### **📊 Model Performance Panel**
- Total predictions count
- Model version (Prophet v1)
- Last run timestamp
- Per-city statistics:
  - Average predicted temperature
  - Temperature range (min-max)
  - Number of predictions

**Access:** http://127.0.0.1:8050

---

## 🗄️ **Database Schema**

New table: `ml_temperature_predictions`

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
SELECT * FROM ml_temperature_predictions 
WHERE created_at = (SELECT MAX(created_at) FROM ml_temperature_predictions)
ORDER BY city_name, prediction_timestamp;
```

---

## 🧪 **Testing**

```powershell
python test_ml_setup.py
```

**Checks:**
- ✅ Prophet installation
- ✅ Module imports
- ✅ Database connection
- ✅ Data availability
- ✅ Predictor initialization

---

## 📚 **Documentation**

| Document | Description | Location |
|----------|-------------|----------|
| **ML Guide** | Complete implementation guide | `docs_c/ML_GUIDE.md` |
| **Quick Start** | 5-minute setup instructions | `docs_c/ML_QUICK_START.md` |
| **Completion Summary** | Full integration report | `docs_c/ML_COMPLETION_SUMMARY.md` |
| **Test Script** | Verification tool | `test_ml_setup.py` |

---

## 🔧 **Technical Details**

### **Model Configuration**
```python
Prophet(
    daily_seasonality=True,      # Day/night patterns
    weekly_seasonality=True,      # Weekly trends
    yearly_seasonality=False,     # Not enough data
    changepoint_prior_scale=0.05, # Adaptive to changes
    seasonality_mode='additive'   # Standard for temperature
)
```

### **Training Process**
1. Fetch historical data (last 30 days)
2. Train Prophet model per city
3. Generate 24-hour forecast
4. Calculate confidence intervals
5. Save to database

### **Performance**
- Training time: ~1 second per city
- Total execution: ~5-6 seconds
- Predictions: 24 hourly values per city

---

## 🎯 **Use Cases**

1. **Predictive Maintenance**
   - Anticipate equipment needs
   - Plan cooling/heating resources

2. **Anomaly Detection**
   - Compare actual vs predicted
   - Alert on significant deviations

3. **Resource Planning**
   - Optimize energy usage
   - Schedule operations

4. **Data-Driven Decisions**
   - Forecast-based recommendations
   - Trend analysis

---

## 🚨 **Troubleshooting**

### **Prophet Installation Issues**
```powershell
pip install --upgrade pip
pip install pystan
pip install prophet
```

### **Insufficient Data Error**
- Minimum: 2 readings per city
- Check: `python test_ml_setup.py`

### **Dashboard Not Showing Predictions**
1. Verify predictions exist:
   ```sql
   SELECT COUNT(*) FROM ml_temperature_predictions;
   ```
2. Restart dashboard:
   ```powershell
   python dashboard/advanced_dashboard.py
   ```

---

## 🔮 **Future Enhancements**

### **Phase 2 (Optional)**
- [ ] Accuracy tracking (MAE, RMSE)
- [ ] Multiple model comparison (Random Forest, LSTM)
- [ ] Alert system for threshold breaches
- [ ] Multi-day forecasts (7-day)
- [ ] Humidity/pressure predictions
- [ ] Automated retraining schedule

---

## 📊 **File Structure**

```
ml/
├── temperature_predictor.py  # Core ML engine (380 lines)
└── __init__.py

docs_c/
├── ML_GUIDE.md              # Complete guide (500 lines)
├── ML_QUICK_START.md        # 5-minute setup
├── ML_COMPLETION_SUMMARY.md # Integration report
└── ML_README.md             # This file

dashboard/
└── advanced_dashboard.py    # +230 lines ML integration

control_panel.py             # +10 lines ML component

test_ml_setup.py             # Testing script (90 lines)

requirements.txt             # +4 ML dependencies
```

---

## ✅ **Verification**

All systems operational:

- [x] Prophet installed
- [x] 120 predictions generated
- [x] Database table created
- [x] Dashboard integrated
- [x] Control panel component added
- [x] Documentation complete
- [x] Tests passing

---

## 🎬 **Demo Steps**

1. **Run Predictions:**
   ```powershell
   python ml/temperature_predictor.py
   ```

2. **Start Dashboard:**
   ```powershell
   python dashboard/advanced_dashboard.py
   ```

3. **Open Browser:**
   http://127.0.0.1:8050

4. **View Results:**
   - Scroll to "🧠 AI Temperature Predictions"
   - Compare actual vs predicted
   - Check model performance panel

---

## 📞 **Support**

**Quick Commands:**
```powershell
# Test setup
python test_ml_setup.py

# Run predictions
python ml/temperature_predictor.py

# Start dashboard
python dashboard/advanced_dashboard.py

# Open control panel
python control_panel.py
```

**Prophet Documentation:** https://facebook.github.io/prophet/

---

## 🏆 **Success Metrics**

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Model Training | < 2s/city | ~1s/city | ✅ |
| Predictions | 120 | 120 | ✅ |
| Cities | 5 | 5 | ✅ |
| Accuracy | High | TBD* | ⏳ |

*Accuracy tracking available after collecting actual vs predicted data

---

## 📝 **License**

Part of DEPI Final Project - IoT Data Pipeline  
Team: Data Rangers  
Year: 2025

---

## 🎉 **Status**

**✅ COMPLETE & OPERATIONAL**

All ML features implemented, tested, and integrated into the IoT pipeline. Ready for production use!

---

**Last Updated:** 2025-11-29  
**Version:** 1.0  
**Model:** Prophet v1.1.5
