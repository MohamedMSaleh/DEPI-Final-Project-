"""
Professional IoT Pipeline Control Panel
========================================
Comprehensive monitoring and control interface for the entire data pipeline
"""
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import subprocess
import threading
import time
import sqlite3
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
import sys

class ProcessManager:
    """Enhanced process manager with monitoring capabilities"""
    def __init__(self):
        self.processes = {}
        self.python_exe = sys.executable or "python"
        self.project_root = Path(__file__).resolve().parent
        self.creationflags = 0
        if sys.platform == "win32":
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                self.creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                self.creationflags |= subprocess.CREATE_NO_WINDOW
        
    def start_process(self, name, command):
        """Start a background process with monitoring"""
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

            stdout_buffer = deque(maxlen=500)
            stderr_buffer = deque(maxlen=500)
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
                "threads": threads,
                "start_time": datetime.now(),
                "errors": 0
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

        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            self._cleanup_process(name)
            return True, f"{name} stopped successfully"
        except Exception as e:
            return False, f"Failed to stop {name}: {str(e)}"
    
    def stop_all(self):
        """Stop all running processes"""
        stopped = []
        errors = []
        names = list(self.processes.keys())
        
        for name in names:
            success, message = self.stop_process(name)
            if success:
                stopped.append(name)
            else:
                errors.append(message)
        
        if errors:
            return False, f"Stopped {len(stopped)} components. Errors: {'; '.join(errors)}"
        return True, f"All {len(stopped)} components stopped successfully"
    
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
    
    def get_output(self, name, lines=50):
        """Get recent output from process"""
        info = self.processes.get(name)
        if not info:
            return ""

        stdout = list(info.get("stdout", []))[-lines:]
        stderr = list(info.get("stderr", []))[-lines:]
        
        output = ""
        if stdout:
            output += "".join(stdout)
        if stderr:
            output += "\n--- Errors ---\n" + "".join(stderr)
        
        return output
    
    def get_process_info(self, name):
        """Get detailed process information"""
        info = self.processes.get(name)
        if not info or info["process"].poll() is not None:
            return None
        
        try:
            proc = psutil.Process(info["process"].pid)
            return {
                "pid": proc.pid,
                "cpu": proc.cpu_percent(interval=0.1),
                "memory": proc.memory_info().rss / 1024 / 1024,  # MB
                "uptime": datetime.now() - info["start_time"],
                "status": proc.status()
            }
        except:
            return None

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

class ProfessionalControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 IoT Pipeline Control Center")
        self.root.state('zoomed')  # Open in fullscreen/maximized mode
        self.root.configure(bg="#0a0e27")
        
        self.manager = ProcessManager()
        self.update_thread = None
        self.running = True
        self.component_configs = {}
        self.selected_component = None
        
        # Pipeline metrics
        self.metrics = {
            "total_records": 0,
            "records_per_second": 0,
            "last_update": datetime.now(),
            "errors": 0
        }
        
        self.setup_ui()
        self.start_monitoring()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Create the professional user interface"""
        
        # === TOP BAR ===
        top_bar = tk.Frame(self.root, bg="#1a1f3a", height=80)
        top_bar.pack(fill=tk.X, padx=0, pady=0)
        top_bar.pack_propagate(False)
        
        # Title and status
        title_frame = tk.Frame(top_bar, bg="#1a1f3a")
        title_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        title_label = tk.Label(
            title_frame, 
            text="🚀 IoT PIPELINE CONTROL CENTER",
            font=("Segoe UI", 18, "bold"),
            bg="#1a1f3a",
            fg="#00ff88"
        )
        title_label.pack(anchor=tk.W)
        
        subtitle = tk.Label(
            title_frame,
            text="Real-time Monitoring & Control System",
            font=("Segoe UI", 10),
            bg="#1a1f3a",
            fg="#6c7a89"
        )
        subtitle.pack(anchor=tk.W)
        
        # Quick Actions - Right side
        actions_frame = tk.Frame(top_bar, bg="#1a1f3a")
        actions_frame.pack(side=tk.RIGHT, padx=20)
        
        self.start_all_btn = tk.Button(
            actions_frame,
            text="▶ START ALL",
            command=self.start_all,
            bg="#00d084",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=25,
            pady=12,
            borderwidth=0
        )
        self.start_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_all_btn = tk.Button(
            actions_frame,
            text="■ STOP ALL",
            command=self.stop_all,
            bg="#ff4757",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=25,
            pady=12,
            borderwidth=0
        )
        self.stop_all_btn.pack(side=tk.LEFT, padx=5)
        
        dashboard_btn = tk.Button(
            actions_frame,
            text="🌐 DASHBOARD",
            command=self.open_dashboard,
            bg="#1e90ff",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            padx=25,
            pady=12,
            borderwidth=0
        )
        dashboard_btn.pack(side=tk.LEFT, padx=5)
        
        # === MAIN CONTENT ===
        content = tk.Frame(self.root, bg="#0a0e27")
        content.pack(fill=tk.BOTH, expand=True)
        
        # === LEFT PANEL: Pipeline Status & Components ===
        left_panel = tk.Frame(content, bg="#12162e", width=450)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        left_panel.pack_propagate(False)
        
        # Pipeline Flow Visualization
        flow_frame = tk.LabelFrame(
            left_panel,
            text="📊 PIPELINE FLOW",
            font=("Segoe UI", 11, "bold"),
            bg="#12162e",
            fg="#00ff88",
            borderwidth=2,
            relief=tk.GROOVE
        )
        flow_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.flow_canvas = tk.Canvas(
            flow_frame,
            bg="#1a1f3a",
            height=120,
            highlightthickness=0
        )
        self.flow_canvas.pack(fill=tk.X, padx=10, pady=10)
        
        self.draw_pipeline_flow()
        
        # System Metrics
        metrics_frame = tk.LabelFrame(
            left_panel,
            text="📈 SYSTEM METRICS",
            font=("Segoe UI", 11, "bold"),
            bg="#12162e",
            fg="#00ff88",
            borderwidth=2,
            relief=tk.GROOVE
        )
        metrics_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.metrics_text = tk.Label(
            metrics_frame,
            text="Loading metrics...",
            font=("Consolas", 10),
            bg="#1a1f3a",
            fg="#ffffff",
            justify=tk.LEFT,
            anchor=tk.W,
            padx=15,
            pady=15
        )
        self.metrics_text.pack(fill=tk.X)
        
        # Components List
        components_frame = tk.LabelFrame(
            left_panel,
            text="⚙️ COMPONENTS",
            font=("Segoe UI", 11, "bold"),
            bg="#12162e",
            fg="#00ff88",
            borderwidth=2,
            relief=tk.GROOVE
        )
        components_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable components
        canvas_frame = tk.Frame(components_frame, bg="#1a1f3a")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.components_canvas = tk.Canvas(
            canvas_frame,
            bg="#1a1f3a",
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            canvas_frame,
            orient=tk.VERTICAL,
            command=self.components_canvas.yview
        )
        self.components_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.components_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.components_inner = tk.Frame(self.components_canvas, bg="#1a1f3a")
        self.components_canvas_window = self.components_canvas.create_window(
            (0, 0),
            window=self.components_inner,
            anchor="nw"
        )
        
        self.components_inner.bind(
            "<Configure>",
            lambda e: self.components_canvas.configure(
                scrollregion=self.components_canvas.bbox("all")
            )
        )
        
        self.components_canvas.bind(
            "<Configure>",
            lambda e: self.components_canvas.itemconfigure(
                self.components_canvas_window,
                width=e.width
            )
        )
        
        # Mouse wheel scrolling for components
        def _on_mousewheel(event):
            self.components_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.components_canvas.bind("<Enter>", lambda e: self.components_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.components_canvas.bind("<Leave>", lambda e: self.components_canvas.unbind_all("<MouseWheel>"))
        
        # === RIGHT PANEL: Monitoring & Logs (Scrollable) ===
        right_outer = tk.Frame(content, bg="#12162e")
        right_outer.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar for right panel
        right_canvas = tk.Canvas(right_outer, bg="#12162e", highlightthickness=0)
        right_scrollbar = tk.Scrollbar(right_outer, orient=tk.VERTICAL, command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create inner frame for content
        right_panel = tk.Frame(right_canvas, bg="#12162e")
        right_canvas_window = right_canvas.create_window((0, 0), window=right_panel, anchor="nw")
        
        # Configure scrolling
        right_panel.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )
        
        right_canvas.bind(
            "<Configure>",
            lambda e: right_canvas.itemconfigure(right_canvas_window, width=e.width)
        )
        
        # Mouse wheel scrolling for right panel
        def _scroll_right_panel(event):
            right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        right_canvas.bind("<Enter>", lambda e: right_canvas.bind_all("<MouseWheel>", _scroll_right_panel))
        right_canvas.bind("<Leave>", lambda e: right_canvas.unbind_all("<MouseWheel>"))
        
        # Database Statistics
        db_frame = tk.LabelFrame(
            right_panel,
            text="💾 DATABASE STATUS",
            font=("Segoe UI", 11, "bold"),
            bg="#12162e",
            fg="#00ff88",
            borderwidth=2,
            relief=tk.GROOVE
        )
        db_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.db_text = tk.Label(
            db_frame,
            text="Loading...",
            font=("Consolas", 10),
            bg="#1a1f3a",
            fg="#00ff88",
            justify=tk.LEFT,
            anchor=tk.W,
            padx=15,
            pady=15
        )
        self.db_text.pack(fill=tk.X)
        
        # Process Output Viewer
        output_frame = tk.LabelFrame(
            right_panel,
            text="📺 LIVE PROCESS OUTPUT",
            font=("Segoe UI", 11, "bold"),
            bg="#12162e",
            fg="#00ff88",
            borderwidth=2,
            relief=tk.GROOVE
        )
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Component selector
        selector_frame = tk.Frame(output_frame, bg="#1a1f3a")
        selector_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            selector_frame,
            text="View Output:",
            font=("Segoe UI", 10, "bold"),
            bg="#1a1f3a",
            fg="#ffffff"
        ).pack(side=tk.LEFT, padx=5)
        
        self.output_selector = ttk.Combobox(
            selector_frame,
            state="readonly",
            font=("Segoe UI", 10)
        )
        self.output_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.output_selector.bind("<<ComboboxSelected>>", self.on_component_selected)
        
        # Output display
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            font=("Consolas", 9),
            bg="#0d1117",
            fg="#58a6ff",
            wrap=tk.WORD,
            insertbackground="white"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Activity Log
        log_frame = tk.LabelFrame(
            right_panel,
            text="📋 ACTIVITY LOG",
            font=("Segoe UI", 11, "bold"),
            bg="#12162e",
            fg="#00ff88",
            borderwidth=2,
            relief=tk.GROOVE,
            height=200
        )
        log_frame.pack(fill=tk.X, padx=5, pady=5)
        log_frame.pack_propagate(False)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#0d1117",
            fg="#ffffff",
            wrap=tk.WORD,
            height=8,
            state=tk.NORMAL
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure text tags for colored messages
        self.log_text.tag_configure("success", foreground="#00ff88")
        self.log_text.tag_configure("error", foreground="#ff4757")
        self.log_text.tag_configure("warning", foreground="#ffa502")
        self.log_text.tag_configure("info", foreground="#58a6ff")
        
        # Add components AFTER all UI elements are created
        self.create_components()
        
        self.log("✓ Control Panel initialized")
        self.log("✓ Ready to manage pipeline components")
    
    def create_components(self):
        """Create all component controls"""
        components = [
            {
                "name": "Sensor Generator",
                "key": "generator",
                "icon": "📡",
                "desc": "Simulates IoT sensors → CSV/Kafka",
                "command": [self.manager.python_exe, "sensor_generator.py", "--use-kafka", "--num-sensors", "10", "--interval", "5"],
                "auto_start": True
            },
            {
                "name": "Kafka Consumer",
                "key": "consumer",
                "icon": "🔄",
                "desc": "Consumes stream → Database",
                "command": [self.manager.python_exe, "streaming/kafka_consumer.py"],
                "auto_start": True
            },
            {
                "name": "Batch ETL",
                "key": "etl",
                "icon": "⚙️",
                "desc": "Batch processing & aggregation",
                "command": [self.manager.python_exe, "etl/batch_etl.py"],
                "auto_start": False
            },
            {
                "name": "Dashboard",
                "key": "dashboard",
                "icon": "📊",
                "desc": "Web UI (port 8050)",
                "command": [self.manager.python_exe, "dashboard/advanced_dashboard.py"],
                "auto_start": True
            },
            {
                "name": "Pipeline Monitor",
                "key": "monitor",
                "icon": "📈",
                "desc": "Real-time statistics viewer",
                "command": [self.manager.python_exe, "monitor_pipeline.py"],
                "auto_start": True
            },
            {
                "name": "Legacy DB Injector",
                "key": "injector",
                "icon": "💉",
                "desc": "Direct database writer (manual)",
                "command": [self.manager.python_exe, "inject_live_data.py"],
                "auto_start": False
            },
            {
                "name": "ML Temperature Predictor",
                "key": "ml_predictor",
                "icon": "🧠",
                "desc": "AI-based temperature forecasting",
                "command": [self.manager.python_exe, "ml/temperature_predictor.py"],
                "auto_start": False
            }
        ]
        
        for comp in components:
            self.create_component_control(comp)
            self.component_configs[comp["key"]] = comp
        
        # Update selector
        self.output_selector['values'] = [c["name"] for c in components]
        if components:
            self.output_selector.current(0)
            self.selected_component = components[0]["key"]
    
    def create_component_control(self, config):
        """Create a component control card"""
        frame = tk.Frame(
            self.components_inner,
            bg="#252b42",
            highlightbackground="#3d4466",
            highlightthickness=1
        )
        frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Header
        header = tk.Frame(frame, bg="#252b42")
        header.pack(fill=tk.X, padx=10, pady=8)
        
        # Icon and name
        name_frame = tk.Frame(header, bg="#252b42")
        name_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(
            name_frame,
            text=f"{config['icon']} {config['name']}",
            font=("Segoe UI", 11, "bold"),
            bg="#252b42",
            fg="#ffffff"
        ).pack(side=tk.LEFT)
        
        # Status indicator
        status_var = tk.StringVar(value="●")
        self.__dict__[f"{config['key']}_status"] = status_var
        self.__dict__[f"{config['key']}_status_label"] = tk.Label(
            name_frame,
            textvariable=status_var,
            font=("Segoe UI", 14),
            bg="#252b42",
            fg="#ff4757"
        )
        self.__dict__[f"{config['key']}_status_label"].pack(side=tk.LEFT, padx=10)
        
        # Process info
        info_var = tk.StringVar(value="")
        self.__dict__[f"{config['key']}_info"] = info_var
        tk.Label(
            header,
            textvariable=info_var,
            font=("Consolas", 8),
            bg="#252b42",
            fg="#6c7a89"
        ).pack(side=tk.RIGHT)
        
        # Description
        tk.Label(
            frame,
            text=config['desc'],
            font=("Segoe UI", 9),
            bg="#252b42",
            fg="#8894a6"
        ).pack(anchor=tk.W, padx=10, pady=(0, 8))
        
        # Buttons
        btn_frame = tk.Frame(frame, bg="#252b42")
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Button(
            btn_frame,
            text="▶ Start",
            command=lambda k=config['key']: self.start_component(k),
            bg="#00d084",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            width=12,
            borderwidth=0,
            pady=5
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="■ Stop",
            command=lambda k=config['key']: self.stop_component(k),
            bg="#ff4757",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            relief=tk.FLAT,
            width=12,
            borderwidth=0,
            pady=5
        ).pack(side=tk.LEFT, padx=2)
        
        if config['key'] in ['etl', 'injector']:
            tk.Button(
                btn_frame,
                text="⚡ Run Once",
                command=lambda k=config['key']: self.run_once(k),
                bg="#ffa502",
                fg="white",
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
                relief=tk.FLAT,
                width=12,
                borderwidth=0,
                pady=5
            ).pack(side=tk.LEFT, padx=2)
    
    def draw_pipeline_flow(self):
        """Draw pipeline flow visualization"""
        self.flow_canvas.delete("all")
        width = self.flow_canvas.winfo_width() or 400
        
        stages = [
            ("📡", "Sensor", "generator"),
            ("→", "", None),
            ("🔄", "Kafka", "consumer"),
            ("→", "", None),
            ("💾", "Database", None),
            ("→", "", None),
            ("📊", "Dashboard", "dashboard")
        ]
        
        x_spacing = width // (len(stages) + 1)
        y_center = 60
        
        for i, (icon, label, key) in enumerate(stages):
            x = x_spacing * (i + 1)
            
            if key:
                # Check status
                status = self.manager.get_status(key) if key else "Active"
                color = "#00ff88" if status == "Running" else "#6c7a89"
                
                # Draw node
                self.flow_canvas.create_oval(
                    x - 25, y_center - 25,
                    x + 25, y_center + 25,
                    fill="#252b42",
                    outline=color,
                    width=3
                )
                
                self.flow_canvas.create_text(
                    x, y_center - 10,
                    text=icon,
                    font=("Segoe UI", 16),
                    fill="#ffffff"
                )
                
                self.flow_canvas.create_text(
                    x, y_center + 15,
                    text=label,
                    font=("Segoe UI", 8, "bold"),
                    fill=color
                )
            else:
                # Draw arrow
                self.flow_canvas.create_text(
                    x, y_center,
                    text=icon,
                    font=("Segoe UI", 20),
                    fill="#6c7a89"
                )
    
    def start_component(self, key):
        """Start a specific component"""
        config = self.component_configs.get(key)
        if not config:
            return
        
        self.log(f"⚡ Starting {config['name']}...")
        success, message = self.manager.start_process(key, config['command'])
        
        if success:
            self.log(f"✓ {message}")
        else:
            self.log(f"✗ {message}")
            messagebox.showerror("Error", message)
    
    def stop_component(self, key):
        """Stop a specific component"""
        config = self.component_configs.get(key)
        if not config:
            return
        
        self.log(f"⏹ Stopping {config['name']}...")
        success, message = self.manager.stop_process(key)
        self.log(f"{'✓' if success else '✗'} {message}")
    
    def run_once(self, key):
        """Run a component once (for ETL, etc.)"""
        config = self.component_configs.get(key)
        if not config:
            return
        
        self.log(f"⚡ Running {config['name']} (one-time)...")
        
        def run_and_wait():
            success, message = self.manager.start_process(key, config['command'])
            if success:
                self.log(f"✓ {config['name']} started")
                # Wait for completion
                info = self.manager.processes.get(key)
                if info:
                    info['process'].wait()
                    self.log(f"✓ {config['name']} completed")
            else:
                self.log(f"✗ {message}")
        
        threading.Thread(target=run_and_wait, daemon=True).start()
    
    def start_all(self):
        """Start all auto-start components"""
        self.log("⚡ Starting all primary components...")
        
        started = []
        errors = []
        
        for key, config in self.component_configs.items():
            if config.get('auto_start', False):
                success, message = self.manager.start_process(key, config['command'])
                if success:
                    started.append(config['name'])
                    self.log(f"✓ {config['name']} started")
                else:
                    errors.append(f"{config['name']}: {message}")
                    self.log(f"✗ {message}")
                time.sleep(0.5)
        
        if errors:
            messagebox.showwarning(
                "Partial Start",
                f"Started: {len(started)} components\nErrors: {len(errors)}\n\n" + "\n".join(errors[:3])
            )
        else:
            self.log(f"✓ All {len(started)} components running!")
            messagebox.showinfo(
                "Success",
                f"🚀 Pipeline is LIVE!\n\n"
                f"✓ {len(started)} components started\n"
                f"✓ Dashboard: http://127.0.0.1:8050\n"
                f"✓ Streaming data flow active"
            )
    
    def stop_all(self):
        """Stop all running components"""
        if not self.manager.processes:
            messagebox.showinfo("Info", "No components are currently running")
            return
        
        self.log("⏹ Stopping all components...")
        success, message = self.manager.stop_all()
        
        self.log(f"{'✓' if success else '✗'} {message}")
        
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showwarning("Partial Stop", message)
    
    def open_dashboard(self):
        """Open dashboard in browser"""
        import webbrowser
        webbrowser.open("http://127.0.0.1:8050")
        self.log("🌐 Opened dashboard in browser")
    
    def on_component_selected(self, event):
        """Handle component selection for output view"""
        selected_name = self.output_selector.get()
        for key, config in self.component_configs.items():
            if config['name'] == selected_name:
                self.selected_component = key
                break
    
    def update_status(self):
        """Update all component statuses"""
        for key, config in self.component_configs.items():
            status = self.manager.get_status(key)
            
            # Update status indicator
            status_label = self.__dict__.get(f"{key}_status_label")
            if status_label:
                if status == "Running":
                    status_label.config(fg="#00ff88")
                else:
                    status_label.config(fg="#6c7a89")
            
            # Update process info
            info_var = self.__dict__.get(f"{key}_info")
            if info_var and status == "Running":
                proc_info = self.manager.get_process_info(key)
                if proc_info:
                    uptime = str(proc_info['uptime']).split('.')[0]
                    info_var.set(f"PID:{proc_info['pid']} | CPU:{proc_info['cpu']:.1f}% | RAM:{proc_info['memory']:.0f}MB | ⏱{uptime}")
                else:
                    info_var.set("")
            elif info_var:
                info_var.set("")
    
    def update_output(self):
        """Update process output display"""
        if self.selected_component:
            output = self.manager.get_output(self.selected_component, lines=100)
            if output:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, output)
                self.output_text.see(tk.END)
    
    def update_metrics(self):
        """Update system metrics"""
        try:
            # Count running processes
            running = sum(1 for key in self.component_configs if self.manager.get_status(key) == "Running")
            total = len(self.component_configs)
            
            # Get database stats
            db_path = Path("database/iot_warehouse.db")
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM fact_weather_reading")
                total_records = cursor.fetchone()[0]
                
                # Calculate rate
                elapsed = (datetime.now() - self.metrics['last_update']).total_seconds()
                if elapsed > 0:
                    new_records = total_records - self.metrics['total_records']
                    self.metrics['records_per_second'] = new_records / elapsed
                
                self.metrics['total_records'] = total_records
                self.metrics['last_update'] = datetime.now()
                
                conn.close()
            else:
                total_records = 0
            
            # System resources
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            metrics_text = (
                f"🔄 Components: {running}/{total} Running\n"
                f"📊 Total Records: {total_records:,}\n"
                f"⚡ Processing Rate: {self.metrics['records_per_second']:.1f} rec/sec\n"
                f"💻 CPU Usage: {cpu:.1f}%\n"
                f"🧠 Memory: {memory.percent:.1f}% ({memory.used / 1024 / 1024 / 1024:.1f} GB)"
            )
            
            self.metrics_text.config(text=metrics_text)
            
        except Exception as e:
            self.metrics_text.config(text=f"Error: {str(e)}")
    
    def update_database_stats(self):
        """Update database statistics display"""
        try:
            db_path = Path("database/iot_warehouse.db")
            if not db_path.exists():
                self.db_text.config(text="⚠ Database not found")
                return
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Total readings
            cursor.execute("SELECT COUNT(*) FROM fact_weather_reading")
            total = cursor.fetchone()[0]
            
            # Latest reading
            cursor.execute("""
                SELECT t.ts, l.city_name, f.temperature, f.humidity
                FROM fact_weather_reading f
                JOIN dim_time t ON f.time_id = t.time_id
                JOIN dim_location l ON f.location_id = l.location_id
                ORDER BY t.ts DESC LIMIT 1
            """)
            latest = cursor.fetchone()
            
            # Readings by city
            cursor.execute("""
                SELECT l.city_name, COUNT(*) as cnt
                FROM fact_weather_reading f
                JOIN dim_location l ON f.location_id = l.location_id
                GROUP BY l.city_name
                ORDER BY cnt DESC
                LIMIT 5
            """)
            cities = cursor.fetchall()
            
            conn.close()
            
            stats = f"📊 Total Records: {total:,}\n\n"
            
            if latest:
                stats += f"🕐 Latest: {latest[0]}\n"
                stats += f"📍 {latest[1]}: {latest[2]}°C, {latest[3]}% humidity\n\n"
            
            stats += "📍 Top Cities:\n"
            for city, count in cities:
                bar = "█" * min(20, count // 100)
                stats += f"  {city}: {count:,} {bar}\n"
            
            self.db_text.config(text=stats)
            
        except Exception as e:
            self.db_text.config(text=f"⚠ Error: {str(e)}")
    
    def start_monitoring(self):
        """Start background monitoring"""
        def monitor_loop():
            while self.running:
                try:
                    self.update_status()
                    self.update_metrics()
                    self.update_database_stats()
                    self.update_output()
                    self.draw_pipeline_flow()
                except Exception as e:
                    print(f"Monitor error: {e}")
                time.sleep(2)
        
        self.update_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.update_thread.start()
    
    def log(self, message):
        """Add message to activity log (thread-safe)"""
        def _log():
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Determine color based on message content
                tag = None
                if "✓" in message or "started" in message.lower() or "success" in message.lower():
                    tag = "success"
                elif "✗" in message or "error" in message.lower() or "failed" in message.lower():
                    tag = "error"
                elif "⚠" in message or "warning" in message.lower():
                    tag = "warning"
                elif "⚡" in message or "starting" in message.lower():
                    tag = "info"
                
                # Insert message with color
                self.log_text.config(state=tk.NORMAL)
                if tag:
                    self.log_text.insert(tk.END, f"[{timestamp}] ", "info")
                    self.log_text.insert(tk.END, f"{message}\n", tag)
                else:
                    self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.NORMAL)
            except Exception as e:
                print(f"Log error: {e}")
        
        # Ensure log runs on main thread
        try:
            self.root.after(0, _log)
        except:
            _log()
    
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Stop all components and exit?"):
            self.running = False
            self.log("⏹ Shutting down...")
            self.manager.stop_all()
            self.root.destroy()

def main():
    root = tk.Tk()
    app = ProfessionalControlPanel(root)
    root.mainloop()

if __name__ == "__main__":
    main()
