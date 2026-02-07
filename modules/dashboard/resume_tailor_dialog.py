"""
Enhanced Resume Tailor Dialog with Full-Fledged Preview
Standalone resume tailoring feature with side-by-side comparison, ATS scoring, and file export.
"""
import os
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
)
from modules.dashboard.api_config_dialog import open_api_config_dialog


def _check_ollama_connection(model_name: str) -> tuple[bool, str]:
    """Check if Ollama is running and the model is available."""
    try:
        from config.secrets import ollama_api_url
        url = f"{ollama_api_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            model_base = model_name.split(":")[0]
            if model_base in models or model_name in [m.get("name", "") for m in data.get("models", [])]:
                return True, f"Connected: {model_name}"
            return False, f"Model '{model_name}' not found"
    except Exception as e:
        return False, f"Ollama offline: {e}"


def _check_api_connection(provider: str) -> tuple[bool, str]:
    """Check if API provider is configured."""
    try:
        if provider == "ollama":
            from config.secrets import ollama_model
            return _check_ollama_connection(ollama_model)

        provider_map = {
            "groq": {
                "key": "groq_api_key",
                "model": "groq_model",
                "invalid": "your_groq_api_key_here",
                "missing": "Groq API key not set",
                "label": lambda m: f"Groq: {m}",
            },
            "huggingface": {
                "key": "huggingface_api_key",
                "model": "huggingface_model",
                "invalid": "your_huggingface_api_key_here",
                "missing": "HuggingFace API key not set",
                "label": lambda m: f"HF: {m.split('/')[-1] if '/' in m else m}",
            },
            "openai": {
                "key": "llm_api_key",
                "model": "llm_model",
                "invalid": "your_openai_api_key_here",
                "missing": "OpenAI API key not set",
                "label": lambda m: f"OpenAI: {m}",
            },
            "deepseek": {
                "key": "deepseek_api_key",
                "model": "deepseek_model",
                "invalid": "your_deepseek_api_key_here",
                "missing": "DeepSeek API key not set",
                "label": lambda m: f"DeepSeek: {m}",
            },
            "gemini": {
                "key": "gemini_api_key",
                "model": "gemini_model",
                "invalid": "your_gemini_api_key_here",
                "missing": "Gemini API key not set",
                "label": lambda m: f"Gemini: {m}",
            },
        }

        config = provider_map.get(provider)
        if not config:
            return False, "Unknown provider"

        from config import secrets
        api_key = getattr(secrets, config["key"], "")
        model = getattr(secrets, config["model"], "")
        if api_key and api_key != config["invalid"]:
            return True, config["label"](model)
        return False, config["missing"]
    except Exception as e:
        return False, str(e)

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
}

# UI constants
UI_FONT = "Segoe UI"
START_TAILORING_TEXT = "🚀 START TAILORING"
JD_PLACEHOLDER_PREFIX = "Paste the job description"
JD_PLACEHOLDER_TEXT = (
    "Paste the job description here...\n\n"
    "Include:\n- Job title\n- Requirements\n- Responsibilities\n- Skills needed"
)
MISSING_JD_TITLE = "Missing JD"


class ResumeTailorDialog(tk.Toplevel):
    """Full-featured Resume Tailoring Dialog with integrated preview."""
    
    def __init__(self, parent: tk.Tk, default_provider: str, default_resume_text: str | None):
        super().__init__(parent)
        self.title("📝 AI Resume Tailor - Standalone")
        self.geometry("1400x900")
        self.minsize(1200, 750)
        self.configure(bg=COLORS['bg'])
        
        # State variables
        self.provider_var = tk.StringVar(value=default_provider)
        self.job_title_var = tk.StringVar(value="")
        self.resume_path_var = tk.StringVar(value="")
        self.master_resume_text = ""
        self.tailored_resume_text = ""
        self.current_paths = {}
        self.is_processing = False
        self.cancel_requested = False  # For cancellation
        self.animation_running = False
        self.animation_value = 0
        self.process_start_time = 0.0  # Track elapsed time
        self.connection_status_label: tk.Label | None = None
        self.model_info_label: tk.Label | None = None
        self.elapsed_time_label: tk.Label | None = None  # Show elapsed time
        self.cancel_btn: ttkb.Button | None = None  # Cancel button
        self.jd_word_count_label: tk.Label | None = None  # JD word count
        
        # UI references
        self.instr_text: scrolledtext.ScrolledText | None = None
        self.resume_text: scrolledtext.ScrolledText | None = None
        self.jd_text: scrolledtext.ScrolledText | None = None
        self.master_preview: scrolledtext.ScrolledText | None = None
        self.tailored_preview: scrolledtext.ScrolledText | None = None
        self.status_label: tk.Label | None = None
        self.progress_bar: ttkb.Progressbar | None = None
        self.progress_label: tk.Label | None = None
        self.ats_score_label: tk.Label | None = None
        self.improvement_label: tk.Label | None = None
        self.keywords_frame: tk.Frame | None = None
        self.open_pdf_btn: ttkb.Button | None = None
        self.open_docx_btn: ttkb.Button | None = None
        self.open_folder_btn: ttkb.Button | None = None
        self.copy_btn: ttkb.Button | None = None
        self.tailor_btn: ttkb.Button | None = None
        self.view_diff_btn: ttkb.Button | None = None
        
        self._build_ui(default_resume_text or "")
        
        # Keyboard shortcuts
        self.bind("<Control-Return>", lambda e: self._run_tailor())  # Ctrl+Enter to tailor
        self.bind("<Escape>", lambda e: self.destroy())  # Escape to close
        self.bind("<Control-r>", lambda e: self._reset_form())  # Ctrl+R to reset
        self.bind("<F5>", lambda e: self._check_connection())  # F5 to refresh connection
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.winfo_screenheight() // 2) - (900 // 2)
        self.geometry(f"1400x900+{x}+{y}")
        
        # Focus on JD text for immediate input
        self.after(100, lambda: self.jd_text.focus_set() if self.jd_text else None)
    
    def _build_ui(self, default_resume_text: str):
        """Build the complete UI with clear layout."""
        
        # ============================================
        # HEADER
        # ============================================
        header_frame = tk.Frame(self, bg=COLORS['bg'])
        header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="🎯 AI Resume Tailor",
            font=(UI_FONT, 18, "bold"),
            fg=COLORS['accent'],
            bg=COLORS['bg']
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle = tk.Label(
            header_frame,
            text="Tailor your resume with AI  •  Ctrl+Enter: Tailor  •  F5: Refresh  •  Esc: Close",
            font=(UI_FONT, 9),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        )
        subtitle.pack(side=tk.LEFT, padx=20)
        
        # ============================================
        # ACTION BAR (ALWAYS VISIBLE AT TOP)
        # ============================================
        action_bar = tk.Frame(self, bg='#0f3460', pady=8)
        action_bar.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Left side - Main action buttons
        left_actions = tk.Frame(action_bar, bg='#0f3460')
        left_actions.pack(side=tk.LEFT, padx=10)
        
        self.tailor_btn = ttkb.Button(
            left_actions, text=START_TAILORING_TEXT, command=self._run_tailor,
            bootstyle="success", width=20
        )
        self.tailor_btn.pack(side=tk.LEFT, padx=5)
        
        # Cancel button (hidden by default, shown during processing)
        self.cancel_btn = ttkb.Button(
            left_actions, text="❌ Cancel", command=self._cancel_processing,
            bootstyle="danger", width=10
        )
        # Don't pack initially - will be shown during processing
        
        ttkb.Button(
            left_actions, text="📊 Check ATS Score", command=self._quick_score,
            bootstyle="info-outline", width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # Center - Progress section
        progress_frame = tk.Frame(action_bar, bg='#0f3460')
        progress_frame.pack(side=tk.LEFT, padx=20, expand=True)
        
        # Progress info row (label + percentage)
        progress_info = tk.Frame(progress_frame, bg='#0f3460')
        progress_info.pack(side=tk.TOP, fill=tk.X)
        
        self.progress_label = tk.Label(
            progress_info,
            text="Ready to tailor",
            font=(UI_FONT, 10, "bold"),
            fg=COLORS['text'],
            bg='#0f3460'
        )
        self.progress_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Elapsed time label (shows during processing)
        self.elapsed_time_label = tk.Label(
            progress_info,
            text="",
            font=(UI_FONT, 9),
            fg=COLORS['text_secondary'],
            bg='#0f3460'
        )
        self.elapsed_time_label.pack(side=tk.LEFT, padx=10, anchor=tk.W)
        
        self.progress_percent_label = tk.Label(
            progress_info,
            text="",
            font=(UI_FONT, 10, "bold"),
            fg=COLORS['success'],
            bg='#0f3460'
        )
        self.progress_percent_label.pack(side=tk.RIGHT, anchor=tk.E)
        
        self.progress_bar = ttkb.Progressbar(
            progress_frame, mode='determinate', bootstyle="success-striped", length=350
        )
        self.progress_bar.pack(side=tk.TOP, fill=tk.X, pady=(3, 0))
        
        # Right side - Other buttons
        right_actions = tk.Frame(action_bar, bg='#0f3460')
        right_actions.pack(side=tk.RIGHT, padx=10)
        
        ttkb.Button(
            right_actions, text="🔄 Reset", command=self._reset_form,
            bootstyle="secondary-outline", width=8
        ).pack(side=tk.LEFT, padx=3)
        
        ttkb.Button(
            right_actions, text="✖️ Close", command=self.destroy,
            bootstyle="danger-outline", width=8
        ).pack(side=tk.LEFT, padx=3)
        
        # ============================================
        # MAIN CONTENT - TWO COLUMNS
        # ============================================
        main_frame = tk.Frame(self, bg=COLORS['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure grid
        main_frame.columnconfigure(0, weight=1, minsize=550)  # Left panel
        main_frame.columnconfigure(1, weight=1, minsize=550)  # Right panel
        main_frame.rowconfigure(0, weight=1)
        
        # LEFT PANEL - Input Section (with scroll)
        left_container = tk.Frame(main_frame, bg=COLORS['bg'])
        left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_container.rowconfigure(0, weight=1)
        left_container.columnconfigure(0, weight=1)
        
        # Create canvas for scrolling with fixed width
        left_canvas = tk.Canvas(left_container, bg=COLORS['bg'], highlightthickness=0, width=500)
        left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
        
        # Create scrollable frame inside canvas
        left_panel = tk.Frame(left_canvas, bg=COLORS['bg'])
        
        # Configure canvas window to expand horizontally
        def _configure_scroll_region(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        
        def _configure_canvas_width(event):
            # Make the inner frame match canvas width
            canvas_width = event.width
            left_canvas.itemconfig(canvas_window_id, width=canvas_width)
        
        canvas_window_id = left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
        left_panel.bind("<Configure>", _configure_scroll_region)
        left_canvas.bind("<Configure>", _configure_canvas_width)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # Use grid for better control
        left_canvas.grid(row=0, column=0, sticky="nsew")
        left_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mouse wheel scrolling only when mouse is over the canvas
        def _on_mousewheel(event):
            try:
                left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass  # Ignore if canvas is destroyed
        
        def _bind_mousewheel(event):
            left_canvas.bind("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            left_canvas.unbind("<MouseWheel>")
        
        left_canvas.bind("<Enter>", _bind_mousewheel)
        left_canvas.bind("<Leave>", _unbind_mousewheel)
        left_panel.bind("<Enter>", _bind_mousewheel)
        left_panel.bind("<Leave>", _unbind_mousewheel)
        
        # Build input panel contents
        self._build_input_panel(left_panel, default_resume_text)
        
        # RIGHT PANEL - Preview Section
        right_panel = tk.Frame(main_frame, bg=COLORS['bg'])
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        self._build_preview_panel(right_panel)
        
        # ============================================
        # BOTTOM - Status & Actions
        # ============================================
        self._build_bottom_panel()
    
    def _build_input_panel(self, parent: tk.Frame, default_resume_text: str):
        """Build the input section (left panel)."""
        
        # ========== CONFIGURATION ==========
        config_frame = ttkb.Labelframe(parent, text="⚙️ Configuration", bootstyle="info")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        config_inner = tk.Frame(config_frame, bg=COLORS['bg'])
        config_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Provider selection row
        provider_row = tk.Frame(config_inner, bg=COLORS['bg'])
        provider_row.pack(fill=tk.X, pady=3)
        
        tk.Label(provider_row, text="AI Provider:", font=(UI_FONT, 10, "bold"), 
                 fg=COLORS['text'], bg=COLORS['bg']).pack(side=tk.LEFT)
        
        provider_combo = ttkb.Combobox(
            provider_row,
            textvariable=self.provider_var,
            values=["ollama", "groq", "huggingface", "openai", "deepseek", "gemini"],
            width=12,
            bootstyle="info"
        )
        provider_combo.pack(side=tk.LEFT, padx=5)
        
        # Connection status indicator (green/red dot)
        self.connection_status_label = tk.Label(
            provider_row,
            text="●",
            font=(UI_FONT, 12),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        )
        self.connection_status_label.pack(side=tk.LEFT, padx=2)
        
        # Model info label (shows actual model name)
        self.model_info_label = tk.Label(
            provider_row,
            text="Checking...",
            font=(UI_FONT, 9, "italic"),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        )
        self.model_info_label.pack(side=tk.LEFT, padx=5)
        
        # Refresh connection button
        ttkb.Button(
            provider_row, text="🔄", command=self._check_connection,
            bootstyle="secondary-outline", width=3
        ).pack(side=tk.LEFT, padx=2)
        
        # Configure API Keys button
        ttkb.Button(
            provider_row, text="⚙️ Config APIs", command=self._open_api_config,
            bootstyle="warning-outline", width=12
        ).pack(side=tk.LEFT, padx=5)
        
        def update_provider_and_check(e):
            self._check_connection()
        provider_combo.bind("<<ComboboxSelected>>", update_provider_and_check)
        
        # Initial connection check (after UI built)
        self.after(500, self._check_connection)
        
        # Job Title row
        title_row = tk.Frame(config_inner, bg=COLORS['bg'])
        title_row.pack(fill=tk.X, pady=5)
        
        tk.Label(title_row, text="Job Title:", font=(UI_FONT, 10, "bold"), 
                 fg=COLORS['text'], bg=COLORS['bg']).pack(side=tk.LEFT)
        ttkb.Entry(title_row, textvariable=self.job_title_var, width=40, 
                   bootstyle="info").pack(side=tk.LEFT, padx=8)
        
        # ========== RESUME FILE ==========
        file_frame = ttkb.Labelframe(parent, text="📄 Master Resume File (optional)", bootstyle="success")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        file_inner = tk.Frame(file_frame, bg=COLORS['bg'])
        file_inner.pack(fill=tk.X, padx=10, pady=10)
        
        file_row = tk.Frame(file_inner, bg=COLORS['bg'])
        file_row.pack(fill=tk.X)
        
        ttkb.Entry(file_row, textvariable=self.resume_path_var, width=40).pack(side=tk.LEFT, padx=(0, 5))
        ttkb.Button(file_row, text="📂 Browse", command=self._browse_resume, 
                    bootstyle="success-outline", width=10).pack(side=tk.LEFT)
        ttkb.Button(file_row, text="📋 Load", command=self._load_resume_file, 
                    bootstyle="info-outline", width=8).pack(side=tk.LEFT, padx=5)
        
        # ========== RESUME TEXT ==========
        resume_frame = ttkb.Labelframe(parent, text="📝 YOUR RESUME (paste or load from file above)", bootstyle="primary")
        resume_frame.pack(fill=tk.X, padx=5, pady=5)
        
        resume_hint = tk.Label(
            resume_frame, 
            text="Paste your complete resume text below:",
            font=(UI_FONT, 9),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        )
        resume_hint.pack(anchor=tk.W, padx=10, pady=(5, 0))
        
        # NOTE: ScrolledText has its own scrollbar - use fill=X for canvas compatibility
        self.resume_text = scrolledtext.ScrolledText(
            resume_frame, 
            height=10,  # Increased height
            font=("Consolas", 9),
            bg=COLORS['card'],
            fg=COLORS['text'],
            insertbackground='white',
            wrap=tk.WORD
        )
        self.resume_text.pack(fill=tk.X, padx=10, pady=10)
        if default_resume_text.strip():
            self.resume_text.insert(tk.END, default_resume_text.strip())
        
        # ========== JOB DESCRIPTION ========== (THE IMPORTANT ONE!)
        jd_frame = ttkb.Labelframe(parent, text="💼 JOB DESCRIPTION (paste the full JD here!)", bootstyle="warning")
        jd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        jd_hint = tk.Label(
            jd_frame,
            text="⬇️ PASTE THE COMPLETE JOB DESCRIPTION BELOW ⬇️",
            font=(UI_FONT, 10, "bold"),
            fg=COLORS['warning'],
            bg=COLORS['bg']
        )
        jd_hint.pack(anchor=tk.W, padx=10, pady=(8, 0))
        
        # NOTE: ScrolledText has its own scrollbar - set large height so user can see full JD
        self.jd_text = scrolledtext.ScrolledText(
            jd_frame,
            height=20,  # Larger height to show more content
            font=("Consolas", 9),
            bg='#1e3a4c',  # Slightly different color to stand out
            fg=COLORS['text'],
            insertbackground='yellow',
            wrap=tk.WORD
        )
        self.jd_text.pack(fill=tk.X, padx=10, pady=10)
        self.jd_text.insert(tk.END, JD_PLACEHOLDER_TEXT)
        
        # Word count label for JD
        self.jd_word_count_label = tk.Label(
            jd_frame,
            text="Words: 0",
            font=(UI_FONT, 8),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        )
        self.jd_word_count_label.pack(anchor=tk.E, padx=10, pady=(0, 5))
        
        # Update word count on key release
        def update_jd_word_count(event=None):
            if not self.jd_text or not self.jd_word_count_label:
                return
            text = self.jd_text.get("1.0", tk.END).strip()
            if text.startswith(JD_PLACEHOLDER_PREFIX):
                word_count = 0
            else:
                word_count = len(text.split())
            self.jd_word_count_label.config(text=f"Words: {word_count}")
            # Color code based on length
            if word_count < 50:
                self.jd_word_count_label.config(fg=COLORS['warning'])
            elif word_count < 200:
                self.jd_word_count_label.config(fg=COLORS['text_secondary'])
            else:
                self.jd_word_count_label.config(fg=COLORS['success'])
        self.jd_text.bind("<KeyRelease>", update_jd_word_count)
        self.jd_text.bind("<<Paste>>", lambda e: self.after(50, update_jd_word_count))
        
        # Clear placeholder on focus
        def clear_placeholder(event):
            if not self.jd_text:
                return
            if self.jd_text.get("1.0", tk.END).strip().startswith(JD_PLACEHOLDER_PREFIX):
                self.jd_text.delete("1.0", tk.END)
                update_jd_word_count()  # Update word count after clearing
        self.jd_text.bind("<FocusIn>", clear_placeholder)
        
        # ========== CUSTOM INSTRUCTIONS ==========
        instr_frame = ttkb.Labelframe(parent, text="📋 Custom Instructions (optional)", bootstyle="secondary")
        instr_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.instr_text = scrolledtext.ScrolledText(
            instr_frame,
            height=3,
            font=("Consolas", 9),
            bg=COLORS['card'],
            fg=COLORS['text'],
            insertbackground='white',
            wrap=tk.WORD
        )
        self.instr_text.pack(fill=tk.X, padx=10, pady=10)
        self.instr_text.insert(tk.END, "Focus on technical skills. Keep it professional and ATS-friendly.")
    
    def _build_preview_panel(self, parent: tk.Frame):
        """Build the preview section (right panel)."""
        
        # ========== ATS SCORE CARD ==========
        score_frame = ttkb.Labelframe(parent, text="📊 ATS Score & Analysis", bootstyle="success")
        score_frame.pack(fill=tk.X, padx=5, pady=5)
        
        score_inner = tk.Frame(score_frame, bg=COLORS['bg'])
        score_inner.pack(fill=tk.X, padx=10, pady=10)
        
        score_row = tk.Frame(score_inner, bg=COLORS['bg'])
        score_row.pack(fill=tk.X)
        
        self.ats_score_label = tk.Label(
            score_row,
            text="ATS Score: --",
            font=(UI_FONT, 16, "bold"),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        )
        self.ats_score_label.pack(side=tk.LEFT)
        
        self.improvement_label = tk.Label(
            score_row,
            text="",
            font=(UI_FONT, 12),
            fg=COLORS['success'],
            bg=COLORS['bg']
        )
        self.improvement_label.pack(side=tk.LEFT, padx=20)
        
        # Keywords display
        self.keywords_frame = tk.Frame(score_inner, bg=COLORS['bg'])
        self.keywords_frame.pack(fill=tk.X, pady=5)
        
        # ========== PREVIEW NOTEBOOK ==========
        preview_notebook = ttkb.Notebook(parent, bootstyle="dark")
        preview_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Tab 1: Side by Side ---
        comparison_frame = tk.Frame(preview_notebook, bg=COLORS['bg'])
        preview_notebook.add(comparison_frame, text="📑 Side-by-Side Comparison")
        
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.columnconfigure(1, weight=1)
        comparison_frame.rowconfigure(1, weight=1)
        
        # Original label
        tk.Label(
            comparison_frame,
            text="📋 ORIGINAL RESUME",
            font=(UI_FONT, 10, "bold"),
            fg="#74c0fc",
            bg=COLORS['bg']
        ).grid(row=0, column=0, pady=5)
        
        # Tailored label
        tk.Label(
            comparison_frame,
            text="✨ TAILORED RESUME",
            font=(UI_FONT, 10, "bold"),
            fg="#69db7c",
            bg=COLORS['bg']
        ).grid(row=0, column=1, pady=5)
        
        # Master preview
        self.master_preview = scrolledtext.ScrolledText(
            comparison_frame,
            font=("Consolas", 9),
            bg='#16213e',
            fg='#e8e8e8',
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.master_preview.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)
        
        # Tailored preview
        self.tailored_preview = scrolledtext.ScrolledText(
            comparison_frame,
            font=("Consolas", 9),
            bg='#16213e',
            fg='#e8e8e8',
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.tailored_preview.grid(row=1, column=1, sticky="nsew", padx=3, pady=3)
        
        # --- Tab 2: Tailored Only ---
        tailored_only_frame = tk.Frame(preview_notebook, bg=COLORS['bg'])
        preview_notebook.add(tailored_only_frame, text="✨ Tailored Result (Full)")
        
        self.tailored_full_preview = scrolledtext.ScrolledText(
            tailored_only_frame,
            font=("Consolas", 10),
            bg='#16213e',
            fg='#e8e8e8',
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.tailored_full_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ========== EXPORT ACTIONS ==========
        actions_frame = ttkb.Labelframe(parent, text="📁 Export & Actions", bootstyle="info")
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        actions_inner = tk.Frame(actions_frame, bg=COLORS['bg'])
        actions_inner.pack(fill=tk.X, padx=10, pady=10)
        
        self.open_pdf_btn = ttkb.Button(
            actions_inner, text="📄 Open PDF", command=self._open_pdf, 
            bootstyle="info", state=tk.DISABLED, width=12
        )
        self.open_pdf_btn.pack(side=tk.LEFT, padx=3)
        
        self.open_docx_btn = ttkb.Button(
            actions_inner, text="📝 Open DOCX", command=self._open_docx, 
            bootstyle="success", state=tk.DISABLED, width=12
        )
        self.open_docx_btn.pack(side=tk.LEFT, padx=3)
        
        self.open_folder_btn = ttkb.Button(
            actions_inner, text="📁 Open Folder", command=self._open_folder, 
            bootstyle="secondary", state=tk.DISABLED, width=12
        )
        self.open_folder_btn.pack(side=tk.LEFT, padx=3)
        
        self.copy_btn = ttkb.Button(
            actions_inner, text="📋 Copy Text", command=self._copy_tailored,
            bootstyle="warning-outline", state=tk.DISABLED, width=12
        )
        self.copy_btn.pack(side=tk.LEFT, padx=3)
        
        # View Diff button - opens HTML diff in browser
        self.view_diff_btn = ttkb.Button(
            actions_inner, text="🔍 View Diff", command=self._open_html_diff,
            bootstyle="primary", state=tk.DISABLED, width=12
        )
        self.view_diff_btn.pack(side=tk.LEFT, padx=3)
    
    def _build_bottom_panel(self):
        """Build the bottom status panel."""
        
        bottom_frame = tk.Frame(self, bg=COLORS['card'], pady=5)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        # Status label
        self.status_label = tk.Label(
            bottom_frame,
            text="💡 Tip: Browse or paste your resume, then paste the job description and click START TAILORING",
            font=(UI_FONT, 9),
            fg=COLORS['text_secondary'],
            bg=COLORS['card']
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
    
    # ============================================
    # ACTION METHODS
    # ============================================
    
    def _browse_resume(self):
        """Browse for resume file and auto-load content."""
        try:
            # Temporarily grab focus to ensure dialog works properly
            self.focus_force()
            self.update()
            
            path = filedialog.askopenfilename(
                parent=self,
                title="Select Master Resume",
                filetypes=[
                    ("All Resume Files", "*.pdf *.docx *.txt"),
                    ("PDF Files", "*.pdf"),
                    ("Word Documents", "*.docx"),
                    ("Text Files", "*.txt")
                ]
            )
            if path:
                self.resume_path_var.set(path)
                # Auto-load the file content
                self._load_resume_file()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file browser: {e}")
    
    def _load_resume_file(self):
        """Load resume content from selected file."""
        path = self.resume_path_var.get().strip()
        if not path:
            messagebox.showwarning("No File", "Please select a resume file first.")
            return
        
        if not os.path.exists(path):
            messagebox.showerror("File Not Found", f"File not found: {path}")
            return
        
        try:
            content = _read_resume_text(path)
            if self.resume_text:
                self.resume_text.delete("1.0", tk.END)
                self.resume_text.insert(tk.END, content)
            self._update_status(f"✅ Loaded resume from {os.path.basename(path)}", "success")
        except Exception as e:
            messagebox.showerror("Error Loading File", str(e))
    
    def _quick_score(self):
        """Calculate ATS score without tailoring."""
        resume_content = self.resume_text.get("1.0", tk.END).strip() if self.resume_text else ""
        jd_content = self.jd_text.get("1.0", tk.END).strip() if self.jd_text else ""
        
        # Check for placeholder text
        if jd_content.startswith(JD_PLACEHOLDER_PREFIX):
            messagebox.showwarning(MISSING_JD_TITLE, "Please paste the job description first!")
            return
        
        if not resume_content:
            messagebox.showwarning("Missing Resume", "Please provide resume content.")
            return
        if not jd_content:
            messagebox.showwarning(MISSING_JD_TITLE, "Please provide job description.")
            return
        
        score_data = _score_match(resume_content, jd_content)
        self._update_score_display(score_data, before_score=None)
        self._update_status(f"📊 Current ATS Score: {score_data['ats']}%", "info")
    
    def _run_tailor(self):
        """Start the tailoring process."""
        if self.is_processing:
            return
        
        resume_content = self.resume_text.get("1.0", tk.END).strip() if self.resume_text else ""
        jd_content = self.jd_text.get("1.0", tk.END).strip() if self.jd_text else ""
        instructions = self.instr_text.get("1.0", tk.END).strip() if self.instr_text else None
        provider = self.provider_var.get().strip().lower()
        job_title = self.job_title_var.get().strip() or None
        resume_path = self.resume_path_var.get().strip() or None
        
        # Validation
        if jd_content.startswith(JD_PLACEHOLDER_PREFIX):
            messagebox.showerror(MISSING_JD_TITLE, "Please paste the job description first!")
            return
        if not jd_content:
            messagebox.showerror("Missing Input", "Please paste the job description.")
            return
        if not resume_content and not resume_path:
            messagebox.showerror("Missing Input", "Please provide resume content or select a file.")
            return
        
        # Store master text for comparison
        self.master_resume_text = resume_content
        
        # Update UI state
        self.is_processing = True
        self.cancel_requested = False
        self.animation_running = True
        import time
        self.process_start_time = time.time()  # Track start time
        if self.tailor_btn:
            self.tailor_btn.config(state=tk.DISABLED, text="⏳ Processing...")
        # Show cancel button
        if self.cancel_btn:
            self.cancel_btn.pack(side=tk.LEFT, padx=5)
        if self.progress_bar:
            self.progress_bar['value'] = 0
            self.progress_bar['mode'] = 'determinate'
        if self.elapsed_time_label:
            self.elapsed_time_label.config(text="⏱️ 0s")
        self._start_progress_animation()
        self._update_progress("🔄 Analyzing resume...", 5)
        
        # Run in background thread
        threading.Thread(
            target=self._worker,
            args=(resume_content, jd_content, instructions, provider, resume_path, job_title),
            daemon=True
        ).start()
    
    def _cancel_processing(self):
        """Cancel the current tailoring process."""
        if self.is_processing:
            self.cancel_requested = True
            self.animation_running = False
            self._update_progress("⚠️ Cancelling...", 0)
            self._update_status("⚠️ Process cancelled by user", "warning")
            # Reset UI
            self.is_processing = False
            if self.tailor_btn:
                self.tailor_btn.config(state=tk.NORMAL, text=START_TAILORING_TEXT)
            if self.cancel_btn:
                self.cancel_btn.pack_forget()
            if self.elapsed_time_label:
                self.elapsed_time_label.config(text="")
            if hasattr(self, 'progress_percent_label') and self.progress_percent_label:
                self.progress_percent_label.config(text="")
    
    def _worker(self, resume_text: str, jd_text: str, instructions: str | None, 
                provider: str, resume_path: str | None, job_title: str | None):
        """Background worker for tailoring with progress updates."""
        try:
            # Step 1: Calculate before score
            self.after(0, lambda: self._update_progress("📊 Calculating initial ATS score...", 10))
            before_score = _score_match(resume_text, jd_text)
            
            # Step 2: AI Processing (this is the long step) - show model name
            model_info = self._get_model_display_name(provider)
            self.after(0, lambda: self._update_progress(f"🤖 {model_info} tailoring... (please wait)", 20))
            
            # Perform tailoring - with longer timeout handled in the tailoring function
            paths = tailor_resume_to_files(
                resume_text=resume_text or None,
                job_description=jd_text,
                instructions=instructions,
                provider=provider,
                resume_path=resume_path,
                job_title=job_title,
                enable_preview=True,
            )
            
            # Step 3: Reading results
            self.after(0, lambda: self._update_progress("📄 Processing tailored content...", 75))
            
            # Read tailored text
            if paths.get("txt") and os.path.exists(paths["txt"]):
                with open(paths["txt"], "r", encoding="utf-8") as f:
                    tailored_text = f.read()
            else:
                self.after(0, lambda: self._update_progress("🔄 Fallback: Generating text...", 80))
                tailored_text = tailor_resume_text(
                    resume_text=resume_text,
                    job_description=jd_text,
                    instructions=instructions,
                    provider=provider
                )
            
            # Step 4: Calculate after score
            self.after(0, lambda: self._update_progress("📈 Calculating new ATS score...", 90))
            after_score = _score_match(tailored_text, jd_text)
            
            # Step 5: Done
            self.after(0, lambda: self._update_progress("✅ Complete!", 100))
            
            # Stop animation and update UI
            self.animation_running = False
            self.after(200, lambda: self._on_success(paths, tailored_text, before_score, after_score))
            
        except Exception as e:
            self.animation_running = False
            error = e
            self.after(0, lambda: self._on_error(error))
    
    def _update_progress(self, text: str, value: int):
        """Update progress bar and label with percentage."""
        if self.progress_label:
            self.progress_label.config(text=text)
        if self.progress_bar:
            self.progress_bar['value'] = value
        if hasattr(self, 'progress_percent_label') and self.progress_percent_label:
            if value > 0:
                self.progress_percent_label.config(text=f"{value}%")
            else:
                self.progress_percent_label.config(text="")
        self.update_idletasks()
    
    def _start_progress_animation(self):
        """Start animated progress with moving numbers."""
        self.animation_value = 0
        self._animate_progress()

    def _update_elapsed_time_display(self):
        if self.is_processing and self.animation_value % 25 == 0:
            import time
            elapsed = int(time.time() - self.process_start_time)
            if self.elapsed_time_label:
                self.elapsed_time_label.config(text=f"⏱️ {elapsed}s")

    def _maybe_bump_progress(self, current: float):
        if current < 70 and self.is_processing:
            if self.animation_value % 15 == 0 and current < 68:
                new_val = min(current + 0.5, 68)
                if self.progress_bar:
                    self.progress_bar['value'] = new_val
                if hasattr(self, 'progress_percent_label') and self.progress_percent_label:
                    self.progress_percent_label.config(text=f"{int(new_val)}%")

    def _maybe_update_activity_text(self):
        if self.progress_label and self.animation_value % 25 == 0:
            dots = "." * ((self.animation_value // 25) % 4)
            base_text = self.progress_label.cget("text").rstrip(".")
            if "please wait" in base_text.lower() or "tailoring" in base_text.lower():
                self.progress_label.config(text=f"{base_text}{dots}")
    
    def _animate_progress(self):
        """Animate progress bar to show activity with smooth increments."""
        if not self.animation_running:
            return
        
        # Pulse effect - smoothly increment during AI processing
        current = self.progress_bar['value'] if self.progress_bar else 0
        
        # Increment counter
        self.animation_value = (self.animation_value + 1) % 1000
        
        self._update_elapsed_time_display()
        self._maybe_bump_progress(current)
        self._maybe_update_activity_text()
        
        # Continue animation (faster refresh = smoother feel)
        if self.animation_running:
            self.after(20, self._animate_progress)
    
    def _get_model_display_name(self, provider: str) -> str:
        """Get display name for the AI model being used."""
        try:
            if provider == "ollama":
                from config.secrets import ollama_model
                return f"Ollama ({ollama_model})"
            elif provider == "groq":
                from config.secrets import groq_model
                return f"Groq ({groq_model})"
            elif provider == "huggingface":
                from config.secrets import huggingface_model
                short_model = huggingface_model.split("/")[-1] if "/" in huggingface_model else huggingface_model
                return f"HuggingFace ({short_model})"
            elif provider == "openai":
                from config.secrets import llm_model
                return f"OpenAI ({llm_model})"
            elif provider == "deepseek":
                from config.secrets import deepseek_model
                return f"DeepSeek ({deepseek_model})"
            elif provider == "gemini":
                from config.secrets import gemini_model
                return f"Gemini ({gemini_model})"
        except Exception:
            pass
        return provider.upper()

    def _check_connection(self):
        """Check AI provider connection status."""
        provider = self.provider_var.get().strip().lower()
        
        # Show checking state
        if self.connection_status_label:
            self.connection_status_label.config(text="○", fg=COLORS['warning'])
        if self.model_info_label:
            self.model_info_label.config(text="Checking...", fg=COLORS['text_secondary'])
        self.update_idletasks()
        
        # Check in background thread to avoid UI freeze
        def check():
            connected, info = _check_api_connection(provider)
            self.after(0, lambda: self._update_connection_status(connected, info))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _open_api_config(self):
        """Open the API configuration dialog."""
        try:
            open_api_config_dialog(self)
            # Recheck connection after config dialog closes
            self.after(500, self._check_connection)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open API config:\n{e}")
    
    def _update_connection_status(self, connected: bool, info: str):
        """Update the connection status display."""
        if self.connection_status_label:
            if connected:
                self.connection_status_label.config(text="●", fg=COLORS['success'])
            else:
                self.connection_status_label.config(text="●", fg=COLORS['danger'])
        
        if self.model_info_label:
            if connected:
                self.model_info_label.config(text=info, fg=COLORS['success'])
            else:
                self.model_info_label.config(text=info, fg=COLORS['danger'])
    
    def _on_success(self, paths: dict, tailored_text: str, before_score: dict, after_score: dict):
        """Handle successful tailoring."""
        import time
        self.is_processing = False
        self.animation_running = False
        
        # Show final elapsed time
        elapsed = int(time.time() - self.process_start_time)
        if self.elapsed_time_label:
            self.elapsed_time_label.config(text=f"✅ {elapsed}s")
        
        if self.progress_bar:
            self.progress_bar['value'] = 100
        if hasattr(self, 'progress_percent_label') and self.progress_percent_label:
            self.progress_percent_label.config(text="100%")
        if self.tailor_btn:
            self.tailor_btn.config(state=tk.NORMAL, text=START_TAILORING_TEXT)
        # Hide cancel button
        if self.cancel_btn:
            self.cancel_btn.pack_forget()
        
        self.current_paths = paths
        self.tailored_resume_text = tailored_text
        self._update_previews(self.master_resume_text, tailored_text)

        # Update score display
        self._update_score_display(after_score, before_score=before_score)

        # Enable action buttons
        self._set_action_buttons_state(paths)
        
        # Update status
        improvement = after_score['ats'] - before_score['ats']
        status_text = f"✅ Done! ATS: {before_score['ats']}% → {after_score['ats']}%"
        if improvement > 0:
            status_text += f" (+{improvement}% 📈)"
        self._update_status(status_text, "success")

    def _update_previews(self, master_text: str, tailored_text: str):
        if self.master_preview:
            self.master_preview.config(state=tk.NORMAL)
            self.master_preview.delete("1.0", tk.END)
            self.master_preview.insert(tk.END, master_text)
            self.master_preview.config(state=tk.DISABLED)

        if self.tailored_preview:
            self.tailored_preview.config(state=tk.NORMAL)
            self.tailored_preview.delete("1.0", tk.END)
            self.tailored_preview.insert(tk.END, tailored_text)
            self.tailored_preview.config(state=tk.DISABLED)

        if self.tailored_full_preview:
            self.tailored_full_preview.config(state=tk.NORMAL)
            self.tailored_full_preview.delete("1.0", tk.END)
            self.tailored_full_preview.insert(tk.END, tailored_text)
            self.tailored_full_preview.config(state=tk.DISABLED)

    def _set_action_buttons_state(self, paths: dict):
        if self.open_pdf_btn:
            self.open_pdf_btn.config(state=tk.NORMAL if paths.get("pdf") else tk.DISABLED)
        if self.open_docx_btn:
            self.open_docx_btn.config(state=tk.NORMAL if paths.get("docx") else tk.DISABLED)
        if self.open_folder_btn:
            self.open_folder_btn.config(state=tk.NORMAL)
        if self.copy_btn:
            self.copy_btn.config(state=tk.NORMAL)
        if self.view_diff_btn:
            self.view_diff_btn.config(state=tk.NORMAL)
    
    def _on_error(self, error: Exception):
        """Handle tailoring error."""
        self.is_processing = False
        self.animation_running = False
        
        if self.progress_bar:
            self.progress_bar['value'] = 0
        if hasattr(self, 'progress_percent_label') and self.progress_percent_label:
            self.progress_percent_label.config(text="")
        if self.progress_label:
            self.progress_label.config(text="❌ Failed")
        if self.tailor_btn:
            self.tailor_btn.config(state=tk.NORMAL, text=START_TAILORING_TEXT)
        # Hide cancel button
        if self.cancel_btn:
            self.cancel_btn.pack_forget()
        if self.elapsed_time_label:
            self.elapsed_time_label.config(text="")
        
        # Show error details with more specific messages
        error_msg = str(error)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            error_msg = "⏱️ AI request timed out.\n\nSuggestions:\n• Use a faster/smaller model (e.g., qwen2.5:7b)\n• Check your internet connection\n• Try Groq API (free & fast)"
        elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
            error_msg = "🔌 Cannot connect to AI provider.\n\nCheck:\n• Is Ollama running? (ollama serve)\n• Is the API key correct?\n• Check network connection"
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            error_msg = "🔍 Model not found.\n\nRun in terminal:\n• ollama pull <model_name>"
        
        self._update_status(f"❌ Error: {error_msg.split(chr(10))[0]}", "danger")
        messagebox.showerror("Tailoring Error", error_msg)
    
    def _score_style(self, score: int) -> tuple[str, str]:
        """Return (color, grade) for a given ATS score."""
        if score >= 80:
            return COLORS['success'], "Excellent"
        if score >= 60:
            return "#69db7c", "Good"
        if score >= 40:
            return COLORS['warning'], "Fair"
        return COLORS['danger'], "Needs Work"

    def _update_score_display(self, score_data: dict, before_score: dict | None = None):
        """Update the ATS score display."""
        score = score_data.get('ats', 0)
        color, grade = self._score_style(score)
        
        if self.ats_score_label:
            self.ats_score_label.config(text=f"ATS Score: {score}% ({grade})", fg=color)
        
        # Show improvement
        if before_score and self.improvement_label:
            improvement = score - before_score.get('ats', 0)
            if improvement > 0:
                self.improvement_label.config(text=f"📈 +{improvement}% improvement!", fg=COLORS['success'])
            elif improvement < 0:
                self.improvement_label.config(text=f"📉 {improvement}%", fg=COLORS['danger'])
            else:
                self.improvement_label.config(text="")
        
        # Update keywords
        if self.keywords_frame:
            for widget in self.keywords_frame.winfo_children():
                widget.destroy()
            
            found = score_data.get('tech_found', [])[:8]
            missing = score_data.get('tech_missing', [])[:5]
            
            if found:
                tk.Label(
                    self.keywords_frame,
                    text=f"✅ Found: {', '.join(found)}",
                    font=(UI_FONT, 8), fg=COLORS['success'], bg=COLORS['bg']
                ).pack(anchor=tk.W)
            
            if missing:
                tk.Label(
                    self.keywords_frame,
                    text=f"⚠️ Missing: {', '.join(missing)}",
                    font=(UI_FONT, 8), fg=COLORS['warning'], bg=COLORS['bg']
                ).pack(anchor=tk.W)
    
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
    
    def _open_pdf(self):
        if self.current_paths.get("pdf") and os.path.exists(self.current_paths["pdf"]):
            os.startfile(self.current_paths["pdf"])
    
    def _open_docx(self):
        if self.current_paths.get("docx") and os.path.exists(self.current_paths["docx"]):
            os.startfile(self.current_paths["docx"])
    
    def _open_folder(self):
        folder = os.path.dirname(
            self.current_paths.get("pdf") or 
            self.current_paths.get("docx") or 
            self.current_paths.get("txt", "")
        )
        if folder and os.path.exists(folder):
            os.startfile(folder)
    
    def _copy_tailored(self):
        if self.tailored_resume_text:
            self.clipboard_clear()
            self.clipboard_append(self.tailored_resume_text)
            self._update_status("📋 Copied to clipboard!", "success")
    
    def _open_html_diff(self):
        """Open an HTML diff view in the browser showing original vs tailored."""
        if not self.master_resume_text or not self.tailored_resume_text:
            messagebox.showinfo("No Diff Available", "Complete a tailoring operation first.")
            return
        
        try:
            from modules.dashboard.html_diff_viewer import generate_html_diff
            job_title = self.job_title_var.get().strip() or "Resume"
            filepath = generate_html_diff(
                master_text=self.master_resume_text,
                tailored_text=self.tailored_resume_text,
                job_title=job_title,
                open_in_browser=True
            )
            self._update_status(f"🔍 Diff opened in browser: {os.path.basename(filepath)}", "success")
        except Exception as e:
            messagebox.showerror("Diff Error", f"Could not generate diff:\n{e}")
    
    def _reset_form(self):
        """Reset the form."""
        self._reset_text_inputs()
        self._reset_scores()
        self._reset_previews()
        self._reset_action_buttons()
        self._reset_progress_ui()
        self._update_status(
            "💡 Tip: Browse or paste your resume, then paste the job description and click START TAILORING",
            "info",
        )

    def _reset_text_inputs(self):
        if self.resume_text:
            self.resume_text.delete("1.0", tk.END)
        if self.jd_text:
            self.jd_text.delete("1.0", tk.END)
            self.jd_text.insert(tk.END, JD_PLACEHOLDER_TEXT)
        if self.instr_text:
            self.instr_text.delete("1.0", tk.END)
            self.instr_text.insert(tk.END, "Focus on technical skills. Keep it professional and ATS-friendly.")

        self.job_title_var.set("")
        self.resume_path_var.set("")

        if self.jd_word_count_label:
            self.jd_word_count_label.config(text="Words: 0", fg=COLORS['text_secondary'])

    def _reset_scores(self):
        if self.ats_score_label:
            self.ats_score_label.config(text="ATS Score: --", fg=COLORS['text_secondary'])
        if self.improvement_label:
            self.improvement_label.config(text="")

    def _reset_previews(self):
        for preview in [self.master_preview, self.tailored_preview, self.tailored_full_preview]:
            if preview:
                preview.config(state=tk.NORMAL)
                preview.delete("1.0", tk.END)
                preview.config(state=tk.DISABLED)

    def _reset_action_buttons(self):
        for btn in [self.open_pdf_btn, self.open_docx_btn, self.open_folder_btn, self.copy_btn, self.view_diff_btn]:
            if btn:
                btn.config(state=tk.DISABLED)

    def _reset_progress_ui(self):
        self.animation_running = False
        self.is_processing = False
        self.cancel_requested = False
        if self.cancel_btn:
            self.cancel_btn.pack_forget()
        if self.progress_bar:
            self.progress_bar['value'] = 0
        if self.progress_label:
            self.progress_label.config(text="Ready to tailor")
        if hasattr(self, 'progress_percent_label') and self.progress_percent_label:
            self.progress_percent_label.config(text="")
        if self.elapsed_time_label:
            self.elapsed_time_label.config(text="")
