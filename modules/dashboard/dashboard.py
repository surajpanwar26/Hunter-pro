'''Modern Tkinter dashboard to control and monitor the bot - Enhanced UI/UX.'''
# sonar:off
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
import re
import json
import threading

from modules.dashboard import log_handler, metrics
from config.secrets import ai_provider
from config.questions import user_information_all
from modules.dashboard.resume_tailor_dialog import ResumeTailorDialog
from modules.dashboard.enhanced_resume_tailor import open_enhanced_resume_tailor_dialog


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

# ===== UI Constants (reduces SonarQube duplicate string warnings) =====
UI_FONT = "Segoe UI"
UI_FONT_EMOJI = "Segoe UI Emoji"
STYLE_CARD_FRAME = 'Card.TFrame'
STYLE_HEADER_FRAME = 'Header.TFrame'
STYLE_HEADER_LABEL = 'Header.TLabel'
EVENT_MOUSEWHEEL = "<MouseWheel>"
EVENT_ENTER = "<Enter>"
EVENT_LEAVE = "<Leave>"
EVENT_CONFIGURE = "<Configure>"
EVENT_COMBOBOX_SELECTED = "<<ComboboxSelected>>"
BTN_REFRESH = "🔄 Refresh"
BTN_SETTINGS = "⚙️ Settings"
LBL_FILTER = "🔍 Filter:"
LBL_ALL_FILES = "All files"
LBL_MISSING_API_KEY = "Missing API Key"
LBL_SUCCESS_RATE = "Success Rate"
LBL_AI_PROVIDER = "AI Provider"
LBL_JOB_TITLE = "Job Title"
LBL_DASHBOARD_REFRESHED = "Dashboard refreshed"
RESUME_AUTO = "Auto (Match Master)"
RESUME_PDF = "PDF Only"
RESUME_DOCX = "DOCX Only"
DETECT_LINKEDIN = "LinkedIn Only"
DETECT_UNIVERSAL = "Universal (All Sites)"
DETECT_SMART = "Smart Detect"
DEFAULT_GROQ_MODEL = "llama-3.1-70b-versatile"
DEFAULT_HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"


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
        self.configure(padding=10, style=STYLE_CARD_FRAME, relief=tk.RIDGE, borderwidth=1)

        # Icon and title row
        header = ttkb.Frame(self, style=STYLE_CARD_FRAME)
        header.pack(fill=tk.X, pady=(0, 6))

        icon_label = ttkb.Label(header, text=icon, font=("Segoe UI Emoji", 22), bootstyle=color)
        icon_label.pack(side=tk.LEFT)

        title_label = ttkb.Label(header, text=title, font=("Segoe UI", 11, "bold"), 
                                 foreground=COLORS['text_secondary'], bootstyle="secondary")
        title_label.pack(side=tk.LEFT, padx=(10, 0))

        # Value
        self.value_label = ttkb.Label(self, text=value, font=("Segoe UI", 28, "bold"),
                                      bootstyle=color)
        self.value_label.pack(anchor=tk.W, pady=(0, 2))

        # Trend indicator (optional)
        self.trend_label = ttkb.Label(self, text="", font=("Segoe UI", 9),
                                      foreground=COLORS['text_secondary'])
        self.trend_label.pack(anchor=tk.W, pady=(4, 0))
    
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
        
        self.scrollable_frame.bind(EVENT_CONFIGURE,
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.activities = []
        self.max_items = 50
    
    def add_activity(self, message, activity_type="info"):
        """Add an activity item to the feed - handles destroyed widgets gracefully"""
        try:
            # Check if scrollable_frame still exists
            if not self.scrollable_frame.winfo_exists():
                return  # Widget has been destroyed, skip adding
        except tk.TclError:
            return  # Widget doesn't exist
        
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
        
        try:
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
                try:
                    old.destroy()
                except tk.TclError:
                    pass  # Already destroyed
            
            # Auto scroll to bottom
            self.canvas.yview_moveto(1.0)
        except tk.TclError:
            pass  # Widget was destroyed during operation
    
    def clear_feed(self):
        for item in self.activities:
            try:
                item.destroy()
            except tk.TclError:
                pass  # Already destroyed
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
            (BTN_REFRESH, self.refresh_all, "primary"),
            (BTN_SETTINGS, self.open_settings, "warning"),
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
        self.dashboard.activity_feed.add_activity(LBL_DASHBOARD_REFRESHED, "info")
    
    def open_settings(self):
        """Navigate to the Settings tab in the dashboard."""
        try:
            # Switch to Settings tab (index 4 - Jobs, Graphs, Analytics, Resume, Settings)
            if hasattr(self.dashboard, 'notebook') and self.dashboard.notebook:
                self.dashboard.notebook.select(4)  # Settings is tab index 4
                self.dashboard.activity_feed.add_activity("Opened Settings tab", "info")
        except Exception as e:
            print(f"Could not open settings: {e}")


class BotDashboard(ttkb.Window):
    def _set_tab_order(self, event=None):
        # Set tab order for visible widgets in main_panel
        if not hasattr(self, 'main_panel'):
            return
        widgets = [w for w in self.main_panel.winfo_children() if isinstance(w, (ttkb.Entry, ttkb.Button))]
        for i, w in enumerate(widgets):
            w.lift()
            if i == 0:
                w.focus_set()

    def show_loading(self, message="Loading..."):
        if hasattr(self, '_loading_overlay') and self._loading_overlay:
            return
        self._loading_overlay = tk.Toplevel(self)
        self._loading_overlay.overrideredirect(True)
        self._loading_overlay.attributes('-topmost', True)
        self._loading_overlay.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{self.winfo_rootx()}+{self.winfo_rooty()}")
        spinner = ttkb.Label(self._loading_overlay, text="⏳", font=("Segoe UI Emoji", 48), bootstyle="info")
        spinner.pack(expand=True)
        msg = ttkb.Label(self._loading_overlay, text=message, font=("Segoe UI", 16), bootstyle="info")
        msg.pack()

    def hide_loading(self):
        if hasattr(self, '_loading_overlay') and self._loading_overlay:
            self._loading_overlay.destroy()
            self._loading_overlay = None

    def show_toast(self, message, level="info"):
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        x = self.winfo_rootx() + self.winfo_width() - 320
        y = self.winfo_rooty() + 60
        toast.geometry(f"300x50+{x}+{y}")
        colors = {
            "success": COLORS['success'],
            "error": COLORS['danger'],
            "warning": COLORS['warning'],
            "info": COLORS['info']
        }
        frame = ttkb.Frame(toast, style=STYLE_CARD_FRAME)
        frame.pack(fill=tk.BOTH, expand=True)
        label = ttkb.Label(frame, text=message, font=("Segoe UI", 11), foreground=colors.get(level, COLORS['info']))
        label.pack(padx=10, pady=10)
        toast.after(2500, toast.destroy)

    def __init__(self, controller):
        # Use ttkbootstrap theme - cyborg for dark modern look
        super().__init__(themename="cyborg")
        self.title("🤖 AI Job Hunter Pro - Control Center")
        self.geometry("1500x900")
        self.state('zoomed')
        self.controller = controller
        self._history_urls = {}
        
        # Configure styles
        self._app_style = ttkb.Style()
        self._app_style.configure(STYLE_CARD_FRAME, background=COLORS['card_bg'])
        self._app_style.configure(STYLE_HEADER_FRAME, background='#1a1a2e')
        self._app_style.configure(STYLE_HEADER_LABEL, background='#1a1a2e')
        self._app_style.configure('Clean.TLabel', background='')  # Transparent background
        self._app_style.configure('Tab.TButton', font=('Segoe UI', 11), padding=(20, 10))
        self._app_style.configure('ActiveTab.TButton', font=('Segoe UI', 11, 'bold'))
        
        # ========== MODERN TABULAR LAYOUT (NO SIDEBAR) ==========
        main_frame = ttkb.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== TOP HEADER BAR (ROW 1: Logo + Status + Main Controls) =====
        header = ttkb.Frame(main_frame, style=STYLE_HEADER_FRAME)
        header.pack(fill=tk.X)
        
        # Left: Logo & Title
        logo_frame = ttkb.Frame(header, style=STYLE_HEADER_FRAME)
        logo_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        ttkb.Label(logo_frame, text="🤖", font=("Segoe UI Emoji", 24), 
                  style=STYLE_HEADER_LABEL).pack(side=tk.LEFT)
        title_stack = ttkb.Frame(logo_frame, style=STYLE_HEADER_FRAME)
        title_stack.pack(side=tk.LEFT, padx=(8, 0))
        ttkb.Label(title_stack, text="AI Job Hunter Pro", 
                  font=("Segoe UI", 14, "bold"), foreground="#ffffff",
                  style=STYLE_HEADER_LABEL).pack(anchor=tk.W)
        ttkb.Label(title_stack, text="LinkedIn Auto Apply Bot", 
                  font=("Segoe UI", 8), foreground="#888888",
                  style=STYLE_HEADER_LABEL).pack(anchor=tk.W)
        
        # Center: Status indicator (clearly visible)
        status_center = ttkb.Frame(header, style=STYLE_HEADER_FRAME)
        status_center.pack(side=tk.LEFT, padx=30)
        
        self.status_indicator = ttkb.Label(status_center, text="●", 
                                          foreground="#ff4757", font=("Arial", 20),
                                          style=STYLE_HEADER_LABEL)
        self.status_indicator.pack(side=tk.LEFT)
        self.status_label = ttkb.Label(status_center, text="STOPPED", 
                                       font=("Segoe UI", 12, "bold"), foreground="#ff4757",
                                       style=STYLE_HEADER_LABEL)
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Right: Main Control Buttons (START, STOP, PAUSE, LIVE PANEL)
        controls_frame = ttkb.Frame(header, style=STYLE_HEADER_FRAME)
        controls_frame.pack(side=tk.RIGHT, padx=15, pady=8)
        
        # Control buttons - compact but visible
        self.start_btn = ttkb.Button(controls_frame, text="▶ START", 
                                     command=self.start_bot, bootstyle="success-outline",
                                     width=10)
        self.start_btn.pack(side=tk.LEFT, padx=3)
        
        self.stop_btn = ttkb.Button(controls_frame, text="⏹ STOP", 
                                    command=self.stop_bot, state=tk.DISABLED,
                                    bootstyle="danger-outline", width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=3)
        
        self.pause_btn = ttkb.Button(controls_frame, text="⏸ PAUSE", 
                                     command=self.toggle_pause, state=tk.DISABLED,
                                     bootstyle="warning-outline", width=10)
        self.pause_btn.pack(side=tk.LEFT, padx=3)
        
        # Separator
        ttkb.Separator(controls_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=3)
        
        # LIVE PANEL button
        self.side_panel_mode = False
        self.side_panel_btn = ttkb.Button(controls_frame, text="📺 LIVE", 
                                          command=self.toggle_side_panel_mode,
                                          bootstyle="info-outline", width=8)
        self.side_panel_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # ===== TAB NAVIGATION BAR (ROW 2: Separate row for tabs) =====
        tab_bar = ttkb.Frame(main_frame)
        tab_bar.pack(fill=tk.X, padx=15, pady=(5, 0))
        
        self.current_tab = "dashboard"
        self.tab_buttons = {}
        
        # Tab frame for navigation buttons
        self.tab_frame = ttkb.Frame(tab_bar)
        self.tab_frame.pack(side=tk.LEFT)
        
        tabs = [
            ("🏠 Dashboard", "dashboard", self.show_dashboard),
            ("✨ Tailor", "tailor", self.show_tailor),
            ("📜 History", "history", self.show_history),
            ("📊 Analytics", "analytics", self.show_analytics),
            (BTN_SETTINGS, "settings", self.show_settings),
            ("❓ Help", "help", self.show_help)
        ]
        
        for text, tab_id, cmd in tabs:
            btn = ttkb.Button(self.tab_frame, text=text, 
                             command=lambda t=tab_id, c=cmd: self._switch_tab(t, c),
                             bootstyle="dark-outline" if tab_id != "dashboard" else "info",
                             padding=(8, 4), width=11)
            btn.pack(side=tk.LEFT, padx=1)
            self.tab_buttons[tab_id] = btn
        
        # Right side of tab bar: Quick actions
        quick_actions = ttkb.Frame(tab_bar)
        quick_actions.pack(side=tk.RIGHT)
        
        ttkb.Button(quick_actions, text="📂 Logs", 
                   command=lambda: __import__('webbrowser').open(f'file:///{os.path.abspath("logs")}'),
                   bootstyle="secondary-outline", width=8).pack(side=tk.LEFT, padx=2)
        ttkb.Button(quick_actions, text=BTN_REFRESH, 
                   command=self._refresh_all if hasattr(self, '_refresh_all') else lambda: None,
                   bootstyle="secondary-outline", width=8).pack(side=tk.LEFT, padx=2)
        
        # Add tooltip-like help text for Live Panel
        self.side_panel_help = ttkb.Label(tab_bar, text="", font=("Segoe UI", 1))
        self.side_panel_help.pack(side=tk.LEFT)  # Hidden placeholder
        
        # Status frame placeholder (for compatibility)
        self.status_frame = status_center
        
        # ===== QUICK STATS BAR (Below Tabs) =====
        stats_bar = ttkb.Frame(main_frame, style=STYLE_CARD_FRAME)
        stats_bar.pack(fill=tk.X, padx=0, pady=0)
        
        stats_inner = ttkb.Frame(stats_bar)
        stats_inner.pack(fill=tk.X, padx=10, pady=6)
        
        # Stats items in a row
        self.quick_stat_labels = {}
        quick_stats = [
            ("🔍", "Jobs Found", "jobs", "#3498db"),
            ("✅", "Applied", "applied", "#00d26a"),
            ("❌", "Failed", "failed", "#ff4757"),
            ("⏭️", "Skipped", "skipped", "#ffb302"),
            ("📊", LBL_SUCCESS_RATE, "rate", "#9b59b6"),
            ("⏱️", "Runtime", "runtime", "#17a2b8"),
            ("🤖", LBL_AI_PROVIDER, "provider", "#e94560"),
        ]
        
        for icon, label, key, color in quick_stats:
            stat_frame = ttkb.Frame(stats_inner)
            stat_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            
            ttkb.Label(stat_frame, text=icon, font=("Segoe UI Emoji", 12)).pack(side=tk.LEFT)
            
            val_frame = ttkb.Frame(stat_frame)
            val_frame.pack(side=tk.LEFT, padx=(5, 0))
            
            if key == "provider":
                val = ttkb.Label(val_frame, text=str(ai_provider).upper(), 
                                font=("Segoe UI", 11, "bold"), foreground=color)
            elif key == "runtime":
                val = ttkb.Label(val_frame, text="00:00:00", 
                                font=("Consolas", 11, "bold"), foreground=color)
            else:
                val = ttkb.Label(val_frame, text="0", 
                                font=("Segoe UI", 12, "bold"), foreground=color)
            val.pack(anchor=tk.W)
            
            ttkb.Label(val_frame, text=label, font=("Segoe UI", 7),
                      foreground="#888888").pack(anchor=tk.W)
            
            self.quick_stat_labels[key] = val
        
        # ===== MAIN CONTENT AREA =====
        self.main_panel = ttkb.Frame(main_frame)
        self.main_panel.pack(fill=tk.BOTH, expand=True)
        
        # Initialize state variables BEFORE status bar (needed by _update_time)
        self.job_count = 0
        self.applied_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.current_status = "Stopped"
        self.start_time = None
        self.current_job_info = {}
        self.skip_reasons = []
        self.application_history = []  # Store history for table view
        
        # ===== BOTTOM STATUS BAR =====
        self.create_status_bar(main_frame)
        
        # Activity Feed (initialize for logging)
        self.activity_feed = ActivityFeed(self.main_panel)
        
        # Setup background updates
        self.log_queue = log_handler.get_queue()
        log_handler.subscribe(self._on_new_log)
        self.after(500, self._refresh_metrics)
        self.after(1000, self._update_runtime)  # Runtime timer
        self._log_buffer: list[str] = []
        self._last_metrics_snapshot: dict | None = None
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Keyboard shortcuts
        self.bind_all('<Alt-1>', lambda e: self._switch_tab("dashboard", self.show_dashboard))
        self.bind_all('<Alt-2>', lambda e: self._switch_tab("tailor", self.show_tailor))
        self.bind_all('<Alt-3>', lambda e: self._switch_tab("history", self.show_history))
        self.bind_all('<Alt-4>', lambda e: self._switch_tab("analytics", self.show_analytics))
        self.bind_all('<Alt-5>', lambda e: self._switch_tab("settings", self.show_settings))
        self.bind_all('<Alt-6>', lambda e: self._switch_tab("help", self.show_help))
        self.bind_all('<F5>', lambda e: self._refresh_all())
        self.bind_all('<Control-s>', lambda e: self.start_bot())
        self.bind_all('<Control-q>', lambda e: self.stop_bot())
        self.bind_all('<F11>', lambda e: self.toggle_side_panel_mode())  # Side panel shortcut
        self.bind_all('<F12>', lambda e: self.toggle_side_panel_mode())  # Alternative shortcut
        
        # Welcome messages
        self.activity_feed.add_activity("Dashboard initialized", "success")
        self.activity_feed.add_activity("Ready to start job hunting!", "info")
        
        # Show dashboard by default
        self.show_dashboard()
    
    def _switch_tab(self, tab_id, cmd):
        """Switch active tab with visual feedback"""
        self.current_tab = tab_id
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn.configure(bootstyle="info")
            else:
                btn.configure(bootstyle="dark-outline")
        cmd()
    
    def _update_runtime(self):
        """Update runtime display"""
        if self.start_time and self.current_status == "Running":
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            if 'runtime' in self.quick_stat_labels:
                self.quick_stat_labels['runtime'].config(text=runtime_str)
        self.after(1000, self._update_runtime)
    
    def _refresh_all(self):
        """Refresh all dashboard data"""
        self._refresh_metrics()
        self.activity_feed.add_activity(LBL_DASHBOARD_REFRESHED, "info")
        self.show_toast("Dashboard refreshed!", "success")

    def clear_main_panel(self):
        for widget in self.main_panel.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        """Show the main dashboard with Settings prominently displayed at top"""
        self.clear_main_panel()
        
        # Configure main panel background
        self.main_panel.configure(style=STYLE_CARD_FRAME)
        
        # ===== TOP SECTION: TITLE ONLY (Stats removed - already in global quick stats bar) =====
        top_section = ttkb.Frame(self.main_panel)
        top_section.pack(fill=tk.X, padx=10, pady=(4, 2))
        
        # Title row
        title_row = ttkb.Frame(top_section)
        title_row.pack(fill=tk.X, pady=(0, 4))
        
        ttkb.Label(title_row, text="🏠 Dashboard - Settings & Control", 
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        
        # Runtime display
        runtime_frame = ttkb.Frame(title_row)
        runtime_frame.pack(side=tk.RIGHT)
        ttkb.Label(runtime_frame, text="⏱️ Runtime:", 
                  font=("Segoe UI", 10), foreground="#888888").pack(side=tk.LEFT)
        self.runtime_label = ttkb.Label(runtime_frame, text="00:00:00", 
                                        font=("Consolas", 11, "bold"), foreground="#00d26a")
        self.runtime_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # NOTE: Duplicate stats row REMOVED - stats are already shown in the global quick stats bar above tabs
        
        # ===== MAIN CONTENT: TWO COLUMN LAYOUT =====
        content_frame = ttkb.Frame(self.main_panel)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        
        # Use PanedWindow for resizable columns
        content_paned = ttkb.Panedwindow(content_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True)
        
        # ===== LEFT COLUMN: ALL SETTINGS (PRIMARY FOCUS - 80% width for wider settings) =====
        left_col = ttkb.Frame(content_paned, width=1000)
        left_col.pack_propagate(False)  # Prevent children from shrinking the frame
        content_paned.add(left_col, weight=8)
        
        # Initialize ALL setting variables with current config values
        self._init_quick_settings_vars()
        
        # ============================================
        # ALL SETTINGS PANEL (MAIN FOCUS - At Top)
        # ============================================
        settings_frame = ttkb.Labelframe(left_col, text="⚙️ All Settings (Change & Run)", bootstyle="info")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Restart warning banner
        restart_banner = ttkb.Frame(settings_frame)
        restart_banner.pack(fill=tk.X, padx=5, pady=(5, 0))
        ttkb.Label(restart_banner, text="⚠️ Browser settings (🔒) require bot restart | Runtime settings (⚡) apply immediately",
                  font=("Segoe UI", 8), foreground="#f59e0b").pack(anchor=tk.W)
        
        # Create scrollable canvas for settings
        settings_canvas = tk.Canvas(settings_frame, bg=COLORS['card_bg'], highlightthickness=0)
        settings_scrollbar = ttkb.Scrollbar(settings_frame, orient="vertical", command=settings_canvas.yview)
        settings_scrollable = ttkb.Frame(settings_canvas)
        
        settings_scrollable.bind(EVENT_CONFIGURE, lambda e: settings_canvas.configure(scrollregion=settings_canvas.bbox("all")))
        settings_canvas.create_window((0, 0), window=settings_scrollable, anchor="nw")
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)
        
        # IMPROVED Mouse wheel scrolling - Bind to ALL child widgets recursively
        def _on_settings_mousewheel(event):
            settings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel_recursive(widget):
            """Recursively bind mousewheel to all child widgets for smooth scrolling."""
            widget.bind(EVENT_MOUSEWHEEL, _on_settings_mousewheel)
            widget.bind(EVENT_ENTER, lambda e: settings_canvas.bind_all(EVENT_MOUSEWHEEL, _on_settings_mousewheel))
            widget.bind(EVENT_LEAVE, lambda e: settings_canvas.unbind_all(EVENT_MOUSEWHEEL))
            for child in widget.winfo_children():
                _bind_mousewheel_recursive(child)
        
        # Bind to canvas and scrollable frame initially
        settings_canvas.bind(EVENT_MOUSEWHEEL, _on_settings_mousewheel)
        settings_scrollable.bind(EVENT_MOUSEWHEEL, _on_settings_mousewheel)
        # Store function for later use when adding new widgets
        self._bind_settings_mousewheel = _bind_mousewheel_recursive
        
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ========== SECTION 0: PILOT MODE & SCHEDULING (TOP PRIORITY) ==========
        self._create_pilot_scheduling_section(settings_scrollable)
        
        # ========== SECTION 1: Bot Behavior ==========
        sec1 = ttkb.Labelframe(settings_scrollable, text="🤖 Bot Behavior", bootstyle="info")
        sec1.pack(fill=tk.X, padx=5, pady=(5, 3))
        
        sec1_inner = ttkb.Frame(sec1)
        sec1_inner.pack(fill=tk.X, padx=8, pady=5)
        
        # 2-column grid layout for wider spread
        sec1_grid = ttkb.Frame(sec1_inner)
        sec1_grid.pack(fill=tk.X, pady=2)
        sec1_grid.columnconfigure(0, weight=1)
        sec1_grid.columnconfigure(1, weight=1)
        
        ttkb.Checkbutton(sec1_grid, text="🔄 Run Non-Stop", variable=self.qs_run_non_stop,
                        bootstyle="success-round-toggle", command=self._save_quick_settings).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttkb.Checkbutton(sec1_grid, text="🔀 Alternate Sort", variable=self.qs_alternate_sortby,
                        bootstyle="info-round-toggle", command=self._save_quick_settings).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttkb.Checkbutton(sec1_grid, text="📅 Cycle Date Posted", variable=self.qs_cycle_date_posted,
                        bootstyle="primary-round-toggle", command=self._save_quick_settings).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttkb.Checkbutton(sec1_grid, text="⏱️ Stop at 24hr", variable=self.qs_stop_date_24hr,
                        bootstyle="warning-round-toggle", command=self._save_quick_settings).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttkb.Checkbutton(sec1_grid, text="📂 Close Tabs", variable=self.qs_close_tabs,
                        bootstyle="secondary-round-toggle", command=self._save_quick_settings).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttkb.Checkbutton(sec1_grid, text="👥 Follow Companies", variable=self.qs_follow_companies,
                        bootstyle="info-round-toggle", command=self._save_quick_settings).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Spinboxes row - spread across full width
        row1c = ttkb.Frame(sec1_inner)
        row1c.pack(fill=tk.X, pady=(6, 2))
        row1c.columnconfigure(1, weight=1)
        row1c.columnconfigure(3, weight=1)
        ttkb.Label(row1c, text="📊 Max Jobs (0=∞):", font=(UI_FONT, 9)).pack(side=tk.LEFT)
        self.qs_max_jobs_spin = ttkb.Spinbox(row1c, from_=0, to=500, width=6, textvariable=self.qs_max_jobs,
                                              command=self._save_quick_settings)
        self.qs_max_jobs_spin.pack(side=tk.LEFT, padx=(5, 30))
        ttkb.Label(row1c, text="⏱️ Click Gap (secs):", font=(UI_FONT, 9)).pack(side=tk.LEFT)
        self.qs_click_gap_spin = ttkb.Spinbox(row1c, from_=1, to=60, width=5, textvariable=self.qs_click_gap,
                                               command=self._save_quick_settings)
        self.qs_click_gap_spin.pack(side=tk.LEFT, padx=(5, 0))
        
        # ========== SECTIONS 2 & 3: Form Filling + Resume Tailoring (side by side) ==========
        sec2_3_row = ttkb.Frame(settings_scrollable)
        sec2_3_row.pack(fill=tk.X, padx=5, pady=3)
        sec2_3_row.columnconfigure(0, weight=1)
        sec2_3_row.columnconfigure(1, weight=1)
        
        # -- Form Filling (left) --
        sec2 = ttkb.Labelframe(sec2_3_row, text="📝 Form Filling", bootstyle="warning")
        sec2.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        sec2_inner = ttkb.Frame(sec2)
        sec2_inner.pack(fill=tk.X, padx=8, pady=5)
        
        ttkb.Checkbutton(sec2_inner, text="⚡ Fast Form Fill", variable=self.qs_fast_mode,
                        bootstyle="primary-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec2_inner, text="🧠 Smart Form Filler V2", variable=self.qs_smart_form_filler,
                        bootstyle="success-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        
        delay_row = ttkb.Frame(sec2_inner)
        delay_row.pack(fill=tk.X, pady=2)
        ttkb.Label(delay_row, text="🐢 Delay Multiplier:", font=(UI_FONT, 9)).pack(side=tk.LEFT)
        self.qs_delay_spin = ttkb.Spinbox(delay_row, from_=0.1, to=2.0, increment=0.1, width=5,
                                          textvariable=self.qs_delay_multiplier, command=self._save_quick_settings)
        self.qs_delay_spin.pack(side=tk.LEFT, padx=(5, 0))
        
        # -- Resume Tailoring (right) --
        sec3 = ttkb.Labelframe(sec2_3_row, text="📄 Resume Tailoring", bootstyle="success")
        sec3.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        sec3_inner = ttkb.Frame(sec3)
        sec3_inner.pack(fill=tk.X, padx=8, pady=5)
        
        ttkb.Checkbutton(sec3_inner, text="📝 Enable Resume Tailor", variable=self.qs_resume_tailor,
                        bootstyle="success-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec3_inner, text="✅ Confirm After Filters", variable=self.qs_tailor_confirm_filters,
                        bootstyle="info-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec3_inner, text="💬 Prompt Before JD", variable=self.qs_tailor_prompt_jd,
                        bootstyle="warning-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        
        # Resume Upload Format dropdown
        fmt_row = ttkb.Frame(sec3_inner)
        fmt_row.pack(fill=tk.X, pady=2)
        ttkb.Label(fmt_row, text="📤 Format:", font=(UI_FONT, 9)).pack(side=tk.LEFT)
        self.qs_resume_format_combo = ttkb.Combobox(fmt_row, 
                                                    textvariable=self.qs_resume_upload_format,
                                                    values=[RESUME_AUTO, RESUME_PDF, RESUME_DOCX],
                                                    state="readonly", width=16)
        self.qs_resume_format_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.qs_resume_format_combo.bind(EVENT_COMBOBOX_SELECTED, lambda e: self._save_quick_settings())
        
        # ========== SECTIONS 4 & 5: Browser & UI + Control (side by side) ==========
        sec4_5_row = ttkb.Frame(settings_scrollable)
        sec4_5_row.pack(fill=tk.X, padx=5, pady=3)
        sec4_5_row.columnconfigure(0, weight=1)
        sec4_5_row.columnconfigure(1, weight=1)
        
        # -- Browser & UI (left) --
        sec4 = ttkb.Labelframe(sec4_5_row, text="🖥️ Browser & UI 🔒", bootstyle="primary")
        sec4.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        sec4_inner = ttkb.Frame(sec4)
        sec4_inner.pack(fill=tk.X, padx=8, pady=5)
        
        ttkb.Label(sec4_inner, text="⚠️ Requires bot restart",
                  font=(UI_FONT, 8), foreground="#ef4444").pack(anchor=tk.W, pady=(0, 5))
        
        ttkb.Checkbutton(sec4_inner, text="🖥️ Show Browser", variable=self.qs_show_browser,
                        bootstyle="secondary-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec4_inner, text="🔌 Disable Extensions", variable=self.qs_disable_extensions,
                        bootstyle="warning-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec4_inner, text="🛡️ Safe Mode", variable=self.qs_safe_mode,
                        bootstyle="danger-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec4_inner, text="📜 Smooth Scroll", variable=self.qs_smooth_scroll,
                        bootstyle="info-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec4_inner, text="🌙 Keep Awake", variable=self.qs_keep_awake,
                        bootstyle="success-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec4_inner, text="🛡️ Stealth Mode", variable=self.qs_stealth_mode,
                        bootstyle="dark-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        
        # -- Control & Alerts (right) --
        sec5 = ttkb.Labelframe(sec4_5_row, text="🎛️ Control & Alerts ⚡", bootstyle="danger")
        sec5.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        sec5_inner = ttkb.Frame(sec5)
        sec5_inner.pack(fill=tk.X, padx=8, pady=5)
        
        ttkb.Checkbutton(sec5_inner, text="⏸️ Pause Before Submit", variable=self.qs_pause_submit,
                        bootstyle="danger-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec5_inner, text="❓ Pause at Failed Q", variable=self.qs_pause_failed_q,
                        bootstyle="warning-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        ttkb.Checkbutton(sec5_inner, text="⚠️ Show AI Errors", variable=self.qs_show_ai_errors,
                        bootstyle="info-round-toggle", command=self._save_quick_settings).pack(anchor=tk.W, pady=2)
        
        # ========== SECTION 6: Chrome Extension & Universal Form Filler ⚡ ==========
        sec6 = ttkb.Labelframe(settings_scrollable, text="🧩 Extension & Form Filler ⚡", bootstyle="success")
        sec6.pack(fill=tk.X, padx=5, pady=3)
        
        sec6_inner = ttkb.Frame(sec6)
        sec6_inner.pack(fill=tk.X, padx=8, pady=5)
        
        # Row 6a: Extension enabled and auto-sync
        row6a = ttkb.Frame(sec6_inner)
        row6a.pack(fill=tk.X, pady=2)
        ttkb.Checkbutton(row6a, text="🧩 Enable Extension", variable=self.qs_extension_enabled,
                        bootstyle="success-round-toggle", command=self._save_quick_settings).pack(side=tk.LEFT, padx=(0, 12))
        ttkb.Checkbutton(row6a, text="🔄 Auto-sync Config", variable=self.qs_extension_auto_sync,
                        bootstyle="info-round-toggle", command=self._save_quick_settings).pack(side=tk.LEFT, padx=(0, 12))
        ttkb.Checkbutton(row6a, text="📚 AI Learning", variable=self.qs_extension_ai_learning,
                        bootstyle="primary-round-toggle", command=self._save_quick_settings).pack(side=tk.LEFT)
        
        # Row 6b: Universal form detection mode
        row6b = ttkb.Frame(sec6_inner)
        row6b.pack(fill=tk.X, pady=2)
        ttkb.Label(row6b, text="🌐 Detection Mode:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.qs_extension_mode_combo = ttkb.Combobox(row6b, 
                                                    textvariable=self.qs_extension_detection_mode,
                                                    values=[DETECT_LINKEDIN, DETECT_UNIVERSAL, DETECT_SMART],
                                                    state="readonly", width=18)
        self.qs_extension_mode_combo.pack(side=tk.LEFT, padx=(5, 15))
        self.qs_extension_mode_combo.bind(EVENT_COMBOBOX_SELECTED, lambda e: self._save_quick_settings())
        
        ttkb.Button(row6b, text="📤 Export Config", 
                   command=self._export_extension_config,
                   bootstyle="success-outline", width=14).pack(side=tk.LEFT, padx=(0, 5))
        ttkb.Button(row6b, text="🔄 Reload Ext", 
                   command=self._reload_extension_manifest,
                   bootstyle="info-outline", width=12).pack(side=tk.LEFT)
        
        # ========== SAVE BUTTON ROW ==========
        save_row = ttkb.Frame(settings_scrollable)
        save_row.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        ttkb.Button(save_row, text="💾 Save All Settings", 
                   command=self._apply_quick_settings,
                   bootstyle="success", width=20).pack(side=tk.LEFT)
        ttkb.Button(save_row, text="🔄 Reset Defaults", 
                   command=self._reset_settings_to_defaults,
                   bootstyle="secondary-outline", width=15).pack(side=tk.LEFT, padx=(10, 0))
        ttkb.Button(save_row, text="📂 Open Logs", 
                   command=lambda: webbrowser.open(f'file:///{os.path.abspath("logs")}'),
                   bootstyle="info-outline", width=12).pack(side=tk.RIGHT)
        
        # ===== RIGHT COLUMN: Current Job + AI Processing + Logs (20% width) =====
        right_col = ttkb.Frame(content_paned)
        content_paned.add(right_col, weight=2)
        
        # Force 80/20 sash position after layout is computed (more room for settings)
        def _set_sash_80_20():
            try:
                content_paned.update_idletasks()
                total_w = content_paned.winfo_width()
                if total_w > 100:  # Window has rendered
                    content_paned.sashpos(0, int(total_w * 0.80))
                else:
                    # Window not ready yet, retry
                    content_paned.after(100, _set_sash_80_20)
            except Exception:
                pass
        content_paned.after(200, _set_sash_80_20)
        
        # Current Job Card (compact)
        job_frame = ttkb.Labelframe(right_col, text="💼 Current Job", bootstyle="info")
        job_frame.pack(fill=tk.X, pady=(0, 4))
        
        job_inner = ttkb.Frame(job_frame)
        job_inner.pack(fill=tk.X, padx=8, pady=6)
        
        self.dash_job_title = ttkb.Label(job_inner, text="Waiting for job...", 
                                         font=("Segoe UI", 11, "bold"), wraplength=350)
        self.dash_job_title.pack(anchor=tk.W)
        
        self.dash_job_company = ttkb.Label(job_inner, text="", font=("Segoe UI", 9), foreground="#aaaaaa")
        self.dash_job_company.pack(anchor=tk.W, pady=(2, 0))
        
        self.dash_job_status = ttkb.Label(job_inner, text="⏳ Idle", font=("Segoe UI", 9), foreground="#ffd93d")
        self.dash_job_status.pack(anchor=tk.W, pady=(4, 0))
        
        # AI Processing Card (compact)
        ai_frame = ttkb.Labelframe(right_col, text="🤖 AI Processing", bootstyle="primary")
        ai_frame.pack(fill=tk.X, pady=(0, 4))
        
        ai_inner = ttkb.Frame(ai_frame)
        ai_inner.pack(fill=tk.X, padx=8, pady=6)
        
        # JD Analysis
        jd_header = ttkb.Frame(ai_inner)
        jd_header.pack(fill=tk.X)
        ttkb.Label(jd_header, text="📋 JD Analysis", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.dash_jd_status = ttkb.Label(jd_header, text="Idle", font=("Segoe UI", 8), foreground="#888888")
        self.dash_jd_status.pack(side=tk.RIGHT)
        
        self.dash_jd_progress = ttkb.Progressbar(ai_inner, mode='determinate', bootstyle="info-striped")
        self.dash_jd_progress.pack(fill=tk.X, pady=(3, 8))
        
        # Resume Tailoring
        resume_header = ttkb.Frame(ai_inner)
        resume_header.pack(fill=tk.X)
        ttkb.Label(resume_header, text="📝 Resume Tailor", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.dash_resume_status = ttkb.Label(resume_header, text="Idle", font=("Segoe UI", 8), foreground="#888888")
        self.dash_resume_status.pack(side=tk.RIGHT)
        
        self.dash_resume_progress = ttkb.Progressbar(ai_inner, mode='determinate', bootstyle="warning-striped")
        self.dash_resume_progress.pack(fill=tk.X, pady=(3, 0))
        
        # Live Log Card (matching side panel style)
        log_frame = ttkb.Labelframe(right_col, text="📋 Live Activity Log", bootstyle="secondary")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Log toolbar
        log_toolbar = ttkb.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, padx=6, pady=(4, 2))
        
        ttkb.Label(log_toolbar, text=LBL_FILTER, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        self.log_filter = ttkb.Combobox(log_toolbar, 
                                        values=["All", "Info", "Success", "Warning", "Error"],
                                        state="readonly", width=10)
        self.log_filter.set("All")
        self.log_filter.pack(side=tk.LEFT, padx=(5, 10))
        
        ttkb.Button(log_toolbar, text="🗑️ Clear", bootstyle="secondary-outline",
                   command=self.clear_logs, width=8).pack(side=tk.RIGHT, padx=2)
        ttkb.Button(log_toolbar, text="📥 Export", bootstyle="info-outline",
                   command=self.export_logs, width=8).pack(side=tk.RIGHT, padx=2)
        
        # Log text area (dark theme matching side panel)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=("Consolas", 9),
            bg='#0f0f23', fg='#00ff88', height=20,
            insertbackground='white', relief=tk.FLAT,
            selectbackground='#388bfd', selectforeground='#ffffff'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))
        
        # Configure log tags for colors
        self.log_text.tag_configure("error", foreground="#ff6b6b")
        self.log_text.tag_configure("success", foreground="#4ade80")
        self.log_text.tag_configure("warning", foreground="#fbbf24")
        self.log_text.tag_configure("info", foreground="#60a5fa")
        self.log_text.tag_configure("timestamp", foreground="#6b7280")
        
        # Initial values
        self._update_dashboard_stats()
    
    def _create_dashboard_stat(self, parent, col, icon, label, attr_name, color):
        """Create a stat card for the main dashboard matching side panel style"""
        frame = ttkb.Frame(parent)
        frame.grid(row=0, column=col, padx=4, pady=3, sticky="nsew")
        
        # Card inner with subtle border
        inner = ttkb.Frame(frame, padding=8)
        inner.pack(fill=tk.BOTH, expand=True)
        
        # Icon and value row
        top_row = ttkb.Frame(inner)
        top_row.pack(fill=tk.X)
        
        ttkb.Label(top_row, text=icon, font=("Segoe UI Emoji", 16)).pack(side=tk.LEFT)
        
        val_label = ttkb.Label(top_row, text="0", 
                               font=("Segoe UI", 18, "bold"),
                               foreground=color)
        val_label.pack(side=tk.RIGHT)
        
        # Label
        ttkb.Label(inner, text=label, font=("Segoe UI", 8),
                  foreground="#888888").pack(anchor=tk.W, pady=(3, 0))
        
        # Store reference
        setattr(self, attr_name, val_label)
    
    def _update_dashboard_stats(self):
        """Update all dashboard statistics including quick stats bar"""
        # Update main dashboard stats - wrap in try/except to handle destroyed widgets
        try:
            if hasattr(self, 'dash_jobs_val') and self.dash_jobs_val.winfo_exists():
                self.dash_jobs_val.config(text=str(self.job_count))
            if hasattr(self, 'dash_applied_val') and self.dash_applied_val.winfo_exists():
                self.dash_applied_val.config(text=str(self.applied_count))
            if hasattr(self, 'dash_failed_val') and self.dash_failed_val.winfo_exists():
                self.dash_failed_val.config(text=str(self.failed_count))
            if hasattr(self, 'dash_skipped_val') and self.dash_skipped_val.winfo_exists():
                self.dash_skipped_val.config(text=str(self.skipped_count))
            if hasattr(self, 'dash_rate_val') and self.dash_rate_val.winfo_exists():
                total = self.applied_count + self.failed_count
                rate = (self.applied_count / total * 100) if total > 0 else 0
                self.dash_rate_val.config(text=f"{rate:.0f}%")
        except tk.TclError:
            pass  # Widget was destroyed
        
        # Update quick stats bar (top bar) - always exists
        if hasattr(self, 'quick_stat_labels'):
            try:
                if 'jobs' in self.quick_stat_labels:
                    self.quick_stat_labels['jobs'].config(text=str(self.job_count))
                if 'applied' in self.quick_stat_labels:
                    self.quick_stat_labels['applied'].config(text=str(self.applied_count))
                if 'failed' in self.quick_stat_labels:
                    self.quick_stat_labels['failed'].config(text=str(self.failed_count))
                if 'skipped' in self.quick_stat_labels:
                    self.quick_stat_labels['skipped'].config(text=str(self.skipped_count))
                if 'rate' in self.quick_stat_labels:
                    total = self.applied_count + self.failed_count
                    rate = (self.applied_count / total * 100) if total > 0 else 0
                    self.quick_stat_labels['rate'].config(text=f"{rate:.0f}%")
            except tk.TclError:
                pass  # Widget might be destroyed

    def show_tailor(self):
        """Show the Resume Tailoring Center with modern UI"""
        self.clear_main_panel()
        
        # Main container
        main_container = ttkb.Frame(self.main_panel)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Header
        header = ttkb.Frame(main_container)
        header.pack(fill=tk.X, pady=(0, 12))
        
        ttkb.Label(header, text="✨ Resume Tailoring Center", 
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        
        ttkb.Button(header, text="📖 Guide", bootstyle="info-outline",
                   command=lambda: webbrowser.open("ENHANCED_RESUME_QUICK_START.md")).pack(side=tk.RIGHT)
        
        # Two column layout
        content = ttkb.Frame(main_container)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        
        # LEFT: Input section
        left_frame = ttkb.Labelframe(content, text="📄 Input", bootstyle="info")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        input_inner = ttkb.Frame(left_frame)
        input_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Resume file input
        ttkb.Label(input_inner, text="📎 Resume File:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        resume_row = ttkb.Frame(input_inner)
        resume_row.pack(fill=tk.X, pady=(5, 15))
        
        self.tailor_resume_entry = ttkb.Entry(resume_row, width=40)
        self.tailor_resume_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        ttkb.Button(resume_row, text="📂 Browse", bootstyle="secondary-outline",
                   command=lambda: self._browse_file(self.tailor_resume_entry)).pack(side=tk.LEFT)
        
        # Job description input
        ttkb.Label(input_inner, text="📋 Job Description:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        self.tailor_jd_text = scrolledtext.ScrolledText(
            input_inner, height=12, wrap=tk.WORD,
            font=("Consolas", 9), bg='#1e1e2e', fg='#e8e8e8',
            insertbackground='white'
        )
        self.tailor_jd_text.pack(fill=tk.BOTH, expand=True, pady=(5, 15))
        self.tailor_jd_text.insert("1.0", "Paste the job description here...")
        
        # Custom instructions
        ttkb.Label(input_inner, text="📝 Custom Instructions (optional):", font=("Segoe UI", 10)).pack(anchor=tk.W)
        
        self.tailor_instr_entry = ttkb.Entry(input_inner)
        self.tailor_instr_entry.pack(fill=tk.X, pady=(5, 0))
        self.tailor_instr_entry.insert(0, "Focus on technical skills and achievements")
        
        # RIGHT: Actions & Preview
        right_frame = ttkb.Labelframe(content, text="🚀 Actions", bootstyle="success")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        right_inner = ttkb.Frame(right_frame)
        right_inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # AI Provider selection
        provider_frame = ttkb.Frame(right_inner)
        provider_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttkb.Label(provider_frame, text="🤖 AI Provider:", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        
        self.tailor_provider = ttkb.Combobox(
            provider_frame, 
            values=["ollama", "groq", "openai", "deepseek", "gemini"],
            state="readonly", width=15
        )
        self.tailor_provider.set("ollama")
        self.tailor_provider.pack(side=tk.LEFT, padx=(10, 0))
        
        # Action buttons
        btn_frame = ttkb.Frame(right_inner)
        btn_frame.pack(fill=tk.X, pady=15)
        
        ttkb.Button(btn_frame, text="✨ Open Enhanced Tailor", 
                   command=self.open_resume_tailor_dialog,
                   bootstyle="success", width=22).pack(fill=tk.X, pady=3)
        
        ttkb.Button(btn_frame, text="📝 Quick Tailor (Classic)", 
                   command=self.open_classic_resume_tailor,
                   bootstyle="info-outline", width=22).pack(fill=tk.X, pady=3)
        
        # Tips section
        tips_frame = ttkb.Labelframe(right_inner, text="💡 Tips", bootstyle="warning")
        tips_frame.pack(fill=tk.X, pady=(15, 0))
        
        tips_inner = ttkb.Frame(tips_frame)
        tips_inner.pack(fill=tk.X, padx=10, pady=10)
        
        tips = [
            "• Use specific job descriptions for best results",
            "• The AI preserves your resume format",
            "• Keywords are automatically optimized for ATS",
            "• Review before submitting to employers"
        ]
        for tip in tips:
            ttkb.Label(tips_inner, text=tip, font=("Segoe UI", 9),
                      foreground="#aaaaaa").pack(anchor=tk.W, pady=1)

    def _browse_file(self, entry_widget):
        path = filedialog.askopenfilename(
            title="Select File", 
            filetypes=[("Resume Files", "*.pdf *.docx *.txt"), ("All Files", "*.*")]
        )
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def show_history(self):
        """Show Application History with modern tabular UI and real data"""
        self.clear_main_panel()
        
        main_container = ttkb.Frame(self.main_panel)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Header with actions
        header = ttkb.Frame(main_container)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttkb.Label(header, text="📜 Application History", 
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        
        # Action buttons
        btn_frame = ttkb.Frame(header)
        btn_frame.pack(side=tk.RIGHT)
        
        ttkb.Button(btn_frame, text="📥 Export CSV", bootstyle="success-outline",
                   command=self.export_history, width=12).pack(side=tk.LEFT, padx=3)
        ttkb.Button(btn_frame, text="📥 Export PDF", bootstyle="info-outline",
                   command=self._export_history_pdf, width=12).pack(side=tk.LEFT, padx=3)
        ttkb.Button(btn_frame, text="🗑️ Clear All", bootstyle="danger-outline",
                   command=self._clear_history, width=10).pack(side=tk.LEFT, padx=3)
        ttkb.Button(btn_frame, text=BTN_REFRESH, bootstyle="secondary-outline",
                   command=self.show_history, width=10).pack(side=tk.LEFT, padx=3)
        
        # Stats summary cards
        stats_frame = ttkb.Frame(main_container)
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        for i in range(5):
            stats_frame.columnconfigure(i, weight=1)
        
        self._create_history_stat(stats_frame, 0, "📊", "Total Jobs", str(self.job_count), "#3498db")
        self._create_history_stat(stats_frame, 1, "✅", "Applied", str(self.applied_count), "#00d26a")
        self._create_history_stat(stats_frame, 2, "❌", "Failed", str(self.failed_count), "#ff4757")
        self._create_history_stat(stats_frame, 3, "⏭️", "Skipped", str(self.skipped_count), "#ffb302")
        total = self.applied_count + self.failed_count
        rate = (self.applied_count / total * 100) if total > 0 else 0
        self._create_history_stat(stats_frame, 4, "📈", LBL_SUCCESS_RATE, f"{rate:.1f}%", "#9b59b6")
        
        # Filter bar
        filter_frame = ttkb.Frame(main_container)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttkb.Label(filter_frame, text=LBL_FILTER, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        
        self.history_filter = ttkb.Combobox(filter_frame, 
                                            values=["All", "Applied", "Failed", "Skipped", "Today", "This Week"],
                                            state="readonly", width=12)
        self.history_filter.set("All")
        self.history_filter.pack(side=tk.LEFT, padx=(8, 15))
        self.history_filter.bind('<<ComboboxSelected>>', lambda e: self._filter_history())
        
        ttkb.Label(filter_frame, text="🔎 Search:", font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.history_search = ttkb.Entry(filter_frame, width=25)
        self.history_search.pack(side=tk.LEFT, padx=(8, 0))
        self.history_search.bind('<KeyRelease>', lambda e: self._filter_history())
        
        # Table Frame with Treeview
        table_frame = ttkb.Labelframe(main_container, text="📋 Application Records", bootstyle="info")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create Treeview table
        columns = ("timestamp", "job_title", "company", "location", "status", "ai_score", "action")
        self.history_tree = ttkb.Treeview(table_frame, columns=columns, show="headings", 
                                          bootstyle="dark", height=15)
        
        # Define columns
        self.history_tree.heading("timestamp", text="⏰ Time", anchor=tk.W)
        self.history_tree.heading("job_title", text="💼 Job Title", anchor=tk.W)
        self.history_tree.heading("company", text="🏢 Company", anchor=tk.W)
        self.history_tree.heading("location", text="📍 Location", anchor=tk.W)
        self.history_tree.heading("status", text="📊 Status", anchor=tk.CENTER)
        self.history_tree.heading("ai_score", text="🤖 AI Score", anchor=tk.CENTER)
        self.history_tree.heading("action", text="⚡ Action", anchor=tk.CENTER)
        
        # Column widths
        self.history_tree.column("timestamp", width=100, minwidth=80)
        self.history_tree.column("job_title", width=250, minwidth=150)
        self.history_tree.column("company", width=150, minwidth=100)
        self.history_tree.column("location", width=120, minwidth=80)
        self.history_tree.column("status", width=100, minwidth=80, anchor=tk.CENTER)
        self.history_tree.column("ai_score", width=80, minwidth=60, anchor=tk.CENTER)
        self.history_tree.column("action", width=100, minwidth=80, anchor=tk.CENTER)
        
        # Add scrollbar
        scrollbar = ttkb.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))
        
        # Load history data
        self._load_history_data()
        
        # Context menu
        self.history_tree.bind('<Button-3>', self._show_history_context_menu)
        self.history_tree.bind('<Double-1>', self._view_application_details)
    
    def _load_history_data(self):
        """Load application history from CSV files"""
        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            self._history_urls.clear()
            
            # Try to load from history files
            import csv
            history_files = [
                "all excels/all_applied_applications_history.csv",
                "all excels/all_failed_applications_history.csv"
            ]
            
            all_records = []
            
            for file_path in history_files:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                status = "✅ Applied" if "applied" in file_path else "❌ Failed"
                                all_records.append({
                                    'timestamp': row.get('timestamp', row.get('date', 'N/A'))[:16],
                                    'job_title': row.get('job_title', row.get('title', 'N/A'))[:40],
                                    'company': row.get('company', 'N/A')[:20],
                                    'location': row.get('location', 'N/A')[:15],
                                    'status': status,
                                    'ai_score': row.get('ai_score', '--'),
                                    'url': row.get('link', row.get('url', ''))
                                })
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
            
            # Sort by timestamp (newest first)
            all_records.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Add to treeview
            for i, record in enumerate(all_records[:100]):  # Limit to 100 records
                tag = 'applied' if '✅' in record['status'] else 'failed'
                item_id = self.history_tree.insert('', 'end', values=(
                    record['timestamp'],
                    record['job_title'],
                    record['company'],
                    record['location'],
                    record['status'],
                    record['ai_score'],
                    "👁️ View"
                ), tags=(tag,))
                if record.get('url'):
                    self._history_urls[item_id] = record['url']
            
            # Configure tags for colors
            self.history_tree.tag_configure('applied', foreground='#4ade80')
            self.history_tree.tag_configure('failed', foreground='#ff6b6b')
            
            if not all_records:
                self.history_tree.insert('', 'end', values=(
                    "--", "No applications yet", "Start the bot!", "--", "⏳ Waiting", "--", "--"
                ))
                
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def _filter_history(self):
        """Filter history table based on search and filter"""
        # Re-load and filter
        self._load_history_data()
    
    def _show_history_context_menu(self, event):
        """Show context menu for history table"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="👁️ View Details", command=self._view_application_details)
        menu.add_command(label="🔗 Open Link", command=self._open_job_link)
        menu.add_separator()
        menu.add_command(label="📋 Copy to Clipboard", command=self._copy_to_clipboard)
        menu.add_command(label="🗑️ Delete Record", command=self._delete_history_record)
        menu.post(event.x_root, event.y_root)
    
    def _view_application_details(self, event=None):
        """View detailed information about selected application"""
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            values = item['values']
            details = f"Job: {values[1]}\nCompany: {values[2]}\nLocation: {values[3]}\nStatus: {values[4]}\nTime: {values[0]}"
            messagebox.showinfo("Application Details", details)
    
    def _open_job_link(self):
        """Open job link in browser"""
        selection = self.history_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        url = self._history_urls.get(item_id)
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("Info", "Job link not available")
    
    def _copy_to_clipboard(self):
        """Copy selected record to clipboard"""
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            values = item['values']
            text = f"{values[1]} at {values[2]} - {values[4]}"
            self.clipboard_clear()
            self.clipboard_append(text)
            self.show_toast("Copied to clipboard!", "success")
    
    def _delete_history_record(self):
        """Delete selected history record"""
        selection = self.history_tree.selection()
        if selection:
            if messagebox.askyesno("Confirm Delete", "Delete this record?"):
                item_id = selection[0]
                self.history_tree.delete(item_id)
                self._history_urls.pop(item_id, None)
                self.show_toast("Record deleted", "info")
    
    def _export_history_pdf(self):
        """Export history to PDF (via HTML)"""
        try:
            # Get all items from tree
            items = self.history_tree.get_children()
            if not items:
                self.show_toast("No history to export!", "warning")
                return
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
                title="Export History",
                initialfile=f"job_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            )
            
            if file_path:
                # Build HTML content
                html = """<!DOCTYPE html>
<html>
<head>
    <title>Job Application History</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .success { color: green; }
        .failed { color: red; }
        .pending { color: orange; }
    </style>
</head>
<body>
    <h1>Job Application History</h1>
    <p>Exported on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    <table>
        <tr><th>#</th><th>Job Title</th><th>Company</th><th>Date</th><th>Status</th></tr>
"""
                for item in items:
                    values = self.history_tree.item(item)['values']
                    status_text = str(values[4])
                    if 'Applied' in status_text:
                        status_class = 'success'
                    elif 'Failed' in status_text:
                        status_class = 'failed'
                    else:
                        status_class = 'pending'
                    html += f"<tr><td>{values[0]}</td><td>{values[1]}</td><td>{values[2]}</td><td>{values[3]}</td><td class='{status_class}'>{values[4]}</td></tr>\n"
                
                html += "</table></body></html>"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                self.show_toast("History exported! Open in browser to print as PDF", "success")
                # Try to open the file
                try:
                    os.startfile(file_path)
                except Exception:
                    pass
        except Exception as e:
            self.show_toast(f"Export failed: {e}", "error")
    
    def _clear_history(self):
        """Clear all history"""
        if messagebox.askyesno("Confirm Clear", "Clear all application history?"):
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            self.show_toast("History cleared", "info")
    
    def _create_history_stat(self, parent, col, icon, label, value, color):
        """Create a stat card for history page"""
        frame = ttkb.Frame(parent, padding=6)
        frame.grid(row=0, column=col, padx=3, sticky="nsew")
        
        ttkb.Label(frame, text=f"{icon} {label}", font=("Segoe UI", 9),
                  foreground="#888888").pack(anchor=tk.W)
        ttkb.Label(frame, text=value, font=("Segoe UI", 18, "bold"),
                  foreground=color).pack(anchor=tk.W)
    
    def export_history(self):
        """Export application history to CSV"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export History"
            )
            if file_path:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Job Title", "Company", "Location", "Status", "AI Score"])
                    for item in self.history_tree.get_children():
                        values = self.history_tree.item(item)['values']
                        writer.writerow(values[:6])
                self.show_toast(f"Exported to {os.path.basename(file_path)}", "success")
                self.activity_feed.add_activity("History exported to CSV", "success")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
    
    def show_analytics(self):
        """Show Analytics Dashboard with charts and insights"""
        self.clear_main_panel()
        
        main_container = ttkb.Frame(self.main_panel)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Header
        header = ttkb.Frame(main_container)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttkb.Label(header, text="📊 Analytics & Insights", 
                  font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        
        ttkb.Button(header, text="📥 Export Report", bootstyle="success-outline",
                   command=self._export_analytics_report).pack(side=tk.RIGHT)
        
        # Main content - Two columns
        content = ttkb.Frame(main_container)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        
        # ===== TOP LEFT: Application Status Breakdown =====
        status_frame = ttkb.Labelframe(content, text="📈 Application Status", bootstyle="info")
        status_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        
        status_inner = ttkb.Frame(status_frame)
        status_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create pie chart using matplotlib
        try:
            fig = Figure(figsize=(4, 3), dpi=100, facecolor='#1a1a2e')
            ax = fig.add_subplot(111)
            ax.set_facecolor('#1a1a2e')
            
            total = self.applied_count + self.failed_count + self.skipped_count
            if total > 0:
                sizes = [self.applied_count, self.failed_count, self.skipped_count]
                labels = ['Applied', 'Failed', 'Skipped']
                colors = ['#4ade80', '#ff6b6b', '#fbbf24']
                explode = (0.05, 0, 0)
                
                ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                      autopct='%1.1f%%', shadow=True, startangle=90,
                      textprops={'color': 'white', 'fontsize': 9})
            else:
                ax.text(0.5, 0.5, 'No data yet', ha='center', va='center',
                       fontsize=12, color='#888888')
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
            
            ax.axis('equal')
            
            canvas = FigureCanvasTkAgg(fig, status_inner)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            ttkb.Label(status_inner, text=f"Chart error: {e}", foreground="#ff6b6b").pack()
        
        # ===== TOP RIGHT: Performance Metrics =====
        perf_frame = ttkb.Labelframe(content, text="🎯 Performance Metrics", bootstyle="success")
        perf_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        
        perf_inner = ttkb.Frame(perf_frame)
        perf_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Metrics list
        metrics_data = [
            ("📊 Total Jobs Processed", str(self.job_count), "#3498db"),
            ("✅ Applications Submitted", str(self.applied_count), "#4ade80"),
            ("❌ Applications Failed", str(self.failed_count), "#ff6b6b"),
            ("⏭️ Jobs Skipped", str(self.skipped_count), "#fbbf24"),
            ("📈 Success Rate", f"{(self.applied_count / max(1, self.applied_count + self.failed_count) * 100):.1f}%", "#9b59b6"),
            ("⏱️ Avg Time/Application", "~45 sec", "#17a2b8"),
            ("🤖 AI Analyses Run", str(self.job_count), "#e94560"),
        ]
        
        for label, value, color in metrics_data:
            row = ttkb.Frame(perf_inner)
            row.pack(fill=tk.X, pady=5)
            ttkb.Label(row, text=label, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            ttkb.Label(row, text=value, font=("Segoe UI", 11, "bold"), 
                      foreground=color).pack(side=tk.RIGHT)
        
        # ===== BOTTOM LEFT: AI Processing Stats =====
        ai_frame = ttkb.Labelframe(content, text="🤖 AI Processing Statistics", bootstyle="primary")
        ai_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        
        ai_inner = ttkb.Frame(ai_frame)
        ai_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ai_stats = [
            ("JD Analyses Completed", str(metrics.get_metrics().get('jd_analysis_count', 0))),
            ("Resume Tailoring Runs", str(metrics.get_metrics().get('resume_tailoring_count', 0))),
            ("Avg JD Analysis Time", f"{metrics.get_metrics().get('jd_analysis_avg', 0):.2f}s"),
            ("Avg Resume Tailor Time", f"{metrics.get_metrics().get('resume_tailoring_avg', 0):.2f}s"),
            (LBL_AI_PROVIDER, str(ai_provider).upper()),
        ]
        
        for label, value in ai_stats:
            row = ttkb.Frame(ai_inner)
            row.pack(fill=tk.X, pady=5)
            ttkb.Label(row, text=label, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            ttkb.Label(row, text=value, font=("Segoe UI", 10, "bold"),
                      foreground="#00d26a").pack(side=tk.RIGHT)
        
        # ===== BOTTOM RIGHT: Session Info =====
        session_frame = ttkb.Labelframe(content, text="📅 Session Information", bootstyle="warning")
        session_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))
        
        session_inner = ttkb.Frame(session_frame)
        session_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Runtime
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            runtime = str(elapsed).split('.')[0]
        else:
            runtime = "Not started"
        
        session_info = [
            ("Session Status", self.current_status),
            ("Started At", self.start_time.strftime("%H:%M:%S") if self.start_time else "N/A"),
            ("Runtime", runtime),
            ("Jobs/Hour", f"{self.job_count / max(1, (datetime.now() - (self.start_time or datetime.now())).total_seconds() / 3600):.1f}" if self.start_time else "N/A"),
            ("Current Date", datetime.now().strftime("%Y-%m-%d")),
        ]
        
        for label, value in session_info:
            row = ttkb.Frame(session_inner)
            row.pack(fill=tk.X, pady=5)
            ttkb.Label(row, text=label, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            ttkb.Label(row, text=value, font=("Segoe UI", 10, "bold"),
                      foreground="#fbbf24").pack(side=tk.RIGHT)
    
    def _export_analytics_report(self):
        """Export analytics report to JSON file."""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Analytics Report",
                initialfile=f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if file_path:
                import json
                
                runtime = "N/A"
                if self.start_time:
                    elapsed = datetime.now() - self.start_time
                    hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    runtime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                report = {
                    "report_generated": datetime.now().isoformat(),
                    "session": {
                        "status": self.current_status,
                        "start_time": self.start_time.isoformat() if self.start_time else None,
                        "runtime": runtime,
                    },
                    "metrics": {
                        "total_jobs_processed": self.job_count,
                        "applications_submitted": self.applied_count,
                        "applications_failed": self.failed_count,
                        "jobs_skipped": self.skipped_count,
                        "success_rate": f"{(self.applied_count / max(1, self.applied_count + self.failed_count) * 100):.1f}%",
                    },
                    "performance": {
                        "jobs_per_hour": f"{self.job_count / max(1, (datetime.now() - (self.start_time or datetime.now())).total_seconds() / 3600):.1f}" if self.start_time else "N/A",
                    }
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2)
                
                self.show_toast("Analytics report exported!", "success")
                self.activity_feed.add_activity("Analytics report exported", "success")
        except Exception as e:
            self.show_toast(f"Export failed: {e}", "error")

    def show_settings(self):
        """Show Settings with modern UI"""
        self.clear_main_panel()
        
        main_container = ttkb.Frame(self.main_panel)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Header
        ttkb.Label(main_container, text="⚙️ Settings & Configuration", 
                  font=("Segoe UI", 16, "bold")).pack(anchor=tk.W, pady=(0, 12))
        
        # Settings sections in scrollable frame
        settings_frame = ttkb.Frame(main_container)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # AI Configuration
        ai_frame = ttkb.Labelframe(settings_frame, text="🤖 AI Configuration", bootstyle="info")
        ai_frame.pack(fill=tk.X, pady=(0, 15))
        
        ai_inner = ttkb.Frame(ai_frame)
        ai_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Provider row
        prov_row = ttkb.Frame(ai_inner)
        prov_row.pack(fill=tk.X, pady=5)
        ttkb.Label(prov_row, text="AI Provider:", width=15, anchor=tk.W).pack(side=tk.LEFT)
        ttkb.Label(prov_row, text=ai_provider.upper(), 
                  font=("Segoe UI", 10, "bold"), foreground="#00d26a").pack(side=tk.LEFT)
        ttkb.Button(prov_row, text="⚙️ Configure", bootstyle="info-outline",
                   command=self._open_api_config).pack(side=tk.RIGHT)
        
        # Application Settings
        app_frame = ttkb.Labelframe(settings_frame, text="📋 Application Settings", bootstyle="warning")
        app_frame.pack(fill=tk.X, pady=(0, 15))
        
        app_inner = ttkb.Frame(app_frame)
        app_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Settings toggles - WIRED to actual config.settings
        # Load current values from settings
        try:
            from config import settings as cfg
            auto_apply_val = getattr(cfg, 'run_non_stop', True)
            tailor_val = getattr(cfg, 'resume_tailoring_enabled', True)
            skip_ext_val = getattr(cfg, 'close_tabs', False)
        except Exception:
            auto_apply_val, tailor_val, skip_ext_val = True, True, False
        
        self.settings_auto_apply_var = tk.BooleanVar(value=auto_apply_val)
        auto_cb = ttkb.Checkbutton(app_inner, text="Auto-apply to Easy Apply jobs (run_non_stop)",
                        variable=self.settings_auto_apply_var, bootstyle="success-round-toggle",
                        command=self._apply_settings_tab_change)
        auto_cb.pack(anchor=tk.W, pady=3)
        
        self.settings_tailor_resume_var = tk.BooleanVar(value=tailor_val)
        tailor_cb = ttkb.Checkbutton(app_inner, text="Auto-tailor resume for each job",
                        variable=self.settings_tailor_resume_var, bootstyle="success-round-toggle",
                        command=self._apply_settings_tab_change)
        tailor_cb.pack(anchor=tk.W, pady=3)
        
        self.settings_skip_external_var = tk.BooleanVar(value=skip_ext_val)
        skip_cb = ttkb.Checkbutton(app_inner, text="Close external application tabs",
                        variable=self.settings_skip_external_var, bootstyle="warning-round-toggle",
                        command=self._apply_settings_tab_change)
        skip_cb.pack(anchor=tk.W, pady=3)
        
        # Restart warning
        warn_frame = ttkb.Frame(app_inner)
        warn_frame.pack(fill=tk.X, pady=(10, 0))
        ttkb.Label(warn_frame, text="⚠️ Changes apply immediately to runtime but require bot restart to take full effect",
                  font=("Segoe UI", 9), foreground="#f59e0b").pack(anchor=tk.W)
        
        # File paths
        paths_frame = ttkb.Labelframe(settings_frame, text="📁 File Paths", bootstyle="secondary")
        paths_frame.pack(fill=tk.X)
        
        paths_inner = ttkb.Frame(paths_frame)
        paths_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ttkb.Button(paths_inner, text="📂 Open Logs Folder",
                   command=lambda: webbrowser.open(f'file:///{os.path.abspath("logs")}'),
                   bootstyle="secondary-outline").pack(side=tk.LEFT, padx=(0, 10))
        ttkb.Button(paths_inner, text="📂 Open Resumes Folder",
                   command=lambda: webbrowser.open(f'file:///{os.path.abspath("all resumes")}'),
                   bootstyle="secondary-outline").pack(side=tk.LEFT)
    
    def _apply_settings_tab_change(self):
        """Apply Settings tab toggle changes to config.settings immediately."""
        try:
            from config import settings as cfg
            
            # Apply changes to runtime config
            if hasattr(self, 'settings_auto_apply_var'):
                cfg.run_non_stop = self.settings_auto_apply_var.get()
            if hasattr(self, 'settings_tailor_resume_var'):
                cfg.resume_tailoring_enabled = self.settings_tailor_resume_var.get()
            if hasattr(self, 'settings_skip_external_var'):
                cfg.close_tabs = self.settings_skip_external_var.get()
            
            self.show_toast("✅ Setting applied to runtime", "success")
        except Exception as e:
            self.show_toast(f"⚠️ Failed: {str(e)[:30]}", "warning")
    
    def _open_api_config(self):
        """Open API configuration dialog"""
        from modules.dashboard.api_config_dialog import open_api_config_dialog
        open_api_config_dialog(self)

    def show_help(self):
        """Show Help with modern UI"""
        self.clear_main_panel()
        
        main_container = ttkb.Frame(self.main_panel)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Header
        ttkb.Label(main_container, text="❓ Help & Documentation", 
                  font=("Segoe UI", 16, "bold")).pack(anchor=tk.W, pady=(0, 12))
        
        # Quick links
        links_frame = ttkb.Labelframe(main_container, text="🔗 Quick Links", bootstyle="info")
        links_frame.pack(fill=tk.X, pady=(0, 15))
        
        links_inner = ttkb.Frame(links_frame)
        links_inner.pack(fill=tk.X, padx=10, pady=10)
        
        links = [
            ("📖 README Documentation", "README.md"),
            ("✨ Enhanced Resume Guide", "ENHANCED_RESUME_QUICK_START.md"),
            ("🔒 Security Setup", "SECURITY_SETUP.md"),
            ("📋 Changelog", "CHANGELOG_ENHANCED_RESUME.md"),
        ]
        
        for text, file in links:
            btn = ttkb.Button(links_inner, text=text, bootstyle="info-outline", width=30,
                             command=lambda f=file: webbrowser.open(f))
            btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Keyboard shortcuts
        shortcuts_frame = ttkb.Labelframe(main_container, text="⌨️ Keyboard Shortcuts", bootstyle="warning")
        shortcuts_frame.pack(fill=tk.X, pady=(0, 15))
        
        shortcuts_inner = ttkb.Frame(shortcuts_frame)
        shortcuts_inner.pack(fill=tk.X, padx=10, pady=10)
        
        shortcuts = [
            ("Alt + 1", "Go to Dashboard"),
            ("Alt + 2", "Go to Resume Tailor"),
            ("Alt + 3", "Go to History"),
            ("Alt + 4", "Go to Settings"),
            ("Alt + 5", "Go to Help"),
        ]
        
        for key, desc in shortcuts:
            row = ttkb.Frame(shortcuts_inner)
            row.pack(fill=tk.X, pady=2)
            ttkb.Label(row, text=key, font=("Consolas", 10, "bold"), width=10).pack(side=tk.LEFT)
            ttkb.Label(row, text=desc, font=("Segoe UI", 10), foreground="#aaaaaa").pack(side=tk.LEFT)
        
        # About section
        about_frame = ttkb.Labelframe(main_container, text="ℹ️ About", bootstyle="secondary")
        about_frame.pack(fill=tk.X)
        
        about_inner = ttkb.Frame(about_frame)
        about_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ttkb.Label(about_inner, text="🤖 AI Job Hunter Pro", 
                  font=("Segoe UI", 14, "bold")).pack(anchor=tk.W)
        ttkb.Label(about_inner, text="Automated LinkedIn Job Application System", 
                  font=("Segoe UI", 10), foreground="#888888").pack(anchor=tk.W, pady=(5, 10))
        ttkb.Label(about_inner, text="Version 2.0 | Built with ❤️ by Suraj Panwar", 
                  font=("Segoe UI", 9), foreground="#666666").pack(anchor=tk.W)
    
    # NOTE: Dead code block removed (create_top_bar, create_stat_cards, create_tabs_section,
    # create_statistics_tab, create_jobs_tab, create_settings_tab, create_right_panel,
    # _create_live_logs_tab, _create_job_details_tab, _create_analytics_tab,
    # _create_settings_tab [old], _get_ollama_models, _refresh_ollama_models,
    # _update_ollama_ui, _update_model_info, _on_ollama_model_select, _on_provider_change,
    # _test_ollama_connection, _test_cloud_api, _pull_ollama_model, _load_llm_settings,
    # _save_llm_settings, _reset_llm_settings, _create_resume_tab, _create_activity_tab)
    # These 14+ methods (~1236 lines) were dead code from old layout, replaced by
    # _create_modern_layout/show_dashboard/show_settings/show_analytics/etc.
    
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
    
    # NOTE: _save_quick_settings is defined later in the class (around line 3851)
    # It actually writes to config.settings module for immediate effect
    
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
        except Exception:
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
        """Create the bottom status bar with prominent Live Monitor button"""
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
        
        # ===== PROMINENT LIVE MONITOR BUTTON IN STATUS BAR =====
        monitor_btn_frame = ttkb.Frame(status_bar)
        monitor_btn_frame.pack(side=tk.LEFT, padx=20)
        
        self.status_bar_monitor_btn = AnimatedButton(
            monitor_btn_frame, 
            text="📺 SIDE PANEL", 
            command=self.toggle_side_panel_mode,
            bootstyle="success",
            width=22,
            padding=(10, 5)
        )
        self.status_bar_monitor_btn.pack(side=tk.LEFT)
        
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
    
    def _toggle_sidebar_expand(self):
        """Toggle sidebar between collapsed (icons) and expanded (icons + labels) mode"""
        if not hasattr(self, 'sidebar') or not hasattr(self, 'sidebar_toggle'):
            return  # Sidebar not created in current layout
        if not self.sidebar_expanded:
            # Expand sidebar
            self.sidebar_expanded = True
            self.sidebar_toggle.config(text="✕")
            self.sidebar.configure(width=180)
            # Show labels next to icons
            for lbl in self.sidebar_labels:
                lbl.pack(side=tk.LEFT, padx=(5, 0))
        else:
            # Collapse sidebar
            self.sidebar_expanded = False
            self.sidebar_toggle.config(text="☰")
            self.sidebar.configure(width=70)
            # Hide labels
            for lbl in self.sidebar_labels:
                lbl.pack_forget()
    
    def _update_time(self):
        """Update the time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"🕐 {current_time}")
        
        # Update runtime if bot is running
        if self.start_time and self.current_status == "Running":
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hasattr(self, 'runtime_label'):
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
        tools_menu.add_command(label="✨ Resume Tailor (Enhanced)", command=self.open_resume_tailor_dialog)
        tools_menu.add_command(label="📝 Resume Tailor (Classic)", command=self.open_classic_resume_tailor)
        tools_menu.add_separator()
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
        if not hasattr(self, 'paned_window') or not hasattr(self, 'right_panel_frame'):
            return  # Right panel not created in current layout
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
            self.side_panel_btn.config(text="❌ Close Panel", bootstyle="danger")
            if hasattr(self, 'side_panel_help'):
                self.side_panel_help.config(text="(Panel Open)")
            
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
        
        # ===== NEXT STEP SECTION (NEW!) =====
        next_frame = ttkb.Frame(main_frame)
        next_frame.pack(fill=tk.X, pady=(0, 8))
        
        next_header = ttkb.Frame(next_frame)
        next_header.pack(fill=tk.X)
        ttkb.Label(next_header, text="➡️ NEXT STEP:", 
                  font=("Segoe UI", 9, "bold"), foreground="#00d26a").pack(side=tk.LEFT)
        
        self.sp_next_step = ttkb.Label(next_frame, text="⏳ Waiting for bot to start...",
                                       font=("Segoe UI", 10, "bold"),
                                       foreground="#fbbf24",
                                       wraplength=300)
        self.sp_next_step.pack(anchor=tk.W, pady=(3, 0))
        
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
            # Update stats (guard each attribute)
            if hasattr(self, 'sp_jobs_val'):
                self.sp_jobs_val.config(text=str(self.job_count))
            if hasattr(self, 'sp_applied_val'):
                self.sp_applied_val.config(text=str(self.applied_count))
            if hasattr(self, 'sp_failed_val'):
                self.sp_failed_val.config(text=str(self.failed_count))
            if hasattr(self, 'sp_skipped_val'):
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
                
                # JD Analysis Progress (REAL-TIME!)
                jd_pct = int(_m.get_metric('jd_progress', 0))
                self.sp_jd_progress.config(value=jd_pct)
                if jd_pct == 0:
                    self.sp_jd_status.config(text="Idle", foreground="#888888")
                elif jd_pct < 100:
                    self.sp_jd_status.config(text=f"Analyzing... {jd_pct}%", foreground="#60a5fa")
                else:
                    self.sp_jd_status.config(text="✓ Done", foreground="#4ade80")
                
                # Resume Tailoring Progress (REAL-TIME!)
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
            
            # Update "Next Step" from log messages
            if hasattr(self, '_last_next_step'):
                if hasattr(self, 'sp_next_step'):
                    self.sp_next_step.config(text=self._last_next_step)
            
            # Schedule next update (faster for real-time progress)
            self.side_panel_window.after(300, self._update_side_panel)
            
        except tk.TclError:
            # Window was closed
            self.side_panel_mode = False
    
    def _add_side_panel_log(self, msg: str, level: str = "info"):
        """Add a log entry to the side panel"""
        if not self.side_panel_mode or not hasattr(self, 'sp_log_text'):
            return
        
        try:
            # Check if this is a "NEXT" step message and update the next step display
            if "[NEXT]" in msg or "➡️ NEXT:" in msg:
                # Extract the next step text
                next_text = msg.replace("[NEXT]", "").replace("➡️ NEXT:", "").strip()
                self._last_next_step = f"➡️ {next_text}"
                if hasattr(self, 'sp_next_step'):
                    self.sp_next_step.config(text=self._last_next_step, foreground="#00d26a")
            
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
        self.side_panel_btn.config(text="📌 Side Panel", bootstyle="info")
        if hasattr(self, 'side_panel_help'):
            self.side_panel_help.config(text="(Live Monitor)")
        
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
            
            # Start periodic health monitoring
            self._start_bot_health_monitor()
            
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
            
            # Stop health monitor first
            self._stop_bot_health_monitor()
            
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
            
            self._reset_ui_to_stopped()
            
            self._log_with_timestamp("✅ Bot stopped completely - all processes killed!", "success")
            self.activity_feed.add_activity("Bot stopped completely", "success")
            
        except Exception as e:
            self._log_with_timestamp(f"❌ Error stopping bot: {str(e)}", "error")
            self.activity_feed.add_activity(f"Stop error: {str(e)}", "error")
            # Re-enable start button even on error
            self._reset_ui_to_stopped()
            messagebox.showerror("Stop Failed", str(e))
    
    def _start_bot_health_monitor(self):
        """Start periodic monitoring of bot thread health."""
        self._health_monitor_active = True
        self._check_bot_health()
    
    def _stop_bot_health_monitor(self):
        """Stop the health monitor."""
        self._health_monitor_active = False
    
    def _check_bot_health(self):
        """Periodically check if bot thread is still alive and sync UI state."""
        if not getattr(self, '_health_monitor_active', False):
            return
        
        try:
            is_running = self.controller.is_running()
            
            # Bot thread died unexpectedly while UI still shows Running/Paused
            if not is_running and self.current_status in ("Running", "Paused"):
                self._log_with_timestamp("⚠️ Bot thread has stopped unexpectedly", "warning")
                self.activity_feed.add_activity("Bot thread stopped", "warning")
                self._reset_ui_to_stopped()
                self._health_monitor_active = False
                return
        except Exception:
            pass
        
        # Schedule next check in 2 seconds
        if self._health_monitor_active:
            self.after(2000, self._check_bot_health)
    
    def _reset_ui_to_stopped(self):
        """Reset all UI elements to stopped state."""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.DISABLED)
        self.pause_btn.config(text="⏸️ Pause")
        self.status_label.config(text="STOPPED")
        self.status_indicator.config(foreground=COLORS['danger'])
        self.current_status = "Stopped"
    
    def toggle_pause(self):
        """Toggle pause state of the bot."""
        if self.current_status != "Running" and self.current_status != "Paused":
            messagebox.showinfo("Info", "Bot is not running.")
            return
        
        # Verify bot thread is actually alive before toggling
        if not self.controller.is_running():
            self._log_with_timestamp("⚠️ Bot thread is no longer running", "warning")
            self._reset_ui_to_stopped()
            return
        
        try:
            is_paused = self.controller.pause()
            
            if is_paused:
                self.status_label.config(text="PAUSED")
                self.status_indicator.config(foreground=COLORS['warning'])
                self.current_status = "Paused"
                self.pause_btn.config(text="▶️ Resume")
                self._log_with_timestamp("⏸️ Bot paused", "warning")
                self.activity_feed.add_activity("Bot paused", "warning")
            else:
                self.status_label.config(text="RUNNING")
                self.status_indicator.config(foreground=COLORS['success'])
                self.current_status = "Running"
                self.pause_btn.config(text="⏸️ Pause")
                self._log_with_timestamp("▶️ Bot resumed", "success")
                self.activity_feed.add_activity("Bot resumed", "success")
                
        except Exception as e:
            self._log_with_timestamp(f"❌ Pause error: {str(e)}", "error")
            messagebox.showwarning("Pause Error", f"Could not toggle pause: {e}")
    
    def skip_current_job(self):
        """Skip the current job being processed"""
        if self.current_status != "Running":
            messagebox.showinfo("Info", "Bot is not currently processing a job.")
            return
        
        try:
            self._log_with_timestamp("⏭️ Skipping current job...", "warning")
            self.activity_feed.add_activity("Skipping current job", "warning")
            
            # Increment skipped count
            self.skipped_count += 1
            self._update_dashboard_stats()
            
            # Signal the controller to skip (if implemented)
            if hasattr(self.controller, 'skip_current_job'):
                self.controller.skip_current_job()
            
            self._log_with_timestamp("✅ Job skipped - moving to next", "success")
            self.activity_feed.add_activity("Job skipped successfully", "success")
        except Exception as e:
            self._log_with_timestamp(f"❌ Error skipping job: {str(e)}", "error")
            self.activity_feed.add_activity(f"Skip failed: {str(e)}", "error")

    def _log_with_timestamp(self, message, msg_type="info"):
        """Add a log message with timestamp and color coding"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", msg_type)
        self.log_text.see(tk.END)
    
    # ========== Menu Actions ==========
    
    def open_resume_tailor_dialog(self):
        """Open resume tailor dialog - now with enhanced version as default."""
        try:
            # Use the enhanced version with diff highlighting and skill suggestions
            open_enhanced_resume_tailor_dialog(self, ai_provider, user_information_all)
        except Exception as e:
            # Fallback to original version if enhanced fails
            print(f"Enhanced dialog failed, using standard version: {e}")
            ResumeTailorDialog(self, ai_provider, user_information_all)
    
    def open_classic_resume_tailor(self):
        """Open the classic resume tailor dialog."""
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
        """Export statistics to a JSON file."""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Statistics"
            )
            if file_path:
                import json
                stats = {
                    "export_date": datetime.now().isoformat(),
                    "session_stats": {
                        "applied_count": self.applied_count,
                        "failed_count": self.failed_count,
                        "success_rate": f"{(self.applied_count / max(self.applied_count + self.skipped_count, 1)) * 100:.1f}%",
                        "skipped_count": self.skipped_count,
                    },
                    "current_status": self.current_status,
                    "start_time": self.start_time.isoformat() if self.start_time else None,
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, indent=2)
                messagebox.showinfo("Success", f"Statistics exported to {file_path}")
                self.activity_feed.add_activity("Statistics exported", "success")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def export_jobs_csv(self):
        """Export job application history to CSV."""
        try:
            # Check if history files exist
            history_file = os.path.join("all excels", "all_applied_applications_history.csv")
            if os.path.exists(history_file):
                # Open file dialog to choose where to save
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    title="Export Job History",
                    initialfile=f"job_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                if file_path:
                    import shutil
                    shutil.copy2(history_file, file_path)
                    messagebox.showinfo("Success", f"Job history exported to {file_path}")
                    self.activity_feed.add_activity("Job history exported", "success")
            else:
                messagebox.showinfo("Info", "No job history file found. Run the bot first to generate application history.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)
        if hasattr(self, 'ai_output'):
            self.ai_output.delete("1.0", tk.END)
        self.activity_feed.add_activity("Logs cleared", "info")
    
    def manual_refresh(self):
        self._refresh_metrics()
        self.activity_feed.add_activity(LBL_DASHBOARD_REFRESHED, "info")
    
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
        """Handle new log message - schedule on main thread for Tkinter safety."""
        try:
            self.root.after_idle(self._process_log_message, msg)
        except Exception:
            # Fallback if root is not available
            self._process_log_message(msg)
    
    def _process_log_message(self, msg: str):
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
                self.add_timeline_event("✅ Applied to job")
            except Exception:
                pass
        elif "failed" in msg_lower or "error" in msg_lower:
            self.failed_count += 1
            self.activity_feed.add_activity("Job application failed", "error")
            try:
                self.add_timeline_event("❌ Application failed")
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
        # Update stat cards (guarded - may not exist in all layouts)
        if hasattr(self, 'jobs_card'):
            self.jobs_card.set_value(self.job_count)
        if hasattr(self, 'applied_card'):
            self.applied_card.set_value(self.applied_count)
        if hasattr(self, 'failed_card'):
            self.failed_card.set_value(self.failed_count)
        if hasattr(self, 'skipped_card'):
            self.skipped_card.set_value(self.skipped_count)
        
        # Calculate success rate
        total = self.applied_count + self.failed_count
        if total > 0:
            rate = round((self.applied_count / total) * 100, 1)
            if hasattr(self, 'rate_card'):
                self.rate_card.set_value(f"{rate}%")
            if hasattr(self, 'progress_circle') and self.progress_circle:
                self.progress_circle.set_progress(rate)
        else:
            if hasattr(self, 'rate_card'):
                self.rate_card.set_value("0%")
            if hasattr(self, 'progress_circle') and self.progress_circle:
                self.progress_circle.set_progress(0)
        
        # Update status bar
        self.quick_stats_label.config(
            text=f"📊 Jobs: {self.job_count} | ✅ Applied: {self.applied_count} | "
                 f"❌ Failed: {self.failed_count} | ⏭️ Skipped: {self.skipped_count}"
        )
    
    # ============================================
    # QUICK SETTINGS PANEL HELPER METHODS
    # ============================================
    def _init_quick_settings_vars(self):
        """Initialize ALL Settings variables with current config values."""
        try:
            from config import settings
            
            # ===== Bot Behavior Settings =====
            self.qs_run_non_stop = tk.BooleanVar(value=getattr(settings, 'run_non_stop', True))
            self.qs_alternate_sortby = tk.BooleanVar(value=getattr(settings, 'alternate_sortby', True))
            self.qs_cycle_date_posted = tk.BooleanVar(value=getattr(settings, 'cycle_date_posted', True))
            self.qs_stop_date_24hr = tk.BooleanVar(value=getattr(settings, 'stop_date_cycle_at_24hr', True))
            self.qs_close_tabs = tk.BooleanVar(value=getattr(settings, 'close_tabs', False))
            self.qs_follow_companies = tk.BooleanVar(value=getattr(settings, 'follow_companies', False))
            self.qs_max_jobs = tk.IntVar(value=getattr(settings, 'max_jobs_to_process', 0))
            self.qs_click_gap = tk.IntVar(value=getattr(settings, 'click_gap', 20))
            
            # ===== Form Filling Settings =====
            self.qs_fast_mode = tk.BooleanVar(value=getattr(settings, 'form_fill_fast_mode', True))
            self.qs_smart_form_filler = tk.BooleanVar(value=getattr(settings, 'use_smart_form_filler', True))
            self.qs_delay_multiplier = tk.DoubleVar(value=getattr(settings, 'form_fill_delay_multiplier', 0.5))
            
            # ===== Resume Tailoring Settings =====
            self.qs_resume_tailor = tk.BooleanVar(value=getattr(settings, 'resume_tailoring_enabled', True))
            self.qs_tailor_confirm_filters = tk.BooleanVar(value=getattr(settings, 'resume_tailoring_confirm_after_filters', True))
            self.qs_tailor_prompt_jd = tk.BooleanVar(value=getattr(settings, 'resume_tailoring_prompt_before_jd', True))
            # Resume upload format: "auto", "pdf", "docx"
            format_val = getattr(settings, 'resume_upload_format', 'auto')
            format_display = {"auto": RESUME_AUTO, "pdf": RESUME_PDF, "docx": RESUME_DOCX}.get(format_val, RESUME_AUTO)
            self.qs_resume_upload_format = tk.StringVar(value=format_display)
            
            # ===== Browser & UI Settings =====
            self.qs_show_browser = tk.BooleanVar(value=not getattr(settings, 'run_in_background', False))
            self.qs_disable_extensions = tk.BooleanVar(value=getattr(settings, 'disable_extensions', False))
            self.qs_safe_mode = tk.BooleanVar(value=getattr(settings, 'safe_mode', True))
            self.qs_smooth_scroll = tk.BooleanVar(value=getattr(settings, 'smooth_scroll', True))
            self.qs_keep_awake = tk.BooleanVar(value=getattr(settings, 'keep_screen_awake', True))
            self.qs_stealth_mode = tk.BooleanVar(value=getattr(settings, 'stealth_mode', False))
            
            # ===== Control & Alerts Settings =====
            self.qs_pause_submit = tk.BooleanVar(value=getattr(settings, 'pause_before_submit', False))
            self.qs_pause_failed_q = tk.BooleanVar(value=getattr(settings, 'pause_at_failed_question', False))
            self.qs_show_ai_errors = tk.BooleanVar(value=getattr(settings, 'showAiErrorAlerts', False))
            
            # ===== PILOT MODE Settings =====
            self.qs_pilot_mode = tk.BooleanVar(value=getattr(settings, 'pilot_mode_enabled', False))
            self.qs_pilot_resume_mode = tk.StringVar(value=getattr(settings, 'pilot_resume_mode', 'tailored'))
            self.qs_pilot_max_apps = tk.IntVar(value=getattr(settings, 'pilot_max_applications', 0))
            self.qs_pilot_delay = tk.IntVar(value=getattr(settings, 'pilot_application_delay', 5))
            self.qs_pilot_continue_error = tk.BooleanVar(value=getattr(settings, 'pilot_continue_on_error', True))
            
            # ===== AUTOPILOT FORM PRE-FILL SETTINGS =====
            # These are used when autopilot encounters common form questions
            self.qs_autopilot_visa_required = tk.StringVar(value=getattr(settings, 'autopilot_visa_required', 'Yes'))
            self.qs_autopilot_willing_relocate = tk.StringVar(value=getattr(settings, 'autopilot_willing_relocate', 'Yes'))
            self.qs_autopilot_work_authorization = tk.StringVar(value=getattr(settings, 'autopilot_work_authorization', 'Yes'))
            self.qs_autopilot_remote_preference = tk.StringVar(value=getattr(settings, 'autopilot_remote_preference', 'Yes'))
            self.qs_autopilot_start_immediately = tk.StringVar(value=getattr(settings, 'autopilot_start_immediately', 'Yes'))
            self.qs_autopilot_background_check = tk.StringVar(value=getattr(settings, 'autopilot_background_check', 'Yes'))
            self.qs_autopilot_commute_ok = tk.StringVar(value=getattr(settings, 'autopilot_commute_ok', 'Yes'))
            self.qs_autopilot_chrome_wait_time = tk.IntVar(value=getattr(settings, 'autopilot_chrome_wait_time', 10))
            
            # ===== SCHEDULING Settings =====
            self.qs_schedule_enabled = tk.BooleanVar(value=getattr(settings, 'scheduling_enabled', False))
            self.qs_schedule_type = tk.StringVar(value=getattr(settings, 'schedule_type', 'interval'))
            self.qs_schedule_interval = tk.IntVar(value=getattr(settings, 'schedule_interval_hours', 4))
            self.qs_schedule_max_runtime = tk.IntVar(value=getattr(settings, 'schedule_max_runtime', 120))
            self.qs_schedule_max_apps = tk.IntVar(value=getattr(settings, 'schedule_max_applications', 50))
            
            # ===== JOB SEARCH Settings =====
            try:
                from config import search as search_config
                # Load search terms as comma-separated string for easy editing
                search_terms_list = getattr(search_config, 'search_terms', [])
                self.qs_search_terms = tk.StringVar(value=', '.join(search_terms_list))
                self.qs_search_location = tk.StringVar(value=getattr(search_config, 'search_location', 'United States'))
                self.qs_date_posted = tk.StringVar(value=getattr(search_config, 'date_posted', 'Past 24 hours'))
                self.qs_easy_apply_only = tk.BooleanVar(value=getattr(search_config, 'easy_apply_only', True))
                self.qs_switch_number = tk.IntVar(value=getattr(search_config, 'switch_number', 30))
                self.qs_randomize_search = tk.BooleanVar(value=getattr(search_config, 'randomize_search_order', False))
                # Job search mode: "sequential", "random", "single" (apply to one job title until limit)
                self.qs_job_search_mode = tk.StringVar(value=getattr(settings, 'job_search_mode', 'sequential'))
                self.qs_current_experience = tk.IntVar(value=getattr(search_config, 'current_experience', 5))
            except Exception as search_err:
                print(f"[Dashboard] Search config load warning: {search_err}")
                self.qs_search_terms = tk.StringVar(value='Software Engineer, Python Developer')
                self.qs_search_location = tk.StringVar(value='United States')
                self.qs_date_posted = tk.StringVar(value='Past 24 hours')
                self.qs_easy_apply_only = tk.BooleanVar(value=True)
                self.qs_switch_number = tk.IntVar(value=30)
                self.qs_randomize_search = tk.BooleanVar(value=False)
                self.qs_job_search_mode = tk.StringVar(value='sequential')
                self.qs_current_experience = tk.IntVar(value=5)
            
            # ===== EXTENSION Settings =====
            self.qs_extension_enabled = tk.BooleanVar(value=getattr(settings, 'extension_enabled', True))
            self.qs_extension_auto_sync = tk.BooleanVar(value=getattr(settings, 'extension_auto_sync', True))
            self.qs_extension_ai_learning = tk.BooleanVar(value=getattr(settings, 'extension_ai_learning', True))
            mode_val = getattr(settings, 'extension_detection_mode', 'universal')
            mode_display = {"linkedin": DETECT_LINKEDIN, "universal": DETECT_UNIVERSAL, "smart": DETECT_SMART}.get(mode_val, DETECT_UNIVERSAL)
            self.qs_extension_detection_mode = tk.StringVar(value=mode_display)
            
        except Exception as e:
            # Default fallback values for ALL settings
            self.qs_run_non_stop = tk.BooleanVar(value=True)
            self.qs_alternate_sortby = tk.BooleanVar(value=True)
            self.qs_cycle_date_posted = tk.BooleanVar(value=True)
            self.qs_stop_date_24hr = tk.BooleanVar(value=True)
            self.qs_close_tabs = tk.BooleanVar(value=False)
            self.qs_follow_companies = tk.BooleanVar(value=False)
            self.qs_max_jobs = tk.IntVar(value=0)
            self.qs_click_gap = tk.IntVar(value=20)
            self.qs_fast_mode = tk.BooleanVar(value=True)
            self.qs_smart_form_filler = tk.BooleanVar(value=True)
            self.qs_delay_multiplier = tk.DoubleVar(value=0.5)
            self.qs_resume_tailor = tk.BooleanVar(value=True)
            self.qs_tailor_confirm_filters = tk.BooleanVar(value=True)
            self.qs_tailor_prompt_jd = tk.BooleanVar(value=True)
            self.qs_resume_upload_format = tk.StringVar(value=RESUME_AUTO)
            self.qs_show_browser = tk.BooleanVar(value=True)
            self.qs_disable_extensions = tk.BooleanVar(value=False)
            self.qs_safe_mode = tk.BooleanVar(value=True)
            self.qs_smooth_scroll = tk.BooleanVar(value=True)
            self.qs_keep_awake = tk.BooleanVar(value=True)
            self.qs_stealth_mode = tk.BooleanVar(value=False)
            self.qs_pause_submit = tk.BooleanVar(value=False)
            self.qs_pause_failed_q = tk.BooleanVar(value=False)
            self.qs_show_ai_errors = tk.BooleanVar(value=False)
            # Pilot Mode defaults
            self.qs_pilot_mode = tk.BooleanVar(value=False)
            self.qs_pilot_resume_mode = tk.StringVar(value='tailored')
            self.qs_pilot_max_apps = tk.IntVar(value=0)
            self.qs_pilot_delay = tk.IntVar(value=5)
            self.qs_pilot_continue_error = tk.BooleanVar(value=True)
            # Autopilot form pre-fill defaults
            self.qs_autopilot_visa_required = tk.StringVar(value='Yes')
            self.qs_autopilot_willing_relocate = tk.StringVar(value='Yes')
            self.qs_autopilot_work_authorization = tk.StringVar(value='Yes')
            self.qs_autopilot_remote_preference = tk.StringVar(value='Yes')
            self.qs_autopilot_start_immediately = tk.StringVar(value='Yes')
            self.qs_autopilot_background_check = tk.StringVar(value='Yes')
            self.qs_autopilot_commute_ok = tk.StringVar(value='Yes')
            self.qs_autopilot_chrome_wait_time = tk.IntVar(value=10)
            # Scheduling defaults
            self.qs_schedule_enabled = tk.BooleanVar(value=False)
            self.qs_schedule_type = tk.StringVar(value='interval')
            self.qs_schedule_interval = tk.IntVar(value=4)
            self.qs_schedule_max_runtime = tk.IntVar(value=120)
            self.qs_schedule_max_apps = tk.IntVar(value=50)
            # Extension defaults
            self.qs_extension_enabled = tk.BooleanVar(value=True)
            self.qs_extension_auto_sync = tk.BooleanVar(value=True)
            self.qs_extension_ai_learning = tk.BooleanVar(value=True)
            self.qs_extension_detection_mode = tk.StringVar(value=DETECT_UNIVERSAL)
            # Job Search defaults (missing from original fallback)
            self.qs_search_terms = tk.StringVar(value='Software Engineer, Python Developer')
            self.qs_search_location = tk.StringVar(value='United States')
            self.qs_date_posted = tk.StringVar(value='Past 24 hours')
            self.qs_easy_apply_only = tk.BooleanVar(value=True)
            self.qs_switch_number = tk.IntVar(value=30)
            self.qs_randomize_search = tk.BooleanVar(value=False)
            self.qs_job_search_mode = tk.StringVar(value='sequential')
            self.qs_current_experience = tk.IntVar(value=5)
            print(f"[Dashboard] Settings init warning: {e}")
    
    def _save_quick_settings(self):
        """Save ALL Settings to runtime config (immediate effect)."""
        try:
            from config import settings
            
            # ===== Bot Behavior Settings =====
            settings.run_non_stop = self.qs_run_non_stop.get()
            settings.alternate_sortby = self.qs_alternate_sortby.get()
            settings.cycle_date_posted = self.qs_cycle_date_posted.get()
            settings.stop_date_cycle_at_24hr = self.qs_stop_date_24hr.get()
            settings.close_tabs = self.qs_close_tabs.get()
            settings.follow_companies = self.qs_follow_companies.get()
            settings.max_jobs_to_process = self.qs_max_jobs.get()
            settings.click_gap = self.qs_click_gap.get()
            
            # ===== Form Filling Settings =====
            settings.form_fill_fast_mode = self.qs_fast_mode.get()
            settings.use_smart_form_filler = self.qs_smart_form_filler.get()
            settings.form_fill_delay_multiplier = self.qs_delay_multiplier.get()
            
            # ===== Resume Tailoring Settings =====
            settings.resume_tailoring_enabled = self.qs_resume_tailor.get()
            settings.resume_tailoring_confirm_after_filters = self.qs_tailor_confirm_filters.get()
            settings.resume_tailoring_prompt_before_jd = self.qs_tailor_prompt_jd.get()
            # Convert display format to setting value
            format_display = self.qs_resume_upload_format.get()
            format_map = {RESUME_AUTO: "auto", RESUME_PDF: "pdf", RESUME_DOCX: "docx"}
            settings.resume_upload_format = format_map.get(format_display, "auto")
            
            # ===== Browser & UI Settings =====
            settings.run_in_background = not self.qs_show_browser.get()
            settings.disable_extensions = self.qs_disable_extensions.get()
            settings.safe_mode = self.qs_safe_mode.get()
            settings.smooth_scroll = self.qs_smooth_scroll.get()
            settings.keep_screen_awake = self.qs_keep_awake.get()
            settings.stealth_mode = self.qs_stealth_mode.get()
            
            # ===== Control & Alerts Settings =====
            settings.pause_before_submit = self.qs_pause_submit.get()
            settings.pause_at_failed_question = self.qs_pause_failed_q.get()
            settings.showAiErrorAlerts = self.qs_show_ai_errors.get()
            
            # ===== PILOT MODE Settings =====
            settings.pilot_mode_enabled = self.qs_pilot_mode.get()
            settings.pilot_resume_mode = self.qs_pilot_resume_mode.get()
            settings.pilot_max_applications = self.qs_pilot_max_apps.get()
            settings.pilot_application_delay = self.qs_pilot_delay.get()
            settings.pilot_continue_on_error = self.qs_pilot_continue_error.get()
            
            # ===== AUTOPILOT FORM PRE-FILL Settings =====
            settings.autopilot_visa_required = self.qs_autopilot_visa_required.get()
            settings.autopilot_willing_relocate = self.qs_autopilot_willing_relocate.get()
            settings.autopilot_work_authorization = self.qs_autopilot_work_authorization.get()
            settings.autopilot_remote_preference = self.qs_autopilot_remote_preference.get()
            settings.autopilot_start_immediately = self.qs_autopilot_start_immediately.get()
            settings.autopilot_background_check = self.qs_autopilot_background_check.get()
            settings.autopilot_commute_ok = self.qs_autopilot_commute_ok.get()
            settings.autopilot_chrome_wait_time = self.qs_autopilot_chrome_wait_time.get()
            
            # ===== SCHEDULING Settings =====
            settings.scheduling_enabled = self.qs_schedule_enabled.get()
            settings.schedule_type = self.qs_schedule_type.get()
            settings.schedule_interval_hours = self.qs_schedule_interval.get()
            settings.schedule_max_runtime = self.qs_schedule_max_runtime.get()
            settings.schedule_max_applications = self.qs_schedule_max_apps.get()
            
            # ===== JOB SEARCH Settings =====
            settings.job_search_mode = self.qs_job_search_mode.get()
            
            # Also save to search config
            try:
                from config import search as search_config
                # Parse comma-separated job titles
                job_titles_str = self.qs_search_terms.get().strip()
                if job_titles_str:
                    search_terms = [t.strip() for t in job_titles_str.split(',') if t.strip()]
                    search_config.search_terms = search_terms
                search_config.search_location = self.qs_search_location.get()
                search_config.date_posted = self.qs_date_posted.get()
                search_config.easy_apply_only = self.qs_easy_apply_only.get()
                search_config.switch_number = self.qs_switch_number.get()
                search_config.randomize_search_order = self.qs_randomize_search.get()
                search_config.current_experience = self.qs_current_experience.get()
            except Exception as search_err:
                print(f"[Dashboard] Search config save warning: {search_err}")
            
            # ===== EXTENSION Settings =====
            settings.extension_enabled = self.qs_extension_enabled.get()
            settings.extension_auto_sync = self.qs_extension_auto_sync.get()
            settings.extension_ai_learning = self.qs_extension_ai_learning.get()
            # Convert display mode to setting value
            mode_display = self.qs_extension_detection_mode.get()
            mode_map = {DETECT_LINKEDIN: "linkedin", DETECT_UNIVERSAL: "universal", DETECT_SMART: "smart"}
            settings.extension_detection_mode = mode_map.get(mode_display, "universal")
            
        except Exception as e:
            print(f"[Dashboard] Settings save warning: {e}")
    
    def _apply_quick_settings(self):
        """Apply ALL Settings and save to config file."""
        self._save_quick_settings()
        
        # Also write to settings.py file for persistence
        try:
            settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'settings.py')
            
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                import re
                # Update ALL settings in file using regex
                # Boolean and numeric settings (matched by True/False/number pattern)
                bool_num_replacements = {
                    # Bot Behavior
                    'run_non_stop': str(self.qs_run_non_stop.get()),
                    'alternate_sortby': str(self.qs_alternate_sortby.get()),
                    'cycle_date_posted': str(self.qs_cycle_date_posted.get()),
                    'stop_date_cycle_at_24hr': str(self.qs_stop_date_24hr.get()),
                    'close_tabs': str(self.qs_close_tabs.get()),
                    'follow_companies': str(self.qs_follow_companies.get()),
                    'max_jobs_to_process': str(self.qs_max_jobs.get()),
                    'click_gap': str(self.qs_click_gap.get()),
                    # Form Filling
                    'form_fill_fast_mode': str(self.qs_fast_mode.get()),
                    'use_smart_form_filler': str(self.qs_smart_form_filler.get()),
                    'form_fill_delay_multiplier': str(self.qs_delay_multiplier.get()),
                    # Resume Tailoring
                    'resume_tailoring_enabled': str(self.qs_resume_tailor.get()),
                    'resume_tailoring_confirm_after_filters': str(self.qs_tailor_confirm_filters.get()),
                    'resume_tailoring_prompt_before_jd': str(self.qs_tailor_prompt_jd.get()),
                    # Browser & UI
                    'run_in_background': str(not self.qs_show_browser.get()),
                    'disable_extensions': str(self.qs_disable_extensions.get()),
                    'safe_mode': str(self.qs_safe_mode.get()),
                    'smooth_scroll': str(self.qs_smooth_scroll.get()),
                    'keep_screen_awake': str(self.qs_keep_awake.get()),
                    'stealth_mode': str(self.qs_stealth_mode.get()),
                    # Control & Alerts
                    'pause_before_submit': str(self.qs_pause_submit.get()),
                    'pause_at_failed_question': str(self.qs_pause_failed_q.get()),
                    'showAiErrorAlerts': str(self.qs_show_ai_errors.get()),
                    # Pilot Mode (bool/int)
                    'pilot_mode_enabled': str(self.qs_pilot_mode.get()),
                    'pilot_max_applications': str(self.qs_pilot_max_apps.get()),
                    'pilot_application_delay': str(self.qs_pilot_delay.get()),
                    'pilot_continue_on_error': str(self.qs_pilot_continue_error.get()),
                    # Scheduling (bool/int)
                    'scheduling_enabled': str(self.qs_schedule_enabled.get()),
                    'schedule_interval_hours': str(self.qs_schedule_interval.get()),
                    'schedule_max_runtime': str(self.qs_schedule_max_runtime.get()),
                    'schedule_max_applications': str(self.qs_schedule_max_apps.get()),
                    # Extension (bool)
                    'extension_enabled': str(self.qs_extension_enabled.get()),
                    'extension_auto_sync': str(self.qs_extension_auto_sync.get()),
                    'extension_ai_learning': str(self.qs_extension_ai_learning.get()),
                    # Autopilot (int)
                    'autopilot_chrome_wait_time': str(self.qs_autopilot_chrome_wait_time.get()),
                }
                
                for setting, value in bool_num_replacements.items():
                    # Handle boolean and numeric values
                    pattern = rf'^(\s*{setting}\s*=\s*)(True|False|\d+\.?\d*)'
                    replacement = rf'\g<1>{value}'
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                
                # String settings (matched by quoted string pattern)
                format_display = self.qs_resume_upload_format.get()
                format_map = {RESUME_AUTO: "auto", RESUME_PDF: "pdf", RESUME_DOCX: "docx"}
                mode_display = self.qs_extension_detection_mode.get()
                mode_map = {DETECT_LINKEDIN: "linkedin", DETECT_UNIVERSAL: "universal", DETECT_SMART: "smart"}
                
                string_replacements = {
                    # Pilot Mode (string)
                    'pilot_resume_mode': self.qs_pilot_resume_mode.get(),
                    # Resume
                    'resume_upload_format': format_map.get(format_display, "auto"),
                    # Scheduling (string)
                    'schedule_type': self.qs_schedule_type.get(),
                    # Job Search (string)
                    'job_search_mode': self.qs_job_search_mode.get(),
                    # Extension (string)
                    'extension_detection_mode': mode_map.get(mode_display, "universal"),
                    # Autopilot form answers (string)
                    'autopilot_visa_required': self.qs_autopilot_visa_required.get(),
                    'autopilot_willing_relocate': self.qs_autopilot_willing_relocate.get(),
                    'autopilot_work_authorization': self.qs_autopilot_work_authorization.get(),
                    'autopilot_remote_preference': self.qs_autopilot_remote_preference.get(),
                    'autopilot_start_immediately': self.qs_autopilot_start_immediately.get(),
                    'autopilot_background_check': self.qs_autopilot_background_check.get(),
                    'autopilot_commute_ok': self.qs_autopilot_commute_ok.get(),
                }
                
                for setting, value in string_replacements.items():
                    # Match quoted string values: setting = "value" or setting = 'value'
                    pattern = rf'^(\s*{setting}\s*=\s*)["\']([^"\']*)["\']'
                    replacement = rf'\g<1>"{value}"'
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                
                with open(settings_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.show_toast("✅ All settings saved successfully!", "success")
            else:
                self.show_toast("⚠️ Applied to runtime only", "warning")
        except Exception as e:
            self.show_toast(f"⚠️ Runtime applied, file save failed: {str(e)[:30]}", "warning")
    
    def _reset_settings_to_defaults(self):
        """Reset all settings to their default values (matching config/settings.py)."""
        # Default values from config/settings.py — MUST match actual file defaults
        self.qs_run_non_stop.set(True)
        self.qs_alternate_sortby.set(False)        # settings.py: alternate_sortby = False
        self.qs_cycle_date_posted.set(True)
        self.qs_stop_date_24hr.set(True)
        self.qs_close_tabs.set(False)
        self.qs_follow_companies.set(False)
        self.qs_max_jobs.set(0)
        self.qs_click_gap.set(20)
        self.qs_fast_mode.set(True)
        self.qs_smart_form_filler.set(True)
        self.qs_delay_multiplier.set(0.5)
        self.qs_resume_tailor.set(True)
        self.qs_tailor_confirm_filters.set(True)
        self.qs_tailor_prompt_jd.set(True)
        self.qs_resume_upload_format.set(RESUME_AUTO)
        self.qs_show_browser.set(True)             # run_in_background=False → show_browser=True
        self.qs_disable_extensions.set(False)       # settings.py: disable_extensions = False
        self.qs_safe_mode.set(False)                # settings.py: safe_mode = False
        self.qs_smooth_scroll.set(True)
        self.qs_keep_awake.set(True)
        self.qs_stealth_mode.set(True)              # settings.py: stealth_mode = True
        self.qs_pause_submit.set(False)
        self.qs_pause_failed_q.set(False)
        self.qs_show_ai_errors.set(True)            # settings.py: showAiErrorAlerts = True
        # Reset pilot mode
        self.qs_pilot_mode.set(False)               # settings.py: pilot_mode_enabled = True (but reset to safe default)
        self.qs_pilot_resume_mode.set('tailored')
        self.qs_pilot_max_apps.set(0)
        self.qs_pilot_delay.set(5)
        self.qs_pilot_continue_error.set(True)
        # Reset autopilot form answers
        self.qs_autopilot_visa_required.set('Yes')
        self.qs_autopilot_willing_relocate.set('Yes')
        self.qs_autopilot_work_authorization.set('Yes')
        self.qs_autopilot_remote_preference.set('Yes')
        self.qs_autopilot_start_immediately.set('Yes')
        self.qs_autopilot_background_check.set('Yes')
        self.qs_autopilot_commute_ok.set('Yes')
        self.qs_autopilot_chrome_wait_time.set(10)
        # Reset scheduling
        self.qs_schedule_enabled.set(False)
        self.qs_schedule_type.set('interval')
        self.qs_schedule_interval.set(4)
        self.qs_schedule_max_runtime.set(120)
        self.qs_schedule_max_apps.set(50)
        # Reset job search mode
        self.qs_job_search_mode.set('sequential')
        # Reset extension settings
        self.qs_extension_enabled.set(True)
        self.qs_extension_auto_sync.set(True)
        self.qs_extension_ai_learning.set(True)
        self.qs_extension_detection_mode.set(DETECT_UNIVERSAL)
        
        self._save_quick_settings()
        self.show_toast("🔄 Settings reset to defaults!", "info")
    
    def _export_extension_config(self):
        """Export current config to extension's user_config.json."""
        try:
            import subprocess
            import sys
            config_loader_path = os.path.join(os.path.dirname(__file__), '..', '..', 'extension', 'config_loader.py')
            config_loader_path = os.path.abspath(config_loader_path)
            
            if os.path.exists(config_loader_path):
                result = subprocess.run([sys.executable, config_loader_path], 
                                       capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.show_toast("✅ Config exported to extension!", "success")
                    self.activity_feed.add_activity("📤 Extension config exported", "success")
                else:
                    self.show_toast(f"⚠️ Export error: {result.stderr[:100]}", "warning")
            else:
                self.show_toast("⚠️ Config loader not found!", "warning")
        except Exception as e:
            self.show_toast(f"❌ Export failed: {str(e)[:50]}", "danger")
    
    def _reload_extension_manifest(self):
        """Show instructions to reload extension in Chrome."""
        import tkinter.messagebox as messagebox
        messagebox.showinfo(
            "Reload Extension",
            "To reload the extension:\n\n"
            "1. Open Chrome and go to: chrome://extensions/\n"
            "2. Enable 'Developer mode' (top right)\n"
            "3. Click 'Load unpacked' and select:\n"
            f"   {os.path.abspath('extension')}\n"
            "4. If already loaded, click the refresh icon\n\n"
            "The extension will detect forms on any job portal!"
        )
        self.activity_feed.add_activity("📋 Extension reload instructions shown", "info")
    
    # ============================================
    # PILOT MODE & SCHEDULING SECTION (TOP PRIORITY)
    # ============================================
    def _create_pilot_scheduling_section(self, parent):
        """Create the Pilot Mode & Scheduling section at the TOP of settings."""
        
        # ========== MASTER CONTAINER FOR PILOT & SCHEDULING ==========
        pilot_master = ttkb.Frame(parent)
        pilot_master.pack(fill=tk.X, padx=3, pady=3)
        
        # --- HEADER BANNER ---
        header_frame = ttkb.Frame(pilot_master)
        header_frame.pack(fill=tk.X, pady=(0, 4))
        
        header_label = ttkb.Label(header_frame, 
            text="🚀 AUTOMATION CONTROL CENTER",
            font=("Segoe UI", 12, "bold"),
            foreground="#4ade80")
        header_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.automation_status_indicator = ttkb.Label(header_frame, 
            text="⬤ MANUAL MODE",
            font=("Segoe UI", 10, "bold"),
            foreground="#888888")
        self.automation_status_indicator.pack(side=tk.RIGHT)
        
        # ========== QUICK START BUTTONS ROW ==========
        quick_start_frame = ttkb.Frame(pilot_master)
        quick_start_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Pilot Mode Quick Start Button (Large, prominent)
        self.pilot_start_btn = ttkb.Button(quick_start_frame,
            text="🚀 START PILOT MODE",
            command=self._quick_start_pilot,
            bootstyle="success",
            width=20)
        self.pilot_start_btn.pack(side=tk.LEFT, padx=(0, 8), ipady=4)
        
        # Schedule Quick Start Button (Large, prominent)
        self.schedule_start_btn = ttkb.Button(quick_start_frame,
            text="📅 START SCHEDULED RUN",
            command=self._quick_start_scheduled,
            bootstyle="primary",
            width=20)
        self.schedule_start_btn.pack(side=tk.LEFT, padx=(0, 8), ipady=4)
        
        # Normal Mode Button
        self.normal_mode_btn = ttkb.Button(quick_start_frame,
            text="🔧 NORMAL MODE",
            command=self._switch_to_normal_mode,
            bootstyle="secondary-outline",
            width=14)
        self.normal_mode_btn.pack(side=tk.LEFT, ipady=4)
        
        # ========== PILOT MODE SETTINGS ==========
        pilot_frame = ttkb.Labelframe(pilot_master, 
            text="✈️ PILOT MODE - Fully Automated", 
            bootstyle="success")
        pilot_frame.pack(fill=tk.X, pady=(0, 5))
        
        pilot_inner = ttkb.Frame(pilot_frame)
        pilot_inner.pack(fill=tk.X, padx=8, pady=5)
        
        # Info banner
        pilot_info = ttkb.Label(pilot_inner, 
            text="🤖 Runs completely hands-free • Auto-applies to jobs • No confirmation dialogs",
            font=("Segoe UI", 8), foreground="#4ade80")
        pilot_info.pack(anchor=tk.W, pady=(0, 5))
        
        # Row 1: Enable toggle + Resume Mode
        pilot_row1 = ttkb.Frame(pilot_inner)
        pilot_row1.pack(fill=tk.X, pady=2)
        
        ttkb.Checkbutton(pilot_row1, text="✈️ Pilot Mode Enabled", 
            variable=self.qs_pilot_mode,
            bootstyle="success-round-toggle", 
            command=self._on_pilot_mode_changed).pack(side=tk.LEFT, padx=(0, 20))
        
        ttkb.Label(pilot_row1, text="📄 Resume:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        pilot_resume_combo = ttkb.Combobox(pilot_row1, 
            textvariable=self.qs_pilot_resume_mode,
            values=["tailored", "default", "preselected", "skip"],
            state="readonly", width=12)
        pilot_resume_combo.pack(side=tk.LEFT, padx=(5, 0))
        pilot_resume_combo.bind(EVENT_COMBOBOX_SELECTED, lambda e: self._save_quick_settings())
        
        # Resume mode info tooltip
        resume_mode_info = ttkb.Label(pilot_row1, 
            text="ℹ️", font=("Segoe UI", 9), foreground="#60a5fa", cursor="hand2")
        resume_mode_info.pack(side=tk.LEFT, padx=(5, 0))
        resume_mode_info.bind(EVENT_ENTER, lambda e: self._show_resume_mode_tooltip(e, resume_mode_info))
        resume_mode_info.bind(EVENT_LEAVE, lambda e: self._hide_tooltip())
        
        # Row 2: Delay + Max Apps + Continue on Error
        pilot_row2 = ttkb.Frame(pilot_inner)
        pilot_row2.pack(fill=tk.X, pady=2)
        
        ttkb.Label(pilot_row2, text="⏱️ Delay (sec):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(pilot_row2, from_=1, to=30, width=5, textvariable=self.qs_pilot_delay,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(pilot_row2, text="📊 Max Apps (0=∞):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(pilot_row2, from_=0, to=500, width=6, textvariable=self.qs_pilot_max_apps,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Checkbutton(pilot_row2, text="🔄 Continue on Errors", 
            variable=self.qs_pilot_continue_error,
            bootstyle="info-round-toggle", 
            command=self._save_quick_settings).pack(side=tk.LEFT)
        
        # ========== AUTOPILOT FORM PRE-FILL SETTINGS ==========
        # These settings are used to automatically fill common form questions in pilot mode
        prefill_frame = ttkb.Labelframe(pilot_master, 
            text="📝 AUTOPILOT FORM PRE-FILL - Common Question Answers", 
            bootstyle="warning")
        prefill_frame.pack(fill=tk.X, pady=(0, 5))
        
        prefill_inner = ttkb.Frame(prefill_frame)
        prefill_inner.pack(fill=tk.X, padx=8, pady=5)
        
        # Info banner
        prefill_info = ttkb.Label(prefill_inner, 
            text="🔧 Pre-configure answers for common job application questions (used in Pilot Mode)",
            font=("Segoe UI", 8), foreground="#f59e0b")
        prefill_info.pack(anchor=tk.W, pady=(0, 5))
        
        # Row 1: Visa, Work Authorization, Willing to Relocate
        prefill_row1 = ttkb.Frame(prefill_inner)
        prefill_row1.pack(fill=tk.X, pady=2)
        
        ttkb.Label(prefill_row1, text="🛂 Visa/Sponsorship:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row1, textvariable=self.qs_autopilot_visa_required,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(prefill_row1, text="🏛️ Work Auth:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row1, textvariable=self.qs_autopilot_work_authorization,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(prefill_row1, text="🚚 Relocate:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row1, textvariable=self.qs_autopilot_willing_relocate,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 0))
        
        # Row 2: Remote, Start Immediately, Background Check, Commute
        prefill_row2 = ttkb.Frame(prefill_inner)
        prefill_row2.pack(fill=tk.X, pady=2)
        
        ttkb.Label(prefill_row2, text="🏠 Remote OK:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row2, textvariable=self.qs_autopilot_remote_preference,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(prefill_row2, text="⏰ Start Now:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row2, textvariable=self.qs_autopilot_start_immediately,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(prefill_row2, text="🔍 BG Check:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row2, textvariable=self.qs_autopilot_background_check,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(prefill_row2, text="🚗 Commute:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Combobox(prefill_row2, textvariable=self.qs_autopilot_commute_ok,
            values=["Yes", "No"], state="readonly", width=5).pack(side=tk.LEFT, padx=(5, 0))
        
        # Row 3: Chrome wait time for stability
        prefill_row3 = ttkb.Frame(prefill_inner)
        prefill_row3.pack(fill=tk.X, pady=2)
        
        ttkb.Label(prefill_row3, text="⏳ Chrome Wait (sec):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(prefill_row3, from_=5, to=30, width=5, textvariable=self.qs_autopilot_chrome_wait_time,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 15))
        ttkb.Label(prefill_row3, text="(Increase if Chrome opens inconsistently)", 
            font=("Segoe UI", 8), foreground="#888888").pack(side=tk.LEFT)
        
        # ========== SCHEDULING SETTINGS ==========
        sched_frame = ttkb.Labelframe(pilot_master, 
            text="📅 SCHEDULING - Auto-Run on Timer", 
            bootstyle="primary")
        sched_frame.pack(fill=tk.X, pady=(0, 5))
        
        sched_inner = ttkb.Frame(sched_frame)
        sched_inner.pack(fill=tk.X, padx=8, pady=5)
        
        # Info banner
        sched_info = ttkb.Label(sched_inner, 
            text="⏰ Run job applications automatically on a schedule • No dashboard needed",
            font=("Segoe UI", 8), foreground="#60a5fa")
        sched_info.pack(anchor=tk.W, pady=(0, 5))
        
        # Row 1: Enable toggle + Schedule Type
        sched_row1 = ttkb.Frame(sched_inner)
        sched_row1.pack(fill=tk.X, pady=2)
        
        ttkb.Checkbutton(sched_row1, text="📅 Scheduling Enabled", 
            variable=self.qs_schedule_enabled,
            bootstyle="primary-round-toggle", 
            command=self._on_schedule_changed).pack(side=tk.LEFT, padx=(0, 20))
        
        ttkb.Label(sched_row1, text="Type:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        sched_type_combo = ttkb.Combobox(sched_row1, 
            textvariable=self.qs_schedule_type,
            values=["interval", "daily", "weekly"],
            state="readonly", width=10)
        sched_type_combo.pack(side=tk.LEFT, padx=(5, 15))
        sched_type_combo.bind(EVENT_COMBOBOX_SELECTED, lambda e: self._save_quick_settings())
        
        ttkb.Label(sched_row1, text="⏱️ Interval (hrs):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(sched_row1, from_=1, to=24, width=5, textvariable=self.qs_schedule_interval,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 0))
        
        # Row 2: Max Runtime + Max Apps + Status
        sched_row2 = ttkb.Frame(sched_inner)
        sched_row2.pack(fill=tk.X, pady=2)
        
        ttkb.Label(sched_row2, text="⏳ Max Runtime (min):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(sched_row2, from_=10, to=480, width=5, textvariable=self.qs_schedule_max_runtime,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 15))
        
        ttkb.Label(sched_row2, text="📊 Max Apps:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(sched_row2, from_=0, to=200, width=6, textvariable=self.qs_schedule_max_apps,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 15))
        
        # Status indicator
        self.schedule_status_label = ttkb.Label(sched_row2, 
            text="⏸️ Stopped", font=("Segoe UI", 9, "bold"), foreground="#888888")
        self.schedule_status_label.pack(side=tk.RIGHT)
        
        # Row 3: Next run info
        sched_row3 = ttkb.Frame(sched_inner)
        sched_row3.pack(fill=tk.X, pady=(5, 2))
        
        self.next_run_label = ttkb.Label(sched_row3, 
            text="📅 Next run: --", font=("Segoe UI", 8), foreground="#888888")
        self.next_run_label.pack(side=tk.LEFT)
        
        # Scheduler control buttons
        ttkb.Button(sched_row3, text="⏹️ Stop", 
            command=self._stop_scheduler,
            bootstyle="danger-outline", width=8).pack(side=tk.RIGHT, padx=2)
        ttkb.Button(sched_row3, text="▶️ Start", 
            command=self._start_scheduler,
            bootstyle="success-outline", width=8).pack(side=tk.RIGHT, padx=2)
        
        # ========== JOB SEARCH SETTINGS ==========
        search_frame = ttkb.Labelframe(pilot_master, 
            text="🔍 JOB SEARCH - What & How to Search", 
            bootstyle="info")
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        search_inner = ttkb.Frame(search_frame)
        search_inner.pack(fill=tk.X, padx=8, pady=5)
        
        # Info banner
        search_info = ttkb.Label(search_inner, 
            text="🎯 Configure job titles, location, and how the bot cycles through searches • Changes apply immediately",
            font=("Segoe UI", 8), foreground="#22d3ee")
        search_info.pack(anchor=tk.W, pady=(0, 5))
        
        # Row 1: Job Titles (multi-line text box)
        search_row1 = ttkb.Frame(search_inner)
        search_row1.pack(fill=tk.X, pady=2)
        
        ttkb.Label(search_row1, text="💼 Job Titles to Search:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        ttkb.Label(search_row1, text="(Comma-separated list - e.g., \"Software Engineer, Python Developer, Full Stack Developer\")", 
            font=("Segoe UI", 7), foreground="#888888").pack(anchor=tk.W)
        
        # Text entry for job titles with larger area
        job_titles_frame = ttkb.Frame(search_inner)
        job_titles_frame.pack(fill=tk.X, pady=2)
        
        self.job_titles_text = tk.Text(job_titles_frame, height=3, width=60, 
            font=("Segoe UI", 9), wrap=tk.WORD)
        self.job_titles_text.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.job_titles_text.insert("1.0", self.qs_search_terms.get())
        self.job_titles_text.bind("<FocusOut>", self._on_job_titles_changed)
        
        # Row 2: Location + Date Posted + Easy Apply
        search_row2 = ttkb.Frame(search_inner)
        search_row2.pack(fill=tk.X, pady=(5, 2))
        
        ttkb.Label(search_row2, text="📍 Location:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        location_entry = ttkb.Entry(search_row2, textvariable=self.qs_search_location, width=20)
        location_entry.pack(side=tk.LEFT, padx=(5, 15))
        location_entry.bind("<FocusOut>", lambda e: self._save_quick_settings())
        
        ttkb.Label(search_row2, text="📅 Date:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        date_combo = ttkb.Combobox(search_row2, textvariable=self.qs_date_posted,
            values=["Any time", "Past month", "Past week", "Past 24 hours"],
            state="readonly", width=12)
        date_combo.pack(side=tk.LEFT, padx=(5, 15))
        date_combo.bind(EVENT_COMBOBOX_SELECTED, lambda e: self._save_quick_settings())
        
        ttkb.Checkbutton(search_row2, text="⚡ Easy Apply Only", 
            variable=self.qs_easy_apply_only,
            bootstyle="info-round-toggle", 
            command=self._save_quick_settings).pack(side=tk.LEFT)
        
        # Row 3: Job Title Switching Behavior (IMPORTANT FOR USER CLARITY)
        search_row3_header = ttkb.Frame(search_inner)
        search_row3_header.pack(fill=tk.X, pady=(8, 2))
        ttkb.Label(search_row3_header, text="🔄 Job Title Switching Behavior:", 
            font=("Segoe UI", 9, "bold"), foreground="#f59e0b").pack(side=tk.LEFT)
        
        search_row3 = ttkb.Frame(search_inner)
        search_row3.pack(fill=tk.X, pady=2)
        
        ttkb.Label(search_row3, text="Mode:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        mode_combo = ttkb.Combobox(search_row3, textvariable=self.qs_job_search_mode,
            values=["sequential", "random", "single"],
            state="readonly", width=10)
        mode_combo.pack(side=tk.LEFT, padx=(5, 10))
        mode_combo.bind(EVENT_COMBOBOX_SELECTED, lambda e: self._on_search_mode_changed())
        
        ttkb.Label(search_row3, text="Switch after:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        switch_spin = ttkb.Spinbox(search_row3, from_=1, to=500, width=5, textvariable=self.qs_switch_number,
            command=self._save_quick_settings)
        switch_spin.pack(side=tk.LEFT, padx=(5, 3))
        ttkb.Label(search_row3, text="applications", font=("Segoe UI", 8), foreground="#888888").pack(side=tk.LEFT, padx=(0, 10))
        
        # Mode info tooltip  
        mode_info = ttkb.Label(search_row3, text="ℹ️ What does this mean?", font=("Segoe UI", 8), 
            foreground="#22d3ee", cursor="hand2")
        mode_info.pack(side=tk.LEFT, padx=(5, 0))
        mode_info.bind(EVENT_ENTER, lambda e: self._show_search_mode_tooltip(e, mode_info))
        mode_info.bind(EVENT_LEAVE, lambda e: self._hide_tooltip())
        
        # Mode explanation label (dynamic based on selection)
        self.mode_explanation_label = ttkb.Label(search_inner, text="", 
            font=("Segoe UI", 8), foreground="#4ade80", wraplength=500)
        self.mode_explanation_label.pack(anchor=tk.W, pady=(2, 0))
        self._update_mode_explanation()  # Set initial explanation
        
        # Row 4: Randomize checkbox + Experience
        search_row4 = ttkb.Frame(search_inner)
        search_row4.pack(fill=tk.X, pady=(5, 2))
        
        ttkb.Checkbutton(search_row4, text="🔀 Shuffle Job Titles List", 
            variable=self.qs_randomize_search,
            bootstyle="info-round-toggle", 
            command=self._save_quick_settings).pack(side=tk.LEFT)
        ttkb.Label(search_row4, text="(Randomize the order before cycling)", 
            font=("Segoe UI", 7), foreground="#888888").pack(side=tk.LEFT, padx=(5, 20))
        
        ttkb.Label(search_row4, text="📊 Exp (yrs):", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        ttkb.Spinbox(search_row4, from_=0, to=30, width=4, textvariable=self.qs_current_experience,
            command=self._save_quick_settings).pack(side=tk.LEFT, padx=(5, 0))
        
        # ========== SETTINGS VALIDATION WARNING ==========
        self.settings_warning_frame = ttkb.Frame(pilot_master)
        self.settings_warning_frame.pack(fill=tk.X, pady=2)
        
        self.settings_warning_label = ttkb.Label(self.settings_warning_frame, 
            text="", font=("Segoe UI", 8), foreground="#f97316")
        self.settings_warning_label.pack(anchor=tk.W)
        
        # Separator after pilot/scheduling
        sep = ttkb.Separator(pilot_master, orient='horizontal')
        sep.pack(fill=tk.X, pady=(10, 5))
        
        # Bind mousewheel to all new widgets
        if hasattr(self, '_bind_settings_mousewheel'):
            self._bind_settings_mousewheel(pilot_master)
        
        # Initial validation
        self._validate_settings()
    
    def _quick_start_pilot_from_header(self):
        """Quick start pilot mode from header button."""
        self._quick_start_pilot()
    
    def _quick_start_scheduled_from_header(self):
        """Quick start scheduled mode from header button."""
        self._quick_start_scheduled()
    
    def _quick_start_pilot(self):
        """Quick start pilot mode - enables pilot and starts the bot."""
        self.qs_pilot_mode.set(True)
        self.qs_pause_submit.set(False)  # Disable pause in pilot mode
        self.qs_safe_mode.set(True)  # Enable safe mode for stability
        self._save_quick_settings()
        self._update_automation_status()
        self.show_toast("🚀 Pilot Mode Enabled! Starting bot...", "success")
        self.activity_feed.add_activity("🚀 PILOT MODE ACTIVATED", "success")
        # Start the bot
        self.start_bot()
    
    def _quick_start_scheduled(self):
        """Quick start scheduled mode - enables scheduling and starts scheduler."""
        self.qs_schedule_enabled.set(True)
        self.qs_pilot_mode.set(True)  # Scheduling needs pilot mode
        self.qs_pause_submit.set(False)  # Disable pause in pilot mode
        self.qs_safe_mode.set(True)  # Enable safe mode for stability
        self._save_quick_settings()
        self._update_automation_status()
        self._start_scheduler()
        self.show_toast("📅 Scheduled Run Started!", "success")
        self.activity_feed.add_activity("📅 SCHEDULED MODE ACTIVATED", "success")
    
    def _switch_to_normal_mode(self):
        """Switch to normal (manual) mode."""
        self.qs_pilot_mode.set(False)
        self.qs_schedule_enabled.set(False)
        self._stop_scheduler()
        self._save_quick_settings()
        self._update_automation_status()
        self.show_toast("🔧 Switched to Normal Mode", "info")
    
    def _on_pilot_mode_changed(self):
        """Handle pilot mode toggle change."""
        self._save_quick_settings()
        self._validate_settings()
        self._update_automation_status()
    
    def _on_schedule_changed(self):
        """Handle schedule toggle change."""
        self._save_quick_settings()
        self._validate_settings()
        self._update_automation_status()
    
    def _update_automation_status(self):
        """Update the automation status indicator."""
        if hasattr(self, 'automation_status_indicator'):
            if self.qs_schedule_enabled.get():
                self.automation_status_indicator.config(
                    text="⬤ SCHEDULED MODE", foreground="#60a5fa")
            elif self.qs_pilot_mode.get():
                self.automation_status_indicator.config(
                    text="⬤ PILOT MODE", foreground="#4ade80")
            else:
                self.automation_status_indicator.config(
                    text="⬤ MANUAL MODE", foreground="#888888")
    
    def _validate_settings(self):
        """Validate settings and show warnings for conflicts."""
        warnings = []
        
        # Check for conflicting settings
        if self.qs_pilot_mode.get() and self.qs_pause_submit.get():
            warnings.append("⚠️ Pilot Mode conflicts with 'Pause Before Submit' - will auto-disable pause")
            self.qs_pause_submit.set(False)
        
        if self.qs_schedule_enabled.get() and not self.qs_pilot_mode.get():
            warnings.append("ℹ️ Scheduling works best with Pilot Mode enabled")
        
        if self.qs_pilot_resume_mode.get() == "skip" and not self.qs_pilot_mode.get():
            warnings.append("ℹ️ 'Skip' resume mode only applies in Pilot Mode")
        
        # Update warning label
        if hasattr(self, 'settings_warning_label'):
            if warnings:
                self.settings_warning_label.config(text=" | ".join(warnings))
            else:
                self.settings_warning_label.config(text="")
    
    def _show_resume_mode_tooltip(self, event, widget):
        """Show tooltip for resume mode options."""
        tooltip_text = """Resume Mode Options:
• tailored - AI-tailored resume for each job (no confirmations)
• default - Upload project's default resume file
• preselected - Use LinkedIn's pre-selected resume (no upload)
• skip - Don't touch resume at all"""
        
        self._tooltip = tk.Toplevel(widget)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = ttkb.Label(self._tooltip, text=tooltip_text, 
            font=("Segoe UI", 9), background="#333333", foreground="#ffffff",
            padding=(8, 5))
        label.pack()
    
    def _hide_tooltip(self):
        """Hide the tooltip."""
        if hasattr(self, '_tooltip') and self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
    
    def _show_search_mode_tooltip(self, event, widget):
        """Show tooltip for job search mode options."""
        tooltip_text = """🔄 JOB TITLE SWITCHING MODES:

📋 SEQUENTIAL (Recommended)
   Apply to each job title in your list order.
   After N applications (set by 'Switch after'), 
   move to the next job title in the list.
   Example: 30 apps for "Software Engineer", 
   then 30 for "Python Developer", etc.

🎲 RANDOM  
   Randomly pick a different job title for 
   each search cycle. Good for diverse coverage.

🎯 SINGLE (Stay on One Title)
   ONLY apply to the FIRST job title in your list.
   Ignores all other titles until limit is reached.
   Use this if you want to focus on one specific role."""
        
        self._tooltip = tk.Toplevel(widget)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = ttkb.Label(self._tooltip, text=tooltip_text, 
            font=("Segoe UI", 9), background="#333333", foreground="#ffffff",
            padding=(8, 5))
        label.pack()
    
    def _on_job_titles_changed(self, event=None):
        """Handle job titles text box change."""
        if hasattr(self, 'job_titles_text'):
            text = self.job_titles_text.get("1.0", tk.END).strip()
            self.qs_search_terms.set(text)
            self._save_quick_settings()
    
    def _on_search_mode_changed(self):
        """Handle search mode combobox change."""
        self._save_quick_settings()
        self._update_mode_explanation()
    
    def _update_mode_explanation(self):
        """Update the mode explanation label based on current selection."""
        if not hasattr(self, 'mode_explanation_label'):
            return
        
        mode = self.qs_job_search_mode.get()
        switch_num = self.qs_switch_number.get()
        
        explanations = {
            "sequential": f"✅ SEQUENTIAL: Bot applies to jobs for each title in order. After {switch_num} apps for 'Title A', it moves to 'Title B', then 'Title C', etc.",
            "random": "🎲 RANDOM: Bot randomly picks a new job title for each search cycle. Useful for diverse applications across all titles.",
            "single": "🎯 SINGLE: Bot ONLY searches for the FIRST job title in your list until the limit is reached. Other titles are ignored."
        }
        
        explanation = explanations.get(mode, "Select a mode to see explanation")
        self.mode_explanation_label.config(text=explanation)

    # ============================================
    # SCHEDULER CONTROL METHODS
    # ============================================
    def _start_scheduler(self):
        """Start the job application scheduler."""
        try:
            from modules.scheduler import get_scheduler
            scheduler = get_scheduler()
            
            # Update scheduler config from current settings
            scheduler.update_config({
                'enabled': True,
                'schedule_type': self.qs_schedule_type.get(),
                'interval_hours': self.qs_schedule_interval.get(),
                'max_runtime': self.qs_schedule_max_runtime.get(),
                'max_applications': self.qs_schedule_max_apps.get(),
                'pilot_mode': self.qs_pilot_mode.get(),
                'pilot_resume_mode': self.qs_pilot_resume_mode.get(),
            })
            
            scheduler.start()
            
            # Update UI
            if hasattr(self, 'schedule_status_label'):
                self.schedule_status_label.config(text="▶️ Scheduler: Running", foreground="#4ade80")
            
            # Show next run time
            next_run = scheduler.get_next_run_time()
            if next_run and hasattr(self, 'next_run_label'):
                self.next_run_label.config(text=f"Next scheduled run: {next_run.strftime('%Y-%m-%d %H:%M')}")
            
            self.show_toast("✅ Scheduler started!", "success")
            self.activity_feed.add_activity("Scheduler started", "success")
            
        except Exception as e:
            self.show_toast(f"❌ Failed to start scheduler: {str(e)[:40]}", "error")
            print(f"[Dashboard] Scheduler start error: {e}")
    
    def _stop_scheduler(self):
        """Stop the job application scheduler."""
        try:
            from modules.scheduler import stop_scheduler
            stop_scheduler()
            
            # Update UI
            if hasattr(self, 'schedule_status_label'):
                self.schedule_status_label.config(text="⏸️ Scheduler: Stopped", foreground="#888888")
            if hasattr(self, 'next_run_label'):
                self.next_run_label.config(text="Next scheduled run: --")
            
            self.show_toast("⏹️ Scheduler stopped", "info")
            self.activity_feed.add_activity("Scheduler stopped", "info")
            
        except Exception as e:
            self.show_toast(f"⚠️ Scheduler stop error: {str(e)[:40]}", "warning")
            print(f"[Dashboard] Scheduler stop error: {e}")
    
    def _update_scheduler_status(self):
        """Update scheduler status display (called periodically)."""
        try:
            from modules.scheduler import get_scheduler
            scheduler = get_scheduler()
            status = scheduler.get_status()
            
            if hasattr(self, 'schedule_status_label'):
                if status.get('running', False):
                    self.schedule_status_label.config(text="▶️ Scheduler: Running", foreground="#4ade80")
                else:
                    self.schedule_status_label.config(text="⏸️ Scheduler: Stopped", foreground="#888888")
            
            next_run = status.get('next_run')
            if next_run and hasattr(self, 'next_run_label'):
                self.next_run_label.config(text=f"Next scheduled run: {next_run[:16]}")
        except Exception:
            pass

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
                
                if hasattr(self, 'ai_output') and msg.startswith('[AI]'):
                    try:
                        self.ai_output.insert(tk.END, msg.replace('[AI]', '').strip() + "\n")
                        self.ai_output.see(tk.END)
                    except tk.TclError:
                        pass
        
        # Update progress bars - REAL-TIME with smooth animation
        jd = int(data.get("jd_progress", 0))
        rs = int(data.get("resume_progress", 0))
        
        # Update JD Analysis progress (all instances)
        try:
            if hasattr(self, 'dash_jd_progress'):
                self.dash_jd_progress.configure(value=jd)
            if hasattr(self, 'jd_progress'):
                self.jd_progress.configure(value=jd)
            # Update status labels with clear visual feedback
            if hasattr(self, 'dash_jd_status'):
                if jd == 0:
                    self.dash_jd_status.config(text="Idle", foreground="#888888")
                elif jd < 100:
                    self.dash_jd_status.config(text=f"Analyzing... {jd}%", foreground="#60a5fa")
                else:
                    self.dash_jd_status.config(text="✓ Complete", foreground="#4ade80")
            if hasattr(self, 'jd_progress_label'):
                self.jd_progress_label.config(text=f"{jd}%")
        except tk.TclError:
            pass
        
        # Update Resume Tailoring progress (all instances)
        try:
            if hasattr(self, 'dash_resume_progress'):
                self.dash_resume_progress.configure(value=rs)
            if hasattr(self, 'resume_progress'):
                self.resume_progress.configure(value=rs)
            # Update status labels with clear visual feedback
            if hasattr(self, 'dash_resume_status'):
                if rs == 0:
                    self.dash_resume_status.config(text="Idle", foreground="#888888")
                elif rs < 100:
                    self.dash_resume_status.config(text=f"Tailoring... {rs}%", foreground="#fbbf24")
                else:
                    self.dash_resume_status.config(text="✓ Complete", foreground="#4ade80")
            if hasattr(self, 'resume_progress_label'):
                self.resume_progress_label.config(text=f"{rs}%")
        except tk.TclError:
            pass
        
        # Update job count
        self.job_count = data.get("jobs_processed", 0)
        
        # Update dashboard stats if available
        self._update_dashboard_stats()
        
        # Update metrics labels (if they exist)
        if hasattr(self, 'metric_labels'):
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
        
        # Update charts (safely)
        try:
            self._update_charts(data)
        except Exception:
            pass
        
        # Update stats (safely)
        try:
            if hasattr(self, 'update_stats_display'):
                self.update_stats_display()
        except Exception:
            pass
        
        # Update analytics panel in right panel
        try:
            if hasattr(self, 'update_analytics_stats'):
                self.update_analytics_stats()
            # Update overall progress
            total_jobs = data.get("jobs_processed", 0)
            if total_jobs > 0 and hasattr(self, 'update_progress'):
                self.update_progress(self.applied_count, total_jobs, "Processing jobs...")
        except Exception:
            pass
        
        self.after(200, self._refresh_metrics)  # 200ms for real-time progress updates
    
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
        """Handle dashboard close - stops bot and kills ALL Chrome processes."""
        import subprocess
        import sys
        
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
        
        # ============================================
        # CLEANUP: Kill Chrome and all related processes
        # ============================================
        print("[Dashboard] Cleaning up all processes...")
        
        # Step 1: Reset Chrome session via open_chrome module
        # Use force=True to ensure cleanup happens even during operation
        try:
            from modules.open_chrome import reset_chrome_session, set_auto_reset_allowed
            set_auto_reset_allowed(True)  # Re-enable auto-reset for cleanup
            reset_chrome_session(force=True)  # Force cleanup with process termination
            print("[Dashboard] Chrome session reset successfully")
        except Exception as e:
            print(f"[Dashboard] Warning: Chrome session reset failed: {e}")
        
        # Step 2: Force kill all Chrome-related processes on Windows
        if sys.platform == 'win32':
            try:
                # Kill chromedriver first
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'chromedriver.exe'],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            
            try:
                # Kill Chrome browser with all child processes
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'chrome.exe', '/T'],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass
            
            # Also try killing any orphaned processes
            try:
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'GoogleCrashHandler.exe'],
                    capture_output=True, timeout=3
                )
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'GoogleCrashHandler64.exe'],
                    capture_output=True, timeout=3
                )
            except Exception:
                pass
        else:
            # Linux/Mac cleanup
            try:
                subprocess.run(['pkill', '-9', '-f', 'chromedriver'], capture_output=True, timeout=5)
                subprocess.run(['pkill', '-9', '-f', 'chrome'], capture_output=True, timeout=5)
            except Exception:
                pass
        
        print("[Dashboard] Cleanup complete - all Chrome processes terminated")
        
        self.destroy()


# Controller wrapper
class BotController:
    def __init__(self, runner):
        self.runner = runner

    def start(self) -> bool:
        """Start the bot. Returns True if started, False if already running."""
        if hasattr(self.runner, 'start_bot_thread'):
            return self.runner.start_bot_thread()
        elif hasattr(self.runner, 'start_bot'):
            self.runner.start_bot()
            return True
        return False

    def stop(self) -> None:
        """Stop the bot and clean up."""
        if hasattr(self.runner, 'stop_bot'):
            self.runner.stop_bot()
    
    def pause(self) -> bool:
        """Pause/unpause the bot. Returns new pause state."""
        if hasattr(self.runner, 'pause_bot'):
            return self.runner.pause_bot()
        return False
    
    def skip(self) -> None:
        """Skip current job."""
        if hasattr(self.runner, 'skip_job'):
            self.runner.skip_job()
    
    def is_running(self) -> bool:
        """Check if bot is running."""
        if hasattr(self.runner, 'is_running'):
            return self.runner.is_running()
        return False
    
    def is_paused(self) -> bool:
        """Check if bot is paused."""
        if hasattr(self.runner, 'is_paused'):
            return self.runner.is_paused()
        return False


def run_dashboard(runner):
    app = BotDashboard(BotController(runner))
    app.mainloop()


if __name__ == "__main__":
    print("Run this module from the main application to open the dashboard")

# sonar:on
