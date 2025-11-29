# 🚀 ML Quick Start Guide

## ⚡ **5-Minute Setup**

### **Step 1: Install Dependencies** (2 min)
```powershell
pip install prophet scikit-learn
```

### **Step 2: Run Predictions** (1 min)
```powershell
python ml/temperature_predictor.py
```

**Expected Output:**
```
✅ Model trained successfully for Cairo
✅ Generated 24 predictions for Cairo
✅ Saved 120 predictions to database
```

### **Step 3: View in Dashboard** (2 min)
```powershell
# Start dashboard
python dashboard/advanced_dashboard.py

# Open browser
http://127.0.0.1:8050
```

Look for **"🧠 AI Temperature Predictions"** section!

---

## 🎯 **Quick Test**

```powershell
# Verify everything works
python test_ml_setup.py
```

All checkmarks? You're good to go! ✅

---

## 📊 **What You Get**

- 🧠 **AI Predictions**: Next 24 hours of temperature
- 📈 **Confidence Intervals**: Upper/lower bounds
- 🌍 **5 Cities**: Cairo, Alexandria, Giza, Luxor, Aswan
- 📊 **Visual Dashboard**: Actual vs Predicted charts
- 🎛️ **Control Panel**: One-click execution

---

## 🔧 **Common Issues**

**Prophet won't install?**
```powershell
pip install --upgrade pip
pip install pystan
pip install prophet
```

**No predictions showing?**
1. Check database: `SELECT COUNT(*) FROM ml_temperature_predictions;`
2. Restart dashboard: `python dashboard/advanced_dashboard.py`

**"Insufficient data" error?**
- Need at least 2 readings per city
- Check: `python test_ml_setup.py`

---

## 📚 **Full Documentation**

- Complete Guide: `docs_c/ML_GUIDE.md`
- Summary Report: `docs_c/ML_COMPLETION_SUMMARY.md`
- Test Script: `test_ml_setup.py`

---

## 🎬 **One-Line Demo**

```powershell
python ml/temperature_predictor.py; python dashboard/advanced_dashboard.py
```

Then open: http://127.0.0.1:8050 🎉

---

**That's it!** Your ML system is ready. 🚀
