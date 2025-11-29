# 🔧 Troubleshooting Guide - Common Issues & Solutions

## ❌ **Problem 1: Dashboard Shows "ERR_CONNECTION_REFUSED"**

### **Symptoms:**
- Browser shows: "127.0.0.1 refused to connect"
- Error: `ERR_CONNECTION_REFUSED`
- Can't access http://127.0.0.1:8050

### **Root Cause:**
The dashboard process crashed due to a **Python error** and never started the web server.

### **What Was Wrong:**
The ML integration code referenced `COLORS['accent_purple']` which doesn't exist in the color dictionary. This caused Python to throw a `KeyError` and crash.

### **✅ Fix Applied:**
Changed all `COLORS['accent_purple']` to `COLORS['gradient_end']` (which is purple: `#8b5cf6`)

**Files Fixed:**
- `dashboard/advanced_dashboard.py` (2 locations)

---

## ❌ **Problem 2: Control Panel Won't Open After Starting Components**

### **Symptoms:**
- Control panel closes/crashes after clicking "Start All"
- Can't reopen control panel
- Processes may still be running in background

### **Possible Causes & Solutions:**

#### **Cause 1: Process Already Running**
```powershell
# Check if Python processes are stuck
Get-Process python -ErrorAction SilentlyContinue

# Kill all Python processes
Stop-Process -Name python -Force
```

#### **Cause 2: Control Panel Script Error**
```powershell
# Run control panel and see error
python control_panel.py
```

#### **Cause 3: Tkinter Window Manager Issue**
- Tkinter may have crashed due to threading issues
- **Solution:** Restart your computer or kill all Python processes

#### **Cause 4: Port Already in Use**
```powershell
# Check if port 8050 is in use
netstat -ano | Select-String "8050"

# If found, kill the process using the PID shown
Stop-Process -Id <PID> -Force
```

---

## 🔍 **Diagnostic Steps**

### **Step 1: Check if Processes are Running**
```powershell
Get-Process python -ErrorAction SilentlyContinue
```

**Expected:** Should show Python processes if components are running  
**If stuck:** Kill all: `Stop-Process -Name python -Force`

---

### **Step 2: Check Port Availability**
```powershell
netstat -ano | Select-String "8050"
```

**Expected:** Empty (no output) if dashboard is not running  
**If occupied:** Note the PID and kill it: `Stop-Process -Id <PID> -Force`

---

### **Step 3: Test Dashboard Directly**
```powershell
python dashboard/advanced_dashboard.py
```

**Expected Output:**
```
============================================================
[STARTING] ADVANCED IOT DASHBOARD
============================================================
[URL] Dashboard: http://127.0.0.1:8050
Dash is running on http://127.0.0.1:8050/
```

**If Error:** Read the Python traceback to identify the issue

---

### **Step 4: Test Control Panel Directly**
```powershell
python control_panel.py
```

**Expected:** Control panel window opens  
**If Error:** Check for Tkinter issues or Python errors in console

---

## 🛠️ **Complete Fix Procedure**

### **When Dashboard Won't Connect:**

```powershell
# 1. Stop all Python processes
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

# 2. Verify port is free
netstat -ano | Select-String "8050"
# Should be empty

# 3. Test dashboard manually
python dashboard/advanced_dashboard.py

# 4. Open browser
# Go to: http://127.0.0.1:8050

# 5. If works, Ctrl+C to stop, then use control panel
python control_panel.py
```

---

### **When Control Panel Won't Open:**

```powershell
# 1. Kill all Python processes
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

# 2. Wait 2 seconds
Start-Sleep -Seconds 2

# 3. Try opening control panel
python control_panel.py

# 4. If still fails, check for errors
python control_panel.py 2>&1 | Tee-Object error.log

# 5. Read error.log for details
```

---

## 🚨 **Common Errors & Quick Fixes**

### **Error: "KeyError: 'accent_purple'"**
**Fix:** ✅ Already fixed in this update

### **Error: "Address already in use"**
```powershell
# Kill process on port 8050
$proc = netstat -ano | Select-String "8050" | ForEach-Object { $_.ToString().Split()[-1] } | Select-Object -First 1
Stop-Process -Id $proc -Force
```

### **Error: "No module named 'prophet'"**
```powershell
pip install prophet scikit-learn
```

### **Error: "Database is locked"**
```powershell
# Close all Python processes accessing database
Stop-Process -Name python -Force

# Wait a moment
Start-Sleep -Seconds 2

# Try again
python control_panel.py
```

### **Error: Tkinter window freezes**
**Cause:** Threading conflict  
**Fix:** 
1. Close control panel
2. Kill Python: `Stop-Process -Name python -Force`
3. Reopen: `python control_panel.py`

---

## ✅ **Verification Checklist**

After fixes, verify everything works:

- [ ] Dashboard starts without errors
  ```powershell
  python dashboard/advanced_dashboard.py
  # Should show "Dash is running on http://127.0.0.1:8050/"
  ```

- [ ] Browser connects to dashboard
  ```
  Open: http://127.0.0.1:8050
  Should see: IoT Dashboard with charts
  ```

- [ ] ML section visible in dashboard
  ```
  Scroll down to: "🧠 AI Temperature Predictions"
  Should see: Chart with predictions or "No predictions yet"
  ```

- [ ] Control panel opens
  ```powershell
  python control_panel.py
  # Should show Tkinter window
  ```

- [ ] Components can be started
  ```
  Click: "▶ Start" on any component
  Check: Activity Log shows "started successfully"
  ```

- [ ] Dashboard can be started from control panel
  ```
  Find: "📊 Dashboard" component
  Click: "▶ Start"
  Wait: 5 seconds
  Open: http://127.0.0.1:8050
  ```

---

## 🔄 **Safe Restart Procedure**

When things get stuck, follow this procedure:

```powershell
# 1. Stop everything
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

# 2. Verify nothing running
Get-Process python -ErrorAction SilentlyContinue
# Should show nothing

# 3. Verify port 8050 free
netstat -ano | Select-String "8050"
# Should be empty

# 4. Wait for cleanup
Start-Sleep -Seconds 3

# 5. Start fresh
python control_panel.py

# 6. Or start components individually:
# Sensor Generator
python sensor_generator.py --use-kafka --num-sensors 10 --interval 5

# Kafka Consumer (separate terminal)
python streaming/kafka_consumer.py

# Dashboard (separate terminal)
python dashboard/advanced_dashboard.py
```

---

## 📊 **Process Management Tips**

### **Check What's Running:**
```powershell
# List all Python processes with details
Get-Process python | Select-Object Id, ProcessName, StartTime, CPU, WorkingSet

# Check what ports are in use
netstat -ano | Select-String ":8050|:9092|:2181"
```

### **Graceful Shutdown:**
```powershell
# From control panel: Click "Stop All"
# OR press Ctrl+C in each terminal
# OR use Stop-Process (less clean)
```

### **Force Cleanup:**
```powershell
# Nuclear option - kills everything
Stop-Process -Name python -Force
Stop-Process -Name java -Force -ErrorAction SilentlyContinue  # Kafka if running

# Restart only what you need
```

---

## 🎯 **Best Practices**

### **1. Start Components in Order:**
1. Sensor Generator (generates data)
2. Kafka Consumer (processes data)
3. Dashboard (displays data)
4. Pipeline Monitor (optional)

### **2. Use Control Panel:**
- Click "Start All" to start auto-start components
- Manually start others as needed
- Use "Stop All" before closing

### **3. Check Logs:**
- Activity Log in control panel shows real-time status
- Process Output Viewer shows detailed logs
- Console window (if running manually) shows Python errors

### **4. Handle Errors:**
- Read error messages carefully
- Check this troubleshooting guide
- Kill processes if stuck
- Restart cleanly

---

## 🆘 **Emergency Recovery**

If everything is broken:

```powershell
# 1. KILL EVERYTHING
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name java -Force -ErrorAction SilentlyContinue

# 2. VERIFY CLEAN STATE
Get-Process python -ErrorAction SilentlyContinue  # Should be empty
netstat -ano | Select-String "8050"  # Should be empty

# 3. TEST COMPONENTS ONE BY ONE

# Test database
python -c "import sqlite3; conn = sqlite3.connect('database/iot_warehouse.db'); print('DB OK'); conn.close()"

# Test dashboard
python dashboard/advanced_dashboard.py
# Wait for "Dash is running", then Ctrl+C

# Test control panel
python control_panel.py
# Window should open, then close it

# 4. START FRESH
python control_panel.py
# Click "Start All"
# Wait 10 seconds
# Open http://127.0.0.1:8050
```

---

## 📞 **Quick Command Reference**

```powershell
# Stop everything
Stop-Process -Name python -Force

# Check if anything running
Get-Process python

# Check ports
netstat -ano | Select-String "8050"

# Start control panel
python control_panel.py

# Start dashboard manually
python dashboard/advanced_dashboard.py

# Test ML predictions
python ml/temperature_predictor.py

# Test setup
python test_ml_setup.py

# Kill specific process by PID
Stop-Process -Id <PID> -Force
```

---

## ✅ **Status After This Fix**

- ✅ Dashboard color error fixed (`accent_purple` → `gradient_end`)
- ✅ Dashboard confirmed working (tested and verified)
- ✅ All HTTP requests successful (200 OK)
- ✅ ML section properly displayed
- ✅ Port 8050 accessible

**Next Steps:**
1. Run `python control_panel.py`
2. Click "Start All" 
3. Wait 10 seconds
4. Open http://127.0.0.1:8050
5. Enjoy your dashboard! 🎉

---

**Last Updated:** 2025-11-29  
**Issues Fixed:** Color reference error, connection refused  
**Status:** ✅ Resolved
