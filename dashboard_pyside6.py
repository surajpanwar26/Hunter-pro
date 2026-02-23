"""Tabbed PySide6 dashboard for AI Hunter pro.

Production dashboard with a top-tab layout where the Home page contains
all settings and configuration controls (similar to the Tkinter dashboard
workflow) while preserving history/analytics/tailoring/help tabs.

Run:
    .venv\\Scripts\\python.exe dashboard_pyside6.py
"""

from __future__ import annotations

import sys
import csv
import queue
import threading
from pathlib import Path
from datetime import datetime
from functools import partial

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QFont

# Shared color palette
try:
    from config.colors import DASHBOARD_COLORS as _DC
except ImportError:
    _DC = {}  # fallback — inline hex values used below

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumHeight(64)
        self.setMaximumHeight(76)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")
        self.value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)


class OperatorDashboard(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Hunter pro — Operator Console")
        self.resize(1700, 1000)
        self._started_at = datetime.now()
        self._tick_counter = 0

        self._jobs = 0
        self._applied = 0
        self._failed = 0
        self._skipped = 0
        self._log_queue = None
        self._event_queue = None
        self._metrics_refresh_every_ticks = 3

        self._build_ui()
        self._apply_styles()
        self._refresh_runtime_metrics(force=True)
        self._setup_timer()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        outer.addWidget(self._build_topbar())
        outer.addWidget(self._build_cards())
        outer.addWidget(self._build_tabs(), 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_state = QLabel("System Ready")
        self.status_time = QLabel()
        status.addWidget(self.status_state)
        status.addPermanentWidget(self.status_time)

    def _build_topbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)

        left = QVBoxLayout()
        title = QLabel("🚀 AI Hunter pro — Premium Console")
        title.setObjectName("HeroTitle")
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(title)
        layout.addLayout(left)

        layout.addStretch()

        self.btn_start = self._mk_button("▶ Start", "BtnSuccess", self._start_bot)
        self.btn_autopilot = self._mk_button("✈ Autopilot", "BtnSuccess", self._start_autopilot)
        self.btn_stop = self._mk_button("⏹ Stop", "BtnDanger", self._stop_bot)
        self.btn_pause = self._mk_button("⏸ Pause", "BtnWarn", self._pause_bot)
        self.btn_live = self._mk_button("🧭 Side Panel", "BtnInfo", self._toggle_live_panel)

        for button in [self.btn_start, self.btn_autopilot, self.btn_stop, self.btn_pause, self.btn_live]:
            layout.addWidget(button)

        return frame

    def _build_cards(self) -> QWidget:
        row = QWidget()
        layout = QGridLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        self.card_jobs = MetricCard("Jobs Found", str(self._jobs), _DC.get("card_jobs_accent", "#38bdf8"))
        self.card_applied = MetricCard("Applied", str(self._applied), _DC.get("card_applied_accent", "#22c55e"))
        self.card_failed = MetricCard("Failed", str(self._failed), _DC.get("card_failed_accent", "#ef4444"))
        self.card_rate = MetricCard("Success Rate", self._rate_text(), _DC.get("card_rate_accent", "#a78bfa"))

        for col, card in enumerate([self.card_jobs, self.card_applied, self.card_failed, self.card_rate]):
            layout.addWidget(card, 0, col)

        return row

    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")

        self.tabs.addTab(self._build_home_tab(), "🏠 Home")
        self.tabs.addTab(self._build_history_tab(), "📜 History")
        self.tabs.addTab(self._build_analytics_tab(), "📊 Analytics")
        self.tabs.addTab(self._build_tailor_tab(), "✨ Resume Tailor")
        self.tabs.addTab(self._build_help_tab(), "❓ Help")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        return self.tabs

    def _build_home_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        splitter = QSplitter()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(8)

        quick_access = QGroupBox("🚀 Quick Access")
        quick_access.setMaximumHeight(112)
        quick_layout = QGridLayout(quick_access)
        quick_layout.setContentsMargins(8, 6, 8, 6)
        quick_layout.setHorizontalSpacing(6)
        quick_layout.setVerticalSpacing(4)
        quick_buttons = [
            self._mk_button("▶ Start Bot", "BtnSuccess", self._start_bot, height=30),
            self._mk_button("✈ Start Autopilot", "BtnSuccess", self._start_autopilot, height=30),
            self._mk_button("⏹ Stop Bot", "BtnDanger", self._stop_bot, height=30),
            self._mk_button("⏸ Pause Bot", "BtnWarn", self._pause_bot, height=30),
            self._mk_button("🧭 Open Side Panel", "BtnInfo", self._toggle_live_panel, height=30),
            self._mk_button("▶ Start Scheduler", "BtnSuccess", self._start_scheduler, height=30),
            self._mk_button("⏹ Stop Scheduler", "BtnDanger", self._stop_scheduler, height=30),
        ]
        for idx, button in enumerate(quick_buttons):
            quick_layout.addWidget(button, idx // 4, idx % 4)
        left_layout.addWidget(quick_access)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.home_scroll = settings_scroll

        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)
        settings_layout.setSpacing(8)

        home_settings = QGroupBox("⚙️ Settings & Configuration")
        home_settings_layout = QVBoxLayout(home_settings)
        home_settings_layout.setSpacing(8)

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(8)
        settings_grid.setVerticalSpacing(8)
        settings_sections = [
            self._settings_pilot(),
            self._settings_scheduler(),
            self._settings_job_search(),
            self._settings_bot_behavior(),
            self._settings_form_filling(),
            self._settings_resume_tailor(),
            self._settings_control_alerts(),
            self._settings_browser_ui(),
            self._settings_extension(),
            self._settings_prefill(),
        ]
        for idx, section in enumerate(settings_sections):
            settings_grid.addWidget(section, idx // 2, idx % 2)
        home_settings_layout.addLayout(settings_grid)

        action_row = QGridLayout()
        action_row.setHorizontalSpacing(8)
        action_row.setVerticalSpacing(6)
        action_row.addWidget(self._mk_button("💾 Apply", "BtnSuccess", self._apply_all_settings, height=30), 0, 0)
        action_row.addWidget(self._mk_button("🔄 Reset", "BtnWarn", self._reset_defaults, height=30), 0, 1)
        action_row.addWidget(self._mk_button("📤 Export Ext", "BtnInfo", self._export_extension_config, height=30), 1, 0)
        action_row.addWidget(self._mk_button("🔁 Reload Ext", "BtnNeutral", self._reload_extension, height=30), 1, 1)
        home_settings_layout.addLayout(action_row)

        settings_layout.addWidget(home_settings)
        settings_scroll.setWidget(settings_container)
        left_layout.addWidget(settings_scroll)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setWidget(self._build_live_operations())
        right_scroll.setMinimumWidth(360)

        splitter.addWidget(left)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([1180, 500])

        root.addWidget(splitter)
        return page

    def _build_live_operations(self) -> QWidget:
        section = QWidget()
        root = QVBoxLayout(section)
        root.setSpacing(8)

        stream_group = QGroupBox("Live Activity Stream")
        stream_layout = QVBoxLayout(stream_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(220)
        stream_layout.addWidget(self.log_box)
        root.addWidget(stream_group)

        browser_group = QGroupBox("Browser Session")
        browser_layout = QVBoxLayout(browser_group)
        self.browser_preview = QTextEdit()
        self.browser_preview.setReadOnly(True)
        self.browser_preview.setMinimumHeight(90)
        self.browser_preview.setMaximumHeight(130)
        self.browser_preview.setPlainText(
            "LinkedIn Browser View\n"
            "- Active tab: Easy Apply jobs\n"
            "- URL: https://www.linkedin.com/jobs/\n"
            "- Status: Ready"
        )
        browser_layout.addWidget(self.browser_preview)
        root.addWidget(browser_group)

        details_and_pipeline = QVBoxLayout()

        details_group = QGroupBox("Important Details")
        details_layout = QGridLayout(details_group)
        details_layout.addWidget(QLabel("Role"), 0, 0)
        self.live_role_value = QLabel("Software Engineer")
        details_layout.addWidget(self.live_role_value, 0, 1)
        details_layout.addWidget(QLabel("Company"), 1, 0)
        self.live_company_value = QLabel("Example Corp")
        details_layout.addWidget(self.live_company_value, 1, 1)
        details_layout.addWidget(QLabel("Location"), 2, 0)
        self.live_location_value = QLabel("Remote / US")
        details_layout.addWidget(self.live_location_value, 2, 1)

        self.job_progress = QProgressBar()
        self.job_progress.setValue(0)
        details_layout.addWidget(QLabel("Current Job Progress"), 3, 0)
        details_layout.addWidget(self.job_progress, 3, 1)
        details_and_pipeline.addWidget(details_group, 1)

        pipeline = QGroupBox("AI Pipeline")
        pipeline_grid = QGridLayout(pipeline)

        self.jd_progress = QProgressBar()
        self.jd_progress.setValue(0)
        self.resume_progress = QProgressBar()
        self.resume_progress.setValue(0)
        self.form_progress = QProgressBar()
        self.form_progress.setValue(0)

        pipeline_grid.addWidget(QLabel("JD Analysis"), 0, 0)
        pipeline_grid.addWidget(self.jd_progress, 0, 1)
        pipeline_grid.addWidget(QLabel("Resume Tailoring"), 1, 0)
        pipeline_grid.addWidget(self.resume_progress, 1, 1)
        pipeline_grid.addWidget(QLabel("Form Filler"), 2, 0)
        pipeline_grid.addWidget(self.form_progress, 2, 1)
        details_and_pipeline.addWidget(pipeline, 1)
        root.addLayout(details_and_pipeline)

        controls_group = QGroupBox("Live Job Controls")
        controls_layout = QVBoxLayout(controls_group)

        actions_group = QGroupBox("Actions")
        grid = QGridLayout(actions_group)
        action_buttons = [
            ("Apply", self._apply_now),
            ("Skip", self._skip_job),
            ("Retry", self._retry_job),
            ("Open Job", self._open_job),
            ("Save", self._save_snapshot),
            ("Flag", self._flag_job),
            ("Pause Before Submit", self._toggle_pause_submit),
            ("Continue", self._continue_flow),
            ("Export Logs", self._export_logs),
            ("Reset Counters", self._reset_counters),
        ]
        for index, (label, handler) in enumerate(action_buttons):
            button = self._mk_button(label, "BtnNeutral", handler, height=30)
            grid.addWidget(button, index // 2, index % 2)
        controls_layout.addWidget(actions_group)
        root.addWidget(controls_group)

        self._log("Dashboard boot complete")
        self._log("Scheduler ready")
        self._log("Waiting for action")
        return section

    def _settings_bot_behavior(self) -> QGroupBox:
        group, layout = self._mk_group("🤖 Bot Behavior")
        toggles = ["Run Non-Stop", "Alternate Sort", "Cycle Date Posted", "Stop at 24hr", "Close Tabs", "Follow Companies"]
        for idx, label in enumerate(toggles):
            layout.addWidget(self._mk_toggle(label), idx // 3, idx % 3)

        layout.addWidget(QLabel("Max Jobs"), 2, 0)
        spin = NoWheelSpinBox()
        spin.setRange(0, 500)
        spin.setValue(50)
        spin.valueChanged.connect(lambda value: self._log(f"Max Jobs set to {value}"))
        layout.addWidget(spin, 2, 1)
        return group

    def _settings_form_filling(self) -> QGroupBox:
        group, layout = self._mk_group("📝 Form Filling")
        layout.addWidget(self._mk_toggle("Fast Mode"), 0, 0)
        layout.addWidget(self._mk_toggle("Smart Form Filler"), 0, 1)

        layout.addWidget(QLabel("Delay Multiplier"), 1, 0)
        combo = NoWheelComboBox()
        combo.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
        combo.currentTextChanged.connect(lambda text: self._log(f"Delay Multiplier changed to {text}"))
        layout.addWidget(combo, 1, 1)
        return group

    def _settings_resume_tailor(self) -> QGroupBox:
        group, layout = self._mk_group("📄 Resume Tailoring")
        for idx, label in enumerate(["Enable Resume Tailoring", "Confirm After Filters", "Prompt Before JD"]):
            layout.addWidget(self._mk_toggle(label), 0, idx)

        layout.addWidget(QLabel("Upload Format"), 1, 0)
        combo = NoWheelComboBox()
        combo.addItems(["Auto", "PDF", "DOCX"])
        combo.currentTextChanged.connect(lambda text: self._log(f"Upload Format changed to {text}"))
        layout.addWidget(combo, 1, 1)
        return group

    def _settings_browser_ui(self) -> QGroupBox:
        group, layout = self._mk_group("🖥 Browser & UI")
        labels = ["Show Browser", "Disable Extensions", "Safe Mode", "Smooth Scroll", "Keep Screen Awake", "Stealth Mode"]
        for idx, label in enumerate(labels):
            layout.addWidget(self._mk_toggle(label), idx // 3, idx % 3)
        return group

    def _settings_control_alerts(self) -> QGroupBox:
        group, layout = self._mk_group("🎛 Control & Alerts")
        labels = ["Pause Before Submit", "Pause At Failed Question", "Show AI Error Alerts"]
        for idx, label in enumerate(labels):
            layout.addWidget(self._mk_toggle(label), 0, idx)
        return group

    def _settings_extension(self) -> QGroupBox:
        group, layout = self._mk_group("🧩 Extension & Form Filler")
        for idx, label in enumerate(["Enable Extension", "Auto Sync", "AI Learning"]):
            layout.addWidget(self._mk_toggle(label), 0, idx)

        layout.addWidget(QLabel("Detection Mode"), 1, 0)
        combo = NoWheelComboBox()
        combo.addItems(["LinkedIn", "Universal", "Smart Detect"])
        combo.currentTextChanged.connect(lambda text: self._log(f"Detection Mode changed to {text}"))
        layout.addWidget(combo, 1, 1)
        return group

    def _settings_pilot(self) -> QGroupBox:
        group, layout = self._mk_group("✈ Pilot Mode")
        layout.addWidget(self._mk_toggle("Pilot Mode Enabled"), 0, 0)
        layout.addWidget(self._mk_toggle("Continue on Error"), 0, 1)

        layout.addWidget(QLabel("Resume Mode"), 1, 0)
        resume_mode = NoWheelComboBox()
        resume_mode.addItems(["tailored", "default", "preselected", "skip"])
        resume_mode.currentTextChanged.connect(lambda text: self._log(f"Pilot Resume Mode changed to {text}"))
        layout.addWidget(resume_mode, 1, 1)

        layout.addWidget(QLabel("Delay (sec)"), 1, 2)
        delay = NoWheelSpinBox()
        delay.setRange(1, 30)
        delay.setValue(5)
        delay.valueChanged.connect(lambda value: self._log(f"Pilot Delay changed to {value}s"))
        layout.addWidget(delay, 1, 3)

        layout.addWidget(QLabel("Max Apps"), 2, 0)
        max_apps = NoWheelSpinBox()
        max_apps.setRange(0, 500)
        max_apps.setValue(100)
        max_apps.valueChanged.connect(lambda value: self._log(f"Pilot Max Apps changed to {value}"))
        layout.addWidget(max_apps, 2, 1)
        return group

    def _settings_prefill(self) -> QGroupBox:
        group, layout = self._mk_group("🧠 Autopilot Form Pre-fill")
        labels = [
            "Visa Required",
            "Work Authorization",
            "Willing Relocate",
            "Remote Preference",
            "Start Immediately",
            "Background Check",
            "Commute OK",
        ]
        for idx, label in enumerate(labels):
            layout.addWidget(QLabel(label), idx // 2, (idx % 2) * 2)
            combo = NoWheelComboBox()
            combo.addItems(["Yes", "No"])
            combo.currentTextChanged.connect(partial(self._prefill_changed, label))
            layout.addWidget(combo, idx // 2, (idx % 2) * 2 + 1)

        layout.addWidget(QLabel("Chrome Wait Time (sec)"), 4, 0)
        wait = NoWheelSpinBox()
        wait.setRange(5, 30)
        wait.setValue(10)
        wait.valueChanged.connect(lambda value: self._log(f"Autopilot Chrome Wait Time changed to {value}s"))
        layout.addWidget(wait, 4, 1)
        return group

    def _settings_scheduler(self) -> QGroupBox:
        group, layout = self._mk_group("📅 Scheduling")
        layout.addWidget(self._mk_toggle("Scheduling Enabled"), 0, 0)

        layout.addWidget(QLabel("Type"), 0, 1)
        schedule_type = NoWheelComboBox()
        schedule_type.addItems(["interval", "daily", "weekly"])
        schedule_type.currentTextChanged.connect(lambda text: self._log(f"Schedule Type changed to {text}"))
        layout.addWidget(schedule_type, 0, 2)

        layout.addWidget(QLabel("Interval Hours"), 1, 0)
        interval = NoWheelSpinBox()
        interval.setRange(1, 24)
        interval.setValue(4)
        interval.valueChanged.connect(lambda value: self._log(f"Schedule Interval changed to {value}h"))
        layout.addWidget(interval, 1, 1)

        layout.addWidget(QLabel("Max Runtime (min)"), 1, 2)
        runtime = NoWheelSpinBox()
        runtime.setRange(10, 480)
        runtime.setValue(120)
        runtime.valueChanged.connect(lambda value: self._log(f"Schedule Runtime changed to {value} min"))
        layout.addWidget(runtime, 1, 3)

        layout.addWidget(QLabel("Max Applications"), 2, 0)
        max_apps = NoWheelSpinBox()
        max_apps.setRange(0, 500)
        max_apps.setValue(50)
        max_apps.valueChanged.connect(lambda value: self._log(f"Schedule Max Applications changed to {value}"))
        layout.addWidget(max_apps, 2, 1)

        start_scheduler = self._mk_button("▶ Start Scheduler", "BtnSuccess", self._start_scheduler, height=32)
        stop_scheduler = self._mk_button("⏹ Stop Scheduler", "BtnDanger", self._stop_scheduler, height=32)
        layout.addWidget(start_scheduler, 3, 2)
        layout.addWidget(stop_scheduler, 3, 3)
        return group

    def _settings_job_search(self) -> QGroupBox:
        group, layout = self._mk_group("🔍 Job Search")

        layout.addWidget(QLabel("Search Terms"), 0, 0)
        self.search_terms = QLineEdit("Software Engineer, Python Developer, React Developer")
        self.search_terms.editingFinished.connect(lambda: self._log(f"Search Terms set to: {self.search_terms.text()}"))
        layout.addWidget(self.search_terms, 0, 1, 1, 3)

        layout.addWidget(QLabel("Location"), 1, 0)
        self.search_location = QLineEdit("United States")
        self.search_location.editingFinished.connect(lambda: self._log(f"Search Location set to: {self.search_location.text()}"))
        layout.addWidget(self.search_location, 1, 1)

        layout.addWidget(QLabel("Date Posted"), 1, 2)
        posted = NoWheelComboBox()
        posted.addItems(["Past 24 hours", "Past week", "Past month"])
        posted.currentTextChanged.connect(lambda text: self._log(f"Date Posted changed to {text}"))
        layout.addWidget(posted, 1, 3)

        layout.addWidget(self._mk_toggle("Easy Apply Only"), 2, 0)
        layout.addWidget(self._mk_toggle("Randomize Search"), 2, 1)
        return group

    def _build_history_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        top = QHBoxLayout()
        self.history_filter = QComboBox()
        self.history_filter.addItems(["All", "Applied", "Failed", "Skipped", "Today", "This Week"])
        self.history_filter.currentTextChanged.connect(lambda text: self._log(f"History filter changed to {text}"))

        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Search job title/company...")
        self.history_search.textChanged.connect(lambda text: self._log(f"History search: {text}"))

        top.addWidget(QLabel("Filter"))
        top.addWidget(self.history_filter)
        top.addWidget(self.history_search, 1)

        top.addWidget(self._mk_button("Export CSV", "BtnSuccess", self._export_history_csv, height=32))
        top.addWidget(self._mk_button("Export PDF", "BtnInfo", self._export_history_pdf, height=32))
        top.addWidget(self._mk_button("Clear", "BtnDanger", self._clear_history, height=32))

        root.addLayout(top)

        self.history_table = QTableWidget(15, 7)
        self.history_table.setHorizontalHeaderLabels(["Time", "Job", "Company", "Location", "Status", "AI Score", "Action"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for row in range(15):
            values = [
                "2026-02-14 13:12",
                f"Role {row + 1}",
                "Example Corp",
                "Remote",
                "Applied" if row % 3 else "Failed",
                str(70 + (row % 25)),
                "View",
            ]
            for col, value in enumerate(values):
                self.history_table.setItem(row, col, QTableWidgetItem(value))
        root.addWidget(self.history_table)
        return page

    def _build_analytics_tab(self) -> QWidget:
        page = QWidget()
        root = QGridLayout(page)

        self.analytics_bars: list[QProgressBar] = []
        for idx, title in enumerate(["Application Status", "Performance Metrics", "AI Statistics", "Session Info"]):
            group = QGroupBox(title)
            layout = QVBoxLayout(group)
            for metric_idx in range(4):
                layout.addWidget(QLabel(f"Metric {metric_idx + 1}"))
                bar = QProgressBar()
                bar.setValue(20 + metric_idx * 20)
                layout.addWidget(bar)
                self.analytics_bars.append(bar)

            root.addWidget(group, idx // 2, idx % 2)

        return page

    def _build_tailor_tab(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)

        left = QGroupBox("Input")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Resume File"))
        self.resume_path = QLineEdit("all resumes/master resume/resume.pdf")
        left_layout.addWidget(self.resume_path)
        left_layout.addWidget(QLabel("Job Description"))
        self.job_description = QTextEdit()
        self.job_description.setPlainText("Paste full JD here...")
        left_layout.addWidget(self.job_description)
        left_layout.addWidget(QLabel("Custom Instructions"))
        self.instructions = QLineEdit("Focus on backend impact and measurable outcomes")
        left_layout.addWidget(self.instructions)

        right = QGroupBox("Actions")
        right_layout = QVBoxLayout(right)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "groq", "openai", "deepseek", "gemini"])
        self.provider_combo.currentTextChanged.connect(lambda text: self._log(f"AI Provider changed to {text}"))

        right_layout.addWidget(QLabel("AI Provider"))
        right_layout.addWidget(self.provider_combo)

        right_layout.addWidget(self._mk_button("✨ Open Enhanced Tailor", "BtnSuccess", self._open_enhanced_tailor))
        right_layout.addWidget(self._mk_button("📝 Quick Tailor (Classic)", "BtnInfo", self._quick_tailor))
        right_layout.addWidget(self._mk_button("📥 Save Tailored Resume", "BtnNeutral", self._save_tailored_resume))
        right_layout.addWidget(self._mk_button("👁 Preview Output", "BtnNeutral", self._preview_output))
        right_layout.addStretch()

        root.addWidget(left, 2)
        root.addWidget(right, 1)
        return page

    def _build_help_tab(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        links = QGroupBox("Quick Links")
        links_layout = QVBoxLayout(links)
        links_layout.addWidget(self._mk_button("📖 Open README", "BtnNeutral", lambda: self._open_doc("README"), height=32))
        links_layout.addWidget(self._mk_button("📖 Open Enhanced Resume Guide", "BtnNeutral", lambda: self._open_doc("Enhanced Resume Guide"), height=32))
        links_layout.addWidget(self._mk_button("📖 Open Security Setup", "BtnNeutral", lambda: self._open_doc("Security Setup"), height=32))
        links_layout.addWidget(self._mk_button("📖 Open Changelog", "BtnNeutral", lambda: self._open_doc("Changelog"), height=32))
        root.addWidget(links)

        shortcuts = QGroupBox("Keyboard Shortcuts")
        shortcuts_layout = QGridLayout(shortcuts)
        pairs = [("Alt+1", "Home"), ("Alt+2", "History"), ("Alt+3", "Analytics"), ("F5", "Refresh"), ("Ctrl+S", "Start")]
        for row, (shortcut, desc) in enumerate(pairs):
            shortcuts_layout.addWidget(QLabel(shortcut), row, 0)
            shortcuts_layout.addWidget(QLabel(desc), row, 1)
        root.addWidget(shortcuts)

        about = QGroupBox("About")
        about_layout = QVBoxLayout(about)
        about_layout.addWidget(QLabel("AI Hunter pro — PySide6 Operator Dashboard"))
        about_layout.addWidget(QLabel("Home page includes complete settings and configuration controls."))
        root.addWidget(about)

        root.addStretch()
        return page

    def _mk_group(self, title: str) -> tuple[QGroupBox, QGridLayout]:
        group = QGroupBox(title)
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(8)
        return group, layout

    def _mk_button(self, label: str, object_name: str, handler, height: int = 38) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName(object_name)
        button.setFixedHeight(height)
        button.setMinimumWidth(96)
        button.setMaximumWidth(170)
        button.clicked.connect(handler)
        return button

    def _mk_toggle(self, label: str) -> QPushButton:
        toggle = QPushButton(label)
        toggle.setCheckable(True)
        toggle.setObjectName("TogglePill")
        toggle.setFixedHeight(34)
        toggle.toggled.connect(partial(self._on_toggle_changed, label))
        return toggle

    def _on_tab_changed(self, index: int) -> None:
        text = self.tabs.tabText(index)
        self._log(f"Tab changed: {text}")

    def _setup_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self) -> None:
        now = datetime.now()
        runtime = now - self._started_at
        self._tick_counter += 1
        self.status_time.setText(f"{now:%Y-%m-%d %H:%M:%S} • Runtime {str(runtime).split('.')[0]}")

        self._drain_dashboard_event_queue()
        self._drain_dashboard_log_queue()
        if self._tick_counter % self._metrics_refresh_every_ticks == 0:
            self._refresh_runtime_metrics()

        self._sync_live_panel_window()

    def _rate_text(self) -> str:
        total = self._applied + self._failed
        if total <= 0:
            return "0%"
        return f"{round((self._applied / total) * 100)}%"

    def _update_cards(self) -> None:
        self.card_jobs.value_label.setText(str(self._jobs))
        self.card_applied.value_label.setText(str(self._applied))
        self.card_failed.value_label.setText(str(self._failed))
        self.card_rate.value_label.setText(self._rate_text())

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {message}")
        if hasattr(self, "live_panel_log_box") and self.live_panel_log_box is not None:
            self.live_panel_log_box.setPlainText(self.log_box.toPlainText())
            self.live_panel_log_box.verticalScrollBar().setValue(self.live_panel_log_box.verticalScrollBar().maximum())

    def _drain_dashboard_log_queue(self) -> None:
        if self._log_queue is None:
            try:
                from modules.dashboard import log_handler
                self._log_queue = log_handler.get_queue()
            except Exception:
                return

        try:
            while True:
                entry = self._log_queue.get_nowait()
                self._log(str(entry))
        except queue.Empty:
            pass

    def _drain_dashboard_event_queue(self) -> None:
        if self._event_queue is None:
            try:
                from modules.dashboard import log_handler
                self._event_queue = log_handler.get_event_queue()
            except Exception:
                return

        try:
            while True:
                payload = self._event_queue.get_nowait()
                if isinstance(payload, dict):
                    self._handle_structured_event(payload)
        except queue.Empty:
            pass
        except Exception:
            pass

    def _handle_structured_event(self, payload: dict) -> None:
        event = str(payload.get("event", "")).strip().lower()
        data = payload.get("data") or {}

        if event == "bot_session_started":
            self.jd_progress.setValue(0)
            self.resume_progress.setValue(0)
            self.form_progress.setValue(0)
            self.job_progress.setValue(0)
            self._set_status("Autopilot Running")

        elif event == "job_context":
            title = str(data.get("title") or "-")
            company = str(data.get("company") or "-")
            location = str(data.get("location") or "-")
            self.live_role_value.setText(title)
            self.live_company_value.setText(company)
            self.live_location_value.setText(location)

        elif event == "jd_analysis_started":
            self.jd_progress.setValue(max(self.jd_progress.value(), 20))
        elif event == "jd_analysis_completed":
            self.jd_progress.setValue(100)

        elif event == "resume_tailoring_started":
            self.resume_progress.setValue(max(self.resume_progress.value(), 20))
        elif event == "resume_tailoring_completed":
            self.resume_progress.setValue(100)

        elif event == "form_filling_started":
            self.form_progress.setValue(max(self.form_progress.value(), 25))
        elif event == "form_filling_completed":
            self.form_progress.setValue(100)

        elif event == "application_submitted":
            self.form_progress.setValue(100)
            self.job_progress.setValue(100)
            self._refresh_runtime_metrics(force=True)

        elif event == "application_failed":
            self.form_progress.setValue(max(5, self.form_progress.value() - 20))
            self._refresh_runtime_metrics(force=True)

    def _count_csv_rows(self, path: Path) -> int:
        try:
            if not path.exists():
                return 0
            with open(path, "r", encoding="utf-8", errors="replace") as file:
                reader = csv.reader(file)
                next(reader, None)
                return sum(1 for _ in reader)
        except Exception:
            return 0

    def _refresh_runtime_metrics(self, force: bool = False) -> None:
        run_ai_bot = sys.modules.get("runAiBot")

        if run_ai_bot is not None:
            easy = int(getattr(run_ai_bot, "easy_applied_count", 0) or 0)
            external = int(getattr(run_ai_bot, "external_jobs_count", 0) or 0)
            failed = int(getattr(run_ai_bot, "failed_count", 0) or 0)
            skipped = int(getattr(run_ai_bot, "skip_count", 0) or 0)

            self._applied = easy + external
            self._failed = failed
            self._skipped = skipped

            max_jobs = int(getattr(run_ai_bot, "max_jobs_to_process", 0) or 0)
            processed = self._applied + self._failed + self._skipped
            self._jobs = max(0, max_jobs - processed) if max_jobs > 0 else 0

            if max_jobs > 0:
                progress = min(100, int((self._applied / max_jobs) * 100))
                self.job_progress.setValue(progress)

        else:
            base = Path("all excels")
            self._applied = self._count_csv_rows(base / "all_applied_applications_history.csv")
            self._failed = self._count_csv_rows(base / "all_failed_applications_history.csv")
            self._jobs = 0

        self._update_cards()

    def _update_pipeline_from_log(self, message: str) -> None:
        text = message.lower()
        if "jd" in text or "job description" in text:
            self.jd_progress.setValue(max(self.jd_progress.value(), 40))
        if "tailor" in text or "resume" in text:
            self.resume_progress.setValue(max(self.resume_progress.value(), 55))
        if "form" in text or "question" in text:
            self.form_progress.setValue(max(self.form_progress.value(), 70))
        if "submitted" in text or "apply clicked" in text or "applied" in text:
            self.jd_progress.setValue(100)
            self.resume_progress.setValue(100)
            self.form_progress.setValue(100)
        if "failed" in text or "error" in text:
            self.form_progress.setValue(max(10, self.form_progress.value() - 15))

    def _set_status(self, text: str) -> None:
        self.status_state.setText(text)

    def _on_toggle_changed(self, label: str, state: bool) -> None:
        value = "ON" if state else "OFF"
        self._log(f"{label}: {value}")

    def _prefill_changed(self, label: str, value: str) -> None:
        self._log(f"{label}: {value}")

    # ------------------------------------------------------------------
    #  Bot lifecycle helpers (run bot in a background thread)
    # ------------------------------------------------------------------
    _bot_thread: threading.Thread | None = None
    _bot_stop_event: threading.Event | None = None

    def _launch_bot_thread(self, autopilot: bool = False) -> None:
        """Import and run the bot in a daemon thread."""
        if self._bot_thread and self._bot_thread.is_alive():
            self._log("Bot is already running")
            return
        self._bot_stop_event = threading.Event()

        def _run() -> None:
            try:
                import runAiBot  # noqa: F811 — lazy import, heavy module
                runAiBot.main()
            except SystemExit:
                pass
            except Exception as exc:
                self._log(f"Bot error: {exc}")
            finally:
                QTimer.singleShot(0, lambda: self._set_status("Bot Stopped"))

        self._bot_thread = threading.Thread(target=_run, daemon=True, name="bot-worker")
        self._bot_thread.start()

    def _start_bot(self) -> None:
        self._set_status("Bot Running")
        self._log("Start pressed — launching bot thread")
        self._launch_bot_thread(autopilot=False)

    def _start_autopilot(self) -> None:
        self._set_status("Autopilot Running")
        self._log("Start Autopilot pressed — launching bot thread (autopilot)")
        self._launch_bot_thread(autopilot=True)

    def _stop_bot(self) -> None:
        self._set_status("Bot Stopped")
        self._log("Stop pressed — requesting bot stop")
        if self._bot_stop_event:
            self._bot_stop_event.set()
        # Signal the bot's global stop flag if exposed
        run_ai_bot = sys.modules.get("runAiBot")
        if run_ai_bot and hasattr(run_ai_bot, "stop_bot"):
            run_ai_bot.stop_bot = True

    def _pause_bot(self) -> None:
        self._set_status("Bot Paused")
        self._log("Pause pressed — toggling pause flag")
        run_ai_bot = sys.modules.get("runAiBot")
        if run_ai_bot and hasattr(run_ai_bot, "pause_bot"):
            run_ai_bot.pause_bot = not getattr(run_ai_bot, "pause_bot", False)
            state = "Paused" if run_ai_bot.pause_bot else "Resumed"
            self._set_status(f"Bot {state}")

    def _toggle_live_panel(self) -> None:
        if hasattr(self, "live_panel_window") and self.live_panel_window is not None and self.live_panel_window.isVisible():
            self._close_live_panel_window()
            return

        self.live_panel_window = QMainWindow(self)
        self.live_panel_window.setWindowTitle("Side Panel — Live Monitor")
        self.live_panel_window.resize(430, 860)
        self._side_panel_anchor = "right"

        container = QWidget()
        layout = QVBoxLayout(container)

        dock_controls = QHBoxLayout()
        self.btn_side_move = self._mk_button("⬅ Move Left", "BtnNeutral", self._toggle_side_panel_anchor, height=28)
        dock_controls.addWidget(self.btn_side_move)
        dock_controls.addStretch()
        layout.addLayout(dock_controls)

        panel_browser = QGroupBox("Browser Session")
        panel_browser_layout = QVBoxLayout(panel_browser)
        self.live_panel_browser_preview = QTextEdit()
        self.live_panel_browser_preview.setReadOnly(True)
        self.live_panel_browser_preview.setMinimumHeight(90)
        self.live_panel_browser_preview.setMaximumHeight(130)
        panel_browser_layout.addWidget(self.live_panel_browser_preview)
        layout.addWidget(panel_browser)

        panel_log = QGroupBox("Live Activity")
        panel_log_layout = QVBoxLayout(panel_log)
        self.live_panel_log_box = QTextEdit()
        self.live_panel_log_box.setReadOnly(True)
        self.live_panel_log_box.setMinimumHeight(250)
        panel_log_layout.addWidget(self.live_panel_log_box)
        layout.addWidget(panel_log)

        panel_details = QGroupBox("Important Details")
        panel_details_grid = QGridLayout(panel_details)
        panel_details_grid.addWidget(QLabel("Role"), 0, 0)
        self.live_panel_role_value = QLabel("-")
        panel_details_grid.addWidget(self.live_panel_role_value, 0, 1)
        panel_details_grid.addWidget(QLabel("Company"), 1, 0)
        self.live_panel_company_value = QLabel("-")
        panel_details_grid.addWidget(self.live_panel_company_value, 1, 1)
        panel_details_grid.addWidget(QLabel("Location"), 2, 0)
        self.live_panel_location_value = QLabel("-")
        panel_details_grid.addWidget(self.live_panel_location_value, 2, 1)
        panel_details_grid.addWidget(QLabel("Progress"), 3, 0)
        self.live_panel_job_progress = QProgressBar()
        panel_details_grid.addWidget(self.live_panel_job_progress, 3, 1)
        layout.addWidget(panel_details)

        panel_pipeline = QGroupBox("AI Pipeline")
        panel_pipeline_grid = QGridLayout(panel_pipeline)
        panel_pipeline_grid.addWidget(QLabel("JD Analysis"), 0, 0)
        self.live_panel_jd_progress = QProgressBar()
        panel_pipeline_grid.addWidget(self.live_panel_jd_progress, 0, 1)
        panel_pipeline_grid.addWidget(QLabel("Resume Tailoring"), 1, 0)
        self.live_panel_resume_progress = QProgressBar()
        panel_pipeline_grid.addWidget(self.live_panel_resume_progress, 1, 1)
        panel_pipeline_grid.addWidget(QLabel("Form Filler"), 2, 0)
        self.live_panel_form_progress = QProgressBar()
        panel_pipeline_grid.addWidget(self.live_panel_form_progress, 2, 1)
        layout.addWidget(panel_pipeline)

        self.live_panel_window.setCentralWidget(container)
        self.live_panel_window.destroyed.connect(lambda _: self._close_live_panel_window(reset_only=True))
        self._sync_live_panel_window()
        self._position_side_panel_window()
        self.live_panel_window.show()

        self.btn_live.setText("🧭 Close Side Panel")
        self._set_status("Side panel opened")
        self._log("Opened narrow side panel live monitor")

    def _toggle_side_panel_anchor(self) -> None:
        self._side_panel_anchor = "left" if getattr(self, "_side_panel_anchor", "right") == "right" else "right"
        if hasattr(self, "btn_side_move") and self.btn_side_move is not None:
            self.btn_side_move.setText("➡ Move Right" if self._side_panel_anchor == "left" else "⬅ Move Left")
        self._position_side_panel_window()

    def _position_side_panel_window(self) -> None:
        if not hasattr(self, "live_panel_window") or self.live_panel_window is None:
            return
        frame = self.frameGeometry()
        panel_w = self.live_panel_window.width()
        x = frame.left() - panel_w - 8 if getattr(self, "_side_panel_anchor", "right") == "left" else frame.right() + 8
        y = max(40, frame.top())
        self.live_panel_window.move(x, y)

    def moveEvent(self, event) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self._position_side_panel_window()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._position_side_panel_window()

    def _close_live_panel_window(self, reset_only: bool = False) -> None:
        if not reset_only and hasattr(self, "live_panel_window") and self.live_panel_window is not None:
            self.live_panel_window.close()
        self.live_panel_window = None
        self.live_panel_browser_preview = None
        self.live_panel_log_box = None
        self.live_panel_role_value = None
        self.live_panel_company_value = None
        self.live_panel_location_value = None
        self.live_panel_job_progress = None
        self.live_panel_jd_progress = None
        self.live_panel_resume_progress = None
        self.live_panel_form_progress = None
        self.btn_side_move = None
        try:
            self.btn_live.setText("🧭 Side Panel")
            self._set_status("System Ready")
        except RuntimeError:
            pass

    def _sync_live_panel_window(self) -> None:
        if not hasattr(self, "live_panel_window") or self.live_panel_window is None:
            return
        if self.live_panel_browser_preview is not None:
            self.live_panel_browser_preview.setPlainText(self.browser_preview.toPlainText())
        if self.live_panel_log_box is not None:
            self.live_panel_log_box.setPlainText(self.log_box.toPlainText())
        panel_role = getattr(self, "live_panel_role_value", None)
        panel_company = getattr(self, "live_panel_company_value", None)
        panel_location = getattr(self, "live_panel_location_value", None)
        panel_job_progress = getattr(self, "live_panel_job_progress", None)
        panel_jd_progress = getattr(self, "live_panel_jd_progress", None)
        panel_resume_progress = getattr(self, "live_panel_resume_progress", None)
        panel_form_progress = getattr(self, "live_panel_form_progress", None)

        if panel_role is not None:
            panel_role.setText(self.live_role_value.text())
        if panel_company is not None:
            panel_company.setText(self.live_company_value.text())
        if panel_location is not None:
            panel_location.setText(self.live_location_value.text())
        if panel_job_progress is not None:
            panel_job_progress.setValue(self.job_progress.value())
        if panel_jd_progress is not None:
            panel_jd_progress.setValue(self.jd_progress.value())
        if panel_resume_progress is not None:
            panel_resume_progress.setValue(self.resume_progress.value())
        if panel_form_progress is not None:
            panel_form_progress.setValue(self.form_progress.value())

    def _apply_now(self) -> None:
        self._applied += 1
        self._jobs = max(0, self._jobs - 1)
        self._update_cards()
        self._log("Apply clicked")

    def _skip_job(self) -> None:
        self._skipped += 1
        self._jobs = max(0, self._jobs - 1)
        self._update_cards()
        self._log("Skip clicked")

    def _retry_job(self) -> None:
        self._failed = max(0, self._failed - 1)
        self._jobs += 1
        self._update_cards()
        self._log("Retry clicked")

    def _open_job(self) -> None:
        self.browser_preview.setPlainText(
            "LinkedIn Browser View\n"
            "- Active tab: Job details\n"
            "- URL: https://www.linkedin.com/jobs/view/123456789\n"
            "- Status: Inspecting posting"
        )
        self._sync_live_panel_window()
        self._set_status("Job opened in browser panel")
        self._log("Open Job clicked")

    def _save_snapshot(self) -> None:
        self._log("Save snapshot clicked")

    def _flag_job(self) -> None:
        self._log("Flag clicked")

    def _toggle_pause_submit(self) -> None:
        self._log("Pause Before Submit toggled")

    def _continue_flow(self) -> None:
        self._set_status("Bot Running")
        self._log("Continue clicked")

    def _export_logs(self) -> None:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        path = logs_dir / f"dashboard_live_{datetime.now():%Y%m%d_%H%M%S}.log"
        path.write_text(self.log_box.toPlainText(), encoding="utf-8")
        self._set_status("Logs exported")
        self._log(f"Exported logs to {path.as_posix()}")

    def _reset_counters(self) -> None:
        self._jobs = 0
        self._applied = 0
        self._failed = 0
        self._skipped = 0
        self._update_cards()
        self._log("Counters reset")

    def _apply_all_settings(self) -> None:
        """Persist current UI settings to config files."""
        import json as _json
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        snapshot = {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "search_terms": self.search_terms.text() if hasattr(self, "search_terms") else "",
            "search_location": self.search_location.text() if hasattr(self, "search_location") else "",
            "toggles": {},
        }
        for toggle in self.findChildren(QPushButton):
            if toggle.objectName() == "TogglePill":
                snapshot["toggles"][toggle.text()] = toggle.isChecked()
        path = config_dir / "dashboard_settings_snapshot.json"
        try:
            path.write_text(_json.dumps(snapshot, indent=2), encoding="utf-8")
            self._set_status("Settings Applied")
            self._log(f"Settings saved to {path.as_posix()}")
        except Exception as exc:
            self._log(f"Failed to save settings: {exc}")

    def _reset_defaults(self) -> None:
        for toggle in self.findChildren(QPushButton):
            if toggle.objectName() == "TogglePill" and toggle.isChecked():
                toggle.setChecked(False)
        if hasattr(self, "search_terms"):
            self.search_terms.setText("Software Engineer, Python Developer, React Developer")
        if hasattr(self, "search_location"):
            self.search_location.setText("United States")
        self._set_status("Defaults Restored")
        self._log("Settings reset to defaults")

    def _export_extension_config(self) -> None:
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        path = config_dir / "dashboard_extension_export.json"
        payload = {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "search_terms": self.search_terms.text() if hasattr(self, "search_terms") else "",
            "search_location": self.search_location.text() if hasattr(self, "search_location") else "",
        }
        import json

        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._set_status("Extension Config Exported")
        self._log(f"Extension config exported to {path.as_posix()}")

    def _reload_extension(self) -> None:
        self._log("Reloading extension API server…")
        try:
            from modules.api_server import app as _api_app  # noqa: F811
            self._log("Extension API module re-imported")
        except Exception as exc:
            self._log(f"Extension reload failed: {exc}")

    _scheduler_instance = None

    def _start_scheduler(self) -> None:
        self._log("Start Scheduler clicked")
        try:
            from modules.scheduler import JobScheduler
            if self._scheduler_instance and getattr(self._scheduler_instance, '_running', False):
                self._log("Scheduler is already running")
                return
            self._scheduler_instance = JobScheduler()
            self._scheduler_instance.start()
            self._set_status("Scheduler Running")
            self._log("Scheduler started successfully")
        except Exception as exc:
            self._log(f"Failed to start scheduler: {exc}")

    def _stop_scheduler(self) -> None:
        self._log("Stop Scheduler clicked")
        try:
            if self._scheduler_instance and hasattr(self._scheduler_instance, 'stop'):
                self._scheduler_instance.stop()
                self._set_status("Scheduler Stopped")
                self._log("Scheduler stopped")
            else:
                self._log("No scheduler instance to stop")
        except Exception as exc:
            self._log(f"Failed to stop scheduler: {exc}")

    def _export_history_csv(self) -> None:
        import shutil as _shutil
        src = Path("all excels/all_applied_applications_history.csv")
        if not src.exists():
            self._log("No history CSV found to export")
            return
        dest_dir = Path("logs")
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / f"history_export_{datetime.now():%Y%m%d_%H%M%S}.csv"
        try:
            _shutil.copy2(src, dest)
            self._set_status("CSV Exported")
            self._log(f"History exported to {dest.as_posix()}")
        except Exception as exc:
            self._log(f"CSV export failed: {exc}")

    def _export_history_pdf(self) -> None:
        self._log("PDF export is not yet implemented — use CSV export")

    def _clear_history(self) -> None:
        self.history_table.clearContents()
        self._log("History cleared")

    def _open_enhanced_tailor(self) -> None:
        self._log("Opening Enhanced Tailor popup…")
        try:
            from modules.quick_tailor_popup import show_quick_tailor_popup
            threading.Thread(
                target=show_quick_tailor_popup,
                kwargs={"resume_path": self.resume_path.text() if hasattr(self, "resume_path") else ""},
                daemon=True,
                name="enhanced-tailor",
            ).start()
        except Exception as exc:
            self._log(f"Failed to open enhanced tailor: {exc}")

    def _quick_tailor(self) -> None:
        self._log("Opening Quick Tailor popup…")
        try:
            from modules.quick_tailor_popup import show_quick_tailor_popup
            threading.Thread(
                target=show_quick_tailor_popup,
                kwargs={"resume_path": self.resume_path.text() if hasattr(self, "resume_path") else ""},
                daemon=True,
                name="quick-tailor",
            ).start()
        except Exception as exc:
            self._log(f"Failed to open quick tailor: {exc}")

    def _save_tailored_resume(self) -> None:
        dest_dir = Path("all resumes/tailored")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"tailored_{datetime.now():%Y%m%d_%H%M%S}.txt"
        jd = self.job_description.toPlainText() if hasattr(self, "job_description") else ""
        try:
            dest.write_text(f"--- Tailored resume placeholder ---\nJD:\n{jd}\n", encoding="utf-8")
            self._log(f"Tailored resume saved to {dest.as_posix()}")
        except Exception as exc:
            self._log(f"Save failed: {exc}")

    def _preview_output(self) -> None:
        tailored_dir = Path("all resumes/tailored")
        if not tailored_dir.exists():
            self._log("No tailored resumes found")
            return
        files = sorted(tailored_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            self._log("No tailored resume files to preview")
            return
        latest = files[0]
        try:
            content = latest.read_text(encoding="utf-8", errors="replace")[:2000]
            self._log(f"--- Preview: {latest.name} ---\n{content}")
        except Exception as exc:
            self._log(f"Preview failed: {exc}")

    def _open_doc(self, name: str) -> None:
        import webbrowser as _wb
        doc_map = {
            "README": "README.md",
            "Enhanced Resume Guide": "docs/ENHANCED_RESUME_TAILORING.md",
            "Security Setup": "docs/SECURITY_SETUP.md",
            "Changelog": "FEATURES.md",
        }
        rel = doc_map.get(name)
        if rel and Path(rel).exists():
            _wb.open(Path(rel).resolve().as_uri())
            self._log(f"Opened {rel}")
        else:
            self._log(f"Document '{name}' not found")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0b1220;
                color: #e2e8f0;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QFrame#TopBar {
                background: #111a2e;
                border: 1px solid #24324a;
                border-radius: 12px;
            }
            QLabel#HeroTitle { font-size: 22px; font-weight: 700; color: #f8fafc; }
            QLabel#HeroSub { color: #94a3b8; }
            QGroupBox {
                border: 1px solid #26354d;
                border-radius: 10px;
                margin-top: 10px;
                background: #121a2f;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #cbd5e1;
            }
            QFrame#Card {
                background: #121a2f;
                border: 1px solid #22324a;
                border-radius: 12px;
                min-height: 64px;
            }
            QLabel#CardTitle { color: #94a3b8; font-size: 12px; }
            QLabel#CardValue { font-size: 22px; font-weight: 700; }
            QTabWidget#MainTabs::pane {
                border: 1px solid #22324a;
                border-radius: 10px;
                background: #111a2e;
                top: -1px;
            }
            QTabBar::tab {
                background: #17243a;
                border: 1px solid #2a3b56;
                border-bottom: none;
                padding: 10px 16px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                color: #cbd5e1;
            }
            QTabBar::tab:selected {
                background: #1d4ed8;
                color: white;
            }
            QPushButton {
                border: 1px solid #2b3b55;
                border-radius: 10px;
                background: #18233a;
                color: #e2e8f0;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #22304a; }
            QPushButton#BtnSuccess { background: #14532d; border-color: #22c55e; }
            QPushButton#BtnSuccess:hover { background: #166534; }
            QPushButton#BtnDanger { background: #4c1d1d; border-color: #ef4444; }
            QPushButton#BtnDanger:hover { background: #7f1d1d; }
            QPushButton#BtnWarn { background: #4a330f; border-color: #f59e0b; }
            QPushButton#BtnWarn:hover { background: #6b4612; }
            QPushButton#BtnInfo { background: #0c4a6e; border-color: #38bdf8; }
            QPushButton#BtnInfo:hover { background: #075985; }
            QPushButton#BtnNeutral { background: #1f2937; border-color: #64748b; }
            QPushButton#BtnNeutral:hover { background: #334155; }
            QPushButton#TogglePill {
                background: #1f2937;
                border: 1px solid #475569;
                color: #cbd5e1;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton#TogglePill:checked {
                background: #0f3b2e;
                border: 1px solid #22c55e;
                color: #dcfce7;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QTableWidget {
                background: #0f172a;
                border: 1px solid #2a3b56;
                border-radius: 8px;
                padding: 6px;
                color: #e2e8f0;
            }
            QTableWidget::item:selected { background: #1e40af; }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                background: #0b1324;
                min-height: 14px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #06b6d4, stop:1 #22c55e);
                border-radius: 5px;
            }
            QStatusBar {
                background: #0f172a;
                border-top: 1px solid #22324a;
                color: #94a3b8;
            }
            """
        )


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    window = OperatorDashboard()

    file_menu = window.menuBar().addMenu("File")
    export_logs_action = QAction("Export Logs", window)
    export_logs_action.triggered.connect(window._export_logs)
    file_menu.addAction(export_logs_action)

    export_settings_action = QAction("Export Settings", window)
    export_settings_action.triggered.connect(window._apply_all_settings)
    file_menu.addAction(export_settings_action)

    file_menu.addSeparator()
    exit_action = QAction("Exit", window)
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    tools_menu = window.menuBar().addMenu("Tools")
    open_api_action = QAction("Open API Config", window)
    open_api_action.triggered.connect(lambda: window._log("Open API Config clicked"))
    tools_menu.addAction(open_api_action)

    open_extension_action = QAction("Open Extension Config", window)
    open_extension_action.triggered.connect(lambda: window._log("Open Extension Config clicked"))
    tools_menu.addAction(open_extension_action)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
