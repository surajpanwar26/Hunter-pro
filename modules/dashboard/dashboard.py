'''Modern Tkinter dashboard to control and monitor the bot - Enhanced UI/UX.'''
import tkinter as tk
from tkinter import scrolledtext, messagebox, Menu, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import ttkbootstrap as ttkb
from datetime import datetime
import webbrowser
import os
import subprocess
import json
import threading

from modules.dashboard import log_handler, metrics
from config.secrets import ai_provider
from config.questions import user_information_all
from modules.dashboard.resume_tailor_dialog import ResumeTailorDialog


# Import for modern styling
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# Modern Color Scheme
COLORS = {
    'bg_dark': '#1a1a2e',
    'bg_medium': '#16213e',
    'bg_light': '#0f3460',
    'accent': '#e94560',
    'success': '#00d26a',
    'warning': '#ffb302',
    'danger': '#ff4757',
    'info': '#3498db',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a0',
    'card_bg': '#252540',
    'border': '#3a3a5c'
}


class AnimatedButton(ttkb.Button):
    """Button with hover animation effect"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        
    def _on_enter(self, e):
        self.configure(cursor='hand2')
        
    def _on_leave(self, e):
        self.configure(cursor='')


class StatusCard(ttkb.Frame):
    """Modern stat card with icon and animated value"""
    def __init__(self, parent, title, icon, value="0", color="info", **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(padding=15)
        
        # Icon and title row
        header = ttkb.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        
        icon_label = ttkb.Label(header, text=icon, font=("Segoe UI Emoji", 24))
        icon_label.pack(side=tk.LEFT)
        
        title_label = ttkb.Label(header, text=title, font=("Segoe UI", 11), 
                                 foreground=COLORS['text_secondary'])
        title_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Value
        self.value_label = ttkb.Label(self, text=value, font=("Segoe UI", 32, "bold"),
                                      bootstyle=color)
        self.value_label.pack(anchor=tk.W)
        
        # Trend indicator (optional)
        self.trend_label = ttkb.Label(self, text="", font=("Segoe UI", 10),
                                      foreground=COLORS['text_secondary'])
        self.trend_label.pack(anchor=tk.W, pady=(5, 0))
    
    def set_value(self, value, trend=None):
        self.value_label.config(text=str(value))
        if trend:
            self.trend_label.config(text=trend)


class CircularProgress(tk.Canvas):
    """Circular progress indicator"""
    def __init__(self, parent, size=100, thickness=10, **kwargs):
        super().__init__(parent, width=size, height=size, 
                        bg=COLORS['bg_dark'], highlightthickness=0, **kwargs)
        self.size = size
        self.thickness = thickness
        self.progress = 0
        self._draw()
    
    def _draw(self):
        self.delete("all")
        padding = 5
        
        # Background circle
        self.create_oval(padding, padding, self.size - padding, self.size - padding,
                        outline=COLORS['border'], width=self.thickness)
        
        # Progress arc
        if self.progress > 0:
            extent = (self.progress / 100) * 360
            self.create_arc(padding, padding, self.size - padding, self.size - padding,
                           start=90, extent=-extent, outline=COLORS['success'],
                           width=self.thickness, style=tk.ARC)
        
        # Center text
        self.create_text(self.size // 2, self.size // 2, text=f"{int(self.progress)}%",
                        fill=COLORS['text_primary'], font=("Segoe UI", 14, "bold"))
    
    def set_progress(self, value):
        self.progress = min(100, max(0, value))
        self._draw()


class ActivityFeed(ttkb.Frame):
    """Live activity feed with timestamps"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Header
        header = ttkb.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttkb.Label(header, text="📋 Activity Feed", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        
        self.clear_btn = ttkb.Button(header, text="Clear", bootstyle="secondary-link",
                                     command=self.clear_feed)
        self.clear_btn.pack(side=tk.RIGHT)
        
        # Feed list
        self.feed_frame = ttkb.Frame(self)
        self.feed_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable canvas
        self.canvas = tk.Canvas(self.feed_frame, bg=COLORS['bg_dark'], 
                               highlightthickness=0, height=200)
        self.scrollbar = ttkb.Scrollbar(self.feed_frame, orient="vertical",
                                        command=self.canvas.yview)
        self.scrollable_frame = ttkb.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.activities = []
        self.max_items = 50
    
    def add_activity(self, message, activity_type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "job": "💼",
            "chrome": "🌐"
        }
        
        colors = {
            "success": COLORS['success'],
            "error": COLORS['danger'],
            "warning": COLORS['warning'],
            "info": COLORS['info'],
            "job": "#9c27b0",
            "chrome": "#ff9800"
        }
        
        icon = icons.get(activity_type, "ℹ️")
        color = colors.get(activity_type, COLORS['info'])
        
        item_frame = ttkb.Frame(self.scrollable_frame)
        item_frame.pack(fill=tk.X, pady=2, padx=5)
        
        time_label = ttkb.Label(item_frame, text=timestamp, font=("Consolas", 9),
                               foreground=COLORS['text_secondary'])
        time_label.pack(side=tk.LEFT, padx=(0, 10))
        
        icon_label = ttkb.Label(item_frame, text=icon, font=("Segoe UI Emoji", 10))
        icon_label.pack(side=tk.LEFT, padx=(0, 5))
        
        msg_label = ttkb.Label(item_frame, text=message[:80], font=("Segoe UI", 10),
                              foreground=color)
        msg_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.activities.append(item_frame)
        
        # Limit items
        if len(self.activities) > self.max_items:
            old = self.activities.pop(0)
            old.destroy()
        
        # Auto scroll to bottom
        self.canvas.yview_moveto(1.0)
    
    def clear_feed(self):
        for item in self.activities:
            item.destroy()
        self.activities.clear()


class QuickActions(ttkb.Frame):
    """Quick action buttons panel"""
    def __init__(self, parent, dashboard, **kwargs):
        super().__init__(parent, **kwargs)
        self.dashboard = dashboard
        
        actions_grid = ttkb.Frame(self)
        actions_grid.pack(fill=tk.X)
        
        actions = [
            ("📂 Open Logs", self.open_logs_folder, "secondary"),
            ("📊 Export CSV", self.export_data, "info"),
            ("🔄 Refresh", self.refresh_all, "primary"),
            ("⚙️ Settings", self.open_settings, "warning"),
        ]
        
        for i, (text, cmd, style) in enumerate(actions):
            btn = AnimatedButton(actions_grid, text=text, command=cmd, 
                               bootstyle=f"{style}-outline", width=14)
            btn.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
        
        actions_grid.columnconfigure(0, weight=1)
        actions_grid.columnconfigure(1, weight=1)
    
    def open_logs_folder(self):
        try:
            logs_path = os.path.abspath("logs")
            if os.path.exists(logs_path):
                webbrowser.open(f'file:///{logs_path}')
            else:
                messagebox.showinfo("Info", "Logs folder not found")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def export_data(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Logs"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.dashboard.log_text.get("1.0", tk.END))
                messagebox.showinfo("Success", f"Logs exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def refresh_all(self):
        self.dashboard._refresh_metrics()
        self.dashboard.activity_feed.add_activity("Dashboard refreshed", "info")
    
    def open_settings(self):
        messagebox.showinfo("Settings", "Settings panel coming soon!")


class BotDashboard(ttkb.Window):
    def __init__(self, controller):
        # Use ttkbootstrap theme - cyborg for dark modern look
        super().__init__(themename="cyborg")
        self.title("🤖 AI Job Hunter Pro - Control Center")
        self.geometry("1400x900")
        self.state('zoomed')
        self.controller = controller
        
        # Configure style (using _style to avoid property conflict)
        self._app_style = ttkb.Style()
        self._app_style.configure('Card.TFrame', background=COLORS['card_bg'])
        
        # Create main menu
        self.create_menu()
        
        # Main container with gradient-like effect
        main_frame = ttkb.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ========== TOP BAR ==========
        self.create_top_bar(main_frame)
        
        # ========== MAIN CONTENT ==========
        content_frame = ttkb.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Create PanedWindow for resizable panels (using tkinter's PanedWindow)
        self.paned_window = tk.PanedWindow(content_frame, orient=tk.HORIZONTAL, 
                                            sashwidth=8, sashrelief=tk.RAISED,
                                            bg='#2d3436')
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (main content) - save reference for toggle
        self.left_panel_frame = ttkb.Frame(self.paned_window)
        self.paned_window.add(self.left_panel_frame, minsize=400, width=700)
        
        # Stat Cards Row
        self.create_stat_cards(self.left_panel_frame)
        
        # Tabs Section
        self.create_tabs_section(self.left_panel_frame)
        
        # Right Panel (resizable info panel) - save reference for toggle
        self.right_panel_frame = ttkb.Frame(self.paned_window)
        self.paned_window.add(self.right_panel_frame, minsize=300, width=450)
        
        self.create_right_panel(self.right_panel_frame)
        
        # Initialize stats BEFORE status bar (needed for _update_time)
        self.job_count = 0
        self.applied_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.current_status = "Stopped"
        self.start_time = None
        self.current_job_info = {}
        self.skip_reasons = []
        
        # ========== BOTTOM STATUS BAR ==========
        self.create_status_bar(main_frame)
        
        # Setup background updates
        self.log_queue = log_handler.get_queue()
        log_handler.subscribe(self._on_new_log)
        self.after(500, self._refresh_metrics)
        self._log_buffer: list[str] = []
        self._last_metrics_snapshot: dict | None = None
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Welcome message
        self.activity_feed.add_activity("Dashboard initialized", "success")
        self.activity_feed.add_activity("Ready to start job hunting!", "info")
    
    def create_top_bar(self, parent):
        """Create the top navigation bar"""
        top_bar = ttkb.Frame(parent)
        top_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Left side - Logo and title
        left_section = ttkb.Frame(top_bar)
        left_section.pack(side=tk.LEFT, padx=15, pady=10)
        
        logo_frame = ttkb.Frame(left_section)
        logo_frame.pack(side=tk.LEFT)
        
        # Animated logo effect
        self.logo_label = ttkb.Label(logo_frame, text="🤖", font=("Segoe UI Emoji", 32))
        self.logo_label.pack(side=tk.LEFT)
        
        title_frame = ttkb.Frame(left_section)
        title_frame.pack(side=tk.LEFT, padx=(15, 0))
        
        ttkb.Label(title_frame, text="AI Job Hunter Pro", 
                  font=("Segoe UI", 20, "bold")).pack(anchor=tk.W)
        ttkb.Label(title_frame, text="Automated LinkedIn Job Application System",
                  font=("Segoe UI", 10), foreground=COLORS['text_secondary']).pack(anchor=tk.W)
        
        # Center - Control Buttons
        controls_frame = ttkb.Frame(top_bar)
        controls_frame.pack(side=tk.LEFT, expand=True, padx=20)
        
        btn_frame = ttkb.Frame(controls_frame)
        btn_frame.pack()
        
        # Row 1: Main control buttons
        self.start_btn = AnimatedButton(btn_frame, text="▶ Start", 
                                        command=self.start_bot, bootstyle="success",
                                        width=10, padding=(10, 8))
        self.start_btn.pack(side=tk.LEFT, padx=3)
        
        self.stop_btn = AnimatedButton(btn_frame, text="⏹ Stop", 
                                       command=self.stop_bot, state=tk.DISABLED,
                                       bootstyle="danger", width=10, padding=(10, 8))
        self.stop_btn.pack(side=tk.LEFT, padx=3)
        
        self.pause_btn = AnimatedButton(btn_frame, text="⏸ Pause", 
                                        command=self.toggle_pause, state=tk.DISABLED,
                                        bootstyle="warning", width=10, padding=(10, 8))
        self.pause_btn.pack(side=tk.LEFT, padx=3)
        
        # Separator
        ttkb.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=5)
        
        # Side Panel Mode Button - PROMINENT
        self.side_panel_mode = False
        self.side_panel_btn = AnimatedButton(btn_frame, text="📌 Side Mode", 
                                             command=self.toggle_side_panel_mode,
                                             bootstyle="primary", width=12, padding=(10, 8))
        self.side_panel_btn.pack(side=tk.LEFT, padx=3)
        
        # Toggle Right Panel Button
        self.panel_visible = True
        self.toggle_panel_btn = AnimatedButton(btn_frame, text="◀ Panel", 
                                               command=self.toggle_right_panel,
                                               bootstyle="secondary-outline", width=10, padding=(10, 8))
        self.toggle_panel_btn.pack(side=tk.LEFT, padx=3)
        
        # Right side - Status
        right_section = ttkb.Frame(top_bar)
        right_section.pack(side=tk.RIGHT, padx=15, pady=10)
        
        status_card = ttkb.Frame(right_section, padding=10)
        status_card.pack()
        
        status_row = ttkb.Frame(status_card)
        status_row.pack()
        
        self.status_indicator = ttkb.Label(status_row, text="●", 
                                          foreground=COLORS['danger'], 
                                          font=("Arial", 20))
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_label = ttkb.Label(status_row, text="STOPPED", 
                                       font=("Segoe UI", 14, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Runtime timer
        self.runtime_label = ttkb.Label(status_card, text="Runtime: 00:00:00",
                                        font=("Consolas", 10),
                                        foreground=COLORS['text_secondary'])
        self.runtime_label.pack(pady=(5, 0))
    
    def create_stat_cards(self, parent):
        """Create the statistics cards row"""
        cards_frame = ttkb.Frame(parent)
        cards_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Configure grid
        for i in range(5):
            cards_frame.columnconfigure(i, weight=1)
        
        # Jobs Found Card
        self.jobs_card = StatusCard(cards_frame, "Jobs Found", "🔍", "0", "info")
        self.jobs_card.grid(row=0, column=0, padx=5, sticky="nsew")
        
        # Applied Card
        self.applied_card = StatusCard(cards_frame, "Applied", "✅", "0", "success")
        self.applied_card.grid(row=0, column=1, padx=5, sticky="nsew")
        
        # Failed Card
        self.failed_card = StatusCard(cards_frame, "Failed", "❌", "0", "danger")
        self.failed_card.grid(row=0, column=2, padx=5, sticky="nsew")
        
        # Skipped Card
        self.skipped_card = StatusCard(cards_frame, "Skipped", "⏭️", "0", "warning")
        self.skipped_card.grid(row=0, column=3, padx=5, sticky="nsew")
        
        # Success Rate Card
        self.rate_card = StatusCard(cards_frame, "Success Rate", "📊", "0%", "primary")
        self.rate_card.grid(row=0, column=4, padx=5, sticky="nsew")
    
    def create_tabs_section(self, parent):
        """Create the main tabbed interface"""
        notebook = ttkb.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # === Live Logs Tab ===
        logs_tab = ttkb.Frame(notebook)
        notebook.add(logs_tab, text="📋 Live Logs")
        
        # Logs toolbar
        logs_toolbar = ttkb.Frame(logs_tab)
        logs_toolbar.pack(fill=tk.X, pady=(5, 10))
        
        ttkb.Label(logs_toolbar, text="🔍 Filter:", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(5, 10))
        
        self.log_filter = ttkb.Combobox(logs_toolbar, values=["All", "Info", "Success", "Warning", "Error"],
                                        state="readonly", width=15)
        self.log_filter.set("All")
        self.log_filter.pack(side=tk.LEFT)
        
        ttkb.Button(logs_toolbar, text="🗑️ Clear Logs", bootstyle="secondary-outline",
                   command=self.clear_logs).pack(side=tk.RIGHT, padx=5)
        
        ttkb.Button(logs_toolbar, text="📥 Export", bootstyle="info-outline",
                   command=self.export_logs).pack(side=tk.RIGHT, padx=5)
        
        # Main log area
        log_paned = ttkb.Panedwindow(logs_tab, orient=tk.VERTICAL)
        log_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log text
        log_frame = ttkb.Frame(log_paned)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, state=tk.NORMAL, height=18,
            bg="#0d1117", fg="#c9d1d9", insertbackground="#ffffff",
            font=("JetBrains Mono", 10), wrap=tk.WORD,
            selectbackground="#388bfd", selectforeground="#ffffff"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log text tags for coloring
        self.log_text.tag_configure("error", foreground="#f85149")
        self.log_text.tag_configure("success", foreground="#3fb950")
        self.log_text.tag_configure("warning", foreground="#d29922")
        self.log_text.tag_configure("info", foreground="#58a6ff")
        self.log_text.tag_configure("timestamp", foreground="#8b949e")
        
        log_paned.add(log_frame, weight=3)
        
        # AI Output
        ai_frame = ttkb.Labelframe(log_paned, text="🤖 AI Assistant Output", bootstyle="info")
        self.ai_output = scrolledtext.ScrolledText(
            ai_frame, height=6, bg="#161b22", fg="#7ee787",
            font=("JetBrains Mono", 10), wrap=tk.WORD
        )
        self.ai_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_paned.add(ai_frame, weight=1)
        
        # === Statistics Tab ===
        stats_tab = ttkb.Frame(notebook)
        notebook.add(stats_tab, text="📊 Statistics")
        self.create_statistics_tab(stats_tab)
        
        # === Job Applications Tab ===
        jobs_tab = ttkb.Frame(notebook)
        notebook.add(jobs_tab, text="💼 Job Applications")
        self.create_jobs_tab(jobs_tab)
        
        # === Settings Tab ===
        settings_tab = ttkb.Frame(notebook)
        notebook.add(settings_tab, text="⚙️ Settings")
        self.create_settings_tab(settings_tab)
    
    def create_statistics_tab(self, parent):
        """Create the statistics and charts tab"""
        # Top metrics row
        metrics_frame = ttkb.Labelframe(parent, text="📈 Live Metrics", bootstyle="info")
        metrics_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.metric_labels: dict[str, ttkb.Label] = {}
        
        metrics_grid = ttkb.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.X, padx=10, pady=10)
        
        metrics_data = [
            ("AI Provider", "ai_provider", 0, 0),
            ("Jobs Processed", "jobs_processed", 0, 1),
            ("Easy Applied", "easy_applied", 0, 2),
            ("External Jobs", "external_jobs", 0, 3),
            ("JD Analyses", "jd_analysis_count", 1, 0),
            ("Resume Tailorings", "resume_tailoring_count", 1, 1),
            ("Avg JD Time (s)", "jd_analysis_avg", 1, 2),
            ("Avg Resume Time (s)", "resume_tailoring_avg", 1, 3),
            ("Last JD Time (s)", "jd_analysis_last", 2, 0),
            ("Last Resume Time (s)", "resume_last", 2, 1),
            ("ETA (min)", "eta_minutes", 2, 2),
            ("Ollama Calls", "ollama_calls", 2, 3),
        ]
        
        for label, key, row, col in metrics_data:
            cell = ttkb.Frame(metrics_grid)
            cell.grid(row=row, column=col, padx=15, pady=8, sticky="w")
            ttkb.Label(cell, text=label, font=("Segoe UI", 10),
                      foreground=COLORS['text_secondary']).pack(anchor=tk.W)
            value_label = ttkb.Label(cell, text="--", font=("Segoe UI", 14, "bold"))
            value_label.pack(anchor=tk.W)
            self.metric_labels[key] = value_label
        
        for i in range(4):
            metrics_grid.columnconfigure(i, weight=1)
        
        # Progress bars
        progress_frame = ttkb.Frame(parent)
        progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # JD Analysis Progress
        jd_frame = ttkb.Frame(progress_frame)
        jd_frame.pack(fill=tk.X, pady=5)
        ttkb.Label(jd_frame, text="Job Description Analysis", 
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.jd_progress_label = ttkb.Label(jd_frame, text="0%", font=("Segoe UI", 10, "bold"),
                                           bootstyle="success")
        self.jd_progress_label.pack(side=tk.RIGHT)
        self.jd_progress = ttkb.Progressbar(progress_frame, bootstyle="success-striped",
                                           mode="determinate", length=400)
        self.jd_progress.pack(fill=tk.X, pady=(0, 10))
        
        # Resume Tailoring Progress
        resume_frame = ttkb.Frame(progress_frame)
        resume_frame.pack(fill=tk.X, pady=5)
        ttkb.Label(resume_frame, text="Resume Tailoring", 
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.resume_progress_label = ttkb.Label(resume_frame, text="0%", 
                                                font=("Segoe UI", 10, "bold"),
                                                bootstyle="info")
        self.resume_progress_label.pack(side=tk.RIGHT)
        self.resume_progress = ttkb.Progressbar(progress_frame, bootstyle="info-striped",
                                               mode="determinate", length=400)
        self.resume_progress.pack(fill=tk.X)
        
        # Charts
        charts_frame = ttkb.Frame(parent)
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        plt.style.use('dark_background')
        
        fig = Figure(figsize=(12, 5), dpi=100, facecolor='#1a1a2e')
        fig.patch.set_alpha(0.9)
        
        self.ax_ts = fig.add_subplot(131)
        self.ax_pie = fig.add_subplot(132)
        self.ax_bar = fig.add_subplot(133)
        
        for ax in [self.ax_ts, self.ax_pie, self.ax_bar]:
            ax.set_facecolor('#16213e')
            ax.tick_params(colors='white', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('#3a3a5c')
        
        self.canvas = FigureCanvasTkAgg(fig, master=charts_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def create_jobs_tab(self, parent):
        """Create the job applications table tab"""
        # Toolbar
        toolbar = ttkb.Frame(parent)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        ttkb.Label(toolbar, text="💼 Recent Applications", 
                  font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        
        ttkb.Button(toolbar, text="🔄 Refresh", bootstyle="info-outline",
                   command=self.refresh_jobs_table).pack(side=tk.RIGHT, padx=5)
        ttkb.Button(toolbar, text="📥 Export to CSV", bootstyle="success-outline",
                   command=self.export_jobs_csv).pack(side=tk.RIGHT, padx=5)
        
        # Table
        table_frame = ttkb.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ("ID", "Job Title", "Company", "Location", "Status", "Date Applied")
        self.job_tree = ttkb.Treeview(table_frame, columns=columns, show="headings",
                                      height=15)
        
        # Column configuration
        widths = {"ID": 80, "Job Title": 250, "Company": 200, "Location": 150, 
                 "Status": 100, "Date Applied": 150}
        
        for col in columns:
            self.job_tree.heading(col, text=col, anchor=tk.W)
            self.job_tree.column(col, width=widths.get(col, 100), anchor=tk.W)
        
        # Tags for coloring
        self.job_tree.tag_configure("applied", background="#1e4620")
        self.job_tree.tag_configure("failed", background="#4a1e1e")
        self.job_tree.tag_configure("skipped", background="#4a3d1e")
        
        # Scrollbars
        y_scroll = ttkb.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.job_tree.yview)
        x_scroll = ttkb.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.job_tree.xview)
        self.job_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.job_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_settings_tab(self, parent):
        """Create the settings tab"""
        settings_frame = ttkb.Frame(parent)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttkb.Label(settings_frame, text="⚙️ Quick Settings", 
                  font=("Segoe UI", 16, "bold")).pack(anchor=tk.W, pady=(0, 20))
        
        # Settings grid
        settings_grid = ttkb.Frame(settings_frame)
        settings_grid.pack(fill=tk.X)
        
        settings = [
            ("🔊 Enable Sound Notifications", "sound_notify", True),
            ("📧 Email Notifications", "email_notify", False),
            ("🌙 Dark Mode", "dark_mode", True),
            ("📊 Auto Refresh Stats", "auto_refresh", True),
            ("💾 Auto Save Logs", "auto_save_logs", True),
        ]
        
        self.setting_vars = {}
        
        for i, (label, key, default) in enumerate(settings):
            frame = ttkb.Frame(settings_grid)
            frame.pack(fill=tk.X, pady=8)
            
            var = tk.BooleanVar(value=default)
            self.setting_vars[key] = var
            
            ttkb.Label(frame, text=label, font=("Segoe UI", 11)).pack(side=tk.LEFT)
            
            switch = ttkb.Checkbutton(frame, variable=var, bootstyle="round-toggle")
            switch.pack(side=tk.RIGHT)
        
        # Info section
        info_frame = ttkb.Labelframe(settings_frame, text="ℹ️ System Information", 
                                    bootstyle="info")
        info_frame.pack(fill=tk.X, pady=(30, 0))
        
        info_grid = ttkb.Frame(info_frame)
        info_grid.pack(fill=tk.X, padx=15, pady=15)
        
        info_items = [
            ("Version", "1.0.0"),
            ("AI Provider", ai_provider),
            ("Python Version", "3.14"),
            ("Author", "Suraj Singh Panwar"),
        ]
        
        for i, (label, value) in enumerate(info_items):
            ttkb.Label(info_grid, text=f"{label}:", font=("Segoe UI", 10, "bold")).grid(
                row=i, column=0, sticky="w", padx=(0, 20), pady=3)
            ttkb.Label(info_grid, text=value, font=("Segoe UI", 10)).grid(
                row=i, column=1, sticky="w", pady=3)
    
    def create_right_panel(self, parent):
        """Create the enhanced right side panel with multiple tabs"""
        # Create notebook for tabbed interface
        self.right_notebook = ttkb.Notebook(parent)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Live Logs
        logs_tab = ttkb.Frame(self.right_notebook)
        self.right_notebook.add(logs_tab, text="📊 Live Logs")
        self._create_live_logs_tab(logs_tab)
        
        # Tab 2: Job Details
        job_tab = ttkb.Frame(self.right_notebook)
        self.right_notebook.add(job_tab, text="📋 Job Details")
        self._create_job_details_tab(job_tab)
        
        # Tab 3: Analytics
        analytics_tab = ttkb.Frame(self.right_notebook)
        self.right_notebook.add(analytics_tab, text="📈 Analytics")
        self._create_analytics_tab(analytics_tab)
        
        # Tab 4: Quick Settings
        settings_tab = ttkb.Frame(self.right_notebook)
        self.right_notebook.add(settings_tab, text="⚙️ Settings")
        self._create_settings_tab(settings_tab)
        
        # Tab 5: Resume Preview
        resume_tab = ttkb.Frame(self.right_notebook)
        self.right_notebook.add(resume_tab, text="📝 Resume")
        self._create_resume_tab(resume_tab)
        
        # Tab 6: Activity Feed (original)
        activity_tab = ttkb.Frame(self.right_notebook)
        self.right_notebook.add(activity_tab, text="🔔 Activity")
        self._create_activity_tab(activity_tab)
    
    def _create_live_logs_tab(self, parent):
        """Create live logs panel with real-time updates"""
        # Header with controls
        header = ttkb.Frame(parent)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        ttkb.Label(header, text="🔴 Live Bot Activity", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        # Controls
        ctrl_frame = ttkb.Frame(header)
        ctrl_frame.pack(side=tk.RIGHT)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttkb.Checkbutton(ctrl_frame, text="Auto-scroll", variable=self.auto_scroll_var,
                        bootstyle="success-round-toggle").pack(side=tk.LEFT, padx=5)
        
        ttkb.Button(ctrl_frame, text="Clear", command=self._clear_live_logs,
                   bootstyle="danger-outline", width=6).pack(side=tk.LEFT)
        
        # Live log text area
        self.live_log_text = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, font=("Consolas", 9),
            bg='#1a1a2e', fg='#00ff00', insertbackground='#00ff00',
            height=15
        )
        self.live_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure tags for colored output
        self.live_log_text.tag_configure("info", foreground="#3498db")
        self.live_log_text.tag_configure("success", foreground="#00d26a")
        self.live_log_text.tag_configure("warning", foreground="#ffb302")
        self.live_log_text.tag_configure("error", foreground="#ff4757")
        self.live_log_text.tag_configure("job", foreground="#e94560", font=("Consolas", 9, "bold"))
        
        # Progress section at bottom
        progress_frame = ttkb.Labelframe(parent, text="Current Progress", bootstyle="info")
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Overall progress bar
        self.overall_progress_var = tk.DoubleVar(value=0)
        ttkb.Label(progress_frame, text="Session Progress:", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=10, pady=(5,0))
        self.overall_progress_bar = ttkb.Progressbar(
            progress_frame, variable=self.overall_progress_var, 
            bootstyle="success-striped", length=280
        )
        self.overall_progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # Current task label
        self.current_task_label = ttkb.Label(progress_frame, text="Status: Idle", 
                                            font=("Segoe UI", 9), foreground=COLORS['text_secondary'])
        self.current_task_label.pack(anchor=tk.W, padx=10, pady=(0,10))
    
    def _create_job_details_tab(self, parent):
        """Create job details panel showing current job info"""
        # Current Job Header
        header_frame = ttkb.Labelframe(parent, text="🎯 Current Job", bootstyle="primary")
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Job title
        self.job_title_label = ttkb.Label(header_frame, text="No job processing", 
                                         font=("Segoe UI", 12, "bold"), wraplength=350)
        self.job_title_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Company
        self.job_company_label = ttkb.Label(header_frame, text="Company: --", 
                                           font=("Segoe UI", 10), foreground=COLORS['text_secondary'])
        self.job_company_label.pack(anchor=tk.W, padx=10)
        
        # Location & Type
        info_frame = ttkb.Frame(header_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.job_location_label = ttkb.Label(info_frame, text="📍 --", font=("Segoe UI", 9))
        self.job_location_label.pack(side=tk.LEFT, padx=(0, 15))
        
        self.job_posted_label = ttkb.Label(info_frame, text="🕐 --", font=("Segoe UI", 9))
        self.job_posted_label.pack(side=tk.LEFT)
        
        # Job Description Preview
        jd_frame = ttkb.Labelframe(parent, text="📄 Job Description Preview", bootstyle="secondary")
        jd_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.jd_preview_text = scrolledtext.ScrolledText(
            jd_frame, wrap=tk.WORD, font=("Segoe UI", 9),
            bg='#252540', fg='#ffffff', height=10
        )
        self.jd_preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.jd_preview_text.insert(tk.END, "Job description will appear here when processing...")
        self.jd_preview_text.config(state=tk.DISABLED)
        
        # Skip Reasons Section
        skip_frame = ttkb.Labelframe(parent, text="⏭️ Recent Skip Reasons", bootstyle="warning")
        skip_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.skip_reasons_list = tk.Listbox(
            skip_frame, font=("Segoe UI", 9), height=5,
            bg='#252540', fg='#ffb302', selectbackground='#3a3a5c'
        )
        self.skip_reasons_list.pack(fill=tk.X, padx=5, pady=5)
        
        # Add sample skip reasons
        self.skip_reasons_list.insert(tk.END, "No skip reasons yet...")
    
    def _create_analytics_tab(self, parent):
        """Create analytics panel with charts and stats"""
        # Success Rate Pie Chart
        chart_frame = ttkb.Labelframe(parent, text="📊 Application Results", bootstyle="info")
        chart_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create matplotlib figure
        self.analytics_fig = Figure(figsize=(3.5, 2.5), dpi=80, facecolor='#1a1a2e')
        self.analytics_ax = self.analytics_fig.add_subplot(111)
        self.analytics_ax.set_facecolor('#1a1a2e')
        
        # Initial empty pie chart
        self._update_analytics_chart()
        
        self.analytics_canvas = FigureCanvasTkAgg(self.analytics_fig, chart_frame)
        self.analytics_canvas.get_tk_widget().pack(fill=tk.X, padx=5, pady=5)
        
        # Stats Grid
        stats_frame = ttkb.Labelframe(parent, text="📈 Session Statistics", bootstyle="success")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        stats_grid = ttkb.Frame(stats_frame)
        stats_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Row 1
        ttkb.Label(stats_grid, text="Success Rate:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        self.success_rate_label = ttkb.Label(stats_grid, text="0%", font=("Segoe UI", 9), bootstyle="success")
        self.success_rate_label.grid(row=0, column=1, sticky="e", pady=2)
        
        ttkb.Label(stats_grid, text="Avg. Time/Job:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        self.avg_time_label = ttkb.Label(stats_grid, text="--", font=("Segoe UI", 9))
        self.avg_time_label.grid(row=1, column=1, sticky="e", pady=2)
        
        ttkb.Label(stats_grid, text="Jobs/Hour:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=2)
        self.jobs_hour_label = ttkb.Label(stats_grid, text="--", font=("Segoe UI", 9))
        self.jobs_hour_label.grid(row=2, column=1, sticky="e", pady=2)
        
        ttkb.Label(stats_grid, text="Resume Tailored:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=2)
        self.resume_tailored_label = ttkb.Label(stats_grid, text="0", font=("Segoe UI", 9))
        self.resume_tailored_label.grid(row=3, column=1, sticky="e", pady=2)
        
        stats_grid.columnconfigure(1, weight=1)
        
        # Recent Activity Timeline
        timeline_frame = ttkb.Labelframe(parent, text="🕐 Recent Activity", bootstyle="secondary")
        timeline_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.timeline_list = tk.Listbox(
            timeline_frame, font=("Consolas", 8), height=8,
            bg='#252540', fg='#a0a0a0', selectbackground='#3a3a5c'
        )
        self.timeline_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_settings_tab(self, parent):
        """Create quick settings panel with LLM configuration"""
        # Create scrollable frame for settings
        canvas = tk.Canvas(parent, bg=COLORS['bg_dark'], highlightthickness=0)
        scrollbar = ttkb.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttkb.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # ============================================
        # LLM CONFIGURATION SECTION
        # ============================================
        llm_frame = ttkb.Labelframe(scrollable_frame, text="🧠 LLM Configuration", bootstyle="primary")
        llm_frame.pack(fill=tk.X, padx=5, pady=5)
        
        llm_container = ttkb.Frame(llm_frame)
        llm_container.pack(fill=tk.X, padx=10, pady=10)
        
        # AI Provider Selection
        provider_frame = ttkb.Frame(llm_container)
        provider_frame.pack(fill=tk.X, pady=5)
        
        ttkb.Label(provider_frame, text="🔌 AI Provider:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        self.ai_provider_var = tk.StringVar(value=ai_provider or "ollama")
        
        # Row 1: Local providers
        provider_row1 = ttkb.Frame(llm_container)
        provider_row1.pack(fill=tk.X, pady=2)
        ttkb.Label(provider_row1, text="Local:", font=("Segoe UI", 8), width=6).pack(side=tk.LEFT)
        ttkb.Radiobutton(provider_row1, text="🦙 Ollama", value="ollama", 
                        variable=self.ai_provider_var, bootstyle="success-toolbutton",
                        command=self._on_provider_change).pack(side=tk.LEFT, padx=2)
        
        # Row 2: Free API providers
        provider_row2 = ttkb.Frame(llm_container)
        provider_row2.pack(fill=tk.X, pady=2)
        ttkb.Label(provider_row2, text="Free:", font=("Segoe UI", 8), width=6).pack(side=tk.LEFT)
        ttkb.Radiobutton(provider_row2, text="⚡ Groq", value="groq", 
                        variable=self.ai_provider_var, bootstyle="warning-toolbutton",
                        command=self._on_provider_change).pack(side=tk.LEFT, padx=2)
        ttkb.Radiobutton(provider_row2, text="🤗 HuggingFace", value="huggingface", 
                        variable=self.ai_provider_var, bootstyle="warning-toolbutton",
                        command=self._on_provider_change).pack(side=tk.LEFT, padx=2)
        
        # Row 3: Paid API providers
        provider_row3 = ttkb.Frame(llm_container)
        provider_row3.pack(fill=tk.X, pady=2)
        ttkb.Label(provider_row3, text="Paid:", font=("Segoe UI", 8), width=6).pack(side=tk.LEFT)
        ttkb.Radiobutton(provider_row3, text="🤖 OpenAI", value="openai", 
                        variable=self.ai_provider_var, bootstyle="info-toolbutton",
                        command=self._on_provider_change).pack(side=tk.LEFT, padx=2)
        ttkb.Radiobutton(provider_row3, text="🌊 DeepSeek", value="deepseek", 
                        variable=self.ai_provider_var, bootstyle="info-toolbutton",
                        command=self._on_provider_change).pack(side=tk.LEFT, padx=2)
        ttkb.Radiobutton(provider_row3, text="💎 Gemini", value="gemini", 
                        variable=self.ai_provider_var, bootstyle="info-toolbutton",
                        command=self._on_provider_change).pack(side=tk.LEFT, padx=2)
        
        # Provider status indicator
        self.provider_status_frame = ttkb.Frame(llm_container)
        self.provider_status_frame.pack(fill=tk.X, pady=5)
        
        self.provider_status_label = ttkb.Label(self.provider_status_frame, text="", font=("Segoe UI", 9))
        self.provider_status_label.pack(side=tk.LEFT)
        
        # ============================================
        # LOCAL LLM (OLLAMA) SECTION
        # ============================================
        self.ollama_frame = ttkb.Labelframe(scrollable_frame, text="🦙 Ollama (Local LLM)", bootstyle="success")
        self.ollama_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ollama_container = ttkb.Frame(self.ollama_frame)
        ollama_container.pack(fill=tk.X, padx=10, pady=10)
        
        # Ollama Status
        status_row = ttkb.Frame(ollama_container)
        status_row.pack(fill=tk.X, pady=3)
        
        ttkb.Label(status_row, text="Status:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.ollama_status_label = ttkb.Label(status_row, text="⏳ Checking...", font=("Segoe UI", 9))
        self.ollama_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        ttkb.Button(status_row, text="🔄 Refresh", command=self._refresh_ollama_models,
                   bootstyle="info-outline", width=10).pack(side=tk.RIGHT)
        
        # Ollama URL
        url_row = ttkb.Frame(ollama_container)
        url_row.pack(fill=tk.X, pady=5)
        
        ttkb.Label(url_row, text="API URL:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.ollama_url_var = tk.StringVar(value="http://localhost:11434")
        ttkb.Entry(url_row, textvariable=self.ollama_url_var, width=30).pack(side=tk.LEFT, padx=(10, 0))
        
        # Available Models Dropdown
        model_row = ttkb.Frame(ollama_container)
        model_row.pack(fill=tk.X, pady=5)
        
        ttkb.Label(model_row, text="Model:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        self.ollama_model_var = tk.StringVar(value="")
        self.ollama_model_combo = ttkb.Combobox(model_row, textvariable=self.ollama_model_var, 
                                                 state="readonly", bootstyle="success", width=25)
        self.ollama_model_combo.pack(side=tk.LEFT, padx=(10, 5))
        
        # Model info
        self.ollama_model_info = ttkb.Label(model_row, text="", font=("Segoe UI", 8), foreground=COLORS['text_secondary'])
        self.ollama_model_info.pack(side=tk.LEFT, padx=(5, 0))
        
        # Available Models List
        models_list_frame = ttkb.Frame(ollama_container)
        models_list_frame.pack(fill=tk.X, pady=5)
        
        ttkb.Label(models_list_frame, text="📦 Available Models:", font=("Segoe UI", 9)).pack(anchor=tk.W)
        
        self.ollama_models_listbox = tk.Listbox(models_list_frame, height=4, font=("Consolas", 9),
                                                 bg=COLORS['card_bg'], fg=COLORS['text_primary'],
                                                 selectbackground=COLORS['accent'])
        self.ollama_models_listbox.pack(fill=tk.X, pady=5)
        self.ollama_models_listbox.bind('<<ListboxSelect>>', self._on_ollama_model_select)
        
        # Ollama Actions
        ollama_actions = ttkb.Frame(ollama_container)
        ollama_actions.pack(fill=tk.X, pady=5)
        
        ttkb.Button(ollama_actions, text="🧪 Test Connection", command=self._test_ollama_connection,
                   bootstyle="info", width=15).pack(side=tk.LEFT, padx=2)
        ttkb.Button(ollama_actions, text="📥 Pull Model", command=self._pull_ollama_model,
                   bootstyle="warning", width=12).pack(side=tk.LEFT, padx=2)
        ttkb.Button(ollama_actions, text="🌐 Ollama Website", command=lambda: webbrowser.open("https://ollama.com/library"),
                   bootstyle="secondary-outline", width=14).pack(side=tk.LEFT, padx=2)
        
        # ============================================
        # CLOUD API SECTION
        # ============================================
        self.cloud_frame = ttkb.Labelframe(scrollable_frame, text="☁️ Cloud API Configuration", bootstyle="info")
        self.cloud_frame.pack(fill=tk.X, padx=5, pady=5)
        
        cloud_container = ttkb.Frame(self.cloud_frame)
        cloud_container.pack(fill=tk.X, padx=10, pady=10)
        
        # OpenAI
        openai_row = ttkb.Frame(cloud_container)
        openai_row.pack(fill=tk.X, pady=3)
        ttkb.Label(openai_row, text="OpenAI API Key:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.openai_key_var = tk.StringVar(value="")
        self.openai_key_entry = ttkb.Entry(openai_row, textvariable=self.openai_key_var, show="*", width=40)
        self.openai_key_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        openai_model_row = ttkb.Frame(cloud_container)
        openai_model_row.pack(fill=tk.X, pady=3)
        ttkb.Label(openai_model_row, text="OpenAI Model:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.openai_model_var = tk.StringVar(value="gpt-4o-mini")
        openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        ttkb.Combobox(openai_model_row, textvariable=self.openai_model_var, values=openai_models, 
                     width=20, bootstyle="info").pack(side=tk.LEFT, padx=(5, 0))
        
        # DeepSeek
        deepseek_row = ttkb.Frame(cloud_container)
        deepseek_row.pack(fill=tk.X, pady=3)
        ttkb.Label(deepseek_row, text="DeepSeek API Key:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.deepseek_key_var = tk.StringVar(value="")
        ttkb.Entry(deepseek_row, textvariable=self.deepseek_key_var, show="*", width=40).pack(side=tk.LEFT, padx=(5, 0))
        
        # Gemini
        gemini_row = ttkb.Frame(cloud_container)
        gemini_row.pack(fill=tk.X, pady=3)
        ttkb.Label(gemini_row, text="Gemini API Key:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.gemini_key_var = tk.StringVar(value="")
        ttkb.Entry(gemini_row, textvariable=self.gemini_key_var, show="*", width=40).pack(side=tk.LEFT, padx=(5, 0))
        
        # Separator for Free APIs
        ttkb.Separator(cloud_container, orient='horizontal').pack(fill=tk.X, pady=10)
        ttkb.Label(cloud_container, text="🆓 FREE API Providers", font=("Segoe UI", 10, "bold"), 
                  foreground=COLORS['success']).pack(anchor=tk.W, pady=(0, 5))
        
        # Groq (FREE)
        groq_row = ttkb.Frame(cloud_container)
        groq_row.pack(fill=tk.X, pady=3)
        ttkb.Label(groq_row, text="Groq API Key:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.groq_key_var = tk.StringVar(value="")
        ttkb.Entry(groq_row, textvariable=self.groq_key_var, show="*", width=40).pack(side=tk.LEFT, padx=(5, 0))
        ttkb.Button(groq_row, text="Get Free Key", command=lambda: webbrowser.open("https://console.groq.com/keys"),
                   bootstyle="success-link", width=12).pack(side=tk.LEFT, padx=5)
        
        groq_model_row = ttkb.Frame(cloud_container)
        groq_model_row.pack(fill=tk.X, pady=3)
        ttkb.Label(groq_model_row, text="Groq Model:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.groq_model_var = tk.StringVar(value="llama-3.1-70b-versatile")
        groq_models = ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "llama3-70b-8192", 
                      "llama3-8b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]
        ttkb.Combobox(groq_model_row, textvariable=self.groq_model_var, values=groq_models,
                     width=25, bootstyle="success").pack(side=tk.LEFT, padx=(5, 0))
        ttkb.Label(groq_model_row, text="⚡ Ultra-fast!", font=("Segoe UI", 8), 
                  foreground=COLORS['success']).pack(side=tk.LEFT, padx=5)
        
        # Hugging Face (FREE)
        hf_row = ttkb.Frame(cloud_container)
        hf_row.pack(fill=tk.X, pady=3)
        ttkb.Label(hf_row, text="HuggingFace Key:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.huggingface_key_var = tk.StringVar(value="")
        ttkb.Entry(hf_row, textvariable=self.huggingface_key_var, show="*", width=40).pack(side=tk.LEFT, padx=(5, 0))
        ttkb.Button(hf_row, text="Get Free Key", command=lambda: webbrowser.open("https://huggingface.co/settings/tokens"),
                   bootstyle="success-link", width=12).pack(side=tk.LEFT, padx=5)
        
        hf_model_row = ttkb.Frame(cloud_container)
        hf_model_row.pack(fill=tk.X, pady=3)
        ttkb.Label(hf_model_row, text="HF Model:", font=("Segoe UI", 9), width=15).pack(side=tk.LEFT)
        self.huggingface_model_var = tk.StringVar(value="mistralai/Mistral-7B-Instruct-v0.3")
        hf_models = ["mistralai/Mistral-7B-Instruct-v0.3", "meta-llama/Meta-Llama-3-8B-Instruct",
                    "microsoft/Phi-3-mini-4k-instruct", "google/gemma-2-9b-it", "Qwen/Qwen2.5-7B-Instruct"]
        ttkb.Combobox(hf_model_row, textvariable=self.huggingface_model_var, values=hf_models,
                     width=35, bootstyle="success").pack(side=tk.LEFT, padx=(5, 0))
        
        # Test Cloud Connection
        ttkb.Button(cloud_container, text="🧪 Test Cloud API", command=self._test_cloud_api,
                   bootstyle="info", width=15).pack(anchor=tk.W, pady=10)
        
        # ============================================
        # BOT SETTINGS SECTION
        # ============================================
        bot_frame = ttkb.Labelframe(scrollable_frame, text="🤖 Bot Settings", bootstyle="warning")
        bot_frame.pack(fill=tk.X, padx=5, pady=5)
        
        settings_container = ttkb.Frame(bot_frame)
        settings_container.pack(fill=tk.X, padx=10, pady=10)
        
        # Slow Mode Toggle
        self.slow_mode_var = tk.BooleanVar(value=False)
        slow_frame = ttkb.Frame(settings_container)
        slow_frame.pack(fill=tk.X, pady=3)
        ttkb.Label(slow_frame, text="🐢 Slow Mode (Anti-Detection)", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Checkbutton(slow_frame, variable=self.slow_mode_var, 
                        bootstyle="warning-round-toggle", command=self._toggle_slow_mode).pack(side=tk.RIGHT)
        
        # Resume Tailoring Toggle
        self.resume_tailor_var = tk.BooleanVar(value=True)
        tailor_frame = ttkb.Frame(settings_container)
        tailor_frame.pack(fill=tk.X, pady=3)
        ttkb.Label(tailor_frame, text="📝 Auto Resume Tailoring", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Checkbutton(tailor_frame, variable=self.resume_tailor_var,
                        bootstyle="success-round-toggle", command=self._toggle_resume_tailor).pack(side=tk.RIGHT)
        
        # Auto-dismiss Popups
        self.auto_dismiss_var = tk.BooleanVar(value=True)
        dismiss_frame = ttkb.Frame(settings_container)
        dismiss_frame.pack(fill=tk.X, pady=3)
        ttkb.Label(dismiss_frame, text="🚫 Auto-dismiss Popups", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Checkbutton(dismiss_frame, variable=self.auto_dismiss_var,
                        bootstyle="info-round-toggle").pack(side=tk.RIGHT)
        
        # Pause Before Submit
        self.pause_submit_var = tk.BooleanVar(value=False)
        pause_frame = ttkb.Frame(settings_container)
        pause_frame.pack(fill=tk.X, pady=3)
        ttkb.Label(pause_frame, text="⏸️ Pause Before Submit", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Checkbutton(pause_frame, variable=self.pause_submit_var,
                        bootstyle="danger-round-toggle").pack(side=tk.RIGHT)
        
        # ============================================
        # SAVE SETTINGS BUTTON
        # ============================================
        save_frame = ttkb.Frame(scrollable_frame)
        save_frame.pack(fill=tk.X, padx=5, pady=15)
        
        ttkb.Button(save_frame, text="💾 Save All Settings", command=self._save_llm_settings,
                   bootstyle="success", width=20).pack(side=tk.LEFT, padx=5)
        ttkb.Button(save_frame, text="🔄 Reset to Defaults", command=self._reset_llm_settings,
                   bootstyle="danger-outline", width=18).pack(side=tk.LEFT, padx=5)
        
        # Load settings and auto-detect models
        self._load_llm_settings()
        self._refresh_ollama_models()
        self._on_provider_change()
    
    def _get_ollama_models(self):
        """Get list of available Ollama models with their sizes"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                models = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            size = parts[2] if len(parts) > 2 else "?"
                            models.append((name, size))
                return models
            return []
        except Exception:
            return []
    
    def _refresh_ollama_models(self):
        """Refresh the list of available Ollama models"""
        def refresh_thread():
            models = self._get_ollama_models()
            
            # Update UI in main thread
            self.after(0, lambda: self._update_ollama_ui(models))
        
        self.ollama_status_label.config(text="⏳ Checking Ollama...")
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def _update_ollama_ui(self, models):
        """Update Ollama UI with detected models"""
        if models:
            self.ollama_status_label.config(text=f"✅ Running ({len(models)} models)", foreground=COLORS['success'])
            
            # Update combobox
            model_names = [m[0] for m in models]
            self.ollama_model_combo['values'] = model_names
            
            # Update listbox with sizes
            self.ollama_models_listbox.delete(0, tk.END)
            for name, size in models:
                self.ollama_models_listbox.insert(tk.END, f"  {name:<25} ({size})")
            
            # Select current model if available
            try:
                from config.secrets import ollama_model
                if ollama_model in model_names:
                    self.ollama_model_var.set(ollama_model)
                    self._update_model_info(ollama_model, models)
                elif model_names:
                    self.ollama_model_var.set(model_names[0])
            except ImportError:
                if model_names:
                    self.ollama_model_var.set(model_names[0])
        else:
            self.ollama_status_label.config(text="❌ Ollama not running", foreground=COLORS['danger'])
            self.ollama_models_listbox.delete(0, tk.END)
            self.ollama_models_listbox.insert(tk.END, "  No models found. Is Ollama running?")
            self.ollama_models_listbox.insert(tk.END, "  Run: ollama serve")
    
    def _update_model_info(self, model_name, models):
        """Update model info label"""
        for name, size in models:
            if name == model_name:
                self.ollama_model_info.config(text=f"Size: {size}")
                return
    
    def _on_ollama_model_select(self, event):
        """Handle model selection from listbox"""
        selection = self.ollama_models_listbox.curselection()
        if selection:
            item = self.ollama_models_listbox.get(selection[0])
            model_name = item.strip().split()[0]
            self.ollama_model_var.set(model_name)
            
            # Update info
            models = self._get_ollama_models()
            self._update_model_info(model_name, models)
    
    def _on_provider_change(self):
        """Handle provider selection change"""
        provider = self.ai_provider_var.get()
        
        if provider == "ollama":
            self.provider_status_label.config(text="🦙 Using local Ollama - No API key needed", foreground=COLORS['success'])
            # Highlight Ollama frame, dim cloud frame
            self.ollama_frame.configure(bootstyle="success")
            self.cloud_frame.configure(bootstyle="secondary")
        elif provider in ["groq", "huggingface"]:
            provider_names = {"groq": "Groq", "huggingface": "HuggingFace"}
            self.provider_status_label.config(text=f"🆓 Using {provider_names[provider]} - FREE API key required", 
                                              foreground=COLORS['success'])
            self.ollama_frame.configure(bootstyle="secondary")
            self.cloud_frame.configure(bootstyle="success")
        else:
            provider_names = {"openai": "OpenAI", "deepseek": "DeepSeek", "gemini": "Google Gemini"}
            self.provider_status_label.config(text=f"☁️ Using {provider_names.get(provider, provider)} - API key required", 
                                              foreground=COLORS['info'])
            self.ollama_frame.configure(bootstyle="secondary")
            self.cloud_frame.configure(bootstyle="info")
    
    def _test_ollama_connection(self):
        """Test connection to Ollama"""
        def test_thread():
            try:
                import urllib.request
                url = self.ollama_url_var.get() + "/api/tags"
                req = urllib.request.urlopen(url, timeout=5)
                data = json.loads(req.read().decode())
                models_count = len(data.get('models', []))
                self.after(0, lambda: messagebox.showinfo("Success", 
                    f"✅ Ollama is running!\n\n{models_count} models available."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Connection Failed", 
                    f"❌ Cannot connect to Ollama\n\nError: {str(e)}\n\nMake sure Ollama is running:\n  ollama serve"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _test_cloud_api(self):
        """Test cloud API connection"""
        provider = self.ai_provider_var.get()
        
        if provider == "openai":
            key = self.openai_key_var.get()
            if not key or key == "your_openai_api_key_here":
                messagebox.showwarning("Missing API Key", "Please enter your OpenAI API key.")
                return
            messagebox.showinfo("Test", "OpenAI API test - check console for results.")
        elif provider == "deepseek":
            key = self.deepseek_key_var.get()
            if not key or key == "your_deepseek_api_key_here":
                messagebox.showwarning("Missing API Key", "Please enter your DeepSeek API key.")
                return
            messagebox.showinfo("Test", "DeepSeek API test - check console for results.")
        elif provider == "gemini":
            key = self.gemini_key_var.get()
            if not key or key == "your_gemini_api_key_here":
                messagebox.showwarning("Missing API Key", "Please enter your Gemini API key.")
                return
            messagebox.showinfo("Test", "Gemini API test - check console for results.")
        elif provider == "groq":
            key = self.groq_key_var.get()
            if not key or key == "your_groq_api_key_here":
                messagebox.showwarning("Missing API Key", "Please enter your Groq API key.\n\nGet a FREE key at:\nhttps://console.groq.com/keys")
                return
            messagebox.showinfo("Test", "Groq API test - check console for results.\n\n⚡ Groq provides ultra-fast inference!")
        elif provider == "huggingface":
            key = self.huggingface_key_var.get()
            if not key or key == "your_huggingface_api_key_here":
                messagebox.showwarning("Missing API Key", "Please enter your HuggingFace API key.\n\nGet a FREE key at:\nhttps://huggingface.co/settings/tokens")
                return
            messagebox.showinfo("Test", "HuggingFace API test - check console for results.")
        else:
            messagebox.showinfo("Info", "Select a cloud provider first.")
    
    def _pull_ollama_model(self):
        """Open dialog to pull a new Ollama model"""
        dialog = tk.Toplevel(self)
        dialog.title("Pull Ollama Model")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttkb.Label(dialog, text="Enter model name to pull:", font=("Segoe UI", 11)).pack(pady=10)
        
        model_var = tk.StringVar(value="qwen2.5:7b")
        suggestions = ["qwen2.5:7b", "qwen2.5:14b", "llama3.1:8b", "mistral:7b", "gemma2:9b", "phi3:14b"]
        
        combo = ttkb.Combobox(dialog, textvariable=model_var, values=suggestions, width=30)
        combo.pack(pady=5)
        
        ttkb.Label(dialog, text="Recommended: qwen2.5:7b (4.7GB)", font=("Segoe UI", 9), 
                  foreground=COLORS['text_secondary']).pack()
        
        def do_pull():
            model = model_var.get()
            if model:
                dialog.destroy()
                messagebox.showinfo("Pulling Model", 
                    f"Pulling {model}...\n\nThis will run in a terminal.\nPlease wait for it to complete.")
                os.system(f'start cmd /k "ollama pull {model}"')
        
        btn_frame = ttkb.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttkb.Button(btn_frame, text="📥 Pull Model", command=do_pull, bootstyle="success", width=15).pack(side=tk.LEFT, padx=5)
        ttkb.Button(btn_frame, text="Cancel", command=dialog.destroy, bootstyle="danger-outline", width=10).pack(side=tk.LEFT, padx=5)
    
    def _load_llm_settings(self):
        """Load LLM settings from secrets.py"""
        try:
            from config import secrets
            
            # Load provider
            self.ai_provider_var.set(getattr(secrets, 'ai_provider', 'ollama'))
            
            # Load Ollama settings
            self.ollama_url_var.set(getattr(secrets, 'ollama_api_url', 'http://localhost:11434'))
            self.ollama_model_var.set(getattr(secrets, 'ollama_model', 'llama2:13b'))
            
            # Load API keys (masked)
            openai_key = getattr(secrets, 'llm_api_key', '')
            if openai_key and openai_key != 'your_openai_api_key_here':
                self.openai_key_var.set(openai_key)
            
            self.openai_model_var.set(getattr(secrets, 'llm_model', 'gpt-4o-mini'))
            
            deepseek_key = getattr(secrets, 'deepseek_api_key', '')
            if deepseek_key and deepseek_key != 'your_deepseek_api_key_here':
                self.deepseek_key_var.set(deepseek_key)
            
            gemini_key = getattr(secrets, 'gemini_api_key', '')
            if gemini_key and gemini_key != 'your_gemini_api_key_here':
                self.gemini_key_var.set(gemini_key)
            
            # Load Groq settings (FREE)
            groq_key = getattr(secrets, 'groq_api_key', '')
            if groq_key and groq_key != 'your_groq_api_key_here':
                self.groq_key_var.set(groq_key)
            self.groq_model_var.set(getattr(secrets, 'groq_model', 'llama-3.1-70b-versatile'))
            
            # Load HuggingFace settings (FREE)
            hf_key = getattr(secrets, 'huggingface_api_key', '')
            if hf_key and hf_key != 'your_huggingface_api_key_here':
                self.huggingface_key_var.set(hf_key)
            self.huggingface_model_var.set(getattr(secrets, 'huggingface_model', 'mistralai/Mistral-7B-Instruct-v0.3'))
                
        except Exception as e:
            print(f"Error loading LLM settings: {e}")
    
    def _save_llm_settings(self):
        """Save LLM settings to secrets.py"""
        try:
            secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'config', 'secrets.py')
            
            with open(secrets_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update provider
            import re
            content = re.sub(r'ai_provider\s*=\s*"[^"]*"', f'ai_provider = "{self.ai_provider_var.get()}"', content)
            
            # Update Ollama settings
            content = re.sub(r'ollama_api_url\s*=\s*"[^"]*"', f'ollama_api_url = "{self.ollama_url_var.get()}"', content)
            content = re.sub(r'ollama_model\s*=\s*"[^"]*"', f'ollama_model = "{self.ollama_model_var.get()}"', content)
            
            # Update OpenAI settings
            if self.openai_key_var.get():
                content = re.sub(r'llm_api_key\s*=\s*"[^"]*"', f'llm_api_key = "{self.openai_key_var.get()}"', content)
            content = re.sub(r'llm_model\s*=\s*"[^"]*"', f'llm_model = "{self.openai_model_var.get()}"', content)
            
            # Update DeepSeek
            if self.deepseek_key_var.get():
                content = re.sub(r'deepseek_api_key\s*=\s*"[^"]*"', f'deepseek_api_key = "{self.deepseek_key_var.get()}"', content)
            
            # Update Gemini
            if self.gemini_key_var.get():
                content = re.sub(r'gemini_api_key\s*=\s*"[^"]*"', f'gemini_api_key = "{self.gemini_key_var.get()}"', content)
            
            # Update Groq (FREE)
            if self.groq_key_var.get():
                content = re.sub(r'groq_api_key\s*=\s*"[^"]*"', f'groq_api_key = "{self.groq_key_var.get()}"', content)
            content = re.sub(r'groq_model\s*=\s*"[^"]*"', f'groq_model = "{self.groq_model_var.get()}"', content)
            
            # Update HuggingFace (FREE)
            if self.huggingface_key_var.get():
                content = re.sub(r'huggingface_api_key\s*=\s*"[^"]*"', f'huggingface_api_key = "{self.huggingface_key_var.get()}"', content)
            content = re.sub(r'huggingface_model\s*=\s*"[^"]*"', f'huggingface_model = "{self.huggingface_model_var.get()}"', content)
            
            with open(secrets_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("Success", "✅ LLM settings saved successfully!\n\nRestart the bot for changes to take effect.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")
    
    def _reset_llm_settings(self):
        """Reset LLM settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all LLM settings to defaults?"):
            self.ai_provider_var.set("ollama")
            self.ollama_url_var.set("http://localhost:11434")
            self.ollama_model_var.set("")
            self.openai_key_var.set("")
            self.openai_model_var.set("gpt-4o-mini")
            self.deepseek_key_var.set("")
            self.gemini_key_var.set("")
            self.groq_key_var.set("")
            self.groq_model_var.set("llama-3.1-70b-versatile")
            self.huggingface_key_var.set("")
            self.huggingface_model_var.set("mistralai/Mistral-7B-Instruct-v0.3")
            self._on_provider_change()
            self._refresh_ollama_models()
    
    def _create_resume_tab(self, parent):
        """Create resume preview panel"""
        # Current Resume Info
        info_frame = ttkb.Labelframe(parent, text="📄 Current Resume", bootstyle="success")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_container = ttkb.Frame(info_frame)
        info_container.pack(fill=tk.X, padx=10, pady=10)
        
        ttkb.Label(info_container, text="File:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.resume_file_label = ttkb.Label(info_container, text="Loading...", font=("Segoe UI", 9))
        self.resume_file_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        ttkb.Label(info_container, text="Type:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w")
        self.resume_type_label = ttkb.Label(info_container, text="--", font=("Segoe UI", 9))
        self.resume_type_label.grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        ttkb.Label(info_container, text="Last Tailored:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w")
        self.resume_tailored_time_label = ttkb.Label(info_container, text="--", font=("Segoe UI", 9))
        self.resume_tailored_time_label.grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        # Resume Preview
        preview_frame = ttkb.Labelframe(parent, text="📝 Resume Content Preview", bootstyle="info")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.resume_preview_text = scrolledtext.ScrolledText(
            preview_frame, wrap=tk.WORD, font=("Consolas", 8),
            bg='#252540', fg='#ffffff', height=12
        )
        self.resume_preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.resume_preview_text.insert(tk.END, "Resume content will be displayed here...")
        self.resume_preview_text.config(state=tk.DISABLED)
        
        # Action Buttons
        btn_frame = ttkb.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttkb.Button(btn_frame, text="📂 Open File", command=self._open_current_resume,
                   bootstyle="info-outline", width=12).pack(side=tk.LEFT, padx=2)
        ttkb.Button(btn_frame, text="🔄 Refresh", command=self._refresh_resume_preview,
                   bootstyle="secondary-outline", width=12).pack(side=tk.LEFT, padx=2)
        ttkb.Button(btn_frame, text="📝 Tailor Now", command=self.open_resume_tailor_dialog,
                   bootstyle="success", width=12).pack(side=tk.RIGHT, padx=2)
    
    def _create_activity_tab(self, parent):
        """Create activity feed panel (original functionality)"""
        # Activity Feed
        self.activity_feed = ActivityFeed(parent)
        self.activity_feed.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Progress Circle
        progress_frame = ttkb.Labelframe(parent, text="📈 Overall Progress", bootstyle="info")
        progress_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        circle_container = ttkb.Frame(progress_frame)
        circle_container.pack(pady=10)
        
        self.progress_circle = CircularProgress(circle_container, size=100, thickness=10)
        self.progress_circle.pack()
        
        # Quick Actions
        actions_frame = ttkb.Labelframe(parent, text="⚡ Quick Actions", bootstyle="warning")
        actions_frame.pack(fill=tk.X, padx=5)
        
        self.quick_actions = QuickActions(actions_frame, self)
        self.quick_actions.pack(fill=tk.X, padx=5, pady=5)
    
    # ========== Right Panel Helper Methods ==========
    
    def _clear_live_logs(self):
        """Clear the live logs panel"""
        self.live_log_text.delete(1.0, tk.END)
    
    def add_live_log(self, message: str, level: str = "info"):
        """Add a log entry to the live logs panel"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.live_log_text.insert(tk.END, f"[{timestamp}] ", "info")
        self.live_log_text.insert(tk.END, f"{message}\n", level)
        
        if self.auto_scroll_var.get():
            self.live_log_text.see(tk.END)
    
    def update_job_details(self, title: str, company: str, location: str, 
                          posted: str, description: str):
        """Update the job details panel"""
        self.job_title_label.config(text=title[:80] + "..." if len(title) > 80 else title)
        self.job_company_label.config(text=f"🏢 {company}")
        self.job_location_label.config(text=f"📍 {location}")
        self.job_posted_label.config(text=f"🕐 {posted}")
        
        self.jd_preview_text.config(state=tk.NORMAL)
        self.jd_preview_text.delete(1.0, tk.END)
        self.jd_preview_text.insert(tk.END, description[:2000] if len(description) > 2000 else description)
        self.jd_preview_text.config(state=tk.DISABLED)
        
        self.current_job_info = {
            'title': title, 'company': company, 
            'location': location, 'posted': posted
        }
    
    def add_skip_reason(self, reason: str, job_title: str = ""):
        """Add a skip reason to the list"""
        timestamp = datetime.now().strftime("%H:%M")
        display = f"[{timestamp}] {job_title[:20]}... - {reason}" if job_title else f"[{timestamp}] {reason}"
        
        # Remove "No skip reasons" placeholder if present
        if self.skip_reasons_list.get(0) == "No skip reasons yet...":
            self.skip_reasons_list.delete(0)
        
        self.skip_reasons_list.insert(0, display)
        
        # Keep only last 20 reasons
        while self.skip_reasons_list.size() > 20:
            self.skip_reasons_list.delete(tk.END)
        
        self.skip_reasons.append({'time': timestamp, 'job': job_title, 'reason': reason})
    
    def _update_analytics_chart(self):
        """Update the analytics pie chart"""
        self.analytics_ax.clear()
        
        applied = max(1, self.applied_count) if hasattr(self, 'applied_count') else 1
        failed = self.failed_count if hasattr(self, 'failed_count') else 0
        skipped = self.skipped_count if hasattr(self, 'skipped_count') else 0
        
        if applied + failed + skipped == 0:
            # Show placeholder
            self.analytics_ax.text(0.5, 0.5, 'No data yet', ha='center', va='center',
                                  color='#a0a0a0', fontsize=10, transform=self.analytics_ax.transAxes)
        else:
            sizes = [applied, failed, skipped]
            labels = ['Applied', 'Failed', 'Skipped']
            colors = ['#00d26a', '#ff4757', '#ffb302']
            explode = (0.05, 0, 0)
            
            self.analytics_ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                                 autopct='%1.1f%%', shadow=True, startangle=90,
                                 textprops={'color': 'white', 'fontsize': 8})
        
        self.analytics_fig.tight_layout()
        if hasattr(self, 'analytics_canvas'):
            self.analytics_canvas.draw()
    
    def _toggle_slow_mode(self):
        """Toggle slow mode setting"""
        from modules import helpers
        helpers.BOT_SLOW_MODE = self.slow_mode_var.get()
        status = "enabled" if self.slow_mode_var.get() else "disabled"
        self.add_live_log(f"Slow mode {status}", "info")
    
    def _toggle_resume_tailor(self):
        """Toggle resume tailoring setting"""
        status = "enabled" if self.resume_tailor_var.get() else "disabled"
        self.add_live_log(f"Auto resume tailoring {status}", "info")
    
    def _save_quick_settings(self):
        """Save quick settings"""
        self.add_live_log("Settings saved successfully", "success")
        messagebox.showinfo("Settings", "Quick settings have been saved!")
    
    def _open_current_resume(self):
        """Open the current resume file"""
        try:
            from config.settings import master_resume_folder
            # Find the first resume file in the master folder
            resume_path = None
            if os.path.exists(master_resume_folder):
                for f in os.listdir(master_resume_folder):
                    if f.lower().endswith(('.pdf', '.docx', '.doc', '.txt')):
                        resume_path = os.path.join(master_resume_folder, f)
                        break
            if resume_path and os.path.exists(resume_path):
                webbrowser.open(f'file:///{os.path.abspath(resume_path)}')
            else:
                webbrowser.open(f'file:///{os.path.abspath(master_resume_folder)}')
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _refresh_resume_preview(self):
        """Refresh the resume preview"""
        try:
            from config.settings import master_resume_folder
            # Find the first resume file
            resume_path = None
            if os.path.exists(master_resume_folder):
                for f in os.listdir(master_resume_folder):
                    if f.lower().endswith(('.pdf', '.docx', '.doc', '.txt')):
                        resume_path = os.path.join(master_resume_folder, f)
                        break
            
            if not resume_path:
                self.resume_file_label.config(text="No resume found")
                self.resume_type_label.config(text="N/A")
                return
                
            self.resume_file_label.config(text=os.path.basename(resume_path))
            ext = os.path.splitext(resume_path)[1].lower()
            self.resume_type_label.config(text=ext.upper())
            
            # Try to load preview text
            if ext == '.txt':
                with open(resume_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:3000]
                self.resume_preview_text.config(state=tk.NORMAL)
                self.resume_preview_text.delete(1.0, tk.END)
                self.resume_preview_text.insert(tk.END, content)
                self.resume_preview_text.config(state=tk.DISABLED)
            else:
                self.resume_preview_text.config(state=tk.NORMAL)
                self.resume_preview_text.delete(1.0, tk.END)
                self.resume_preview_text.insert(tk.END, f"Preview not available for {ext} files.\nClick 'Open File' to view.")
                self.resume_preview_text.config(state=tk.DISABLED)
        except Exception as e:
            self.resume_file_label.config(text="Error loading")
    
    def add_timeline_event(self, event: str):
        """Add an event to the analytics timeline"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.timeline_list.insert(0, f"[{timestamp}] {event}")
        
        # Keep only last 50 events
        while self.timeline_list.size() > 50:
            self.timeline_list.delete(tk.END)
    
    def update_progress(self, current: int, total: int, task: str = ""):
        """Update the progress bar and task label"""
        if total > 0:
            progress = (current / total) * 100
            self.overall_progress_var.set(progress)
        
        if task:
            self.current_task_label.config(text=f"Status: {task}")
    
    def update_analytics_stats(self):
        """Update analytics statistics"""
        total = self.applied_count + self.failed_count + self.skipped_count
        if total > 0:
            rate = (self.applied_count / total) * 100
            self.success_rate_label.config(text=f"{rate:.1f}%")
        
        # Update chart
        self._update_analytics_chart()
        
        # Calculate jobs per hour
        if self.start_time:
            elapsed_hours = (datetime.now() - self.start_time).total_seconds() / 3600
            if elapsed_hours > 0:
                jobs_per_hour = total / elapsed_hours
                self.jobs_hour_label.config(text=f"{jobs_per_hour:.1f}")

    
    def create_status_bar(self, parent):
        """Create the bottom status bar"""
        status_bar = ttkb.Frame(parent)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Left - Connection status
        left_frame = ttkb.Frame(status_bar)
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.connection_indicator = ttkb.Label(left_frame, text="●", 
                                              foreground=COLORS['success'])
        self.connection_indicator.pack(side=tk.LEFT)
        ttkb.Label(left_frame, text="System Ready", 
                  font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Center - Quick stats
        center_frame = ttkb.Frame(status_bar)
        center_frame.pack(side=tk.LEFT, expand=True)
        
        self.quick_stats_label = ttkb.Label(
            center_frame, 
            text="📊 Jobs: 0 | ✅ Applied: 0 | ❌ Failed: 0 | ⏭️ Skipped: 0",
            font=("Segoe UI", 9)
        )
        self.quick_stats_label.pack()
        
        # Right - Time
        right_frame = ttkb.Frame(status_bar)
        right_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.time_label = ttkb.Label(right_frame, text="", font=("Consolas", 9))
        self.time_label.pack()
        self._update_time()
    
    def _update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"🕐 {current_time}")
        
        # Update runtime if bot is running
        if self.start_time and self.current_status == "Running":
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.runtime_label.config(text=f"Runtime: {hours:02d}:{minutes:02d}:{seconds:02d}")
        
        self.after(1000, self._update_time)
    
    def create_menu(self):
        """Create the application menu"""
        menubar = Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="📁 File", menu=file_menu)
        file_menu.add_command(label="📥 Export Logs", command=self.export_logs)
        file_menu.add_command(label="📊 Export Statistics", command=self.export_stats)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self.on_close)
        
        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="👁️ View", menu=view_menu)
        view_menu.add_command(label="🔄 Refresh All", command=self.manual_refresh)
        view_menu.add_command(label="🗑️ Clear Logs", command=self.clear_logs)
        
        # Tools menu
        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="🛠️ Tools", menu=tools_menu)
        tools_menu.add_command(label="📝 Resume Tailor", command=self.open_resume_tailor_dialog)
        tools_menu.add_command(label="⚙️ Configuration", command=self.open_config)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="❓ Help", menu=help_menu)
        help_menu.add_command(label="📖 Documentation", command=self.show_docs)
        help_menu.add_command(label="🐛 Report Bug", command=self.report_bug)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
    
    # ========== Panel Toggle Methods ==========
    
    def toggle_right_panel(self):
        """Toggle the right panel visibility"""
        if self.panel_visible:
            # Hide the right panel
            self.paned_window.forget(self.right_panel_frame)
            self.toggle_panel_btn.config(text="▶ Panel")
            self.panel_visible = False
            self.activity_feed.add_activity("Right panel hidden", "info")
        else:
            # Show the right panel
            self.paned_window.add(self.right_panel_frame, minsize=300, width=450)
            self.toggle_panel_btn.config(text="◀ Panel")
            self.panel_visible = True
            self.activity_feed.add_activity("Right panel shown", "info")
    
    def toggle_side_panel_mode(self):
        """Toggle side panel mode - opens a clean compact window"""
        if not self.side_panel_mode:
            # Enter side panel mode - create separate window
            self.side_panel_mode = True
            self.side_panel_btn.config(text="❌ Close Side", bootstyle="danger")
            
            # Create side panel window
            self._create_side_panel_window()
            
        else:
            # Exit side panel mode
            self._close_side_panel()
    
    def _create_side_panel_window(self):
        """Create a clean, compact side panel window"""
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Panel dimensions
        panel_width = 340
        panel_height = screen_height - 80
        x_pos = screen_width - panel_width - 10
        y_pos = 0
        
        # Create toplevel window
        self.side_panel_window = tk.Toplevel(self)
        self.side_panel_window.title("📊 Live Monitor")
        self.side_panel_window.geometry(f"{panel_width}x{panel_height}+{x_pos}+{y_pos}")
        self.side_panel_window.attributes('-topmost', True)
        self.side_panel_window.configure(bg='#1a1a2e')
        self.side_panel_window.resizable(True, True)
        self.side_panel_window.minsize(280, 400)
        
        # Handle close
        self.side_panel_window.protocol("WM_DELETE_WINDOW", self._close_side_panel)
        
        # Main container with padding
        main_frame = ttkb.Frame(self.side_panel_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # ===== HEADER =====
        header = ttkb.Frame(main_frame)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttkb.Label(header, text="🤖 AI Job Hunter", 
                  font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        
        # Status indicator in header
        self.sp_status_frame = ttkb.Frame(header)
        self.sp_status_frame.pack(side=tk.RIGHT)
        
        self.sp_status_dot = ttkb.Label(self.sp_status_frame, text="●", 
                                        foreground="#ff6b6b", font=("Arial", 14))
        self.sp_status_dot.pack(side=tk.LEFT)
        self.sp_status_text = ttkb.Label(self.sp_status_frame, text="STOPPED",
                                         font=("Segoe UI", 10, "bold"))
        self.sp_status_text.pack(side=tk.LEFT, padx=(5, 0))
        
        # ===== QUICK STATS ROW =====
        stats_frame = ttkb.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create 4 mini stat boxes
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)
        
        # Jobs stat
        self._create_mini_stat(stats_frame, 0, "🔍", "Jobs", "sp_jobs_val")
        # Applied stat
        self._create_mini_stat(stats_frame, 1, "✅", "Applied", "sp_applied_val")
        # Failed stat  
        self._create_mini_stat(stats_frame, 2, "❌", "Failed", "sp_failed_val")
        # Skipped stat
        self._create_mini_stat(stats_frame, 3, "⏭️", "Skip", "sp_skipped_val")
        
        # ===== CURRENT JOB SECTION =====
        job_frame = ttkb.Labelframe(main_frame, text="💼 Current Job", bootstyle="info")
        job_frame.pack(fill=tk.X, pady=(0, 10))
        
        job_inner = ttkb.Frame(job_frame)
        job_inner.pack(fill=tk.X, padx=10, pady=8)
        
        self.sp_job_title = ttkb.Label(job_inner, text="Waiting...", 
                                       font=("Segoe UI", 10, "bold"),
                                       wraplength=280)
        self.sp_job_title.pack(anchor=tk.W)
        
        self.sp_job_company = ttkb.Label(job_inner, text="",
                                         font=("Segoe UI", 9),
                                         foreground="#aaaaaa")
        self.sp_job_company.pack(anchor=tk.W)
        
        self.sp_job_status = ttkb.Label(job_inner, text="⏳ Idle",
                                        font=("Segoe UI", 9),
                                        foreground="#ffd93d")
        self.sp_job_status.pack(anchor=tk.W, pady=(5, 0))
        
        # ===== AI PROGRESS SECTION =====
        ai_frame = ttkb.Labelframe(main_frame, text="🤖 AI Processing", bootstyle="primary")
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        
        ai_inner = ttkb.Frame(ai_frame)
        ai_inner.pack(fill=tk.X, padx=8, pady=8)
        
        # JD Analysis Progress
        jd_header = ttkb.Frame(ai_inner)
        jd_header.pack(fill=tk.X)
        ttkb.Label(jd_header, text="📋 JD Analysis:", 
                  font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.sp_jd_status = ttkb.Label(jd_header, text="Idle",
                                       font=("Segoe UI", 8), foreground="#888888")
        self.sp_jd_status.pack(side=tk.RIGHT)
        
        self.sp_jd_progress = ttkb.Progressbar(ai_inner, mode='determinate',
                                               bootstyle="info-striped", length=280)
        self.sp_jd_progress.pack(fill=tk.X, pady=(3, 8))
        
        # Resume Tailoring Progress  
        resume_header = ttkb.Frame(ai_inner)
        resume_header.pack(fill=tk.X)
        ttkb.Label(resume_header, text="📝 Resume Tailoring:", 
                  font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.sp_resume_status = ttkb.Label(resume_header, text="Idle",
                                           font=("Segoe UI", 8), foreground="#888888")
        self.sp_resume_status.pack(side=tk.RIGHT)
        
        self.sp_resume_progress = ttkb.Progressbar(ai_inner, mode='determinate',
                                                   bootstyle="warning-striped", length=280)
        self.sp_resume_progress.pack(fill=tk.X, pady=(3, 0))
        
        # ===== OVERALL PROGRESS BAR =====
        progress_frame = ttkb.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttkb.Label(progress_frame, text="📊 Overall Progress:", 
                  font=("Segoe UI", 9)).pack(anchor=tk.W)
        self.sp_progress = ttkb.Progressbar(progress_frame, mode='determinate',
                                            bootstyle="success-striped", length=300)
        self.sp_progress.pack(fill=tk.X, pady=(3, 0))
        self.sp_progress_label = ttkb.Label(progress_frame, text="0%",
                                            font=("Segoe UI", 9))
        self.sp_progress_label.pack(anchor=tk.E)
        
        # ===== LIVE LOG =====
        log_frame = ttkb.Labelframe(main_frame, text="📋 Live Log", bootstyle="secondary")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.sp_log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 8),
            bg='#0f0f23', fg='#00ff88', height=12,
            insertbackground='white'
        )
        self.sp_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure log tags for colors
        self.sp_log_text.tag_configure("error", foreground="#ff6b6b")
        self.sp_log_text.tag_configure("success", foreground="#4ade80")
        self.sp_log_text.tag_configure("warning", foreground="#fbbf24")
        self.sp_log_text.tag_configure("info", foreground="#60a5fa")
        self.sp_log_text.tag_configure("timestamp", foreground="#6b7280")
        
        # ===== CONTROL BUTTONS =====
        btn_frame = ttkb.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        self.sp_start_btn = ttkb.Button(btn_frame, text="▶ Start", 
                                        command=self.start_bot,
                                        bootstyle="success", width=10)
        self.sp_start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.sp_stop_btn = ttkb.Button(btn_frame, text="⏹ Stop",
                                       command=self.stop_bot,
                                       bootstyle="danger", width=10, state=tk.DISABLED)
        self.sp_stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttkb.Button(btn_frame, text="📂 Logs",
                   command=lambda: webbrowser.open(f'file:///{os.path.abspath("logs")}'),
                   bootstyle="info-outline", width=8).pack(side=tk.RIGHT)
        
        # Start update loop for side panel
        self._update_side_panel()
        
        self.activity_feed.add_activity("Side Panel opened", "success")
    
    def _create_mini_stat(self, parent, col, icon, label, attr_name):
        """Create a mini stat box for the side panel"""
        frame = ttkb.Frame(parent)
        frame.grid(row=0, column=col, padx=2, pady=2, sticky="nsew")
        
        inner = ttkb.Frame(frame)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        ttkb.Label(inner, text=icon, font=("Segoe UI Emoji", 12)).pack()
        val_label = ttkb.Label(inner, text="0", font=("Segoe UI", 12, "bold"))
        val_label.pack()
        ttkb.Label(inner, text=label, font=("Segoe UI", 7),
                  foreground="#888888").pack()
        
        # Store reference
        setattr(self, attr_name, val_label)
    
    def _update_side_panel(self):
        """Update side panel with current data"""
        if not self.side_panel_mode or not hasattr(self, 'side_panel_window'):
            return
        
        try:
            # Update stats
            self.sp_jobs_val.config(text=str(self.job_count))
            self.sp_applied_val.config(text=str(self.applied_count))
            self.sp_failed_val.config(text=str(self.failed_count))
            self.sp_skipped_val.config(text=str(self.skipped_count))
            
            # Update status
            if self.current_status == "Running":
                self.sp_status_dot.config(foreground="#4ade80")
                self.sp_status_text.config(text="RUNNING")
                self.sp_start_btn.config(state=tk.DISABLED)
                self.sp_stop_btn.config(state=tk.NORMAL)
            elif self.current_status == "Paused":
                self.sp_status_dot.config(foreground="#fbbf24")
                self.sp_status_text.config(text="PAUSED")
            else:
                self.sp_status_dot.config(foreground="#ff6b6b")
                self.sp_status_text.config(text="STOPPED")
                self.sp_start_btn.config(state=tk.NORMAL)
                self.sp_stop_btn.config(state=tk.DISABLED)
            
            # Update progress
            total = self.applied_count + self.failed_count + self.skipped_count
            if self.job_count > 0:
                pct = int((total / self.job_count) * 100)
                self.sp_progress.config(value=pct)
                self.sp_progress_label.config(text=f"{pct}%")
            
            # Update current job
            if hasattr(self, 'current_job_info') and self.current_job_info:
                self.sp_job_title.config(text=self.current_job_info.get('title', 'Processing...'))
                self.sp_job_company.config(text=self.current_job_info.get('company', ''))
                status = self.current_job_info.get('status', 'Processing')
                if 'success' in status.lower() or 'applied' in status.lower():
                    self.sp_job_status.config(text=f"✅ {status}", foreground="#4ade80")
                elif 'fail' in status.lower() or 'error' in status.lower():
                    self.sp_job_status.config(text=f"❌ {status}", foreground="#ff6b6b")
                else:
                    self.sp_job_status.config(text=f"⏳ {status}", foreground="#fbbf24")
            
            # Update AI Progress bars from metrics
            try:
                from modules.dashboard import metrics as _m
                
                # JD Analysis Progress
                jd_pct = int(_m.get_metric('jd_progress', 0))
                self.sp_jd_progress.config(value=jd_pct)
                if jd_pct == 0:
                    self.sp_jd_status.config(text="Idle", foreground="#888888")
                elif jd_pct < 100:
                    self.sp_jd_status.config(text=f"Analyzing... {jd_pct}%", foreground="#60a5fa")
                else:
                    self.sp_jd_status.config(text="✓ Done", foreground="#4ade80")
                
                # Resume Tailoring Progress
                resume_pct = int(_m.get_metric('resume_progress', 0))
                self.sp_resume_progress.config(value=resume_pct)
                if resume_pct == 0:
                    self.sp_resume_status.config(text="Idle", foreground="#888888")
                elif resume_pct < 100:
                    self.sp_resume_status.config(text=f"Tailoring... {resume_pct}%", foreground="#fbbf24")
                else:
                    self.sp_resume_status.config(text="✓ Done", foreground="#4ade80")
            except Exception:
                pass
            
            # Schedule next update
            self.side_panel_window.after(500, self._update_side_panel)
            
        except tk.TclError:
            # Window was closed
            self.side_panel_mode = False
    
    def _add_side_panel_log(self, msg: str, level: str = "info"):
        """Add a log entry to the side panel"""
        if not self.side_panel_mode or not hasattr(self, 'sp_log_text'):
            return
        
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.sp_log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.sp_log_text.insert(tk.END, f"{msg}\n", level)
            self.sp_log_text.see(tk.END)
            
            # Limit lines
            lines = int(self.sp_log_text.index('end-1c').split('.')[0])
            if lines > 200:
                self.sp_log_text.delete('1.0', '50.0')
        except tk.TclError:
            pass
    
    def _close_side_panel(self):
        """Close the side panel window"""
        self.side_panel_mode = False
        self.side_panel_btn.config(text="📌 Side Mode", bootstyle="primary")
        
        if hasattr(self, 'side_panel_window'):
            try:
                self.side_panel_window.destroy()
            except Exception:
                pass
        
        self.activity_feed.add_activity("Side Panel closed", "info")
    
    # ========== Bot Control Methods ==========
    
    def start_bot(self):
        try:
            self._log_with_timestamp("🚀 Starting bot...", "info")
            self._log_with_timestamp("📂 Loading configuration...", "info")
            self.activity_feed.add_activity("Starting bot...", "info")
            
            ok = self.controller.start()
            if not ok:
                self._log_with_timestamp("⚠️ Bot is already running!", "warning")
                self.activity_feed.add_activity("Bot already running", "warning")
                messagebox.showinfo("Already Running", "The bot is already running.")
                return
            
            self._log_with_timestamp("🌐 Opening Chrome browser...", "chrome")
            self.activity_feed.add_activity("Opening Chrome browser", "chrome")
            
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.NORMAL)
            self.status_label.config(text="RUNNING")
            self.status_indicator.config(foreground=COLORS['success'])
            self.current_status = "Running"
            self.start_time = datetime.now()
            
            self._log_with_timestamp("✅ Bot started successfully!", "success")
            self.activity_feed.add_activity("Bot started successfully!", "success")
            
        except Exception as e:
            self._log_with_timestamp(f"❌ Failed to start bot: {str(e)}", "error")
            self.activity_feed.add_activity(f"Start failed: {str(e)}", "error")
            messagebox.showerror("Start Failed", str(e))
    
    def stop_bot(self):
        try:
            self._log_with_timestamp("🛑 Stopping bot - please wait...", "warning")
            self.activity_feed.add_activity("Stopping bot...", "warning")
            
            # Disable buttons during stop
            self.stop_btn.config(state=tk.DISABLED)
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.DISABLED)
            self.status_label.config(text="STOPPING...")
            self.status_indicator.config(foreground=COLORS['warning'])
            
            # Force update UI
            self.update_idletasks()
            
            self._log_with_timestamp("🔧 Terminating bot processes...", "chrome")
            self.activity_feed.add_activity("Terminating processes", "chrome")
            
            # Call stop (this now kills all processes)
            self.controller.stop()
            
            self._log_with_timestamp("🌐 Chrome and chromedriver terminated", "chrome")
            self.activity_feed.add_activity("Chrome browser closed", "chrome")
            
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.DISABLED)
            self.status_label.config(text="STOPPED")
            self.status_indicator.config(foreground=COLORS['danger'])
            self.current_status = "Stopped"
            
            self._log_with_timestamp("✅ Bot stopped completely - all processes killed!", "success")
            self.activity_feed.add_activity("Bot stopped completely", "success")
            
        except Exception as e:
            self._log_with_timestamp(f"❌ Error stopping bot: {str(e)}", "error")
            self.activity_feed.add_activity(f"Stop error: {str(e)}", "error")
            # Re-enable start button even on error
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            messagebox.showerror("Stop Failed", str(e))
    
    def toggle_pause(self):
        messagebox.showinfo("Pause", "Pause functionality coming soon!")
    
    def _log_with_timestamp(self, message, msg_type="info"):
        """Add a log message with timestamp and color coding"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", msg_type)
        self.log_text.see(tk.END)
    
    # ========== Menu Actions ==========
    
    def open_resume_tailor_dialog(self):
        ResumeTailorDialog(self, ai_provider, user_information_all)
    
    def export_logs(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("Log files", "*.log")],
                title="Export Logs"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                messagebox.showinfo("Success", f"Logs exported to {file_path}")
                self.activity_feed.add_activity("Logs exported", "success")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def export_stats(self):
        messagebox.showinfo("Export", "Statistics export coming soon!")
    
    def export_jobs_csv(self):
        messagebox.showinfo("Export", "CSV export coming soon!")
    
    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)
        self.ai_output.delete("1.0", tk.END)
        self.activity_feed.add_activity("Logs cleared", "info")
    
    def manual_refresh(self):
        self._refresh_metrics()
        self.activity_feed.add_activity("Dashboard refreshed", "info")
    
    def refresh_jobs_table(self):
        self.activity_feed.add_activity("Jobs table refreshed", "info")
    
    def open_config(self):
        try:
            config_path = os.path.abspath("config")
            webbrowser.open(f'file:///{config_path}')
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def show_docs(self):
        webbrowser.open("https://github.com/surajpanwar26/Auto_job_applier_linkedIn")
    
    def report_bug(self):
        webbrowser.open("https://github.com/surajpanwar26/Auto_job_applier_linkedIn/issues")
    
    def show_about(self):
        about_text = """
🤖 AI Job Hunter Pro v1.0

Automated LinkedIn Job Application System
Powered by AI and Machine Learning

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Author: Suraj Singh Panwar
LinkedIn: linkedin.com/in/suraj-panwar-11b444308
GitHub: github.com/surajpanwar26

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

© 2024-2026 All Rights Reserved
        """
        messagebox.showinfo("About AI Job Hunter Pro", about_text)
    
    # ========== Background Updates ==========
    
    def _on_new_log(self, msg: str):
        if isinstance(msg, str):
            self._log_buffer.append(msg)
        
        # Detect message level for live log panel
        msg_lower = msg.lower() if isinstance(msg, str) else ""
        level = "info"
        if "error" in msg_lower or "failed" in msg_lower:
            level = "error"
        elif "success" in msg_lower or "applied" in msg_lower:
            level = "success"
        elif "warning" in msg_lower or "skip" in msg_lower:
            level = "warning"
        
        # Feed to live logs panel (right panel)
        try:
            self.add_live_log(msg, level)
        except Exception:
            pass
        
        # Feed to side panel if open
        try:
            self._add_side_panel_log(msg, level)
        except Exception:
            pass
        
        # Detect events for analytics and activity
        if "applied" in msg_lower and "easy" in msg_lower:
            self.applied_count += 1
            self.activity_feed.add_activity("Applied to job!", "success")
            try:
                self.add_timeline_event(f"✅ Applied to job")
            except Exception:
                pass
        elif "failed" in msg_lower or "error" in msg_lower:
            self.failed_count += 1
            self.activity_feed.add_activity("Job application failed", "error")
            try:
                self.add_timeline_event(f"❌ Application failed")
            except Exception:
                pass
        elif "skipped" in msg_lower or "skip" in msg_lower:
            self.skipped_count += 1
            # Extract skip reason
            try:
                reason = msg.split(":")[-1].strip() if ":" in msg else "Unknown reason"
                self.add_skip_reason(reason)
            except Exception:
                pass
        
        # Detect job details from log messages and update side panel
        if "processing job:" in msg_lower or "applying to:" in msg_lower:
            try:
                # Extract job info from message
                parts = msg.split(":")
                if len(parts) >= 2:
                    job_info = parts[1].strip()
                    self.current_job_info = {'title': job_info, 'company': '', 'status': 'Processing'}
                    self.update_job_details(
                        title=job_info,
                        company="Extracting...",
                        location="",
                        posted="",
                        description=""
                    )
            except Exception:
                pass
        
        # Update job status in side panel
        if "applied" in msg_lower:
            self.current_job_info['status'] = 'Applied Successfully'
        elif "failed" in msg_lower:
            self.current_job_info['status'] = 'Failed'
        elif "skipped" in msg_lower:
            self.current_job_info['status'] = 'Skipped'
        
        self.update_stats_display()
    
    def update_stats_display(self):
        # Update stat cards
        self.jobs_card.set_value(self.job_count)
        self.applied_card.set_value(self.applied_count)
        self.failed_card.set_value(self.failed_count)
        self.skipped_card.set_value(self.skipped_count)
        
        # Calculate success rate
        total = self.applied_count + self.failed_count
        if total > 0:
            rate = round((self.applied_count / total) * 100, 1)
            self.rate_card.set_value(f"{rate}%")
            self.progress_circle.set_progress(rate)
        else:
            self.rate_card.set_value("0%")
            self.progress_circle.set_progress(0)
        
        # Update status bar
        self.quick_stats_label.config(
            text=f"📊 Jobs: {self.job_count} | ✅ Applied: {self.applied_count} | "
                 f"❌ Failed: {self.failed_count} | ⏭️ Skipped: {self.skipped_count}"
        )
    
    def _refresh_metrics(self):
        data = metrics.get_metrics()
        
        # Flush log buffer
        if self._log_buffer:
            chunk = self._log_buffer[:100]
            del self._log_buffer[:100]
            for msg in chunk:
                # Determine message type
                msg_type = "info"
                if "error" in msg.lower() or "failed" in msg.lower():
                    msg_type = "error"
                elif "success" in msg.lower() or "applied" in msg.lower():
                    msg_type = "success"
                elif "warning" in msg.lower() or "skip" in msg.lower():
                    msg_type = "warning"
                
                self._log_with_timestamp(msg, msg_type)
                
                if msg.startswith('[AI]'):
                    self.ai_output.insert(tk.END, msg.replace('[AI]', '').strip() + "\n")
                    self.ai_output.see(tk.END)
        
        # Update progress bars
        jd = int(data.get("jd_progress", 0))
        rs = int(data.get("resume_progress", 0))
        self.jd_progress.configure(value=jd)
        self.jd_progress_label.config(text=f"{jd}%")
        self.resume_progress.configure(value=rs)
        self.resume_progress_label.config(text=f"{rs}%")
        
        # Update job count
        self.job_count = data.get("jobs_processed", 0)
        
        # Update metrics labels
        try:
            self.metric_labels["ai_provider"].config(text=str(ai_provider).upper())
            self.metric_labels["jobs_processed"].config(text=str(data.get("jobs_processed", 0)))
            self.metric_labels["easy_applied"].config(text=str(data.get("easy_applied", 0)))
            self.metric_labels["external_jobs"].config(text=str(data.get("external_jobs", 0)))
            self.metric_labels["jd_analysis_count"].config(text=str(data.get("jd_analysis_count", 0)))
            self.metric_labels["resume_tailoring_count"].config(text=str(data.get("resume_tailoring_count", 0)))
            self.metric_labels["jd_analysis_avg"].config(text=f"{data.get('jd_analysis_avg', 0):.2f}")
            self.metric_labels["resume_tailoring_avg"].config(text=f"{data.get('resume_tailoring_avg', 0):.2f}")
            self.metric_labels["jd_analysis_last"].config(text=f"{data.get('jd_analysis_last', 0):.2f}")
            self.metric_labels["resume_last"].config(text=f"{data.get('resume_last', 0):.2f}")
            
            eta_seconds = data.get("eta_seconds", 0) or 0
            eta_minutes = eta_seconds / 60 if eta_seconds else 0
            self.metric_labels["eta_minutes"].config(text=f"{eta_minutes:.1f}")
            self.metric_labels["ollama_calls"].config(text=str(data.get("ollama_calls", 0)))
        except Exception:
            pass
        
        # Update charts
        self._update_charts(data)
        
        # Update stats
        self.update_stats_display()
        
        # Update analytics panel in right panel
        try:
            self.update_analytics_stats()
            # Update overall progress
            total_jobs = data.get("jobs_processed", 0)
            if total_jobs > 0:
                self.update_progress(self.applied_count, total_jobs, "Processing jobs...")
        except Exception:
            pass
        
        self.after(1000, self._refresh_metrics)
    
    def _update_charts(self, data):
        try:
            # Time series chart
            ts = metrics.get_time_series('jd_analysis')
            if ts and len(ts) > 0:
                self.ax_ts.clear()
                self.ax_ts.plot(list(range(len(ts))), ts, marker='o', color='#4CAF50',
                               linewidth=2, markersize=4)
                self.ax_ts.fill_between(list(range(len(ts))), ts, alpha=0.3, color='#4CAF50')
                self.ax_ts.set_title('JD Analysis Times', color='white', fontsize=10)
                self.ax_ts.set_xlabel('Analysis #', color='#a0a0a0', fontsize=8)
                self.ax_ts.set_ylabel('Time (s)', color='#a0a0a0', fontsize=8)
                self.ax_ts.grid(True, alpha=0.2)
        except Exception:
            pass
        
        try:
            # Pie chart
            total = self.applied_count + self.failed_count + self.skipped_count
            if total > 0:
                sizes = [self.applied_count, self.failed_count, self.skipped_count]
                labels = ['Applied', 'Failed', 'Skipped']
                colors = ['#4CAF50', '#F44336', '#FF9800']
                explode = (0.05, 0, 0)
                
                self.ax_pie.clear()
                self.ax_pie.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                               startangle=90, explode=explode,
                               textprops={'color': 'white', 'fontsize': 8})
                self.ax_pie.set_title('Application Results', color='white', fontsize=10)
        except Exception:
            pass
        
        try:
            # Bar chart
            metric_names = ['easy_applied', 'external_jobs', 'jd_analysis_count']
            metric_values = [data.get(name, 0) for name in metric_names]
            labels = ['Easy Applied', 'External', 'JD Analysis']
            colors = ['#4CAF50', '#9C27B0', '#00BCD4']
            
            self.ax_bar.clear()
            bars = self.ax_bar.bar(labels, metric_values, color=colors, edgecolor='white',
                                  linewidth=0.5)
            self.ax_bar.set_title('Metrics Overview', color='white', fontsize=10)
            self.ax_bar.grid(True, alpha=0.2, axis='y')
            
            for bar, val in zip(bars, metric_values):
                height = bar.get_height()
                self.ax_bar.text(bar.get_x() + bar.get_width()/2., height,
                                f'{int(val)}', ha='center', va='bottom',
                                color='white', fontsize=9, fontweight='bold')
        except Exception:
            pass
        
        try:
            self.canvas.draw_idle()
        except Exception:
            pass
    
    def on_close(self):
        try:
            if self.current_status == "Running":
                if messagebox.askyesno("Confirm Exit", 
                    "Bot is still running. Do you want to stop it and exit?"):
                    self.controller.stop()
                else:
                    return
        except Exception:
            pass
        
        try:
            log_handler.unsubscribe(self._on_new_log)
        except Exception:
            pass
        
        self.destroy()


# Controller wrapper
class BotController:
    def __init__(self, runner):
        self.runner = runner

    def start(self) -> bool:
        return self.runner.start_bot_thread()

    def stop(self) -> None:
        self.runner.stop_bot()


def run_dashboard(runner):
    app = BotDashboard(BotController(runner))
    app.mainloop()


if __name__ == "__main__":
    print("Run this module from the main application to open the dashboard")
