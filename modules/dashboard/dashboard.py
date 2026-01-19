'''Modern Tkinter dashboard to control and monitor the bot.'''
import threading
import queue
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Menu, PhotoImage
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib import style
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from modules.dashboard import log_handler, metrics

# Import for modern styling
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class BotDashboard(ttkb.Window):
    def __init__(self, controller):
        # Use ttkbootstrap theme
        super().__init__(themename="darkly")
        self.title("AI Job Finder Pro - Dashboard")
        self.geometry("1200x800")
        self.state('zoomed')  # Maximized window
        self.controller = controller
        
        # Set icon if available
        try:
            self.iconbitmap()  # Use default if no custom icon
        except:
            pass
        
        # Create main menu
        self.create_menu()
        
        # Main container frame
        main_frame = ttkb.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header section with logo and title
        header_frame = ttkb.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo and title
        title_label = ttkb.Label(header_frame, text="🤖 AI Job Finder Pro", font=("Segoe UI", 24, "bold"))
        title_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Status indicator
        self.status_frame = ttkb.Frame(header_frame)
        self.status_frame.pack(side=tk.RIGHT)
        
        self.status_indicator = ttkb.Label(self.status_frame, text="●", foreground="red", font=("Arial", 16))
        self.status_indicator.pack(side=tk.LEFT)
        
        self.status_label = ttkb.Label(self.status_frame, text="Status: Stopped", font=("Segoe UI", 12))
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Control buttons
        controls_frame = ttkb.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttkb.Button(controls_frame, text="▶ Start Bot", command=self.start_bot, bootstyle="success-outline")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttkb.Button(controls_frame, text="⏹ Stop Bot", command=self.stop_bot, state=tk.DISABLED, bootstyle="danger-outline")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.pause_btn = ttkb.Button(controls_frame, text="⏸ Pause", command=self.toggle_pause, state=tk.DISABLED, bootstyle="warning-outline")
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stats summary
        stats_frame = ttkb.Frame(controls_frame)
        stats_frame.pack(side=tk.RIGHT)
        
        self.stats_label = ttkb.Label(stats_frame, text="📊 Jobs: 0 | Applied: 0 | Failed: 0", font=("Segoe UI", 10))
        self.stats_label.pack()

        # Middle: logs and metrics
        paned = ttkb.Notebook(main_frame)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Live Logs Tab
        logs_frame = ttkb.Frame(paned)
        paned.add(logs_frame, text="Live Logs")
        
        # Main logs area
        logs_container = ttkb.Frame(logs_frame)
        logs_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Live logs with modern styling
        log_inner_frame = ttkb.Frame(logs_container)
        log_inner_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable text widget for logs
        log_text_frame = ttkb.Frame(log_inner_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_text_frame, state=tk.NORMAL, height=15, 
                                               bg="#2d2d2d", fg="#ffffff", insertbackground="#ffffff",
                                               font=("Consolas", 10))
        scrollbar_logs = ttkb.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar_logs.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_logs.pack(side=tk.RIGHT, fill=tk.Y)
        
        # AI Output section
        ai_frame = ttkb.Labelframe(log_inner_frame, text="AI Assistant Output", bootstyle="primary")
        ai_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.ai_output = scrolledtext.ScrolledText(ai_frame, height=6, bg="#1e1e1e", fg="#aaffaa",
                                                  font=("Consolas", 10))
        scrollbar_ai = ttkb.Scrollbar(ai_frame, orient="vertical", command=self.ai_output.yview)
        self.ai_output.configure(yscrollcommand=scrollbar_ai.set)
        
        self.ai_output.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        scrollbar_ai.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Stats and Metrics Tab
        stats_frame = ttkb.Frame(paned)
        paned.add(stats_frame, text="Statistics & Metrics")
        
        # Stats grid
        stats_grid = ttkb.Frame(stats_frame)
        stats_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create stat cards
        self.create_stat_cards(stats_grid)
        
        # Progress section
        progress_frame = ttkb.Frame(stats_grid)
        progress_frame.pack(fill=tk.X, pady=10)
        
        # JD Analysis Progress
        jd_progress_frame = ttkb.Frame(progress_frame)
        jd_progress_frame.pack(fill=tk.X, pady=5)
        ttkb.Label(jd_progress_frame, text="Job Description Analysis Progress", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.jd_progress = ttkb.Floodgauge(jd_progress_frame, bootstyle="success", mask="{}%")
        self.jd_progress.pack(fill=tk.X, pady=2)
        
        # Resume Tailoring Progress
        resume_progress_frame = ttkb.Frame(progress_frame)
        resume_progress_frame.pack(fill=tk.X, pady=5)
        ttkb.Label(resume_progress_frame, text="Resume Tailoring Progress", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.resume_progress = ttkb.Floodgauge(resume_progress_frame, bootstyle="info", mask="{}%")
        self.resume_progress.pack(fill=tk.X, pady=2)
        
        # Charts section
        charts_frame = ttkb.Frame(stats_grid)
        charts_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Configure matplotlib style
        plt.style.use('dark_background')
        
        # Create figure with subplots
        fig = Figure(figsize=(12, 6), dpi=100, facecolor='#2d2d2d')
        fig.patch.set_alpha(0.8)
        self.ax_ts = fig.add_subplot(221)  # Top left
        self.ax_stage = fig.add_subplot(222)  # Top right
        self.ax_pie = fig.add_subplot(223)  # Bottom left
        self.ax_bar = fig.add_subplot(224)  # Bottom right
        
        # Set subplot backgrounds
        for ax in [self.ax_ts, self.ax_stage, self.ax_pie, self.ax_bar]:
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
        
        self.canvas = FigureCanvasTkAgg(fig, master=charts_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Job Applications Tab
        jobs_frame = ttkb.Frame(paned)
        paned.add(jobs_frame, text="Job Applications")
        
        # Create job applications table
        self.create_job_table(jobs_frame)

        # Setup background updates
        self.log_queue = log_handler.get_queue()
        log_handler.subscribe(self._on_new_log)
        self.after(500, self._refresh_metrics)
            
        # Initialize stats
        self.job_count = 0
        self.applied_count = 0
        self.failed_count = 0
        self.current_status = "Stopped"
    
        self.protocol("WM_DELETE_WINDOW", self.on_close)
            
        # Initialize job data for table
        self.job_data = []
    
    def create_menu(self):
        menubar = Menu(self)
        self.config(menu=menubar)
            
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Logs", command=self.export_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
            
        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.manual_refresh)
            
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_docs)
        help_menu.add_command(label="About", command=self.show_about)
        
    def create_stat_cards(self, parent):
        # Create a frame for stat cards
        cards_frame = ttkb.Frame(parent)
        cards_frame.pack(fill=tk.X, pady=5)
            
        # Job Stats Card
        job_card = ttkb.Frame(cards_frame, bootstyle="secondary")
        job_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttkb.Label(job_card, text="🔍 Total Jobs Found", font=("Segoe UI", 12, "bold"), bootstyle="light").pack(pady=5)
        self.job_count_label = ttkb.Label(job_card, text="0", font=("Segoe UI", 18, "bold"), bootstyle="info")
        self.job_count_label.pack(pady=5)
            
        # Applied Jobs Card
        applied_card = ttkb.Frame(cards_frame, bootstyle="secondary")
        applied_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttkb.Label(applied_card, text="✅ Successfully Applied", font=("Segoe UI", 12, "bold"), bootstyle="light").pack(pady=5)
        self.applied_count_label = ttkb.Label(applied_card, text="0", font=("Segoe UI", 18, "bold"), bootstyle="success")
        self.applied_count_label.pack(pady=5)
            
        # Failed Jobs Card
        failed_card = ttkb.Frame(cards_frame, bootstyle="secondary")
        failed_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttkb.Label(failed_card, text="❌ Failed Applications", font=("Segoe UI", 12, "bold"), bootstyle="light").pack(pady=5)
        self.failed_count_label = ttkb.Label(failed_card, text="0", font=("Segoe UI", 18, "bold"), bootstyle="danger")
        self.failed_count_label.pack(pady=5)
            
        # Success Rate Card
        rate_card = ttkb.Frame(cards_frame, bootstyle="secondary")
        rate_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttkb.Label(rate_card, text="📊 Success Rate", font=("Segoe UI", 12, "bold"), bootstyle="light").pack(pady=5)
        self.success_rate_label = ttkb.Label(rate_card, text="0%", font=("Segoe UI", 18, "bold"), bootstyle="warning")
        self.success_rate_label.pack(pady=5)
        
    def create_job_table(self, parent):
        # Create frame for job table
        table_frame = ttkb.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        # Treeview for job applications
        columns = ("Job Title", "Company", "Location", "Date Applied", "Status", "Notes")
        self.job_tree = ttkb.Treeview(table_frame, columns=columns, show="headings", height=10)
            
        # Define headings
        for col in columns:
            self.job_tree.heading(col, text=col)
            self.job_tree.column(col, width=120)
            
        # Add scrollbar
        scrollbar = ttkb.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.job_tree.yview)
        self.job_tree.configure(yscrollcommand=scrollbar.set)
            
        # Pack the treeview and scrollbar
        self.job_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def start_bot(self):
        try:
            ok = self.controller.start()
            if ok:
                self.start_btn.config(state=tk.DISABLED)
                self.stop_btn.config(state=tk.NORMAL)
                self.pause_btn.config(state=tk.NORMAL)
                self.status_label.config(text="Status: Running")
                self.status_indicator.config(foreground="green")
                self.current_status = "Running"
                self.update_stats_display()
        except Exception as e:
            messagebox.showerror("Start Failed", str(e))
    
    def stop_bot(self):
        try:
            self.controller.stop()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Stopped")
            self.status_indicator.config(foreground="red")
            self.current_status = "Stopped"
            self.update_stats_display()
        except Exception as e:
            messagebox.showerror("Stop Failed", str(e))
        
    def toggle_pause(self):
        # Placeholder for pause functionality
        messagebox.showinfo("Pause", "Pause functionality would be implemented here")
    
    def export_logs(self):
        # Placeholder for export functionality
        messagebox.showinfo("Export Logs", "Logs export functionality would be implemented here")
        
    def manual_refresh(self):
        # Force a refresh of metrics
        self._refresh_metrics()
        
    def show_docs(self):
        messagebox.showinfo("Documentation", "Documentation would be available here")
        
    def show_about(self):
        messagebox.showinfo("About", "AI Job Finder Pro v1.0\nAutomated Job Application System\nPowered by AI and Machine Learning")
    
    def _on_new_log(self, msg: str):
        # Called in publisher context - keep it lightweight
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        # If AI stream messages come prefixed, show them in AI output
        if isinstance(msg, str) and msg.startswith('[AI]'):
            try:
                self.ai_output.insert(tk.END, msg.replace('[AI]', '').strip() + "\n")
                self.ai_output.see(tk.END)
            except Exception:
                pass
            
        # Process job application events
        if "applied to" in msg.lower():
            self.applied_count += 1
        elif "failed" in msg.lower() or "error" in msg.lower():
            self.failed_count += 1
            
        self.update_stats_display()
    
    def update_stats_display(self):
        # Update the stat labels
        self.job_count_label.config(text=str(self.job_count))
        self.applied_count_label.config(text=str(self.applied_count))
        self.failed_count_label.config(text=str(self.failed_count))
            
        # Calculate success rate
        total_attempts = self.applied_count + self.failed_count
        if total_attempts > 0:
            success_rate = round((self.applied_count / total_attempts) * 100, 1)
            self.success_rate_label.config(text=f"{success_rate}%")
        else:
            self.success_rate_label.config(text="0%")
            
        # Update stats summary label
        self.stats_label.config(text=f"📊 Jobs: {self.job_count} | Applied: {self.applied_count} | Failed: {self.failed_count}")
    
    def _refresh_metrics(self):
        data = metrics.get_metrics()
            
        # Update progress bars if metrics available
        jd = int(data.get("jd_progress", 0))
        rs = int(data.get("resume_progress", 0))
        self.jd_progress.configure(bootstyle="success")
        self.jd_progress.configure(value=jd)
        self.resume_progress.configure(bootstyle="info")
        self.resume_progress.configure(value=rs)
    
        # Update job counts
        jobs_processed = data.get("jobs_processed", 0)
        self.job_count = jobs_processed
            
        # time-series chart
        try:
            ts = metrics.get_time_series('jd_analysis')
            if ts and len(ts) > 0:
                self.ax_ts.clear()
                self.ax_ts.plot(list(range(len(ts))), ts, marker='o', color='#4CAF50')
                self.ax_ts.set_title('JD Analysis Durations (s)', color='white')
                self.ax_ts.grid(True, alpha=0.3)
        except Exception:
            pass
    
        # per-stage average bar chart
        try:
            stages = ['jd_analysis', 'question_answering']
            avgs = [metrics.get_average(s) for s in stages]
            self.ax_stage.clear()
            bars = self.ax_stage.bar(stages, avgs, color=['#4CAF50', '#2196F3'])
            self.ax_stage.set_title('Avg Processing Times (s)', color='white')
            self.ax_stage.grid(True, alpha=0.3)
            # Add value labels on bars
            for bar, avg in zip(bars, avgs):
                height = bar.get_height()
                self.ax_stage.text(bar.get_x() + bar.get_width()/2., height,
                                  f'{avg:.2f}s', ha='center', va='bottom', color='white')
        except Exception:
            pass
                
        # Pie chart for success/failure ratio
        try:
            total = self.applied_count + self.failed_count
            if total > 0:
                sizes = [self.applied_count, self.failed_count]
                labels = [f'Applied ({self.applied_count})', f'Failed ({self.failed_count})']
                colors = ['#4CAF50', '#F44336']
                self.ax_pie.clear()
                self.ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
                self.ax_pie.set_title('Application Success/Failure', color='white')
        except Exception:
            pass
                
        # Bar chart for different metrics
        try:
            metric_names = ['easy_applied', 'external_jobs', 'jd_analysis_count']
            metric_values = [data.get(name, 0) for name in metric_names]
            labels = ['Easy Applied', 'External Links', 'JD Analyses']
            self.ax_bar.clear()
            bars = self.ax_bar.bar(labels, metric_values, color=['#FF9800', '#9C27B0', '#00BCD4'])
            self.ax_bar.set_title('Application Metrics', color='white')
            self.ax_bar.grid(True, alpha=0.3)
            # Add value labels on bars
            for bar, val in zip(bars, metric_values):
                height = bar.get_height()
                self.ax_bar.text(bar.get_x() + bar.get_width()/2., height,
                                f'{int(val)}', ha='center', va='bottom', color='white')
        except Exception:
            pass
    
        try:
            self.canvas.draw_idle()
        except Exception:
            pass
            
        # Update stats display
        self.update_stats_display()
    
        self.after(1000, self._refresh_metrics)
    
    def on_close(self):
        try:
            log_handler.unsubscribe(self._on_new_log)
        except Exception:
            pass
        self.destroy()


# Controller wrapper that interacts with runAiBot
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
