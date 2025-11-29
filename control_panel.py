"""
IoT Pipeline Control Panel
==========================
Single interface to control the entire pipeline - start, stop, monitor all components.
No need for multiple terminals!
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import deque
import sys

class ProcessManager:
    """Manages all pipeline processes"""
    def __init__(self):
        self.processes = {}
        self.python_exe = sys.executable or "C:/Python314/python.exe"
        self.project_root = Path(__file__).resolve().parent
        self.creationflags = 0
        if sys.platform == "win32":
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                self.creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                self.creationflags |= subprocess.CREATE_NO_WINDOW
        
    def start_process(self, name, command):
        """Start a background process"""
        existing = self.processes.get(name)
        if existing:
            process = existing["process"]
            if process.poll() is None:
                return False, f"{name} is already running"
            self._cleanup_process(name)
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.project_root),
                creationflags=self.creationflags,
                text=True,
                bufsize=1
            )

            stdout_buffer = deque(maxlen=200)
            stderr_buffer = deque(maxlen=200)
            threads = []

            if process.stdout:
                t_out = threading.Thread(
                    target=self._stream_reader,
                    args=(process.stdout, stdout_buffer),
                    daemon=True
                )
                t_out.start()
                threads.append(t_out)

            if process.stderr:
                t_err = threading.Thread(
                    target=self._stream_reader,
                    args=(process.stderr, stderr_buffer),
                    daemon=True
                )
                t_err.start()
                threads.append(t_err)

            self.processes[name] = {
                "process": process,
                "command": command,
                "stdout": stdout_buffer,
                "stderr": stderr_buffer,
                "threads": threads
            }
            return True, f"{name} started successfully"
        except Exception as e:
            return False, f"Failed to start {name}: {str(e)}"
    
    def stop_process(self, name):
        """Stop a specific process"""
        info = self.processes.get(name)
        if not info:
            return False, f"{name} is not running"

        process = info["process"]

        if process.poll() is not None:
            self._cleanup_process(name)
            return True, f"{name} was already stopped"

        error_message = None

        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired as exc:
                    error_message = f"Timed out while stopping: {exc}"
        except Exception as exc:
            error_message = str(exc)
        finally:
            if name in self.processes:
                self._cleanup_process(name)

        if error_message:
            return False, f"Failed to stop {name}: {error_message}"

        return True, f"{name} stopped"
    
    def stop_all(self):
        """Stop all running processes"""
        results = []
        names = list(self.processes.keys())
        for name in names:
            success, message = self.stop_process(name)
            results.append((success, message))

        errors = [msg for success, msg in results if not success]
        if errors:
            return False, "; ".join(errors)
        return True, "All processes stopped"
    
    def get_status(self, name):
        """Check if process is running"""
        info = self.processes.get(name)
        if not info:
            return "Stopped"

        process = info["process"]
        if process.poll() is None:
            return "Running"

        self._cleanup_process(name)
        return "Stopped"
    
    def get_output(self, name, lines=10):
        """Get recent output from process"""
        info = self.processes.get(name)
        if not info:
            return ""

        buffer = info.get("stdout")
        if not buffer:
            return ""

        recent = list(buffer)[-lines:]
        return "".join(recent)

    def _stream_reader(self, stream, buffer):
        """Continuously drain a process stream into a ring buffer"""
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                buffer.append(line)
        except Exception:
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _cleanup_process(self, name):
        """Join reader threads and forget process metadata"""
        info = self.processes.pop(name, None)
        if not info:
            return

        for thread in info.get("threads", []):
            if thread and thread.is_alive():
                thread.join(timeout=0.2)

class ControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("IoT Pipeline Control Panel")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e1e")
        
        self.manager = ProcessManager()
        self.update_thread = None
        self.running = True
        self.component_configs = {}
        self.start_sequence = []
        
        self.setup_ui()
        self.start_monitoring()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Create the user interface"""
        
        # Title
        title_frame = tk.Frame(self.root, bg="#2d2d2d", height=60)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🚀 IoT PIPELINE CONTROL PANEL",
            font=("Segoe UI", 20, "bold"),
            bg="#2d2d2d",
            fg="#00d4ff"
        )
        title_label.pack(pady=10)
        
        # Main container
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side - Controls (scrollable)
        left_outer = tk.Frame(main_frame, bg="#2d2d2d", width=420)
        left_outer.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        left_outer.pack_propagate(False)

        controls_container = tk.Frame(left_outer, bg="#2d2d2d")
        controls_container.pack(fill=tk.BOTH, expand=True)

        self.control_canvas = tk.Canvas(
            controls_container,
            bg="#2d2d2d",
            highlightthickness=0,
            borderwidth=0
        )
        scroll_bar = tk.Scrollbar(
            controls_container,
            orient=tk.VERTICAL,
            command=self.control_canvas.yview
        )
        self.control_canvas.configure(yscrollcommand=scroll_bar.set)
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.controls_frame = tk.Frame(self.control_canvas, bg="#2d2d2d")
        self.controls_frame_id = self.control_canvas.create_window((0, 0), window=self.controls_frame, anchor="nw")

        self.controls_frame.bind(
            "<Configure>",
            lambda e: self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))
        )
        self.control_canvas.bind(
            "<Configure>",
            lambda e: self.control_canvas.itemconfigure(self.controls_frame_id, width=e.width)
        )
        self.control_canvas.bind(
            "<Enter>",
            lambda e: self.control_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        )
        self.control_canvas.bind(
            "<Leave>",
            lambda e: self.control_canvas.unbind_all("<MouseWheel>")
        )

        # Right side - Monitoring
        right_frame = tk.Frame(main_frame, bg="#2d2d2d")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === LEFT SIDE: COMPONENT CONTROLS ===
        
        controls_label = tk.Label(
            self.controls_frame,
            text="COMPONENT CONTROLS",
            font=("Segoe UI", 14, "bold"),
            bg="#2d2d2d",
            fg="#ffffff"
        )
        controls_label.pack(pady=10)
        
        # Component 1: Sensor data generation
        self.create_component_control(
            self.controls_frame,
            "Sensor Generator",
            "generator",
            "Simulates IoT sensors and writes to files/Kafka",
            [
                self.manager.python_exe,
                "sensor_generator.py",
                "--use-kafka",
                "--num-sensors",
                "10",
                "--interval",
                "5"
            ],
            auto_start=True
        )

        # Component 2: Kafka consumer
        self.create_component_control(
            self.controls_frame,
            "Kafka Consumer",
            "consumer",
            "Consumes stream and loads the data warehouse",
            [self.manager.python_exe, "streaming/kafka_consumer.py"],
            auto_start=True
        )

        # Component 3: Batch ETL pipeline (on-demand)
        self.create_component_control(
            self.controls_frame,
            "Batch ETL",
            "etl",
            "Runs batch ETL to refresh warehouse & aggregates",
            [self.manager.python_exe, "etl/batch_etl.py"],
            auto_start=False
        )

        # Component 4: Interactive dashboard
        self.create_component_control(
            self.controls_frame,
            "Dashboard",
            "dashboard",
            "Web visualization (port 8050)",
            [self.manager.python_exe, "dashboard/advanced_dashboard.py"],
            auto_start=True
        )

        # Component 5: Terminal monitor
        self.create_component_control(
            self.controls_frame,
            "Pipeline Monitor",
            "monitor",
            "Real-time statistics viewer",
            [self.manager.python_exe, "monitor_pipeline.py"],
            auto_start=True
        )

        # Component 6: Legacy direct injector (manual)
        self.create_component_control(
            self.controls_frame,
            "Legacy DB Injector",
            "injector",
            "Directly writes demo readings to the warehouse",
            [self.manager.python_exe, "inject_live_data.py"],
            auto_start=False
        )
        
        # Quick Actions
        quick_frame = tk.LabelFrame(
            self.controls_frame,
            text="QUICK ACTIONS",
            font=("Segoe UI", 12, "bold"),
            bg="#2d2d2d",
            fg="#00d4ff",
            pady=10
        )
        quick_frame.pack(fill=tk.X, padx=10, pady=10)
        
        btn_start_all = tk.Button(
            quick_frame,
            text="▶ START ALL",
            command=self.start_all,
            bg="#28a745",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        btn_start_all.pack(fill=tk.X, padx=10, pady=5)
        
        btn_stop_all = tk.Button(
            quick_frame,
            text="■ STOP ALL",
            command=self.stop_all,
            bg="#dc3545",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        btn_stop_all.pack(fill=tk.X, padx=10, pady=5)
        
        btn_run_etl = tk.Button(
            quick_frame,
            text="⚙ RUN BATCH ETL",
            command=lambda: self.start_component("etl"),
            bg="#ffc107",
            fg="#1e1e1e",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        btn_run_etl.pack(fill=tk.X, padx=10, pady=5)
        
        btn_dashboard = tk.Button(
            quick_frame,
            text="🌐 OPEN DASHBOARD",
            command=self.open_dashboard,
            bg="#007bff",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        btn_dashboard.pack(fill=tk.X, padx=10, pady=5)
        
        # === RIGHT SIDE: MONITORING ===
        
        monitor_label = tk.Label(
            right_frame,
            text="SYSTEM MONITORING",
            font=("Segoe UI", 14, "bold"),
            bg="#2d2d2d",
            fg="#ffffff"
        )
        monitor_label.pack(pady=10)
        
        # Database Stats
        stats_frame = tk.LabelFrame(
            right_frame,
            text="DATABASE STATISTICS",
            font=("Segoe UI", 10, "bold"),
            bg="#2d2d2d",
            fg="#00d4ff"
        )
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_text = tk.Label(
            stats_frame,
            text="Loading...",
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#00ff00",
            justify=tk.LEFT,
            anchor=tk.W,
            padx=10,
            pady=10
        )
        self.stats_text.pack(fill=tk.X)
        
        # Activity Log
        log_frame = tk.LabelFrame(
            right_frame,
            text="ACTIVITY LOG",
            font=("Segoe UI", 10, "bold"),
            bg="#2d2d2d",
            fg="#00d4ff"
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#ffffff",
            wrap=tk.WORD,
            height=15
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log("Control Panel initialized")
        self.log("Ready to start pipeline components")
    
    def create_component_control(self, parent, name, key, description, command, auto_start=False):
        """Create a control panel for a component"""
        self.component_configs[key] = {
            "name": name,
            "command": command,
            "auto_start": auto_start
        }
        if auto_start:
            self.start_sequence.append(key)

        frame = tk.LabelFrame(
            parent,
            text=name,
            font=("Segoe UI", 11, "bold"),
            bg="#2d2d2d",
            fg="#00d4ff",
            pady=5
        )
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        desc_label = tk.Label(
            frame,
            text=description,
            font=("Segoe UI", 9),
            bg="#2d2d2d",
            fg="#999999"
        )
        desc_label.pack(anchor=tk.W, padx=10, pady=(5, 10))
        
        btn_frame = tk.Frame(frame, bg="#2d2d2d")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_var = tk.StringVar(value="●")
        self.__dict__[f"{key}_status"] = status_var
        
        status_label = tk.Label(
            btn_frame,
            textvariable=status_var,
            font=("Segoe UI", 16),
            bg="#2d2d2d",
            fg="#ff0000",
            width=2
        )
        status_label.pack(side=tk.LEFT, padx=5)
        
        btn_start = tk.Button(
            btn_frame,
            text="▶ Start",
            command=lambda k=key: self.start_component(k),
            bg="#28a745",
            fg="white",
            font=("Segoe UI", 10),
            cursor="hand2",
            relief=tk.FLAT,
            width=10
        )
        btn_start.pack(side=tk.LEFT, padx=5)
        
        btn_stop = tk.Button(
            btn_frame,
            text="■ Stop",
            command=lambda k=key: self.stop_component(k),
            bg="#6c757d",
            fg="white",
            font=("Segoe UI", 10),
            cursor="hand2",
            relief=tk.FLAT,
            width=10
        )
        btn_stop.pack(side=tk.LEFT, padx=5)
    
    def start_component(self, key):
        """Start a component"""
        config = self.component_configs.get(key)
        if not config:
            messagebox.showerror("Error", f"Unknown component: {key}")
            return

        name = config["name"]
        command = config["command"]

        success, message = self.manager.start_process(key, command)
        self.log(f"{name}: {message}")
        if not success:
            messagebox.showerror("Error", message)
    
    def stop_component(self, key):
        """Stop a component"""
        config = self.component_configs.get(key)
        if not config:
            messagebox.showerror("Error", f"Unknown component: {key}")
            return

        name = config["name"]
        success, message = self.manager.stop_process(key)
        self.log(f"{name}: {message}")

    def _on_mousewheel(self, event):
        """Scroll the control canvas when the mouse wheel is moved."""
        if not hasattr(self, "control_canvas"):
            return
        # Windows sends multiples of 120; normalize so each notch scrolls one unit
        delta = int(-1 * (event.delta / 120))
        if delta:
            self.control_canvas.yview_scroll(delta, "units")
    
    def start_all(self):
        """Start all components"""
        self.log("Starting all components...")
        errors = []

        for key in self.start_sequence:
            config = self.component_configs.get(key)
            if not config:
                continue

            success, message = self.manager.start_process(key, config["command"])
            self.log(f"{config['name']}: {message}")
            if not success:
                errors.append(f"{config['name']}: {message}")
            time.sleep(1)

        if errors:
            messagebox.showerror("Error", "\n".join(errors))
        else:
            self.log("Primary components started")
            messagebox.showinfo(
                "Success",
                "Streaming pipeline is live!\n\n"
                "Components: Sensor Generator, Kafka Consumer, Dashboard, Monitor\n"
                "Dashboard: http://127.0.0.1:8050"
            )
    
    def stop_all(self):
        """Stop all components"""
        self.log("Stopping all components...")
        success, message = self.manager.stop_all()
        self.log(message)
        if success:
            messagebox.showinfo("Success", "All components stopped")
        else:
            messagebox.showerror("Error", message)
    
    def open_dashboard(self):
        """Open dashboard in browser"""
        import webbrowser
        webbrowser.open("http://127.0.0.1:8050")
        self.log("Opened dashboard in browser")
    
    def update_status(self):
        """Update component status indicators"""
        for comp in list(self.component_configs.keys()):
            status = self.manager.get_status(comp)
            status_var = self.__dict__.get(f"{comp}_status")
            if status_var:
                status_var.set("●")
                if status == "Running":
                    # Change color by updating the label directly
                    for widget in self.root.winfo_children():
                        self.update_status_color(widget, comp, "#00ff00")
                else:
                    for widget in self.root.winfo_children():
                        self.update_status_color(widget, comp, "#ff0000")
    
    def update_status_color(self, widget, comp_name, color):
        """Recursively update status label color"""
        for child in widget.winfo_children():
            if isinstance(child, tk.Label) and hasattr(child, 'textvariable'):
                if child.textvariable == self.__dict__.get(f"{comp_name}_status"):
                    child.config(fg=color)
            self.update_status_color(child, comp_name, color)
    
    def update_database_stats(self):
        """Update database statistics"""
        try:
            db_path = Path("database/iot_warehouse.db")
            if not db_path.exists():
                self.stats_text.config(text="Database not found")
                return
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get total readings
            cursor.execute("SELECT COUNT(*) FROM fact_weather_reading")
            total_readings = cursor.fetchone()[0]
            
            # Get latest reading
            cursor.execute("""
                SELECT t.ts, l.city_name, f.temperature, f.humidity
                FROM fact_weather_reading f
                JOIN dim_time t ON f.time_id = t.time_id
                JOIN dim_location l ON f.location_id = l.location_id
                ORDER BY t.ts DESC LIMIT 1
            """)
            latest = cursor.fetchone()
            
            # Get readings per city
            cursor.execute("""
                SELECT l.city_name, COUNT(*) as count
                FROM fact_weather_reading f
                JOIN dim_location l ON f.location_id = l.location_id
                GROUP BY l.city_name
                ORDER BY count DESC
            """)
            city_counts = cursor.fetchall()
            
            conn.close()
            
            # Format statistics
            stats = f"Total Readings: {total_readings:,}\n\n"
            
            if latest:
                stats += f"Latest Reading:\n"
                stats += f"  Time: {latest[0]}\n"
                stats += f"  City: {latest[1]}\n"
                stats += f"  Temp: {latest[2]}°C\n"
                stats += f"  Humidity: {latest[3]}%\n\n"
            
            stats += "Readings by City:\n"
            for city, count in city_counts:
                stats += f"  {city}: {count:,}\n"
            
            self.stats_text.config(text=stats)
            
        except Exception as e:
            self.stats_text.config(text=f"Error: {str(e)}")
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        def monitor_loop():
            while self.running:
                try:
                    self.update_status()
                    self.update_database_stats()
                except:
                    pass
                time.sleep(2)
        
        self.update_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.update_thread.start()
    
    def log(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Stop all components and exit?"):
            self.running = False
            self.manager.stop_all()
            self.root.destroy()

def main():
    root = tk.Tk()
    app = ControlPanel(root)
    root.mainloop()

if __name__ == "__main__":
    main()
