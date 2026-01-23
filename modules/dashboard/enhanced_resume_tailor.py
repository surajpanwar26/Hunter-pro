"""
Enhanced Resume Tailor Dialog with Advanced Features
- Diff highlighting (additions in green, removals in red)
- Skill suggestion system with one-click addition
- Before/After ATS score comparison
- Visual change tracker
"""
import os
import re
import difflib
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import urllib.request
import urllib.error
import json

import ttkbootstrap as ttkb

from modules.ai.resume_tailoring import (
    tailor_resume_to_files, 
    tailor_resume_text,
    _read_resume_text,
    _score_match,
    _extract_jd_keywords,
)
from modules.dashboard.api_config_dialog import open_api_config_dialog


# Dark theme colors
COLORS = {
    'bg': '#1a1a2e',
    'card': '#16213e',
    'accent': '#6c5ce7',
    'success': '#00b894',
    'warning': '#fdcb6e',
    'danger': '#e74c3c',
    'text': '#e8e8e8',
    'text_secondary': '#adb5bd',
    'border': '#333',
    'addition': '#2ecc71',  # Green for additions
    'removal': '#e74c3c',   # Red for removals
    'highlight': '#f39c12', # Orange for highlights
}


def calculate_text_diff(original: str, tailored: str) -> tuple[list, list]:
    """
    Calculate differences between original and tailored text.
    Returns (additions, removals) as lists of text snippets.
    """
    original_lines = original.split('\n')
    tailored_lines = tailored.split('\n')
    
    differ = difflib.Differ()
    diff = list(differ.compare(original_lines, tailored_lines))
    
    additions = []
    removals = []
    
    for line in diff:
        if line.startswith('+ '):
            additions.append(line[2:].strip())
        elif line.startswith('- '):
            removals.append(line[2:].strip())
    
    return additions, removals


def extract_skill_suggestions(jd_text: str, resume_text: str, max_suggestions: int = 10) -> list[dict]:
    """
    Extract skill suggestions from JD that are missing in resume.
    Returns list of dicts with 'skill', 'category', and 'priority'.
    """
    jd_keywords = _extract_jd_keywords(jd_text)
    resume_lower = resume_text.lower()
    
    suggestions = []
    
    # Skill categories for organization
    skill_categories = {
        'programming': ['python', 'java', 'kotlin', 'go', 'golang', 'scala', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'rust', 'php', 'swift'],
        'frameworks': ['spring', 'spring boot', 'flask', 'django', 'fastapi', 'node.js', 'express', 'react', 'angular', 'vue', '.net'],
        'databases': ['postgresql', 'postgres', 'mysql', 'mongodb', 'dynamodb', 'cassandra', 'redis', 'elasticsearch', 'oracle', 'sql server', 'nosql', 'rdbms', 'sql'],
        'cloud': ['aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'k8s', 'ci/cd', 'jenkins', 'terraform', 'ansible', 'saas', 'paas', 'iaas', 'cloud'],
        'architecture': ['microservices', 'restful', 'rest api', 'graphql', 'api', 'distributed systems', 'scalable', 'event-driven', 'serverless'],
        'practices': ['agile', 'scrum', 'devops', 'tdd', 'testing', 'security', 'monitoring', 'collaboration', 'mentoring'],
    }
    
    for keyword in jd_keywords:
        if keyword not in resume_lower:
            # Find category
            category = 'other'
            for cat, skills in skill_categories.items():
                if keyword in skills:
                    category = cat
                    break
            
            # Calculate priority (higher if appears multiple times in JD)
            priority = jd_text.lower().count(keyword)
            
            suggestions.append({
                'skill': keyword,
                'category': category,
                'priority': priority
            })
    
    # Sort by priority and limit
    suggestions.sort(key=lambda x: x['priority'], reverse=True)
    return suggestions[:max_suggestions]


class EnhancedResumeTailorDialog(tk.Toplevel):
    """Enhanced Resume Tailoring Dialog with diff view and skill suggestions."""
    
    def __init__(self, parent: tk.Tk, default_provider: str, default_resume_text: str | None):
        super().__init__(parent)
        self.title("📝 Enhanced AI Resume Tailor")
        self.geometry("1600x950")
        self.minsize(1400, 800)
        self.configure(bg=COLORS['bg'])
        
        # State variables
        self.provider_var = tk.StringVar(value=default_provider)
        self.job_title_var = tk.StringVar(value="")
        self.resume_path_var = tk.StringVar(value="")
        self.master_resume_text = ""
        self.tailored_resume_text = ""
        self.current_paths = {}
        self.is_processing = False
        self.skill_suggestions = []
        self.before_ats_score = None
        self.after_ats_score = None
        
        # UI references
        self.resume_text: scrolledtext.ScrolledText = None  # type: ignore
        self.jd_text: scrolledtext.ScrolledText = None  # type: ignore
        self.master_preview: tk.Text = None  # type: ignore
        self.tailored_preview: tk.Text = None  # type: ignore
        self.diff_text: scrolledtext.ScrolledText = None  # type: ignore
        self.suggestions_frame: tk.Frame = None  # type: ignore
        self.before_score_label: tk.Label = None  # type: ignore
        self.after_score_label: tk.Label = None  # type: ignore
        self.improvement_arrow: tk.Label = None  # type: ignore
        self.status_label: tk.Label = None  # type: ignore
        self.progress_bar: ttkb.Progressbar = None  # type: ignore
        self.tailor_btn: ttkb.Button = None  # type: ignore
        
        # Export buttons
        self.open_pdf_btn: ttkb.Button = None  # type: ignore
        self.open_docx_btn: ttkb.Button = None  # type: ignore
        self.download_pdf_btn: ttkb.Button = None  # type: ignore
        self.download_docx_btn: ttkb.Button = None  # type: ignore
        self.open_folder_btn: ttkb.Button = None  # type: ignore
        self.copy_text_btn: ttkb.Button = None  # type: ignore
        
        self._build_ui(default_resume_text or "")
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1600 // 2)
        y = (self.winfo_screenheight() // 2) - (950 // 2)
        self.geometry(f"1600x950+{x}+{y}")
        
        # Keyboard shortcuts
        self.bind("<Control-Return>", lambda e: self._run_tailor())
        self.bind("<Escape>", lambda e: self.destroy())
    
    def _build_ui(self, default_resume_text: str):
        """Build the complete enhanced UI."""
        
        # HEADER with ATS Score Display
        header_frame = tk.Frame(self, bg=COLORS['bg'])
        header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="🎯 Enhanced AI Resume Tailor",
            font=("Segoe UI", 18, "bold"),
            fg=COLORS['accent'],
            bg=COLORS['bg']
        )
        title_label.pack(side=tk.LEFT)
        
        # ATS Score Comparison (top right)
        ats_frame = tk.Frame(header_frame, bg=COLORS['card'], padx=15, pady=8)
        ats_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(
            ats_frame,
            text="ATS Score:",
            font=("Segoe UI", 10, "bold"),
            fg=COLORS['text'],
            bg=COLORS['card']
        ).pack(side=tk.LEFT, padx=5)
        
        self.before_score_label = tk.Label(
            ats_frame,
            text="--",
            font=("Segoe UI", 16, "bold"),
            fg=COLORS['text_secondary'],
            bg=COLORS['card']
        )
        self.before_score_label.pack(side=tk.LEFT, padx=5)
        
        self.improvement_arrow = tk.Label(
            ats_frame,
            text="",
            font=("Segoe UI", 14, "bold"),
            fg=COLORS['accent'],
            bg=COLORS['card']
        )
        self.improvement_arrow.pack(side=tk.LEFT, padx=3)
        
        self.after_score_label = tk.Label(
            ats_frame,
            text="--",
            font=("Segoe UI", 16, "bold"),
            fg=COLORS['text_secondary'],
            bg=COLORS['card']
        )
        self.after_score_label.pack(side=tk.LEFT, padx=5)
        
        # ACTION BAR
        action_bar = tk.Frame(self, bg='#0f3460', pady=8)
        action_bar.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        self.tailor_btn = ttkb.Button(
            action_bar, text="🚀 START TAILORING", command=self._run_tailor,
            bootstyle="success", width=20
        )
        self.tailor_btn.pack(side=tk.LEFT, padx=10)
        
        ttkb.Button(
            action_bar, text="📊 Quick ATS Check", command=self._quick_ats_check,
            bootstyle="info-outline", width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress_bar = ttkb.Progressbar(
            action_bar, mode='indeterminate', bootstyle="success-striped", length=300
        )
        self.progress_bar.pack(side=tk.LEFT, padx=20)
        
        ttkb.Button(
            action_bar, text="🔄 Reset", command=self._reset_form,
            bootstyle="secondary-outline", width=10
        ).pack(side=tk.RIGHT, padx=10)
        
        # MAIN CONTENT - Three columns
        main_frame = tk.Frame(self, bg=COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        main_frame.columnconfigure(0, weight=1, minsize=400)  # Input
        main_frame.columnconfigure(1, weight=2, minsize=700)  # Preview with diff
        main_frame.columnconfigure(2, weight=1, minsize=350)  # Suggestions
        main_frame.rowconfigure(0, weight=1)
        
        # LEFT: Input Section
        self._build_input_section(main_frame, default_resume_text)
        
        # CENTER: Preview & Diff Section
        self._build_preview_section(main_frame)
        
        # RIGHT: Skill Suggestions Section
        self._build_suggestions_section(main_frame)
        
        # BOTTOM: Status
        status_frame = tk.Frame(self, bg=COLORS['card'], pady=5)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.status_label = tk.Label(
            status_frame,
            text="💡 Ready to tailor your resume with AI",
            font=("Segoe UI", 9),
            fg=COLORS['text_secondary'],
            bg=COLORS['card']
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
    
    def _build_input_section(self, parent: tk.Frame, default_resume_text: str):
        """Build the input section (left column)."""
        input_frame = tk.Frame(parent, bg=COLORS['bg'])
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Configuration
        config_frame = ttkb.Labelframe(input_frame, text="⚙️ Configuration", bootstyle="info")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        config_inner = tk.Frame(config_frame, bg=COLORS['bg'])
        config_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Provider selection
        tk.Label(config_inner, text="AI Provider:", font=("Segoe UI", 9), 
                 fg=COLORS['text'], bg=COLORS['bg']).pack(anchor=tk.W)
        
        provider_combo = ttkb.Combobox(
            config_inner,
            textvariable=self.provider_var,
            values=["ollama", "groq", "huggingface", "openai", "deepseek", "gemini"],
            width=20,
            bootstyle="info"
        )
        provider_combo.pack(fill=tk.X, pady=3)
        
        # Job Title
        tk.Label(config_inner, text="Job Title:", font=("Segoe UI", 9), 
                 fg=COLORS['text'], bg=COLORS['bg']).pack(anchor=tk.W, pady=(5, 0))
        ttkb.Entry(config_inner, textvariable=self.job_title_var, 
                   bootstyle="info").pack(fill=tk.X, pady=3)
        
        # Resume File
        file_frame = ttkb.Labelframe(input_frame, text="📄 Resume File", bootstyle="success")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        file_inner = tk.Frame(file_frame, bg=COLORS['bg'])
        file_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ttkb.Entry(file_inner, textvariable=self.resume_path_var).pack(fill=tk.X, pady=3)
        
        btn_row = tk.Frame(file_inner, bg=COLORS['bg'])
        btn_row.pack(fill=tk.X, pady=3)
        
        ttkb.Button(btn_row, text="📂 Browse", command=self._browse_resume, 
                    bootstyle="success-outline", width=12).pack(side=tk.LEFT, padx=2)
        ttkb.Button(btn_row, text="📋 Load", command=self._load_resume_file, 
                    bootstyle="info-outline", width=12).pack(side=tk.LEFT, padx=2)
        
        # Resume Text
        resume_frame = ttkb.Labelframe(input_frame, text="📝 Your Resume", bootstyle="primary")
        resume_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.resume_text = scrolledtext.ScrolledText(
            resume_frame, 
            height=8,
            font=("Consolas", 9),
            bg=COLORS['card'],
            fg=COLORS['text'],
            insertbackground='white',
            wrap=tk.WORD
        )
        self.resume_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        if default_resume_text.strip():
            self.resume_text.insert(tk.END, default_resume_text.strip())
        
        # Job Description
        jd_frame = ttkb.Labelframe(input_frame, text="💼 Job Description", bootstyle="warning")
        jd_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.jd_text = scrolledtext.ScrolledText(
            jd_frame,
            height=10,
            font=("Consolas", 9),
            bg='#1e3a4c',
            fg=COLORS['text'],
            insertbackground='yellow',
            wrap=tk.WORD
        )
        self.jd_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.jd_text.insert(tk.END, "Paste the complete job description here...")
    
    def _build_preview_section(self, parent: tk.Frame):
        """Build the preview and diff section (center column)."""
        preview_frame = tk.Frame(parent, bg=COLORS['bg'])
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        
        # Notebook for different views
        preview_notebook = ttkb.Notebook(preview_frame, bootstyle="dark")
        preview_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Side-by-Side Comparison
        comparison_frame = tk.Frame(preview_notebook, bg=COLORS['bg'])
        preview_notebook.add(comparison_frame, text="📑 Side-by-Side")
        
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.columnconfigure(1, weight=1)
        comparison_frame.rowconfigure(1, weight=1)
        
        tk.Label(
            comparison_frame,
            text="📋 ORIGINAL",
            font=("Segoe UI", 10, "bold"),
            fg="#74c0fc",
            bg=COLORS['bg']
        ).grid(row=0, column=0, pady=5)
        
        tk.Label(
            comparison_frame,
            text="✨ TAILORED",
            font=("Segoe UI", 10, "bold"),
            fg="#69db7c",
            bg=COLORS['bg']
        ).grid(row=0, column=1, pady=5)
        
        self.master_preview = tk.Text(
            comparison_frame,
            font=("Consolas", 9),
            bg='#16213e',
            fg='#e8e8e8',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.master_preview.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)
        
        master_scroll = ttk.Scrollbar(comparison_frame, command=self.master_preview.yview)
        master_scroll.grid(row=1, column=0, sticky="nse")
        self.master_preview.configure(yscrollcommand=master_scroll.set)
        
        self.tailored_preview = tk.Text(
            comparison_frame,
            font=("Consolas", 9),
            bg='#16213e',
            fg='#e8e8e8',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.tailored_preview.grid(row=1, column=1, sticky="nsew", padx=3, pady=3)
        
        tailored_scroll = ttk.Scrollbar(comparison_frame, command=self.tailored_preview.yview)
        tailored_scroll.grid(row=1, column=1, sticky="nse")
        self.tailored_preview.configure(yscrollcommand=tailored_scroll.set)
        
        # Configure text tags for highlighting
        self.tailored_preview.tag_configure("addition", background="#1e5631", foreground="#2ecc71")
        self.tailored_preview.tag_configure("removal", background="#5c1a1a", foreground="#e74c3c", overstrike=True)
        
        # Tab 2: Diff View with Highlights
        diff_frame = tk.Frame(preview_notebook, bg=COLORS['bg'])
        preview_notebook.add(diff_frame, text="🔍 Changes Highlighted")
        
        # Legend
        legend_frame = tk.Frame(diff_frame, bg=COLORS['bg'])
        legend_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            legend_frame,
            text="Legend:",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            legend_frame,
            text="● Added",
            font=("Segoe UI", 9),
            fg=COLORS['addition'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Label(
            legend_frame,
            text="● Removed",
            font=("Segoe UI", 9),
            fg=COLORS['removal'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT, padx=10)
        
        # Diff text area
        self.diff_text = scrolledtext.ScrolledText(
            diff_frame,
            font=("Consolas", 9),
            bg='#16213e',
            fg='#e8e8e8',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.diff_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure tags for diff highlighting
        self.diff_text.tag_configure("added", foreground=COLORS['addition'], background="#1e5631")
        self.diff_text.tag_configure("removed", foreground=COLORS['removal'], background="#5c1a1a", overstrike=True)
        self.diff_text.tag_configure("context", foreground=COLORS['text_secondary'])
        
        # Tab 3: Full Tailored Resume
        full_frame = tk.Frame(preview_notebook, bg=COLORS['bg'])
        preview_notebook.add(full_frame, text="✨ Tailored Resume (Full)")
        
        self.tailored_full_preview = scrolledtext.ScrolledText(
            full_frame,
            font=("Consolas", 10),
            bg='#16213e',
            fg='#e8e8e8',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.tailored_full_preview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Export Actions Frame (below preview)
        export_frame = ttkb.Labelframe(preview_frame, text="📁 Export & View Options", bootstyle="info")
        export_frame.pack(fill=tk.X, padx=5, pady=5)
        
        export_inner = tk.Frame(export_frame, bg=COLORS['bg'])
        export_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Row 1: View buttons
        view_row = tk.Frame(export_inner, bg=COLORS['bg'])
        view_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            view_row,
            text="View:",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.open_pdf_btn = ttkb.Button(
            view_row, text="📄 Open PDF", command=self._open_pdf,
            bootstyle="info", state=tk.DISABLED, width=12
        )
        self.open_pdf_btn.pack(side=tk.LEFT, padx=2)
        
        self.open_docx_btn = ttkb.Button(
            view_row, text="📝 Open DOCX", command=self._open_docx,
            bootstyle="success", state=tk.DISABLED, width=12
        )
        self.open_docx_btn.pack(side=tk.LEFT, padx=2)
        
        self.open_folder_btn = ttkb.Button(
            view_row, text="📁 Open Folder", command=self._open_folder,
            bootstyle="secondary", state=tk.DISABLED, width=12
        )
        self.open_folder_btn.pack(side=tk.LEFT, padx=2)
        
        # Row 2: Download/Export buttons
        export_row = tk.Frame(export_inner, bg=COLORS['bg'])
        export_row.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(
            export_row,
            text="Export:",
            font=("Segoe UI", 9, "bold"),
            fg=COLORS['text'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.download_pdf_btn = ttkb.Button(
            export_row, text="⬇️ Save PDF As...", command=self._download_pdf,
            bootstyle="primary-outline", state=tk.DISABLED, width=15
        )
        self.download_pdf_btn.pack(side=tk.LEFT, padx=2)
        
        self.download_docx_btn = ttkb.Button(
            export_row, text="⬇️ Save DOCX As...", command=self._download_docx,
            bootstyle="success-outline", state=tk.DISABLED, width=15
        )
        self.download_docx_btn.pack(side=tk.LEFT, padx=2)
        
        self.copy_text_btn = ttkb.Button(
            export_row, text="📋 Copy Text", command=self._copy_text,
            bootstyle="warning-outline", state=tk.DISABLED, width=12
        )
        self.copy_text_btn.pack(side=tk.LEFT, padx=2)
    
    def _build_suggestions_section(self, parent: tk.Frame):
        """Build the skill suggestions section (right column)."""
        suggestions_container = tk.Frame(parent, bg=COLORS['bg'])
        suggestions_container.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # Header
        header = ttkb.Labelframe(suggestions_container, text="💡 Skill Suggestions", bootstyle="warning")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header,
            text="Missing skills from JD that could boost your ATS score:",
            font=("Segoe UI", 8),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg'],
            wraplength=300
        ).pack(padx=10, pady=5)
        
        # Suggestions list (scrollable)
        canvas = tk.Canvas(suggestions_container, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(suggestions_container, orient="vertical", command=canvas.yview)
        
        self.suggestions_frame = tk.Frame(canvas, bg=COLORS['bg'])
        
        canvas_window = canvas.create_window((0, 0), window=self.suggestions_frame, anchor="nw")
        
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_width(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        self.suggestions_frame.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", configure_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Enable mouse wheel
        def on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
    
    def _display_skill_suggestions(self, suggestions: list[dict]):
        """Display skill suggestions with add buttons."""
        # Clear existing
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
        
        if not suggestions:
            tk.Label(
                self.suggestions_frame,
                text="✅ All key skills from JD are present!",
                font=("Segoe UI", 9),
                fg=COLORS['success'],
                bg=COLORS['bg'],
                wraplength=300
            ).pack(pady=20)
            return
        
        # Group by category
        by_category = {}
        for sugg in suggestions:
            cat = sugg['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(sugg)
        
        for category, skills in by_category.items():
            # Category header
            cat_frame = tk.Frame(self.suggestions_frame, bg=COLORS['card'], pady=5)
            cat_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(
                cat_frame,
                text=f"📌 {category.title()}",
                font=("Segoe UI", 10, "bold"),
                fg=COLORS['accent'],
                bg=COLORS['card']
            ).pack(anchor=tk.W, padx=10)
            
            # Skills in this category
            for skill_data in skills:
                skill = skill_data['skill']
                priority = skill_data['priority']
                
                skill_frame = tk.Frame(self.suggestions_frame, bg=COLORS['bg'])
                skill_frame.pack(fill=tk.X, padx=10, pady=2)
                
                # Priority indicator
                priority_color = COLORS['danger'] if priority >= 3 else COLORS['warning']
                tk.Label(
                    skill_frame,
                    text=f"({priority})",
                    font=("Segoe UI", 8),
                    fg=priority_color,
                    bg=COLORS['bg'],
                    width=4
                ).pack(side=tk.LEFT)
                
                # Skill name
                tk.Label(
                    skill_frame,
                    text=skill,
                    font=("Segoe UI", 9),
                    fg=COLORS['text'],
                    bg=COLORS['bg']
                ).pack(side=tk.LEFT, padx=5)
                
                # Add button
                ttkb.Button(
                    skill_frame,
                    text="+ Add",
                    command=lambda s=skill: self._add_skill_to_resume(s),
                    bootstyle="success-outline",
                    width=6
                ).pack(side=tk.RIGHT)
    
    def _add_skill_to_resume(self, skill: str):
        """Add a suggested skill to the resume text."""
        if not self.resume_text:
            return
        
        current_text = self.resume_text.get("1.0", tk.END).strip()
        
        # Try to find skills section
        lines = current_text.split('\n')
        inserted = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Look for skills line with commas
            if 'skill' in line_lower or (',' in line and any(tech in line_lower for tech in ['python', 'java', 'aws', 'docker', 'sql', 'api'])):
                # Found a skills line - append to it
                if i + 1 < len(lines) and ',' in lines[i + 1]:
                    # Skills are on next line
                    lines[i + 1] = lines[i + 1].rstrip() + f", {skill.title()}"
                    inserted = True
                    break
                elif ',' in line:
                    # Skills are on this line
                    lines[i] = line.rstrip() + f", {skill.title()}"
                    inserted = True
                    break
        
        if not inserted:
            # Append to end
            lines.append(f"\nAdditional Skills: {skill.title()}")
        
        # Update resume text
        new_text = '\n'.join(lines)
        self.resume_text.delete("1.0", tk.END)
        self.resume_text.insert(tk.END, new_text)
        
        self._update_status(f"✅ Added '{skill}' to resume", "success")
    
    def _quick_ats_check(self):
        """Quick ATS check without tailoring."""
        resume_content = self.resume_text.get("1.0", tk.END).strip() if self.resume_text else ""
        jd_content = self.jd_text.get("1.0", tk.END).strip() if self.jd_text else ""
        
        if not resume_content or not jd_content or jd_content.startswith("Paste the"):
            messagebox.showwarning("Missing Input", "Please provide both resume and job description.")
            return
        
        # Calculate score
        score_data = _score_match(resume_content, jd_content)
        self.before_ats_score = score_data
        
        # Update UI
        self._update_ats_display(before=score_data['ats'], after=None)
        
        # Show suggestions
        suggestions = extract_skill_suggestions(jd_content, resume_content)
        self.skill_suggestions = suggestions
        self._display_skill_suggestions(suggestions)
        
        self._update_status(f"📊 Current ATS Score: {score_data['ats']}% ({score_data['matched']}/{score_data['total']} keywords)", "info")
    
    def _run_tailor(self):
        """Start tailoring process."""
        if self.is_processing:
            return
        
        resume_content = self.resume_text.get("1.0", tk.END).strip() if self.resume_text else ""
        jd_content = self.jd_text.get("1.0", tk.END).strip() if self.jd_text else ""
        provider = self.provider_var.get().strip().lower()
        job_title = self.job_title_var.get().strip() or None
        resume_path = self.resume_path_var.get().strip() or None
        
        if not jd_content or jd_content.startswith("Paste the"):
            messagebox.showerror("Missing Input", "Please paste the job description.")
            return
        if not resume_content and not resume_path:
            messagebox.showerror("Missing Input", "Please provide resume content or file.")
            return
        
        self.master_resume_text = resume_content
        self.is_processing = True
        
        if self.tailor_btn:
            self.tailor_btn.config(state=tk.DISABLED, text="⏳ Processing...")
        if self.progress_bar:
            self.progress_bar.start()
        
        self._update_status("🔄 Tailoring resume with AI...", "info")
        
        # Calculate before score
        before_score = _score_match(resume_content, jd_content)
        self.before_ats_score = before_score
        self._update_ats_display(before=before_score['ats'], after=None)
        
        # Run in background
        threading.Thread(
            target=self._worker,
            args=(resume_content, jd_content, provider, resume_path, job_title),
            daemon=True
        ).start()
    
    def _worker(self, resume_text: str, jd_text: str, provider: str, 
                resume_path: str | None, job_title: str | None):
        """Background worker for tailoring."""
        try:
            # Perform tailoring
            paths = tailor_resume_to_files(
                resume_text=resume_text or None,
                job_description=jd_text,
                instructions=None,
                provider=provider,
                resume_path=resume_path,
                job_title=job_title,
                enable_preview=False,
            )
            
            # Read tailored text
            if paths.get("txt") and os.path.exists(paths["txt"]):
                with open(paths["txt"], "r", encoding="utf-8") as f:
                    tailored_text = f.read()
            else:
                tailored_text = tailor_resume_text(
                    resume_text=resume_text,
                    job_description=jd_text,
                    instructions=None,
                    provider=provider
                )
            
            # Calculate after score
            after_score = _score_match(tailored_text, jd_text)
            
            # Generate suggestions for missing skills
            suggestions = extract_skill_suggestions(jd_text, tailored_text)
            
            self.after(0, lambda: self._on_success(paths, tailored_text, after_score, suggestions))
            
        except Exception as e:
            self.after(0, lambda: self._on_error(e))
    
    def _on_success(self, paths: dict, tailored_text: str, after_score: dict, suggestions: list[dict]):
        """Handle successful tailoring."""
        self.is_processing = False
        
        if self.progress_bar:
            self.progress_bar.stop()
        if self.tailor_btn:
            self.tailor_btn.config(state=tk.NORMAL, text="🚀 START TAILORING")
        
        self.current_paths = paths
        self.tailored_resume_text = tailored_text
        self.after_ats_score = after_score
        self.skill_suggestions = suggestions
        
        # Update ATS display
        before_score = self.before_ats_score['ats'] if self.before_ats_score else 0
        self._update_ats_display(before=before_score, after=after_score['ats'])
        
        # Update previews with highlighting
        self._update_previews_with_highlighting(self.master_resume_text, tailored_text)
        
        # Display diff
        self._display_diff(self.master_resume_text, tailored_text)
        
        # Update full preview
        if hasattr(self, 'tailored_full_preview') and self.tailored_full_preview:
            self.tailored_full_preview.config(state=tk.NORMAL)
            self.tailored_full_preview.delete("1.0", tk.END)
            self.tailored_full_preview.insert(tk.END, tailored_text)
            self.tailored_full_preview.config(state=tk.DISABLED)
        
        # Show suggestions
        self._display_skill_suggestions(suggestions)
        
        # Enable export buttons
        if self.open_pdf_btn:
            self.open_pdf_btn.config(state=tk.NORMAL if paths.get("pdf") else tk.DISABLED)
        if self.open_docx_btn:
            self.open_docx_btn.config(state=tk.NORMAL if paths.get("docx") else tk.DISABLED)
        if self.download_pdf_btn:
            self.download_pdf_btn.config(state=tk.NORMAL if paths.get("pdf") else tk.DISABLED)
        if self.download_docx_btn:
            self.download_docx_btn.config(state=tk.NORMAL if paths.get("docx") else tk.DISABLED)
        if self.open_folder_btn:
            self.open_folder_btn.config(state=tk.NORMAL)
        if self.copy_text_btn:
            self.copy_text_btn.config(state=tk.NORMAL)
        
        improvement = after_score['ats'] - before_score
        self._update_status(f"✅ Done! ATS improved from {before_score}% to {after_score['ats']}% (+{improvement}%)", "success")
    
    def _update_previews_with_highlighting(self, original: str, tailored: str):
        """Update preview panels with diff highlighting."""
        # Original text (no highlighting)
        if self.master_preview:
            self.master_preview.config(state=tk.NORMAL)
            self.master_preview.delete("1.0", tk.END)
            self.master_preview.insert(tk.END, original)
            self.master_preview.config(state=tk.DISABLED)
        
        # Tailored text with additions highlighted
        if self.tailored_preview:
            self.tailored_preview.config(state=tk.NORMAL)
            self.tailored_preview.delete("1.0", tk.END)
            
            # Calculate additions
            additions, removals = calculate_text_diff(original, tailored)
            
            # Insert tailored text
            self.tailored_preview.insert(tk.END, tailored)
            
            # Highlight additions in tailored text
            for addition in additions:
                if addition.strip():
                    # Find and highlight the addition
                    start_idx = "1.0"
                    while True:
                        start_idx = self.tailored_preview.search(addition, start_idx, tk.END, nocase=False)
                        if not start_idx:
                            break
                        end_idx = f"{start_idx}+{len(addition)}c"
                        self.tailored_preview.tag_add("addition", start_idx, end_idx)
                        start_idx = end_idx
            
            self.tailored_preview.config(state=tk.DISABLED)
    
    def _display_diff(self, original: str, tailored: str):
        """Display detailed diff with color coding."""
        if not self.diff_text:
            return
        
        self.diff_text.config(state=tk.NORMAL)
        self.diff_text.delete("1.0", tk.END)
        
        # Calculate diff
        original_lines = original.split('\n')
        tailored_lines = tailored.split('\n')
        
        differ = difflib.Differ()
        diff = list(differ.compare(original_lines, tailored_lines))
        
        for line in diff:
            if line.startswith('+ '):
                # Addition
                self.diff_text.insert(tk.END, line[2:] + '\n', "added")
            elif line.startswith('- '):
                # Removal
                self.diff_text.insert(tk.END, line[2:] + '\n', "removed")
            elif line.startswith('  '):
                # Context (unchanged)
                self.diff_text.insert(tk.END, line[2:] + '\n', "context")
        
        self.diff_text.config(state=tk.DISABLED)
    
    def _update_ats_display(self, before: int, after: int | None):
        """Update ATS score display."""
        # Color coding
        def get_color(score):
            if score >= 80:
                return COLORS['success']
            elif score >= 60:
                return COLORS['warning']
            else:
                return COLORS['danger']
        
        if self.before_score_label:
            self.before_score_label.config(text=f"{before}%", fg=get_color(before))
        
        if after is not None:
            if self.improvement_arrow:
                improvement = after - before
                if improvement > 0:
                    self.improvement_arrow.config(text=f"→ +{improvement}%", fg=COLORS['success'])
                elif improvement < 0:
                    self.improvement_arrow.config(text=f"→ {improvement}%", fg=COLORS['danger'])
                else:
                    self.improvement_arrow.config(text="→", fg=COLORS['text_secondary'])
            
            if self.after_score_label:
                self.after_score_label.config(text=f"{after}%", fg=get_color(after))
        else:
            if self.improvement_arrow:
                self.improvement_arrow.config(text="")
            if self.after_score_label:
                self.after_score_label.config(text="--", fg=COLORS['text_secondary'])
    
    def _on_error(self, error: Exception):
        """Handle error."""
        self.is_processing = False
        
        if self.progress_bar:
            self.progress_bar.stop()
        if self.tailor_btn:
            self.tailor_btn.config(state=tk.NORMAL, text="🚀 START TAILORING")
        
        self._update_status(f"❌ Error: {str(error)}", "danger")
        messagebox.showerror("Tailoring Error", str(error))
    
    def _update_status(self, text: str, level: str = "info"):
        """Update status label."""
        if self.status_label:
            colors = {
                "success": COLORS['success'],
                "warning": COLORS['warning'],
                "danger": COLORS['danger'],
                "info": COLORS['text_secondary']
            }
            self.status_label.config(text=text, fg=colors.get(level, COLORS['text']))
    
    def _browse_resume(self):
        """Browse for resume file."""
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Resume",
            filetypes=[
                ("All Resume Files", "*.pdf *.docx *.txt"),
                ("PDF Files", "*.pdf"),
                ("Word Documents", "*.docx"),
                ("Text Files", "*.txt")
            ]
        )
        if path:
            self.resume_path_var.set(path)
    
    def _load_resume_file(self):
        """Load resume from file."""
        path = self.resume_path_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("File Not Found", "Please select a valid resume file.")
            return
        
        try:
            content = _read_resume_text(path)
            if self.resume_text:
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(tk.END, content)
            self._update_status(f"✅ Loaded {os.path.basename(path)}", "success")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")
    
    def _reset_form(self):
        """Reset the form."""
        if self.resume_text:
            self.resume_text.delete("1.0", tk.END)
        if self.jd_text:
            self.jd_text.delete("1.0", tk.END)
            self.jd_text.insert(tk.END, "Paste the complete job description here...")
        
        self.job_title_var.set("")
        self.resume_path_var.set("")
        
        for preview in [self.master_preview, self.tailored_preview]:
            if preview:
                preview.config(state=tk.NORMAL)
                preview.delete("1.0", tk.END)
                preview.config(state=tk.DISABLED)
        
        if self.diff_text:
            self.diff_text.config(state=tk.NORMAL)
            self.diff_text.delete("1.0", tk.END)
            self.diff_text.config(state=tk.DISABLED)
        
        self._update_ats_display(before=0, after=None)
        self._display_skill_suggestions([])
        self._update_status("💡 Ready to tailor your resume with AI", "info")
        
        # Disable export buttons
        for btn in [self.open_pdf_btn, self.open_docx_btn, self.download_pdf_btn, 
                    self.download_docx_btn, self.open_folder_btn, self.copy_text_btn]:
            if btn:
                btn.config(state=tk.DISABLED)
    
    # Export/View Methods
    
    def _open_pdf(self):
        """Open the generated PDF file."""
        if self.current_paths.get("pdf") and os.path.exists(self.current_paths["pdf"]):
            try:
                os.startfile(self.current_paths["pdf"])
                self._update_status("📄 Opening PDF viewer...", "info")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open PDF: {e}")
    
    def _open_docx(self):
        """Open the generated DOCX file."""
        if self.current_paths.get("docx") and os.path.exists(self.current_paths["docx"]):
            try:
                os.startfile(self.current_paths["docx"])
                self._update_status("📝 Opening Word document...", "info")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open DOCX: {e}")
    
    def _open_folder(self):
        """Open the folder containing generated files."""
        folder = os.path.dirname(
            self.current_paths.get("pdf") or 
            self.current_paths.get("docx") or 
            self.current_paths.get("txt", "")
        )
        if folder and os.path.exists(folder):
            try:
                os.startfile(folder)
                self._update_status("📁 Opening output folder...", "info")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {e}")
    
    def _download_pdf(self):
        """Save PDF to user-selected location."""
        if not self.current_paths.get("pdf") or not os.path.exists(self.current_paths["pdf"]):
            messagebox.showwarning("No PDF", "PDF file not found. Please tailor resume first.")
            return
        
        try:
            save_path = filedialog.asksaveasfilename(
                parent=self,
                title="Save PDF As",
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
                initialfile="tailored_resume.pdf"
            )
            
            if save_path:
                import shutil
                shutil.copy2(self.current_paths["pdf"], save_path)
                self._update_status(f"✅ PDF saved to {os.path.basename(save_path)}", "success")
                messagebox.showinfo("Success", f"PDF saved successfully!\n\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF: {e}")
    
    def _download_docx(self):
        """Save DOCX to user-selected location."""
        if not self.current_paths.get("docx") or not os.path.exists(self.current_paths["docx"]):
            messagebox.showwarning("No DOCX", "DOCX file not found. Please tailor resume first.")
            return
        
        try:
            save_path = filedialog.asksaveasfilename(
                parent=self,
                title="Save DOCX As",
                defaultextension=".docx",
                filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")],
                initialfile="tailored_resume.docx"
            )
            
            if save_path:
                import shutil
                shutil.copy2(self.current_paths["docx"], save_path)
                self._update_status(f"✅ DOCX saved to {os.path.basename(save_path)}", "success")
                messagebox.showinfo("Success", f"DOCX saved successfully!\n\n{save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save DOCX: {e}")
    
    def _copy_text(self):
        """Copy tailored resume text to clipboard."""
        if self.tailored_resume_text:
            try:
                self.clipboard_clear()
                self.clipboard_append(self.tailored_resume_text)
                self.update()  # Update the clipboard
                self._update_status("📋 Copied to clipboard!", "success")
                messagebox.showinfo("Success", "Resume text copied to clipboard!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to copy text: {e}")


def open_enhanced_resume_tailor_dialog(parent, default_provider: str = "ollama", default_resume_text: str = ""):
    """Open the enhanced resume tailor dialog."""
    dialog = EnhancedResumeTailorDialog(parent, default_provider, default_resume_text)
    dialog.wait_window()
