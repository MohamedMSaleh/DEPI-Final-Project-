# Troubleshooting Guide - IoT Weather Monitoring System

**Solutions to common problems and error messages**

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Control Panel Problems](#control-panel-problems)
3. [Dashboard Issues](#dashboard-issues)
4. [Data Generation Issues](#data-generation-issues)
5. [ETL Problems](#etl-problems)
6. [Database Issues](#database-issues)
7. [ML Prediction Issues](#ml-prediction-issues)
8. [Performance Issues](#performance-issues)
9. [Network Issues](#network-issues)
10. [Log Files Guide](#log-files-guide)

---

## Installation Issues

### Problem: "Module not found" Error

**Error Message:**
```
ModuleNotFoundError: No module named 'pandas'
```

**Solution:**
```powershell
# Install missing module
pip install pandas

# Or reinstall all dependencies
pip install -r requirements.txt

# If still failing, upgrade pip first
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Common Missing Modules:**
- `pandas`: `pip install pandas`
- `dash`: `pip install dash`
- `prophet`: `pip install prophet`
- `sqlalchemy`: `pip install sqlalchemy`

---

### Problem: Prophet Installation Fails

**Error Message:**
```
ERROR: Could not build wheels for prophet
```

**Cause**: Prophet requires additional build tools

**Solution (Windows):**

**Option 1 - Use conda (Recommended):**
```powershell
conda install -c conda-forge prophet
```

**Option 2 - Pre-built wheel:**
```powershell
pip install prophet --no-cache-dir
```

**Option 3 - Install build tools:**
1. Install Visual Studio Build Tools
2. Install CMake
3. Then: `pip install prophet`

**Alternative**: Run system without ML predictions (other features work fine)

---

### Problem: "Python not recognized"

**Error Message:**
```
'python' is not recognized as an internal or external command
```

**Solution:**
1. Add Python to PATH environment variable
2. Or use full path: `C:\Python314\python.exe`
3. Or use `py` command instead: `py control_panel.py`

---

## Control Panel Problems

### Problem: Control Panel Won't Start

**Symptoms**: Double-click does nothing or window closes immediately

**Solutions:**

**1. Check Python Installation:**
```powershell
python --version
# Should show: Python 3.14.x or 3.10+
```

**2. Run from Terminal:**
```powershell
python control_panel.py
```
This will show any error messages

**3. Check Tkinter:**
```powershell
python -m tkinter
# A test window should appear
```

**4. Reinstall if needed:**
```powershell
# Tkinter comes with Python, reinstall Python if missing
```

---

### Problem: Components Won't Start

**Symptoms**: Click "Start" but component stays in "Stopped" state

**Solutions:**

**1. Check Logs:**
- Click on component name
- View output panel for error messages

**2. Check File Paths:**
- Ensure you're in project root directory
- All scripts should be in correct locations

**3. Check Permissions:**
- Run terminal as Administrator
- Check file permissions

**4. Check Port Availability:**
```powershell
# Check if port 8050 is in use
netstat -ano | findstr :8050

# If occupied, kill process:
taskkill /PID <PID> /F
```

---

### Problem: "Run All" Fails

**Symptoms**: Some components start, others don't

**Solutions:**

**1. Start Components Individually:**
- Identify which component fails
- Start one by one
- Check logs for specific errors

**2. Restart Control Panel:**
- Close all
- Reopen control_panel.py
- Try "Run All" again

**3. Check System Resources:**
- CPU < 90%
- Memory available > 1GB
- Disk space > 500MB

---

## Dashboard Issues

### Problem: Dashboard Shows No Data

**Symptoms**: Dashboard opens but all charts are empty

**Solutions:**

**1. Verify Data Generation:**
```powershell
# Check if data files exist
dir output\sensor_data.csv
```

**2. Run ETL:**
```powershell
python etl\batch_etl.py
```
ETL must run at least once to populate database

**3. Check Database:**
Open Control Panel and check database statistics.
Should show row counts > 0

**4. Hard Refresh Browser:**
- Press `Ctrl + Shift + R`
- Or `Ctrl + F5`
- Clears browser cache

---

### Problem: Dashboard Shows Old Data

**Symptoms**: Data doesn't update, shows readings from hours ago

**Solutions:**

**1. Wait for Auto-Refresh:**
- Dashboard refreshes every 10 seconds
- Be patient for 10-15 seconds

**2. Force Refresh:**
- Click "Refresh Now" button
- Or hard refresh: `Ctrl + Shift + R`

**3. Restart Dashboard:**
- Control Panel → Stop Dashboard
- Wait 5 seconds
- Start Dashboard again

**4. Check ETL is Running:**
- Control Panel → Components
- ETL should show "Running" status
- ETL runs every 60 seconds

---

### Problem: Dashboard Won't Open

**Error**: "Unable to connect" or "This site can't be reached"

**Solutions:**

**1. Check Dashboard is Running:**
- Control Panel shows "Running" status
- Or terminal shows: "Dash is running on http://127.0.0.1:8050"

**2. Check Correct URL:**
- Use: `http://127.0.0.1:8050`
- NOT: `http://localhost:8050` (sometimes fails)
- NOT: `https://...` (no SSL)

**3. Check Firewall:**
- Windows Firewall may block
- Allow Python through firewall
- Or temporarily disable firewall for testing

**4. Check Port Availability:**
```powershell
netstat -ano | findstr :8050
```
If port occupied, stop other process or use alternative dashboard (port 8051)

---

### Problem: Dropdown Options Are Black (Can't Read)

**Symptoms**: Dropdown text invisible or black on dark background

**Solutions:**

**1. Hard Refresh Browser:**
```
Ctrl + Shift + R
```
CSS changes require cache clear

**2. Clear Browser Cache:**
- Settings → Privacy → Clear browsing data
- Select "Cached images and files"

**3. Restart Dashboard:**
- Stop dashboard completely
- Close all browser tabs
- Start dashboard again
- Open in NEW browser tab

**4. Try Different Browser:**
- Chrome (recommended)
- Firefox
- Edge

---

## Data Generation Issues

### Problem: Sensor Generator Crashes

**Error**: Script stops unexpectedly

**Solutions:**

**1. Check Disk Space:**
```powershell
# Ensure enough space for data files
# Generates ~70KB/hour
dir output\
```

**2. Check Write Permissions:**
- Ensure `output/` folder is writable
- Run as Administrator if needed

**3. Reduce Sensor Count:**
```powershell
# Start with fewer sensors
python sensor_generator.py --num-sensors 5
```

**4. Increase Interval:**
```powershell
# Slower generation
python sensor_generator.py --interval 10
```

---

### Problem: No Data Files Created

**Symptoms**: `output/` folder empty

**Solutions:**

**1. Check Folder Exists:**
```powershell
# Create if missing
mkdir output
```

**2. Run with Full Path:**
```powershell
cd C:\Users\mahmo\OneDrive\Desktop\DEPI\DEPI-Final-Project-
python sensor_generator.py
```

**3. Check Logs:**
- Look for error messages in console
- Check `logs/sensor_generator.log`

---

## ETL Problems

### Problem: ETL Stops After One Cycle

**Symptoms**: ETL runs once then exits

**Solutions:**

This is **FIXED** in latest version. ETL now runs continuously.

**1. Use Latest Version:**
- Ensure you have the updated `etl/batch_etl.py`
- Should show: "BATCH ETL PIPELINE - CONTINUOUS MODE"

**2. Use Control Panel:**
- Control Panel auto-starts ETL in continuous mode
- Don't run ETL manually unless testing

**3. Check Logs:**
```
[CYCLE 1] Starting ETL at HH:MM:SS
[CYCLE 1] Complete in 1.23s | Inserted: 120 | Skipped: 0
[CYCLE 2] Starting ETL at HH:MM:SS
...
```
Should see multiple cycles

---

### Problem: "Database is Locked" Error

**Error Message:**
```
sqlite3.OperationalError: database is locked
```

**Cause**: Multiple processes writing to database simultaneously

**Solutions:**

**1. Use Control Panel:**
- Handles database access automatically
- Prevents conflicts

**2. Don't Run ETL Manually:**
- Let Control Panel manage ETL
- Avoid running `python etl\batch_etl.py` directly

**3. Close Dashboard Before Manual ETL:**
```powershell
# If you must run manually:
# 1. Stop dashboard
# 2. Run ETL
# 3. Restart dashboard
```

**4. Wait and Retry:**
- SQLite retries automatically
- Usually resolves in 1-2 seconds

---

### Problem: ETL Skips All Records

**Symptoms**: "Inserted: 0 | Skipped: 1000"

**Cause**: Records already in database (duplicate prevention)

**Solutions:**

**1. This is Normal:**
- ETL is idempotent (safe to rerun)
- Skips prevent duplicates
- Expected behavior after first run

**2. To Force Reload:**
```powershell
# Backup first
copy database\iot_warehouse.db database\backups\backup.db

# Delete and recreate
python database\schema.py

# Run ETL again
python etl\batch_etl.py
```

---

## Database Issues

### Problem: Database File Corrupted

**Symptoms**: "Malformed database" or "disk I/O error"

**Solutions:**

**1. Restore from Backup:**
```powershell
# List backups
dir database\backups\

# Restore most recent
copy database\backups\iot_warehouse_20251129_143000.db database\iot_warehouse.db
```

**2. Recreate Database:**
```powershell
# Backup old one first
move database\iot_warehouse.db database\iot_warehouse_OLD.db

# Create fresh database
python database\schema.py

# Rerun ETL to repopulate
python etl\batch_etl.py
```

**3. Check Disk Health:**
```powershell
chkdsk C: /F
```

---

### Problem: Database Growing Too Large

**Symptoms**: File size > 1GB, queries slow

**Solutions:**

**1. Clean Old Data:**
- Control Panel → Database → Clean Old Data
- Keep last 30 days only

**2. Vacuum Database:**
```powershell
sqlite3 database\iot_warehouse.db
VACUUM;
.quit
```

**3. Archive Old Data:**
```powershell
# Export to CSV before deleting
# Then delete from database
```

---

## ML Prediction Issues

### Problem: No Predictions Generated

**Symptoms**: ML predictions chart empty

**Solutions:**

**1. Run ML Predictor:**
```powershell
python ml\temperature_predictor.py
```
Must be run manually (not auto-start)

**2. Check Sufficient Data:**
- Need at least 30 days of history
- Check database has enough readings:
Open Control Panel and verify database statistics show sufficient records.

**3. Check Prophet Installed:**
```powershell
python -c "from prophet import Prophet; print('OK')"
```

**4. View Logs:**
- Check `logs/ml_predictions.log`
- Or Control Panel → ML Predictor → View Logs

---

### Problem: ML Predictions Inaccurate

**Symptoms**: Predicted temps way off from actual

**Solutions:**

**1. More Training Data:**
- Run system for 30+ days
- More history = better predictions

**2. Retrain Models:**
```powershell
python ml\temperature_predictor.py
```
Run daily for best results

**3. Check MAE:**
- Dashboard → Model Performance panel
- MAE > 5°C = poor model
- MAE < 2°C = good model

**4. Check for Anomalies:**
- Outliers can skew models
- Clean anomalous data

---

## Performance Issues

### Problem: High CPU Usage

**Symptoms**: CPU at 90-100%, system slow

**Solutions:**

**1. Reduce Sensor Count:**
```powershell
python sensor_generator.py --num-sensors 10
```

**2. Increase Data Interval:**
```powershell
python sensor_generator.py --interval 10
```

**3. Close Unused Components:**
- Stop Dashboard V2 if not using
- Stop Kafka Consumer if not needed

**4. Check for Runaway Processes:**
```powershell
# Control Panel → System Monitor
# Identify high CPU processes
# Restart or stop them
```

---

### Problem: High Memory Usage

**Symptoms**: RAM usage growing, system freezing

**Solutions:**

**1. Restart Components:**
- Control Panel → Restart All
- Fresh start clears memory

**2. Close Other Applications:**
- Chrome tabs (big memory users)
- Other programs

**3. Reduce Dashboard Refresh:**
- Edit `advanced_dashboard.py`
- Change interval from 10s to 30s

**4. Add More RAM:**
- 8GB recommended
- 4GB minimum

---

### Problem: Slow Dashboard

**Symptoms**: Dashboard takes 10+ seconds to load

**Solutions:**

**1. Optimize Database:**
```powershell
sqlite3 database\iot_warehouse.db
ANALYZE;
.quit
```

**2. Clean Old Data:**
- Keep only recent data
- Archive old records

**3. Use Time Filters:**
- Dashboard → Time Range → "Last 24 Hours"
- Queries less data = faster

**4. Close Other Tabs:**
- Browser memory affects performance

---

## Network Issues

### Problem: Kafka Broker Won't Start

**Symptoms**: "Address already in use" or Kafka Consumer can't connect

**Solutions:**

**1. Check Port Availability:**
```powershell
# Kafka uses internal messaging (no network port)
# If using actual Kafka, check port 9092
netstat -ano | findstr :9092
```

**2. Use In-Memory Broker:**
- Default configuration uses in-memory queue
- No network required

**3. Restart Broker:**
- Control Panel → Kafka Broker → Restart

---

### Problem: Can't Access Dashboard from Another Computer

**Symptom**: Dashboard works on localhost but not from network

**Cause**: Dashboard bound to 127.0.0.1 (localhost only)

**Solution (For testing only, not secure):**

Edit `dashboard/advanced_dashboard.py`:
```python
# Change this line:
app.run(debug=False, host='127.0.0.1', port=8050)

# To this:
app.run(debug=False, host='0.0.0.0', port=8050)
```

**Warning**: This exposes dashboard to network without authentication. Only use on trusted networks.

---

## Log Files Guide

### Log Locations

```
logs/
├── sensor_generator.log      # Data generation logs
├── etl_pipeline.log          # ETL processing logs
├── kafka_streaming.log       # Kafka consumer logs
├── ml_predictions.log        # ML model logs
└── control_panel.log         # Control panel logs
```

### Reading Logs

**View in Control Panel:**
1. Select component
2. Logs appear in output panel
3. Auto-scrolls to latest

**View in Terminal:**
```powershell
# Tail (last 50 lines)
Get-Content logs\etl_pipeline.log -Tail 50

# Follow (live updates)
Get-Content logs\etl_pipeline.log -Wait -Tail 10
```

**View in Text Editor:**
```powershell
notepad logs\sensor_generator.log
```

### Log Levels

- **INFO**: Normal operations
- **WARNING**: Potential issues
- **ERROR**: Failures
- **CRITICAL**: System failures

### Common Log Messages

**Normal:**
```
INFO: Starting sensor generator...
INFO: [CYCLE 1] Starting ETL at 14:30:00
INFO: Model trained for Cairo: 45 readings
```

**Warnings:**
```
WARNING: Duplicate reading skipped
WARNING: Reading outside expected range
```

**Errors:**
```
ERROR: Failed to connect to database
ERROR: File not found: output/sensor_data.csv
ERROR: Prophet training failed: insufficient data
```

---

## Quick Diagnostic Commands

### System Health Check
```powershell
python control_panel.py
```
Check all status indicators in the GUI.

### Database Status
```powershell
sqlite3 database\iot_warehouse.db "SELECT name, COUNT(*) FROM sqlite_master WHERE type='table';"
```

### Check Running Processes
```powershell
Get-Process python
```

### Port Usage
```powershell
netstat -ano | findstr :8050
netstat -ano | findstr :8051
```

### Disk Space
```powershell
Get-PSDrive C | Select-Object Used,Free
```

### Python Version
```powershell
python --version
```

### Installed Packages
```powershell
pip list
```

---

## Getting Help

### Self-Help Resources

1. **Read this guide** thoroughly
2. **Check log files** for specific errors
3. **Open Control Panel** to diagnose system status
4. **Read source code comments** in scripts
5. **Check README.md** for architecture

### Reporting Issues

When reporting problems, include:

1. **Error message** (exact text)
2. **Log files** (last 20-50 lines)
3. **Steps to reproduce**
4. **System info**:
   - Windows version
   - Python version
   - Installed packages (pip list)
5. **Database stats** (from Control Panel)

### Example Issue Report

```
Title: Dashboard won't load - connection refused

Error: Unable to connect to http://127.0.0.1:8050

Steps:
1. Ran control_panel.py
2. Clicked "Run All"
3. All components show "Running"
4. Opened Chrome to http://127.0.0.1:8050
5. Got connection refused error

System:
- Windows 11 Pro
- Python 3.14.0
- Dash 3.3.0

Logs:
[Last 10 lines of dashboard logs...]

Database:
- 16,168 readings
- 120 predictions
- 16 alerts
```

---

## Advanced Troubleshooting

### Reset Everything

**Nuclear option - complete reset:**

```powershell
# 1. Stop all processes
# (via Control Panel or close terminal)

# 2. Backup important data
copy database\iot_warehouse.db database\backups\manual_backup.db
copy output\sensor_data.csv output\backups\

# 3. Clean data
Remove-Item database\iot_warehouse.db
Remove-Item output\* -Exclude *.log
Remove-Item logs\* 

# 4. Recreate database
python database\schema.py

# 5. Restart system
python control_panel.py
# Click "Run All"
```

---

### Debug Mode

**Enable verbose logging:**

Edit scripts to change logging level:
```python
# In any script
import logging
logging.basicConfig(level=logging.DEBUG)  # Was INFO
```

---

### Performance Profiling

**Profile slow components:**

```python
import cProfile

cProfile.run('your_function_here()')
```

---

## Still Having Issues?

1. ✅ **Reviewed this guide thoroughly?**
2. ✅ **Checked all log files?**
3. ✅ **Opened Control Panel?**
4. ✅ **Tried restarting components?**
5. ✅ **Tried complete reset?**

**If all else fails:**
- Review source code comments
- Check Python and package versions
- Ensure Windows is updated
- Try on different machine (if available)

---

**Version**: 2.0  
**Last Updated**: November 2025  
**Status**: Production Ready

**Remember**: Most issues are solved by:
1. Reading error messages carefully
2. Checking logs
3. Restarting components
4. Hard refreshing browser
