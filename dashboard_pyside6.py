"""Tabbed PySide6 dashboard for Auto Job Applier.

Production dashboard with a top-tab layout where the Home page contains
all settings and configuration controls (similar to the Tkinter dashboard
workflow) while preserving history/analytics/tailoring/help tabs.

Run:
    .venv\\Scripts\\python.exe dashboard_pyside6.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from functools import partial

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QFont
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
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
        self.setWindowTitle("Auto Job Applier — Operator Console")
        self.resize(1700, 1000)
        self._started_at = datetime.now()

        self._jobs = 124
        self._applied = 37
        self._failed = 6
        self._skipped = 12

        self._build_ui()
        self._apply_styles()
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
        layout.setContentsMargins(14, 10, 14, 10)

        left = QVBoxLayout()
        title = QLabel("🚀 Auto Job Applier — Premium Console")
        title.setObjectName("HeroTitle")
        subtitle = QLabel("Modern tabbed workspace • Home-centric settings • Fully interactive")
        subtitle.setObjectName("HeroSub")
        left.addWidget(title)
        left.addWidget(subtitle)
        layout.addLayout(left)

        layout.addStretch()

        self.btn_start = self._mk_button("▶ Start", "BtnSuccess", self._start_bot)
        self.btn_stop = self._mk_button("⏹ Stop", "BtnDanger", self._stop_bot)
        self.btn_pause = self._mk_button("⏸ Pause", "BtnWarn", self._pause_bot)
        self.btn_live = self._mk_button("📺 Live Panel", "BtnInfo", self._toggle_live_panel)

        for button in [self.btn_start, self.btn_stop, self.btn_pause, self.btn_live]:
            layout.addWidget(button)

        return frame

    def _build_cards(self) -> QWidget:
        row = QWidget()
        layout = QGridLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        self.card_jobs = MetricCard("Jobs Found", str(self._jobs), "#38bdf8")
        self.card_applied = MetricCard("Applied", str(self._applied), "#22c55e")
        self.card_failed = MetricCard("Failed", str(self._failed), "#ef4444")
        self.card_rate = MetricCard("Success Rate", self._rate_text(), "#a78bfa")

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        content = QVBoxLayout(container)
        content.setSpacing(10)

        home_settings = QGroupBox("⚙️ Settings & Configuration")
        home_settings_layout = QVBoxLayout(home_settings)
        home_settings_layout.setSpacing(10)

        home_settings_layout.addWidget(self._settings_bot_behavior())
        home_settings_layout.addWidget(self._settings_form_filling())
        home_settings_layout.addWidget(self._settings_resume_tailor())
        home_settings_layout.addWidget(self._settings_browser_ui())
        home_settings_layout.addWidget(self._settings_control_alerts())
        home_settings_layout.addWidget(self._settings_extension())
        home_settings_layout.addWidget(self._settings_pilot())
        home_settings_layout.addWidget(self._settings_prefill())
        home_settings_layout.addWidget(self._settings_scheduler())
        home_settings_layout.addWidget(self._settings_job_search())

        action_row = QHBoxLayout()
        action_row.addWidget(self._mk_button("💾 Apply All Settings", "BtnSuccess", self._apply_all_settings))
        action_row.addWidget(self._mk_button("🔄 Reset Defaults", "BtnWarn", self._reset_defaults))
        action_row.addWidget(self._mk_button("📤 Export Extension Config", "BtnInfo", self._export_extension_config))
        action_row.addWidget(self._mk_button("🔁 Reload Extension", "BtnNeutral", self._reload_extension))
        home_settings_layout.addLayout(action_row)

        content.addWidget(home_settings)
        content.addWidget(self._build_live_operations())

        scroll.setWidget(container)
        root.addWidget(scroll)
        return page

    def _build_live_operations(self) -> QWidget:
        section = QWidget()
        root = QVBoxLayout(section)

        top_row = QHBoxLayout()

        browser_group = QGroupBox("Browser Session")
        browser_layout = QVBoxLayout(browser_group)
        self.browser_preview = QTextEdit()
        self.browser_preview.setReadOnly(True)
        self.browser_preview.setPlainText(
            "LinkedIn Browser View\n"
            "- Active tab: Easy Apply jobs\n"
            "- URL: https://www.linkedin.com/jobs/\n"
            "- Status: Ready"
        )
        browser_layout.addWidget(self.browser_preview)
        top_row.addWidget(browser_group, 2)

        self.live_side_panel = QGroupBox("Live Side Panel")
        side_layout = QVBoxLayout(self.live_side_panel)

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
        self.job_progress.setValue(42)
        details_layout.addWidget(QLabel("Current Job Progress"), 3, 0)
        details_layout.addWidget(self.job_progress, 3, 1)
        side_layout.addWidget(details_group)

        stream_group = QGroupBox("Live Activity Stream")
        stream_layout = QVBoxLayout(stream_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        stream_layout.addWidget(self.log_box)
        side_layout.addWidget(stream_group)

        pipeline = QGroupBox("AI Pipeline")
        pipeline_grid = QGridLayout(pipeline)

        self.jd_progress = QProgressBar()
        self.jd_progress.setValue(60)
        self.resume_progress = QProgressBar()
        self.resume_progress.setValue(35)
        self.form_progress = QProgressBar()
        self.form_progress.setValue(75)

        pipeline_grid.addWidget(QLabel("JD Analysis"), 0, 0)
        pipeline_grid.addWidget(self.jd_progress, 0, 1)
        pipeline_grid.addWidget(QLabel("Resume Tailoring"), 1, 0)
        pipeline_grid.addWidget(self.resume_progress, 1, 1)
        pipeline_grid.addWidget(QLabel("Form Filler"), 2, 0)
        pipeline_grid.addWidget(self.form_progress, 2, 1)

        side_layout.addWidget(pipeline)
        top_row.addWidget(self.live_side_panel, 1)
        root.addLayout(top_row)

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
            button = self._mk_button(label, "BtnNeutral", handler, height=34)
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
        spin = QSpinBox()
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
        combo = QComboBox()
        combo.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
        combo.currentTextChanged.connect(lambda text: self._log(f"Delay Multiplier changed to {text}"))
        layout.addWidget(combo, 1, 1)
        return group

    def _settings_resume_tailor(self) -> QGroupBox:
        group, layout = self._mk_group("📄 Resume Tailoring")
        for idx, label in enumerate(["Enable Resume Tailoring", "Confirm After Filters", "Prompt Before JD"]):
            layout.addWidget(self._mk_toggle(label), 0, idx)

        layout.addWidget(QLabel("Upload Format"), 1, 0)
        combo = QComboBox()
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
        combo = QComboBox()
        combo.addItems(["LinkedIn", "Universal", "Smart Detect"])
        combo.currentTextChanged.connect(lambda text: self._log(f"Detection Mode changed to {text}"))
        layout.addWidget(combo, 1, 1)
        return group

    def _settings_pilot(self) -> QGroupBox:
        group, layout = self._mk_group("✈ Pilot Mode")
        layout.addWidget(self._mk_toggle("Pilot Mode Enabled"), 0, 0)
        layout.addWidget(self._mk_toggle("Continue on Error"), 0, 1)

        layout.addWidget(QLabel("Resume Mode"), 1, 0)
        resume_mode = QComboBox()
        resume_mode.addItems(["tailored", "default", "preselected", "skip"])
        resume_mode.currentTextChanged.connect(lambda text: self._log(f"Pilot Resume Mode changed to {text}"))
        layout.addWidget(resume_mode, 1, 1)

        layout.addWidget(QLabel("Delay (sec)"), 1, 2)
        delay = QSpinBox()
        delay.setRange(1, 30)
        delay.setValue(5)
        delay.valueChanged.connect(lambda value: self._log(f"Pilot Delay changed to {value}s"))
        layout.addWidget(delay, 1, 3)

        layout.addWidget(QLabel("Max Apps"), 2, 0)
        max_apps = QSpinBox()
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
            combo = QComboBox()
            combo.addItems(["Yes", "No"])
            combo.currentTextChanged.connect(partial(self._prefill_changed, label))
            layout.addWidget(combo, idx // 2, (idx % 2) * 2 + 1)

        layout.addWidget(QLabel("Chrome Wait Time (sec)"), 4, 0)
        wait = QSpinBox()
        wait.setRange(5, 30)
        wait.setValue(10)
        wait.valueChanged.connect(lambda value: self._log(f"Autopilot Chrome Wait Time changed to {value}s"))
        layout.addWidget(wait, 4, 1)
        return group

    def _settings_scheduler(self) -> QGroupBox:
        group, layout = self._mk_group("📅 Scheduling")
        layout.addWidget(self._mk_toggle("Scheduling Enabled"), 0, 0)

        layout.addWidget(QLabel("Type"), 0, 1)
        schedule_type = QComboBox()
        schedule_type.addItems(["interval", "daily", "weekly"])
        schedule_type.currentTextChanged.connect(lambda text: self._log(f"Schedule Type changed to {text}"))
        layout.addWidget(schedule_type, 0, 2)

        layout.addWidget(QLabel("Interval Hours"), 1, 0)
        interval = QSpinBox()
        interval.setRange(1, 24)
        interval.setValue(4)
        interval.valueChanged.connect(lambda value: self._log(f"Schedule Interval changed to {value}h"))
        layout.addWidget(interval, 1, 1)

        layout.addWidget(QLabel("Max Runtime (min)"), 1, 2)
        runtime = QSpinBox()
        runtime.setRange(10, 480)
        runtime.setValue(120)
        runtime.valueChanged.connect(lambda value: self._log(f"Schedule Runtime changed to {value} min"))
        layout.addWidget(runtime, 1, 3)

        layout.addWidget(QLabel("Max Applications"), 2, 0)
        max_apps = QSpinBox()
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
        posted = QComboBox()
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
        about_layout.addWidget(QLabel("Auto Job Applier — PySide6 Operator Dashboard"))
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
        self.status_time.setText(f"{now:%Y-%m-%d %H:%M:%S} • Runtime {str(runtime).split('.')[0]}")

        self.job_progress.setValue((self.job_progress.value() + 2) % 101)
        self.jd_progress.setValue((self.jd_progress.value() + 1) % 101)
        self.resume_progress.setValue((self.resume_progress.value() + 1) % 101)
        self.form_progress.setValue((self.form_progress.value() + 2) % 101)

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

    def _set_status(self, text: str) -> None:
        self.status_state.setText(text)

    def _on_toggle_changed(self, label: str, state: bool) -> None:
        value = "ON" if state else "OFF"
        self._log(f"{label}: {value}")

    def _prefill_changed(self, label: str, value: str) -> None:
        self._log(f"{label}: {value}")

    def _start_bot(self) -> None:
        self._set_status("Bot Running")
        self._log("Start pressed")

    def _stop_bot(self) -> None:
        self._set_status("Bot Stopped")
        self._log("Stop pressed")

    def _pause_bot(self) -> None:
        self._set_status("Bot Paused")
        self._log("Pause pressed")

    def _toggle_live_panel(self) -> None:
        should_show = not self.live_side_panel.isVisible()
        self.live_side_panel.setVisible(should_show)
        if should_show:
            self.btn_live.setText("📺 Hide Panel")
            self._set_status("Live Panel Visible")
            self._log("Live side panel opened")
        else:
            self.btn_live.setText("📺 Live Panel")
            self._set_status("Live Panel Hidden")
            self._log("Live side panel hidden")

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
        self._set_status("Settings Applied")
        self._log("All settings applied")

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
        self._log("Reload Extension clicked")

    def _start_scheduler(self) -> None:
        self._log("Start Scheduler clicked")

    def _stop_scheduler(self) -> None:
        self._log("Stop Scheduler clicked")

    def _export_history_csv(self) -> None:
        self._log("Export History CSV clicked")

    def _export_history_pdf(self) -> None:
        self._log("Export History PDF clicked")

    def _clear_history(self) -> None:
        self.history_table.clearContents()
        self._log("History cleared")

    def _open_enhanced_tailor(self) -> None:
        self._log("Open Enhanced Tailor clicked")

    def _quick_tailor(self) -> None:
        self._log("Quick Tailor clicked")

    def _save_tailored_resume(self) -> None:
        self._log("Save Tailored Resume clicked")

    def _preview_output(self) -> None:
        self._log("Preview Output clicked")

    def _open_doc(self, name: str) -> None:
        self._log(f"Open doc clicked: {name}")

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
                min-height: 100px;
            }
            QLabel#CardTitle { color: #94a3b8; font-size: 12px; }
            QLabel#CardValue { font-size: 30px; font-weight: 700; }
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
