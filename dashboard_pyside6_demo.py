"""PySide6 full dashboard demo for Auto Job Applier.

This is a high-fidelity UI/UX demo (not wired to backend automation yet).
Run:
  "C:/Users/surpanwar/Desktop/Hunter pro/Auto_job_applier_linkedIn/.venv/Scripts/python.exe" dashboard_pyside6_demo.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFrame,
    QGridLayout,
    QTextEdit,
    QProgressBar,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStatusBar,
    QSplitter,
)


class Card(QFrame):
    def __init__(self, title: str, value: str, accent: str):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("CardTitle")
        val_lbl = QLabel(value)
        val_lbl.setObjectName("CardValue")
        val_lbl.setStyleSheet(f"color: {accent};")
        lay.addWidget(title_lbl)
        lay.addWidget(val_lbl)
        self.value_label = val_lbl


class DemoDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Job Applier — PySide6 Premium Demo")
        self.resize(1680, 980)
        self._started_at = datetime.now()
        self._jobs = 124
        self._applied = 37
        self._failed = 6
        self._skipped = 12

        self._build_ui()
        self._setup_timer()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        outer.addWidget(self._build_topbar())

        shell = QHBoxLayout()
        shell.setSpacing(10)
        outer.addLayout(shell, 1)

        nav = self._build_sidebar()
        shell.addWidget(nav)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_control_page())
        self.pages.addWidget(self._build_settings_page())
        self.pages.addWidget(self._build_history_page())
        self.pages.addWidget(self._build_analytics_page())
        self.pages.addWidget(self._build_tailor_page())
        self.pages.addWidget(self._build_help_page())
        shell.addWidget(self.pages, 1)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_time = QLabel()
        self.status_state = QLabel("System Ready • Demo Mode")
        status.addWidget(self.status_state)
        status.addPermanentWidget(self.status_time)

        self._apply_styles()

    def _build_topbar(self) -> QWidget:
        box = QFrame()
        box.setObjectName("TopBar")
        lay = QHBoxLayout(box)
        lay.setContentsMargins(14, 10, 14, 10)

        left = QVBoxLayout()
        title = QLabel("🚀 Auto Job Applier — Operator Console")
        title.setObjectName("HeroTitle")
        sub = QLabel("High-fidelity PySide6 demo • Fully redesigned layout")
        sub.setObjectName("HeroSub")
        left.addWidget(title)
        left.addWidget(sub)
        lay.addLayout(left)

        lay.addStretch()

        controls = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start")
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_live = QPushButton("📺 Live Panel")
        for b, cls in [
            (self.btn_start, "BtnSuccess"),
            (self.btn_stop, "BtnDanger"),
            (self.btn_pause, "BtnWarn"),
            (self.btn_live, "BtnInfo"),
        ]:
            b.setObjectName(cls)
            b.setFixedHeight(38)
            controls.addWidget(b)

        lay.addLayout(controls)
        return box

    def _build_sidebar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Sidebar")
        frame.setFixedWidth(260)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 10, 10, 10)

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        items = [
            "🏠 Control Center",
            "⚙️ All Settings",
            "📜 History",
            "📊 Analytics",
            "✨ Resume Tailor",
            "❓ Help",
        ]
        for text in items:
            item = QListWidgetItem(text)
            item.setSizeHint(QSize(220, 42))
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)

        lay.addWidget(QLabel("Navigation"))
        lay.addWidget(self.nav, 1)

        quick = QGroupBox("Quick Modes")
        ql = QVBoxLayout(quick)
        for text, obj in [
            ("🚀 Start Pilot Mode", "BtnSuccess"),
            ("📅 Start Scheduled Run", "BtnInfo"),
            ("🔧 Switch to Normal Mode", "BtnNeutral"),
        ]:
            b = QPushButton(text)
            b.setObjectName(obj)
            b.setFixedHeight(34)
            ql.addWidget(b)
        lay.addWidget(quick)

        return frame

    def _build_control_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        root.setSpacing(10)

        cards = QGridLayout()
        self.card_jobs = Card("Jobs Found", str(self._jobs), "#38bdf8")
        self.card_applied = Card("Applied", str(self._applied), "#22c55e")
        self.card_failed = Card("Failed", str(self._failed), "#ef4444")
        self.card_rate = Card("Success Rate", "86%", "#a78bfa")
        for i, c in enumerate([self.card_jobs, self.card_applied, self.card_failed, self.card_rate]):
            cards.addWidget(c, 0, i)
        root.addLayout(cards)

        split = QSplitter(Qt.Horizontal)

        left = QFrame()
        ll = QVBoxLayout(left)
        now_box = QGroupBox("Current Job")
        nlay = QVBoxLayout(now_box)
        nlay.addWidget(QLabel("Role: Software Engineer"))
        nlay.addWidget(QLabel("Company: Example Corp"))
        nlay.addWidget(QLabel("Location: Remote / US"))
        self.progress_job = QProgressBar()
        self.progress_job.setValue(42)
        nlay.addWidget(self.progress_job)
        ll.addWidget(now_box)

        actions = QGroupBox("Actions")
        al = QGridLayout(actions)
        action_buttons = [
            "Apply", "Skip", "Retry", "Open Job", "Save", "Flag",
            "Pause Before Submit", "Continue", "Export Logs", "Reset Counters"
        ]
        for i, text in enumerate(action_buttons):
            b = QPushButton(text)
            b.setObjectName("BtnNeutral")
            b.setFixedHeight(32)
            al.addWidget(b, i // 2, i % 2)
        ll.addWidget(actions, 1)

        right = QFrame()
        rl = QVBoxLayout(right)
        log_box = QGroupBox("Live Activity Stream")
        lb = QVBoxLayout(log_box)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.append("[13:10:21] Dashboard boot complete")
        self.log.append("[13:10:24] Scheduler ready")
        self.log.append("[13:10:30] Waiting for action")
        lb.addWidget(self.log)
        rl.addWidget(log_box, 1)

        ai_box = QGroupBox("AI Pipeline")
        ail = QGridLayout(ai_box)
        ail.addWidget(QLabel("JD Analysis"), 0, 0)
        p1 = QProgressBar(); p1.setValue(60)
        ail.addWidget(p1, 0, 1)
        ail.addWidget(QLabel("Resume Tailoring"), 1, 0)
        p2 = QProgressBar(); p2.setValue(35)
        ail.addWidget(p2, 1, 1)
        ail.addWidget(QLabel("Form Filler"), 2, 0)
        p3 = QProgressBar(); p3.setValue(75)
        ail.addWidget(p3, 2, 1)
        rl.addWidget(ai_box)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        root.addWidget(split, 1)

        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        main = QVBoxLayout(container)
        main.setSpacing(10)

        main.addWidget(self._group_bot_behavior())
        main.addWidget(self._group_form_filling())
        main.addWidget(self._group_resume_tailor())
        main.addWidget(self._group_browser_ui())
        main.addWidget(self._group_control_alerts())
        main.addWidget(self._group_extension())
        main.addWidget(self._group_pilot_mode())
        main.addWidget(self._group_autopilot_prefill())
        main.addWidget(self._group_scheduler())
        main.addWidget(self._group_job_search())

        btns = QHBoxLayout()
        for text, name in [
            ("💾 Apply All Settings", "BtnSuccess"),
            ("🔄 Reset Defaults", "BtnWarn"),
            ("📤 Export Extension Config", "BtnInfo"),
            ("🔁 Reload Extension", "BtnNeutral"),
        ]:
            b = QPushButton(text)
            b.setObjectName(name)
            b.setFixedHeight(36)
            btns.addWidget(b)
        main.addLayout(btns)
        main.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)
        return page

    def _mk_group(self, title: str) -> tuple[QGroupBox, QGridLayout]:
        g = QGroupBox(title)
        l = QGridLayout(g)
        l.setHorizontalSpacing(14)
        l.setVerticalSpacing(8)
        return g, l

    def _group_bot_behavior(self):
        g, l = self._mk_group("🤖 Bot Behavior")
        checks = ["Run Non-Stop", "Alternate Sort", "Cycle Date Posted", "Stop at 24hr", "Close Tabs", "Follow Companies"]
        for i, c in enumerate(checks):
            l.addWidget(QCheckBox(c), i // 3, i % 3)
        l.addWidget(QLabel("Max Jobs"), 2, 0)
        sp = QSpinBox(); sp.setRange(0, 500); sp.setValue(50)
        l.addWidget(sp, 2, 1)
        l.addWidget(QLabel("Click Gap (sec)"), 2, 2)
        sp2 = QSpinBox(); sp2.setRange(1, 60); sp2.setValue(3)
        l.addWidget(sp2, 2, 3)
        return g

    def _group_form_filling(self):
        g, l = self._mk_group("📝 Form Filling")
        l.addWidget(QCheckBox("Fast Mode"), 0, 0)
        l.addWidget(QCheckBox("Smart Form Filler"), 0, 1)
        l.addWidget(QLabel("Delay Multiplier"), 1, 0)
        cmb = QComboBox(); cmb.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
        l.addWidget(cmb, 1, 1)
        return g

    def _group_resume_tailor(self):
        g, l = self._mk_group("📄 Resume Tailoring")
        l.addWidget(QCheckBox("Enable Resume Tailoring"), 0, 0)
        l.addWidget(QCheckBox("Confirm After Filters"), 0, 1)
        l.addWidget(QCheckBox("Prompt Before JD"), 0, 2)
        l.addWidget(QLabel("Upload Format"), 1, 0)
        c = QComboBox(); c.addItems(["Auto", "PDF", "DOCX"])
        l.addWidget(c, 1, 1)
        return g

    def _group_browser_ui(self):
        g, l = self._mk_group("🖥 Browser & UI")
        for i, t in enumerate(["Show Browser", "Disable Extensions", "Safe Mode", "Smooth Scroll", "Keep Screen Awake", "Stealth Mode"]):
            l.addWidget(QCheckBox(t), i // 3, i % 3)
        return g

    def _group_control_alerts(self):
        g, l = self._mk_group("🎛 Control & Alerts")
        for i, t in enumerate(["Pause Before Submit", "Pause At Failed Question", "Show AI Error Alerts"]):
            l.addWidget(QCheckBox(t), 0, i)
        return g

    def _group_extension(self):
        g, l = self._mk_group("🧩 Extension & Form Filler")
        l.addWidget(QCheckBox("Enable Extension"), 0, 0)
        l.addWidget(QCheckBox("Auto Sync"), 0, 1)
        l.addWidget(QCheckBox("AI Learning"), 0, 2)
        l.addWidget(QLabel("Detection Mode"), 1, 0)
        c = QComboBox(); c.addItems(["LinkedIn", "Universal", "Smart Detect"])
        l.addWidget(c, 1, 1)
        return g

    def _group_pilot_mode(self):
        g, l = self._mk_group("✈ Pilot Mode")
        l.addWidget(QCheckBox("Pilot Mode Enabled"), 0, 0)
        l.addWidget(QCheckBox("Continue on Error"), 0, 1)
        l.addWidget(QLabel("Resume Mode"), 1, 0)
        c = QComboBox(); c.addItems(["tailored", "default", "preselected", "skip"])
        l.addWidget(c, 1, 1)
        l.addWidget(QLabel("Delay (sec)"), 1, 2)
        s1 = QSpinBox(); s1.setRange(1, 30); s1.setValue(5)
        l.addWidget(s1, 1, 3)
        l.addWidget(QLabel("Max Apps"), 2, 0)
        s2 = QSpinBox(); s2.setRange(0, 500); s2.setValue(100)
        l.addWidget(s2, 2, 1)
        return g

    def _group_autopilot_prefill(self):
        g, l = self._mk_group("🧠 Autopilot Form Pre-fill")
        labels = [
            "Visa Required", "Work Authorization", "Willing Relocate", "Remote Preference",
            "Start Immediately", "Background Check", "Commute OK",
        ]
        for i, label in enumerate(labels):
            l.addWidget(QLabel(label), i // 2, (i % 2) * 2)
            c = QComboBox(); c.addItems(["Yes", "No"])
            l.addWidget(c, i // 2, (i % 2) * 2 + 1)
        l.addWidget(QLabel("Chrome Wait Time (sec)"), 4, 0)
        s = QSpinBox(); s.setRange(5, 30); s.setValue(10)
        l.addWidget(s, 4, 1)
        return g

    def _group_scheduler(self):
        g, l = self._mk_group("📅 Scheduling")
        l.addWidget(QCheckBox("Scheduling Enabled"), 0, 0)
        l.addWidget(QLabel("Type"), 0, 1)
        c = QComboBox(); c.addItems(["interval", "daily", "weekly"])
        l.addWidget(c, 0, 2)
        l.addWidget(QLabel("Interval Hours"), 1, 0)
        i = QSpinBox(); i.setRange(1, 24); i.setValue(4)
        l.addWidget(i, 1, 1)
        l.addWidget(QLabel("Max Runtime (min)"), 1, 2)
        r = QSpinBox(); r.setRange(10, 480); r.setValue(120)
        l.addWidget(r, 1, 3)
        l.addWidget(QLabel("Max Applications"), 2, 0)
        m = QSpinBox(); m.setRange(0, 500); m.setValue(50)
        l.addWidget(m, 2, 1)

        b1 = QPushButton("▶ Start Scheduler"); b1.setObjectName("BtnSuccess")
        b2 = QPushButton("⏹ Stop Scheduler"); b2.setObjectName("BtnDanger")
        l.addWidget(b1, 3, 2)
        l.addWidget(b2, 3, 3)
        return g

    def _group_job_search(self):
        g, l = self._mk_group("🔍 Job Search")
        l.addWidget(QLabel("Search Terms"), 0, 0)
        l.addWidget(QLineEdit("Software Engineer, Python Developer, React Developer"), 0, 1, 1, 3)
        l.addWidget(QLabel("Location"), 1, 0)
        l.addWidget(QLineEdit("United States"), 1, 1)
        l.addWidget(QLabel("Date Posted"), 1, 2)
        c = QComboBox(); c.addItems(["Past 24 hours", "Past week", "Past month"])
        l.addWidget(c, 1, 3)
        l.addWidget(QCheckBox("Easy Apply Only"), 2, 0)
        l.addWidget(QCheckBox("Randomize Search"), 2, 1)
        return g

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        top = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Applied", "Failed", "Skipped", "Today", "This Week"])
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search job title/company...")
        top.addWidget(QLabel("Filter"))
        top.addWidget(self.filter_combo)
        top.addWidget(self.search_box, 1)
        for text, cls in [("Export CSV", "BtnSuccess"), ("Export PDF", "BtnInfo"), ("Clear", "BtnDanger")]:
            b = QPushButton(text); b.setObjectName(cls)
            top.addWidget(b)
        root.addLayout(top)

        table = QTableWidget(15, 7)
        table.setHorizontalHeaderLabels(["Time", "Job", "Company", "Location", "Status", "AI Score", "Action"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for r in range(15):
            row = ["2026-02-14 13:12", f"Role {r+1}", "Example Corp", "Remote", "Applied" if r % 3 else "Failed", str(70 + (r % 25)), "View"]
            for c, val in enumerate(row):
                table.setItem(r, c, QTableWidgetItem(val))
        root.addWidget(table)
        return page

    def _build_analytics_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)
        g = QGridLayout()

        panels = []
        for title in ["Application Status", "Performance Metrics", "AI Statistics", "Session Info"]:
            box = QGroupBox(title)
            lay = QVBoxLayout(box)
            for i in range(4):
                pb = QProgressBar()
                pb.setValue(20 + i * 20)
                lay.addWidget(QLabel(f"Metric {i+1}"))
                lay.addWidget(pb)
            panels.append(box)

        g.addWidget(panels[0], 0, 0)
        g.addWidget(panels[1], 0, 1)
        g.addWidget(panels[2], 1, 0)
        g.addWidget(panels[3], 1, 1)
        root.addLayout(g)
        return page

    def _build_tailor_page(self) -> QWidget:
        page = QWidget()
        root = QHBoxLayout(page)

        left = QGroupBox("Input")
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Resume File"))
        ll.addWidget(QLineEdit("all resumes/master resume/resume.pdf"))
        ll.addWidget(QLabel("Job Description"))
        jd = QTextEdit()
        jd.setPlainText("Paste full JD here...")
        ll.addWidget(jd)
        ll.addWidget(QLabel("Custom Instructions"))
        ll.addWidget(QLineEdit("Focus on backend impact and measurable outcomes"))

        right = QGroupBox("Actions")
        rl = QVBoxLayout(right)
        provider = QComboBox(); provider.addItems(["ollama", "groq", "openai", "deepseek", "gemini"])
        rl.addWidget(QLabel("AI Provider"))
        rl.addWidget(provider)
        for text, cls in [
            ("✨ Open Enhanced Tailor", "BtnSuccess"),
            ("📝 Quick Tailor (Classic)", "BtnInfo"),
            ("📥 Save Tailored Resume", "BtnNeutral"),
            ("👁 Preview Output", "BtnNeutral"),
        ]:
            b = QPushButton(text)
            b.setObjectName(cls)
            b.setFixedHeight(38)
            rl.addWidget(b)
        rl.addStretch()

        root.addWidget(left, 2)
        root.addWidget(right, 1)
        return page

    def _build_help_page(self) -> QWidget:
        page = QWidget()
        root = QVBoxLayout(page)

        links = QGroupBox("Quick Links")
        ll = QVBoxLayout(links)
        for t in ["README", "Enhanced Resume Guide", "Security Setup", "Changelog"]:
            b = QPushButton(f"📖 Open {t}")
            b.setObjectName("BtnNeutral")
            ll.addWidget(b)
        root.addWidget(links)

        shortcuts = QGroupBox("Keyboard Shortcuts")
        sl = QGridLayout(shortcuts)
        data = [("Alt+1", "Control Center"), ("Alt+2", "Settings"), ("Alt+3", "History"), ("F5", "Refresh"), ("Ctrl+S", "Start")]
        for i, (k, d) in enumerate(data):
            sl.addWidget(QLabel(k), i, 0)
            sl.addWidget(QLabel(d), i, 1)
        root.addWidget(shortcuts)

        about = QGroupBox("About")
        al = QVBoxLayout(about)
        al.addWidget(QLabel("Auto Job Applier — PySide6 Demo"))
        al.addWidget(QLabel("This demo includes all key buttons and config groups for decision-making."))
        root.addWidget(about)

        root.addStretch()
        return page

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        now = datetime.now()
        runtime = now - self._started_at
        self.status_time.setText(f"{now.strftime('%Y-%m-%d %H:%M:%S')}  •  Runtime {str(runtime).split('.')[0]}")

        self.progress_job.setValue((self.progress_job.value() + 2) % 101)
        if self.progress_job.value() % 20 == 0:
            self.log.append(f"[{now.strftime('%H:%M:%S')}] Processing stage -> {self.progress_job.value()}%")

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0b1220;
                color: #e2e8f0;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QFrame#TopBar, QFrame#Sidebar {
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
            QListWidget#Nav {
                border: 1px solid #22324a;
                border-radius: 10px;
                background: #0f1728;
                outline: none;
            }
            QListWidget#Nav::item {
                padding: 10px;
                border-radius: 8px;
                margin: 3px;
            }
            QListWidget#Nav::item:selected {
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


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    win = DemoDashboard()

    file_menu = win.menuBar().addMenu("File")
    file_menu.addAction(QAction("Export Logs", win))
    file_menu.addAction(QAction("Export Settings", win))
    file_menu.addSeparator()
    file_menu.addAction(QAction("Exit", win, triggered=win.close))

    tools = win.menuBar().addMenu("Tools")
    tools.addAction(QAction("Open API Config", win))
    tools.addAction(QAction("Open Extension Config", win))

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
