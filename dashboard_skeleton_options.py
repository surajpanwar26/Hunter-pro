"""Five radically different dashboard skeleton options for visual selection.
Run: python dashboard_skeleton_options.py
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb


class DashboardSkeletonShowcase(ttkb.Window):
    def __init__(self):
        super().__init__(themename="superhero")
        self.title("Dashboard Skeleton Showcase - 5 Options")
        self.geometry("1600x980")
        self.minsize(1280, 800)

        self._build_shell()
        self._show_option("option1")

    def _build_shell(self):
        root = ttkb.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        left = ttkb.Labelframe(root, text="Choose Skeleton", width=300, bootstyle="primary")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)

        ttkb.Label(
            left,
            text="5 completely different dashboard skeletons\n(layout, style, and button ecosystem)",
            justify=tk.LEFT,
            font=("Segoe UI", 10),
            foreground="#9fb6d8",
            wraplength=260,
        ).pack(anchor=tk.W, padx=12, pady=(12, 10))

        self.option_buttons = {}
        options = [
            ("option1", "Option 1: Mission Control"),
            ("option2", "Option 2: Pipeline Board"),
            ("option3", "Option 3: Ops Terminal"),
            ("option4", "Option 4: Focus Workspace"),
            ("option5", "Option 5: Scheduler Studio"),
        ]
        for key, label in options:
            btn = ttkb.Button(
                left,
                text=label,
                width=30,
                bootstyle="secondary-outline",
                command=lambda k=key: self._show_option(k),
            )
            btn.pack(anchor=tk.W, padx=12, pady=5)
            self.option_buttons[key] = btn

        ttkb.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=12)
        ttkb.Label(
            left,
            text="These are visual skeletons only.\nNo backend wiring yet.",
            font=("Segoe UI", 9),
            foreground="#84a0c6",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=12)

        self.preview = ttkb.Frame(root)
        self.preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _clear_preview(self):
        for child in self.preview.winfo_children():
            child.destroy()

    def _activate_button(self, option_key: str):
        for key, btn in self.option_buttons.items():
            if key == option_key:
                btn.configure(bootstyle="primary")
            else:
                btn.configure(bootstyle="secondary-outline")

    def _show_option(self, option_key: str):
        self._clear_preview()
        self._activate_button(option_key)

        if option_key == "option1":
            self._render_option_1()
        elif option_key == "option2":
            self._render_option_2()
        elif option_key == "option3":
            self._render_option_3()
        elif option_key == "option4":
            self._render_option_4()
        else:
            self._render_option_5()

    def _render_option_1(self):
        frame = ttkb.Frame(self.preview, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        hero = ttkb.Frame(frame)
        hero.pack(fill=tk.X, pady=(0, 10))
        ttkb.Label(hero, text="🚀 Mission Control", font=("Segoe UI", 22, "bold")).pack(side=tk.LEFT)
        ttkb.Button(hero, text="▶ Start", bootstyle="success").pack(side=tk.RIGHT, padx=4)
        ttkb.Button(hero, text="⏸ Pause", bootstyle="warning").pack(side=tk.RIGHT, padx=4)
        ttkb.Button(hero, text="⏹ Stop", bootstyle="danger").pack(side=tk.RIGHT, padx=4)

        body = ttkb.Panedwindow(frame, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttkb.Labelframe(body, text="Control Deck", bootstyle="info")
        body.add(left, weight=2)

        center = ttkb.Frame(body)
        body.add(center, weight=4)

        right = ttkb.Labelframe(body, text="Live Feed", bootstyle="secondary")
        body.add(right, weight=3)

        for text in [
            "Auto Apply",
            "Pilot Mode",
            "Safe Mode",
            "Smart Filler",
            "Resume Tailor",
            "Extension Sync",
        ]:
            ttkb.Checkbutton(left, text=text, bootstyle="round-toggle").pack(anchor=tk.W, padx=10, pady=6)

        cards = ttkb.Frame(center)
        cards.pack(fill=tk.X)
        for i, (icon, title, value, style) in enumerate([
            ("📊", "Jobs", "124", "info"),
            ("✅", "Applied", "37", "success"),
            ("❌", "Failed", "6", "danger"),
            ("⚡", "Success", "86%", "primary"),
        ]):
            card = ttkb.Labelframe(cards, text=title, bootstyle=style)
            card.grid(row=0, column=i, sticky="nsew", padx=4)
            cards.columnconfigure(i, weight=1)
            ttkb.Label(card, text=f"{icon} {value}", font=("Segoe UI", 18, "bold")).pack(padx=20, pady=16)

        ttkb.Labelframe(center, text="Workflow Timeline", bootstyle="warning").pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        log = tk.Text(right, height=20, bg="#0f172a", fg="#a7f3d0", relief=tk.FLAT)
        log.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        log.insert(tk.END, "[13:10:21] System initialized\n[13:10:23] Queue loaded\n[13:10:26] Awaiting command...\n")

    def _render_option_2(self):
        frame = ttkb.Frame(self.preview, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        top = ttkb.Frame(frame)
        top.pack(fill=tk.X, pady=(0, 10))
        ttkb.Label(top, text="🧭 Pipeline Board", font=("Segoe UI", 22, "bold")).pack(side=tk.LEFT)
        ttkb.Button(top, text="+ Add Lane", bootstyle="info-outline").pack(side=tk.RIGHT, padx=4)
        ttkb.Button(top, text="🔄 Sync", bootstyle="secondary-outline").pack(side=tk.RIGHT, padx=4)

        filters = ttkb.Frame(frame)
        filters.pack(fill=tk.X, pady=(0, 10))
        for name in ["All", "Easy Apply", "External", "Priority", "Interview"]:
            ttkb.Button(filters, text=name, bootstyle="dark-outline", width=12).pack(side=tk.LEFT, padx=4)

        board = ttkb.Frame(frame)
        board.pack(fill=tk.BOTH, expand=True)
        for i in range(4):
            board.columnconfigure(i, weight=1)

        lanes = [
            ("🔎 Discovery", "info"),
            ("🧠 Qualified", "primary"),
            ("📤 Applied", "success"),
            ("📞 Follow-up", "warning"),
        ]

        for col, (title, style) in enumerate(lanes):
            lane = ttkb.Labelframe(board, text=title, bootstyle=style)
            lane.grid(row=0, column=col, sticky="nsew", padx=5)
            for idx in range(5):
                card = ttkb.Frame(lane, padding=8)
                card.pack(fill=tk.X, padx=8, pady=6)
                ttkb.Label(card, text=f"Job Card {idx + 1}", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
                ttkb.Label(card, text="Company • Location • Score", font=("Segoe UI", 8), foreground="#95a7c4").pack(anchor=tk.W)
                actions = ttkb.Frame(card)
                actions.pack(fill=tk.X, pady=(5, 0))
                ttkb.Button(actions, text="Open", width=6, bootstyle="secondary-outline").pack(side=tk.LEFT)
                ttkb.Button(actions, text="Move", width=6, bootstyle="info-outline").pack(side=tk.LEFT, padx=4)

    def _render_option_3(self):
        frame = ttkb.Frame(self.preview, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ttkb.Frame(frame)
        header.pack(fill=tk.X, pady=(0, 10))
        ttkb.Label(header, text="🛰 Ops Terminal", font=("Segoe UI", 22, "bold")).pack(side=tk.LEFT)
        ttkb.Entry(header, width=60).pack(side=tk.RIGHT, padx=8)
        ttkb.Button(header, text="Run Command", bootstyle="primary").pack(side=tk.RIGHT)

        split = ttkb.Panedwindow(frame, orient=tk.VERTICAL)
        split.pack(fill=tk.BOTH, expand=True)

        top = ttkb.Frame(split)
        split.add(top, weight=2)
        bottom = ttkb.Frame(split)
        split.add(bottom, weight=3)

        top_left = ttkb.Labelframe(top, text="System Health", bootstyle="success")
        top_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        top_right = ttkb.Labelframe(top, text="Execution Queue", bootstyle="info")
        top_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        for t in ["CPU 32%", "Memory 41%", "Chrome Sessions 1", "Lock Status Active"]:
            ttkb.Label(top_left, text=f"• {t}", font=("Segoe UI", 10)).pack(anchor=tk.W, padx=12, pady=6)

        q = ttk.Treeview(top_right, columns=("task", "status", "eta"), show="headings", height=6)
        q.heading("task", text="Task")
        q.heading("status", text="Status")
        q.heading("eta", text="ETA")
        q.column("task", width=200)
        q.column("status", width=90)
        q.column("eta", width=80)
        q.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        for row in [("Search Python roles", "Running", "00:32"), ("Apply batch 3", "Queued", "01:15")]:
            q.insert("", tk.END, values=row)

        logs = ttkb.Labelframe(bottom, text="Event Stream", bootstyle="secondary")
        logs.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(logs, bg="#020617", fg="#93c5fd", relief=tk.FLAT)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        text.insert(tk.END, "[INFO] Orchestrator started\n[STEP] Loading profiles\n[OK] Ready for execution\n")

    def _render_option_4(self):
        frame = ttkb.Frame(self.preview, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        shell = ttkb.Frame(frame)
        shell.pack(fill=tk.BOTH, expand=True)

        top = ttkb.Frame(shell)
        top.pack(fill=tk.X)
        ttkb.Label(top, text="🧩 Focus Workspace", font=("Segoe UI", 22, "bold")).pack(side=tk.LEFT)
        ttkb.Button(top, text="Theme", bootstyle="secondary-outline").pack(side=tk.RIGHT, padx=4)
        ttkb.Button(top, text="Layouts", bootstyle="secondary-outline").pack(side=tk.RIGHT, padx=4)

        workspace = ttkb.Frame(shell)
        workspace.pack(fill=tk.BOTH, expand=True, pady=10)

        left = ttkb.Labelframe(workspace, text="Primary Task", bootstyle="primary")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = ttkb.Labelframe(workspace, text="Context Drawer", bootstyle="dark")
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))

        ttkb.Label(left, text="Current focus: Application Quality Pass", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 4))
        ttkb.Progressbar(left, value=64, bootstyle="success-striped").pack(fill=tk.X, padx=10, pady=6)

        action_grid = ttkb.Frame(left)
        action_grid.pack(fill=tk.X, padx=10, pady=6)
        for i, text in enumerate(["Analyze", "Tailor", "Submit", "Skip", "Review", "Requeue"]):
            ttkb.Button(action_grid, text=text, width=12, bootstyle="info-outline").grid(row=i // 3, column=i % 3, padx=4, pady=4)

        ttkb.Labelframe(left, text="Notes", bootstyle="secondary").pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for section in ["Quick Stats", "Alerts", "Upcoming", "Shortcuts"]:
            box = ttkb.Labelframe(right, text=section, bootstyle="secondary")
            box.pack(fill=tk.X, padx=8, pady=6)
            ttkb.Label(box, text="Placeholder", foreground="#8fa4c8").pack(anchor=tk.W, padx=8, pady=6)

        dock = ttkb.Frame(shell)
        dock.pack(fill=tk.X, pady=(4, 0))
        for name in ["Home", "Jobs", "AI", "Schedule", "Logs", "Settings"]:
            ttkb.Button(dock, text=name, bootstyle="dark-outline", width=14).pack(side=tk.LEFT, padx=4)

    def _render_option_5(self):
        frame = ttkb.Frame(self.preview, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        hero = ttkb.Frame(frame)
        hero.pack(fill=tk.X, pady=(0, 10))
        ttkb.Label(hero, text="📅 Scheduler Studio", font=("Segoe UI", 22, "bold")).pack(side=tk.LEFT)
        ttkb.Button(hero, text="+ New Rule", bootstyle="success").pack(side=tk.RIGHT, padx=4)
        ttkb.Button(hero, text="Run Now", bootstyle="primary").pack(side=tk.RIGHT, padx=4)

        body = ttkb.Panedwindow(frame, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttkb.Labelframe(body, text="Automation Rules", bootstyle="info")
        body.add(left, weight=3)

        center = ttkb.Labelframe(body, text="Weekly Planner", bootstyle="warning")
        body.add(center, weight=4)

        right = ttkb.Labelframe(body, text="Run Inspector", bootstyle="secondary")
        body.add(right, weight=3)

        for i in range(7):
            row = ttkb.Frame(left)
            row.pack(fill=tk.X, padx=8, pady=6)
            ttkb.Checkbutton(row, text=f"Rule {i + 1}: Auto-apply batch", bootstyle="round-toggle").pack(side=tk.LEFT)
            ttkb.Button(row, text="Edit", width=7, bootstyle="secondary-outline").pack(side=tk.RIGHT)

        grid = ttkb.Frame(center)
        grid.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for c, d in enumerate(days):
            grid.columnconfigure(c, weight=1)
            ttkb.Label(grid, text=d, font=("Segoe UI", 10, "bold")).grid(row=0, column=c, padx=3, pady=5)
        for r in range(1, 7):
            grid.rowconfigure(r, weight=1)
            for c in range(7):
                cell = ttkb.Frame(grid, padding=4)
                cell.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
                ttkb.Label(cell, text="• Slot", foreground="#9ab0d4", font=("Segoe UI", 8)).pack(anchor=tk.W)

        inspector = tk.Text(right, bg="#0b1220", fg="#c4b5fd", relief=tk.FLAT)
        inspector.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        inspector.insert(tk.END, "Latest run details\n- Trigger: Interval\n- Applied: 8\n- Failed: 1\n- Avg latency: 2.1s\n")


if __name__ == "__main__":
    app = DashboardSkeletonShowcase()
    app.mainloop()
