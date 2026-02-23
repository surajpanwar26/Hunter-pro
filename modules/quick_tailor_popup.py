"""
Quick Resume Tailor Popup - Modern UI with Color Diff Support
Provides a clean, modern popup for resume tailoring decisions.
Features proper color-highlighted diff view using Tkinter Text tags.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import difflib
from typing import Optional, Tuple, Dict, List
from modules.helpers import print_lg

try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    TTKB_AVAILABLE = True
except ImportError:
    TTKB_AVAILABLE = False

# Result constants
RESULT_TAILOR = "tailor"
RESULT_SKIP_TAILOR = "skip"
RESULT_CANCEL = "cancel"

# Global result variables
_popup_result = None
_tailored_resume_path = None

# ============ MODERN COLOR SCHEME ============
# Import from shared module; fall back to inline dict if import fails
try:
    from config.colors import TAILOR_COLORS as COLORS
except ImportError:
    COLORS = {
        'bg_dark': '#1a1a2e',
        'bg_card': '#16213e',
        'bg_input': '#0f3460',
        'accent': '#e94560',
        'accent_hover': '#ff6b6b',
        'success': '#00d9a5',
        'warning': '#ffc107',
        'error': '#ff4757',
        'text_primary': '#ffffff',
        'text_secondary': '#a0a0a0',
        'text_muted': '#6c757d',
        'diff_added_bg': '#1e4620',
        'diff_added_fg': '#7fff7f',
        'diff_removed_bg': '#4a1515',
        'diff_removed_fg': '#ff7f7f',
        'diff_changed_bg': '#4a4a15',
        'diff_changed_fg': '#ffff7f',
        'border': '#2d3748',
    }

# ============ MASTER RESUME CACHE ============
_master_resume_cache = {
    "path": None,
    "text": None,
    "mtime": 0,
}


def _get_cached_master_resume(resume_path: str) -> str:
    """Get master resume text with caching."""
    global _master_resume_cache
    
    if not resume_path or not os.path.exists(resume_path):
        return ""
    
    try:
        current_mtime = os.path.getmtime(resume_path)
        
        if (_master_resume_cache["path"] == resume_path and 
            _master_resume_cache["mtime"] == current_mtime and
            _master_resume_cache["text"]):
            return _master_resume_cache["text"]
        
        from modules.ai.resume_tailoring import _read_resume_text
        resume_text = _read_resume_text(resume_path)
        
        _master_resume_cache["path"] = resume_path
        _master_resume_cache["text"] = resume_text
        _master_resume_cache["mtime"] = current_mtime
        
        return resume_text
    except Exception:
        return ""


class ModernButton(tk.Canvas):
    """Modern styled button with hover effects."""
    
    def __init__(self, parent, text, command, style='primary', width=150, height=40):
        super().__init__(parent, width=width, height=height, 
                        bg=COLORS['bg_card'], highlightthickness=0)
        
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.style = style
        
        # Style colors
        styles = {
            'primary': (COLORS['accent'], COLORS['accent_hover']),
            'success': (COLORS['success'], '#00ffb3'),
            'secondary': (COLORS['bg_input'], COLORS['border']),
            'danger': (COLORS['error'], '#ff6b6b'),
        }
        self.color, self.hover_color = styles.get(style, styles['primary'])
        self.current_color = self.color
        
        self._draw()
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _draw(self):
        self.delete('all')
        # Rounded rectangle
        r = 8  # radius
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=self.current_color, outline='')
        self.create_arc(self.width-r*2, 0, self.width, r*2, start=0, extent=90, fill=self.current_color, outline='')
        self.create_arc(0, self.height-r*2, r*2, self.height, start=180, extent=90, fill=self.current_color, outline='')
        self.create_arc(self.width-r*2, self.height-r*2, self.width, self.height, start=270, extent=90, fill=self.current_color, outline='')
        self.create_rectangle(r, 0, self.width-r, self.height, fill=self.current_color, outline='')
        self.create_rectangle(0, r, self.width, self.height-r, fill=self.current_color, outline='')
        # Text
        self.create_text(self.width//2, self.height//2, text=self.text, 
                        fill=COLORS['text_primary'], font=('Segoe UI', 10, 'bold'))
    
    def _on_enter(self, e):
        self.current_color = self.hover_color
        self._draw()
    
    def _on_leave(self, e):
        self.current_color = self.color
        self._draw()
    
    def _on_click(self, e):
        if self.command:
            self.command()


class ColorDiffViewer(tk.Frame):
    """
    Advanced color diff viewer using Tkinter Text widget tags.
    Shows side-by-side comparison with proper syntax highlighting.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS['bg_dark'], **kwargs)
        
        # Header
        header = tk.Frame(self, bg=COLORS['bg_card'])
        header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(header, text="📄 Original Resume", font=('Segoe UI', 10, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT, padx=10, pady=5, expand=True)
        tk.Label(header, text="✨ Tailored Resume", font=('Segoe UI', 10, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['success']).pack(side=tk.RIGHT, padx=10, pady=5, expand=True)
        
        # Main container for side-by-side view
        container = tk.Frame(self, bg=COLORS['bg_dark'])
        container.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Original
        left_frame = tk.Frame(container, bg=COLORS['bg_card'], bd=1, relief=tk.FLAT)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        self.left_text = tk.Text(left_frame, wrap=tk.WORD, font=('Consolas', 9),
                                 bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                 insertbackground=COLORS['text_primary'],
                                 selectbackground=COLORS['accent'],
                                 padx=10, pady=10, bd=0)
        left_scroll = ttk.Scrollbar(left_frame, command=self._sync_scroll_left)
        self.left_text.configure(yscrollcommand=left_scroll.set)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_text.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Tailored
        right_frame = tk.Frame(container, bg=COLORS['bg_card'], bd=1, relief=tk.FLAT)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        self.right_text = tk.Text(right_frame, wrap=tk.WORD, font=('Consolas', 9),
                                  bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                  insertbackground=COLORS['text_primary'],
                                  selectbackground=COLORS['accent'],
                                  padx=10, pady=10, bd=0)
        right_scroll = ttk.Scrollbar(right_frame, command=self._sync_scroll_right)
        self.right_text.configure(yscrollcommand=right_scroll.set)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure diff tags for color highlighting
        self._configure_tags()
        
        # Legend
        legend = tk.Frame(self, bg=COLORS['bg_dark'])
        legend.pack(fill=tk.X, pady=(5, 0))
        
        tk.Label(legend, text="Legend:", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).pack(side=tk.LEFT, padx=5)
        
        # Removed indicator
        rem_box = tk.Label(legend, text="  ", bg=COLORS['diff_removed_bg'])
        rem_box.pack(side=tk.LEFT, padx=(10, 2))
        tk.Label(legend, text="Removed", font=('Segoe UI', 8),
                bg=COLORS['bg_dark'], fg=COLORS['diff_removed_fg']).pack(side=tk.LEFT)
        
        # Added indicator
        add_box = tk.Label(legend, text="  ", bg=COLORS['diff_added_bg'])
        add_box.pack(side=tk.LEFT, padx=(15, 2))
        tk.Label(legend, text="Added", font=('Segoe UI', 8),
                bg=COLORS['bg_dark'], fg=COLORS['diff_added_fg']).pack(side=tk.LEFT)
        
        # Changed indicator
        chg_box = tk.Label(legend, text="  ", bg=COLORS['diff_changed_bg'])
        chg_box.pack(side=tk.LEFT, padx=(15, 2))
        tk.Label(legend, text="Modified", font=('Segoe UI', 8),
                bg=COLORS['bg_dark'], fg=COLORS['diff_changed_fg']).pack(side=tk.LEFT)
    
    def _configure_tags(self):
        """Configure text tags for diff highlighting."""
        # Tags for left panel (original)
        self.left_text.tag_configure('removed', 
            background=COLORS['diff_removed_bg'], 
            foreground=COLORS['diff_removed_fg'])
        self.left_text.tag_configure('changed',
            background=COLORS['diff_changed_bg'],
            foreground=COLORS['diff_changed_fg'])
        self.left_text.tag_configure('normal',
            foreground=COLORS['text_primary'])
        self.left_text.tag_configure('section',
            foreground=COLORS['accent'],
            font=('Consolas', 9, 'bold'))
        
        # Tags for right panel (tailored)
        self.right_text.tag_configure('added',
            background=COLORS['diff_added_bg'],
            foreground=COLORS['diff_added_fg'])
        self.right_text.tag_configure('changed',
            background=COLORS['diff_changed_bg'],
            foreground=COLORS['diff_changed_fg'])
        self.right_text.tag_configure('normal',
            foreground=COLORS['text_primary'])
        self.right_text.tag_configure('section',
            foreground=COLORS['success'],
            font=('Consolas', 9, 'bold'))
    
    def _sync_scroll_left(self, *args):
        self.left_text.yview(*args)
        self.right_text.yview(*args)
    
    def _sync_scroll_right(self, *args):
        self.right_text.yview(*args)
        self.left_text.yview(*args)
    
    def set_diff(self, original: str, tailored: str):
        """
        Set the diff content with proper color highlighting.
        Uses difflib for accurate line-by-line comparison.
        """
        self.left_text.config(state=tk.NORMAL)
        self.right_text.config(state=tk.NORMAL)
        self.left_text.delete('1.0', tk.END)
        self.right_text.delete('1.0', tk.END)
        
        if not original or not tailored:
            self.left_text.insert(tk.END, original or "(No content)")
            self.right_text.insert(tk.END, tailored or "(No content)")
            self.left_text.config(state=tk.DISABLED)
            self.right_text.config(state=tk.DISABLED)
            return
        
        # Split into lines
        orig_lines = original.splitlines(keepends=True)
        tail_lines = tailored.splitlines(keepends=True)
        
        # Use SequenceMatcher for detailed diff
        matcher = difflib.SequenceMatcher(None, orig_lines, tail_lines)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Unchanged lines
                for line in orig_lines[i1:i2]:
                    self._insert_line(self.left_text, line, 'normal')
                for line in tail_lines[j1:j2]:
                    self._insert_line(self.right_text, line, 'normal')
                    
            elif tag == 'replace':
                # Changed lines - show both with highlighting
                for line in orig_lines[i1:i2]:
                    self._insert_line(self.left_text, line, 'changed')
                for line in tail_lines[j1:j2]:
                    self._insert_line(self.right_text, line, 'changed')
                # Pad shorter side
                diff = (i2 - i1) - (j2 - j1)
                if diff > 0:
                    for _ in range(diff):
                        self._insert_line(self.right_text, '\n', 'normal')
                elif diff < 0:
                    for _ in range(-diff):
                        self._insert_line(self.left_text, '\n', 'normal')
                        
            elif tag == 'delete':
                # Lines removed from original
                for line in orig_lines[i1:i2]:
                    self._insert_line(self.left_text, line, 'removed')
                # Add empty lines to right side to keep alignment
                for _ in range(i2 - i1):
                    self._insert_line(self.right_text, '\n', 'normal')
                    
            elif tag == 'insert':
                # Lines added in tailored
                for line in tail_lines[j1:j2]:
                    self._insert_line(self.right_text, line, 'added')
                # Add empty lines to left side to keep alignment
                for _ in range(j2 - j1):
                    self._insert_line(self.left_text, '\n', 'normal')
        
        self.left_text.config(state=tk.DISABLED)
        self.right_text.config(state=tk.DISABLED)
    
    def _insert_line(self, text_widget: tk.Text, line: str, tag: str):
        """Insert a line with the specified tag."""
        # Check if it's a section header
        stripped = line.strip().upper()
        if stripped and len(stripped) < 50 and not any(c.islower() for c in stripped):
            if any(kw in stripped for kw in ['EXPERIENCE', 'EDUCATION', 'SKILLS', 'SUMMARY', 'OBJECTIVE', 'PROJECTS', 'CERTIFICATIONS']):
                tag = 'section'
        
        text_widget.insert(tk.END, line, tag)


class ModernTailorPopup:
    """
    Modern Resume Tailoring Popup with clean UI and color diff support.
    
    Flow:
    1. Show initial popup with job info and Tailor/Default/Skip options
    2. If user clicks Tailor -> Start AI tailoring with progress
    3. After tailoring -> Show comprehensive preview with color diff
    4. User approves -> Return result for application
    """
    
    def __init__(self, job_title: str, company: str, job_description: str, 
                 default_resume_path: str, master_resume_text: str = None):
        self.job_title = job_title
        self.company = company
        self.job_description = job_description
        self.default_resume_path = default_resume_path
        self.master_resume_text = master_resume_text or _get_cached_master_resume(default_resume_path)
        
        self.result = RESULT_CANCEL
        self.tailored_path = None
        self.tailored_text = ""
        self.review_report = None
        self.initial_score = 0
        self.after_score = 0
        
        self.root = None
        self.preview_window = None
    
    def show(self) -> Tuple[str, Optional[str]]:
        """Show the popup and return (result, tailored_path)."""
        self.root = tk.Tk()
        self.root.title("🎯 Resume Tailoring")
        
        # Calculate optimal size based on screen (75% width, 80% height for better content fit)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Window size: min 800x650, max 1100x850, scales with screen
        win_width = max(800, min(1100, int(screen_width * 0.55)))
        win_height = max(650, min(850, int(screen_height * 0.75)))
        
        self.root.geometry(f"{win_width}x{win_height}")
        self.root.configure(bg=COLORS['bg_dark'])
        self.root.resizable(True, True)
        self.root.minsize(750, 600)  # Ensure buttons are always visible
        
        # Center on screen
        self.root.update_idletasks()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2 - 30
        self.root.geometry(f"+{x}+{y}")
        
        # Make it stay on top initially
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))
        
        self._build_initial_ui()
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.mainloop()
        
        return self.result, self.tailored_path
    
    def _build_initial_ui(self):
        """Build the initial decision popup UI with grid layout for guaranteed button visibility."""
        # Configure root to use grid
        self.root.grid_rowconfigure(0, weight=1)  # Content area expands
        self.root.grid_rowconfigure(1, weight=0)  # Button area fixed
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main scrollable content area
        content_frame = tk.Frame(self.root, bg=COLORS['bg_dark'], padx=20, pady=15)
        content_frame.grid(row=0, column=0, sticky='nsew')
        
        # Header
        header = tk.Frame(content_frame, bg=COLORS['bg_dark'])
        header.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(header, text="🎯 Tailor Resume for This Job?",
                font=('Segoe UI', 18, 'bold'), bg=COLORS['bg_dark'],
                fg=COLORS['text_primary']).pack(anchor=tk.W)
        
        tk.Label(header, text="AI will optimize your resume to match this specific job description",
                font=('Segoe UI', 10), bg=COLORS['bg_dark'],
                fg=COLORS['text_secondary']).pack(anchor=tk.W, pady=(5, 0))
        
        # Job Info Card
        job_card = tk.Frame(content_frame, bg=COLORS['bg_card'], padx=15, pady=12)
        job_card.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(job_card, text=f"📋 {self.job_title}",
                font=('Segoe UI', 14, 'bold'), bg=COLORS['bg_card'],
                fg=COLORS['text_primary'], wraplength=700, justify=tk.LEFT).pack(anchor=tk.W)
        
        tk.Label(job_card, text=f"🏢 {self.company}",
                font=('Segoe UI', 11), bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']).pack(anchor=tk.W, pady=(5, 0))
        
        # ATS Score Preview
        self._calculate_initial_score()
        
        score_frame = tk.Frame(content_frame, bg=COLORS['bg_card'], padx=15, pady=10)
        score_frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(score_frame, text="📊 Current ATS Match Score",
                font=('Segoe UI', 10, 'bold'), bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']).pack(anchor=tk.W)
        
        score_color = COLORS['error'] if self.initial_score < 50 else COLORS['warning'] if self.initial_score < 70 else COLORS['success']
        
        score_row = tk.Frame(score_frame, bg=COLORS['bg_card'])
        score_row.pack(fill=tk.X, pady=(8, 0))
        
        tk.Label(score_row, text=f"{self.initial_score}%",
                font=('Segoe UI', 28, 'bold'), bg=COLORS['bg_card'],
                fg=score_color).pack(side=tk.LEFT)
        
        # Progress bar
        progress_frame = tk.Frame(score_row, bg=COLORS['bg_input'], height=8)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20, pady=10)
        progress_fill = tk.Frame(progress_frame, bg=score_color, height=8)
        progress_fill.place(relwidth=self.initial_score/100, relheight=1)
        
        tip = "💡 Tailoring can improve your match by 15-30%"
        tk.Label(score_row, text=tip, font=('Segoe UI', 9),
                bg=COLORS['bg_card'], fg=COLORS['text_muted']).pack(side=tk.RIGHT)
        
        # Job Description Preview - use remaining space
        jd_frame = tk.Frame(content_frame, bg=COLORS['bg_card'])
        jd_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        jd_header = tk.Frame(jd_frame, bg=COLORS['bg_card'])
        jd_header.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(jd_header, text="📝 Job Description",
                font=('Segoe UI', 10, 'bold'), bg=COLORS['bg_card'],
                fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        
        # Scrollable job description with scrollbar
        jd_container = tk.Frame(jd_frame, bg=COLORS['bg_card'])
        jd_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        jd_scroll = ttk.Scrollbar(jd_container)
        jd_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        jd_text = tk.Text(jd_container, wrap=tk.WORD, font=('Consolas', 9),
                         bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                         padx=10, pady=10, bd=0, yscrollcommand=jd_scroll.set)
        jd_text.pack(fill=tk.BOTH, expand=True)
        jd_scroll.config(command=jd_text.yview)
        jd_text.insert(tk.END, self.job_description[:3000] + ("..." if len(self.job_description) > 3000 else ""))
        jd_text.config(state=tk.DISABLED)
        
        # Status label (for progress updates) - part of content
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(content_frame, textvariable=self.status_var,
                                    font=('Segoe UI', 10), bg=COLORS['bg_dark'],
                                    fg=COLORS['text_secondary'])
        self.status_label.pack(pady=(5, 0))
        
        # Progress bar (hidden initially)
        self.progress_frame = tk.Frame(content_frame, bg=COLORS['bg_dark'])
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate', length=400)
        
        # ===== FIXED BUTTON BAR AT BOTTOM - Always visible =====
        btn_container = tk.Frame(self.root, bg=COLORS['bg_card'], padx=20, pady=15)
        btn_container.grid(row=1, column=0, sticky='ew')
        
        # Separator line
        sep = tk.Frame(btn_container, bg=COLORS['border'], height=1)
        sep.pack(fill=tk.X, pady=(0, 12))
        
        # Button row
        btn_frame = tk.Frame(btn_container, bg=COLORS['bg_card'])
        btn_frame.pack(fill=tk.X)
        
        self.tailor_btn = ModernButton(btn_frame, "✨ Tailor Resume", 
                                       self._on_tailor, style='success', width=180, height=45)
        self.tailor_btn.pack(side=tk.LEFT, padx=5)
        
        self.default_btn = ModernButton(btn_frame, "📄 Use Default", 
                                        self._on_default, style='secondary', width=140, height=45)
        self.default_btn.pack(side=tk.LEFT, padx=5)
        
        self.skip_btn = ModernButton(btn_frame, "❌ Skip Job", 
                                     self._on_cancel, style='danger', width=120, height=45)
        self.skip_btn.pack(side=tk.RIGHT, padx=5)
    
    def _calculate_initial_score(self):
        """Calculate initial ATS match score."""
        try:
            from modules.ai.resume_tailoring import _score_match
            if self.master_resume_text and self.job_description:
                score_data = _score_match(self.master_resume_text, self.job_description)
                self.initial_score = score_data.get('match', 0)
        except Exception:
            self.initial_score = 0
    
    def _on_tailor(self):
        """Handle tailor button click - start AI tailoring."""
        self.status_var.set("🔄 Starting AI tailoring...")
        self.progress_frame.pack(fill=tk.X, pady=(5, 10))
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.start(10)
        
        # Disable buttons
        self.tailor_btn.unbind('<Button-1>')
        self.default_btn.unbind('<Button-1>')
        self.skip_btn.unbind('<Button-1>')
        
        # Start tailoring in background thread
        thread = threading.Thread(target=self._tailor_thread, daemon=True)
        thread.start()
    
    def _tailor_thread(self):
        """Background thread for resume tailoring with detailed logging."""
        try:
            from modules.ai.resume_tailoring import tailor_resume_to_files, _score_match, _extract_important_keywords
            from config.settings import generated_resume_path, resume_tailoring_default_instructions
            
            # ============ PHASE 1: INITIAL ANALYSIS ============
            print_lg("\n" + "="*80)
            print_lg("🚀 RESUME TAILORING STARTED")
            print_lg("="*80)
            print_lg(f"📋 Job: {self.job_title} @ {self.company}")
            
            # Calculate and log initial scores
            self.root.after(0, lambda: self.status_var.set("📊 Analyzing JD keywords..."))
            
            initial_score_data = _score_match(self.master_resume_text, self.job_description)
            self.initial_score = initial_score_data.get('match', 0)
            
            print_lg(f"\n📊 INITIAL ANALYSIS:")
            print_lg(f"   └─ JD Match Score: {self.initial_score}%")
            print_lg(f"   └─ ATS Compatibility: {initial_score_data.get('ats', 0)}%")
            print_lg(f"   └─ Keywords Matched: {initial_score_data.get('matched', 0)}/{initial_score_data.get('total', 0)}")
            
            # Log keyword details
            if initial_score_data.get('tech_found'):
                print_lg(f"   └─ ✅ Technical Keywords FOUND: {', '.join(initial_score_data['tech_found'][:10])}")
            if initial_score_data.get('tech_missing'):
                print_lg(f"   └─ ❌ Technical Keywords MISSING: {', '.join(initial_score_data['tech_missing'][:10])}")
            if initial_score_data.get('soft_found'):
                print_lg(f"   └─ ✅ Soft Skills FOUND: {', '.join(initial_score_data['soft_found'][:5])}")
            if initial_score_data.get('soft_missing'):
                print_lg(f"   └─ ❌ Soft Skills MISSING: {', '.join(initial_score_data['soft_missing'][:5])}")
            
            # ============ PHASE 2: AI TAILORING ============
            self.root.after(0, lambda: self.status_var.set("🤖 AI is optimizing your resume..."))
            print_lg(f"\n🤖 AI TAILORING IN PROGRESS...")
            print_lg(f"   └─ Provider: Generating tailored content")
            
            output_dir = os.path.join(generated_resume_path, "temp")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate tailored resume
            print_lg(f"   └─ 📝 Input resume length: {len(self.master_resume_text) if self.master_resume_text else 0} chars")
            print_lg(f"   └─ 📋 JD length: {len(self.job_description) if self.job_description else 0} chars")
            
            try:
                paths = tailor_resume_to_files(
                    resume_text=self.master_resume_text,
                    job_description=self.job_description,
                    job_title=self.job_title,
                    instructions=resume_tailoring_default_instructions,
                    output_dir=output_dir,
                    enable_preview=True
                )
            except Exception as tailor_err:
                import traceback
                print_lg(f"   └─ ❌ EXCEPTION in tailor_resume_to_files: {tailor_err}")
                print_lg(f"   └─ Traceback: {traceback.format_exc()}")
                paths = None
            
            # Debug: Log what we got back
            print_lg(f"   └─ 📦 tailor_resume_to_files returned: type={type(paths).__name__}")
            if paths:
                print_lg(f"   └─ 📦 paths.keys={list(paths.keys()) if hasattr(paths, 'keys') else 'N/A'}")
                print_lg(f"   └─ 📦 pdf={paths.get('pdf', 'NOT SET') if isinstance(paths, dict) else 'NOT A DICT'}")
            
            if paths and paths.get('pdf'):
                self.tailored_path = paths['pdf']
                print_lg(f"   └─ ✅ AI tailoring complete! Files generated.")
                
                # Read tailored text
                if paths.get('txt') and os.path.exists(paths['txt']):
                    with open(paths['txt'], 'r', encoding='utf-8') as f:
                        self.tailored_text = f.read()
                
                # Calculate post-tailoring score
                post_tailor_data = _score_match(self.tailored_text, self.job_description)
                post_tailor_score = post_tailor_data.get('match', 0)
                improvement = post_tailor_score - self.initial_score
                
                print_lg(f"\n📈 POST-TAILORING ANALYSIS:")
                print_lg(f"   └─ New JD Match: {post_tailor_score}% (was {self.initial_score}%)")
                print_lg(f"   └─ Improvement: +{improvement}%")
                print_lg(f"   └─ Keywords Now Matched: {post_tailor_data.get('matched', 0)}/{post_tailor_data.get('total', 0)}")
                
                # ============ PHASE 3: REVIEWER AGENT ============
                self.root.after(0, lambda: self.status_var.set("🔍 Reviewer Agent: Validating quality..."))
                print_lg(f"\n🔍 REVIEWER AGENT: Starting quality validation...")
                
                try:
                    from modules.ai.reviewer_agent import ReviewerAgent
                    reviewer = ReviewerAgent()
                    
                    self.review_report = reviewer.review_and_fix_iteratively(
                        tailored_resume=self.tailored_text,
                        original_resume=self.master_resume_text,
                        job_description=self.job_description,
                        job_title=self.job_title,
                        company=self.company,
                        max_iterations=3,
                    )
                    
                    # Log reviewer results
                    if self.review_report:
                        print_lg(f"\n📝 REVIEWER AGENT RESULTS:")
                        print_lg(f"   └─ Overall Quality Score: {self.review_report.overall_score:.0f}%")
                        print_lg(f"   └─ Structure Score: {self.review_report.structure_score:.0f}%")
                        print_lg(f"   └─ Keyword Score: {self.review_report.keyword_score:.0f}%")
                        print_lg(f"   └─ Grammar Score: {self.review_report.grammar_score:.0f}%")
                        print_lg(f"   └─ Total Issues Found: {self.review_report.total_issues}")
                        print_lg(f"   └─ Critical Issues: {self.review_report.critical_issues}")
                        print_lg(f"   └─ Auto-Fixed: {self.review_report.auto_fixed_count} issues")
                        reviewer_passed = self.review_report.overall_score >= 85 and self.review_report.critical_issues == 0
                        reviewer_fix = "FIXED" if (self.review_report.was_modified or self.review_report.auto_fixed_count > 0) else "NO FIXES"
                        reviewer_status = "PASSED" if reviewer_passed else "SENT BACK"
                        print_lg(f"   └─ Reviewer Decision: {reviewer_status} ({reviewer_fix})")
                        
                        if self.review_report.improvements_made:
                            print_lg(f"   └─ Improvements Made:")
                            for imp in self.review_report.improvements_made[:5]:
                                print_lg(f"      • {imp}")
                        
                        # Log critical findings
                        critical_findings = [f for f in self.review_report.findings if f.severity.value == 'critical']
                        if critical_findings:
                            print_lg(f"   └─ ⚠️ Critical Findings:")
                            for finding in critical_findings[:3]:
                                print_lg(f"      • {finding.issue}")
                    
                    if self.review_report and self.review_report.was_modified:
                        self.tailored_text = self.review_report.corrected_resume
                        print_lg(f"   └─ Resume was corrected by reviewer agent")
                        
                        # Save corrected version
                        from modules.ai.resume_tailoring import _save_text, _write_docx, _write_pdf
                        from datetime import datetime
                        
                        base_name = f"{self.job_title or 'Resume'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_final"
                        _save_text(self.review_report.corrected_resume, output_dir, base_name=base_name)
                        _write_docx(self.review_report.corrected_resume, output_dir, base_name=base_name)
                        pdf_path = _write_pdf(self.review_report.corrected_resume, output_dir, base_name=base_name)
                        if pdf_path:
                            self.tailored_path = pdf_path
                            
                except ImportError:
                    print_lg("   └─ ℹ️ Reviewer agent not available")
                except Exception as e:
                    print_lg(f"   └─ ⚠️ Reviewer warning: {e}")
                
                # ============ PHASE 4: FINAL SCORE ============
                if self.tailored_text:
                    final_score_data = _score_match(self.tailored_text, self.job_description)
                    self.after_score = final_score_data.get('match', 0)
                    total_improvement = self.after_score - self.initial_score
                    
                    print_lg(f"\n✅ FINAL RESULTS:")
                    print_lg(f"   └─ Initial Score: {self.initial_score}%")
                    print_lg(f"   └─ Final Score: {self.after_score}%")
                    print_lg(f"   └─ Total Improvement: +{total_improvement}%")
                    print_lg(f"   └─ ATS Compatibility: {final_score_data.get('ats', 0)}%")
                    
                    # Quality assessment
                    if self.after_score >= 80:
                        print_lg(f"   └─ 🌟 EXCELLENT: Resume highly optimized for this job!")
                    elif self.after_score >= 60:
                        print_lg(f"   └─ ✅ GOOD: Resume well-tailored for this position")
                    elif self.after_score >= 40:
                        print_lg(f"   └─ ⚠️ FAIR: Some keywords may still be missing")
                    else:
                        print_lg(f"   └─ ❌ NEEDS WORK: Consider adding more relevant experience")
                
                print_lg("="*80 + "\n")
                
                # Show preview popup
                self.root.after(0, self._stop_progress)
                self.root.after(100, self._show_preview)
            else:
                print_lg("❌ TAILORING FAILED: No output files generated")
                self.root.after(0, lambda: self.status_var.set("❌ Tailoring failed! Using default resume."))
                self.root.after(0, self._stop_progress)
                self.root.after(0, self._enable_buttons)
                
        except Exception as e:
            error_msg = str(e)[:100]
            print_lg(f"❌ TAILORING ERROR: {error_msg}")
            self.root.after(0, lambda: self.status_var.set(f"❌ Error: {error_msg}"))
            self.root.after(0, self._stop_progress)
            self.root.after(0, self._enable_buttons)
    
    def _stop_progress(self):
        """Stop progress bar."""
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
    
    def _enable_buttons(self):
        """Re-enable buttons after error."""
        self.tailor_btn.bind('<Button-1>', lambda e: self._on_tailor())
        self.default_btn.bind('<Button-1>', lambda e: self._on_default())
        self.skip_btn.bind('<Button-1>', lambda e: self._on_cancel())
    
    def _show_preview(self):
        """Show the comprehensive preview popup with color diff."""
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("📋 Resume Preview - Review & Approve")
        
        # Get screen dimensions and set window to 90% of screen size for better visibility
        screen_width = self.preview_window.winfo_screenwidth()
        screen_height = self.preview_window.winfo_screenheight()
        window_width = min(1400, int(screen_width * 0.9))
        window_height = min(900, int(screen_height * 0.85))
        
        self.preview_window.geometry(f"{window_width}x{window_height}")
        self.preview_window.minsize(900, 700)  # Minimum size to ensure buttons are visible
        self.preview_window.configure(bg=COLORS['bg_dark'])
        
        # Center on screen (not parent, for better positioning)
        self.preview_window.update_idletasks()
        px = (screen_width - window_width) // 2
        py = (screen_height - window_height) // 2 - 30
        self.preview_window.geometry(f"+{px}+{py}")
        
        self.preview_window.transient(self.root)
        self.preview_window.grab_set()
        
        # Use grid layout for better control - button bar at bottom stays visible
        self.preview_window.grid_rowconfigure(0, weight=1)  # Main content expands
        self.preview_window.grid_rowconfigure(1, weight=0)  # Button bar fixed
        self.preview_window.grid_columnconfigure(0, weight=1)
        
        main = tk.Frame(self.preview_window, bg=COLORS['bg_dark'], padx=20, pady=15)
        main.grid(row=0, column=0, sticky='nsew')
        
        # Header with status
        header = tk.Frame(main, bg=COLORS['bg_dark'])
        header.pack(fill=tk.X, pady=(0, 15))
        
        # Status indicator
        passed = self.review_report and self.review_report.overall_score >= 85 and self.review_report.critical_issues == 0
        status_color = COLORS['success'] if passed else COLORS['warning']
        status_text = "✅ PASSED REVIEW" if passed else "⚠️ NEEDS ATTENTION"
        
        tk.Label(header, text=status_text, font=('Segoe UI', 16, 'bold'),
                bg=COLORS['bg_dark'], fg=status_color).pack(side=tk.LEFT)
        
        tk.Label(header, text=f"📋 {self.job_title[:40]}... @ {self.company}",
                font=('Segoe UI', 10), bg=COLORS['bg_dark'],
                fg=COLORS['text_muted']).pack(side=tk.RIGHT)
        
        # Score comparison card
        score_card = tk.Frame(main, bg=COLORS['bg_card'], padx=20, pady=15)
        score_card.pack(fill=tk.X, pady=(0, 15))
        
        # Before score
        before_frame = tk.Frame(score_card, bg=COLORS['bg_card'])
        before_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(before_frame, text="BEFORE", font=('Segoe UI', 9),
                bg=COLORS['bg_card'], fg=COLORS['text_muted']).pack()
        before_color = COLORS['error'] if self.initial_score < 50 else COLORS['warning'] if self.initial_score < 70 else COLORS['success']
        tk.Label(before_frame, text=f"{self.initial_score}%", font=('Segoe UI', 32, 'bold'),
                bg=COLORS['bg_card'], fg=before_color).pack()
        
        # Arrow
        tk.Label(score_card, text="→", font=('Segoe UI', 28),
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT, padx=30)
        
        # After score
        after_frame = tk.Frame(score_card, bg=COLORS['bg_card'])
        after_frame.pack(side=tk.LEFT, expand=True)
        tk.Label(after_frame, text="AFTER", font=('Segoe UI', 9),
                bg=COLORS['bg_card'], fg=COLORS['text_muted']).pack()
        after_color = COLORS['success'] if self.after_score >= 70 else COLORS['warning'] if self.after_score >= 50 else COLORS['error']
        tk.Label(after_frame, text=f"{self.after_score}%", font=('Segoe UI', 32, 'bold'),
                bg=COLORS['bg_card'], fg=after_color).pack()
        
        # Improvement
        improvement = self.after_score - self.initial_score
        imp_frame = tk.Frame(score_card, bg=COLORS['bg_card'])
        imp_frame.pack(side=tk.RIGHT, padx=20)
        tk.Label(imp_frame, text="IMPROVEMENT", font=('Segoe UI', 9),
                bg=COLORS['bg_card'], fg=COLORS['text_muted']).pack()
        imp_color = COLORS['success'] if improvement > 0 else COLORS['error']
        imp_sign = "+" if improvement >= 0 else ""
        tk.Label(imp_frame, text=f"{imp_sign}{improvement}%", font=('Segoe UI', 24, 'bold'),
                bg=COLORS['bg_card'], fg=imp_color).pack()
        
        # Reviewer report if available
        if self.review_report:
            review_card = tk.Frame(main, bg=COLORS['bg_card'], padx=15, pady=10)
            review_card.pack(fill=tk.X, pady=(0, 10))
            
            scores_text = f"Quality: {self.review_report.overall_score:.0f}% | "
            scores_text += f"ATS: {self.review_report.ats_score:.0f}% | "
            scores_text += f"Grammar: {self.review_report.grammar_score:.0f}% | "
            scores_text += f"Keywords: {self.review_report.keyword_score:.0f}%"
            
            tk.Label(review_card, text="🔍 Reviewer Agent", font=('Segoe UI', 10, 'bold'),
                    bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(anchor=tk.W)
            tk.Label(review_card, text=scores_text, font=('Segoe UI', 9),
                    bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(5, 0))
            
            if self.review_report.was_modified:
                fixes_text = f"✅ {self.review_report.auto_fixed_count} issues automatically fixed"
                tk.Label(review_card, text=fixes_text, font=('Segoe UI', 9),
                        bg=COLORS['bg_card'], fg=COLORS['success']).pack(anchor=tk.W, pady=(3, 0))
        
        # Notebook for tabs
        style = ttk.Style()
        style.configure('Dark.TNotebook', background=COLORS['bg_dark'])
        style.configure('Dark.TNotebook.Tab', background=COLORS['bg_card'], 
                       foreground=COLORS['text_primary'], padding=[15, 8])
        
        notebook = ttk.Notebook(main, style='Dark.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Tab 1: Color Diff View
        diff_tab = tk.Frame(notebook, bg=COLORS['bg_dark'])
        notebook.add(diff_tab, text="📊 Side-by-Side Diff")
        
        diff_viewer = ColorDiffViewer(diff_tab)
        diff_viewer.pack(fill=tk.BOTH, expand=True, pady=5)
        diff_viewer.set_diff(self.master_resume_text, self.tailored_text)
        
        # Tab 2: Editable Tailored Resume
        edit_tab = tk.Frame(notebook, bg=COLORS['bg_dark'])
        notebook.add(edit_tab, text="✏️ Edit Resume")
        
        # Edit instructions banner
        edit_banner = tk.Frame(edit_tab, bg=COLORS['bg_input'], padx=10, pady=8)
        edit_banner.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(edit_banner, text="✏️ You can edit the tailored resume below. Changes will be saved when you click 'Continue'.",
                font=('Segoe UI', 9), bg=COLORS['bg_input'], fg=COLORS['warning']).pack(side=tk.LEFT)
        
        # Save edits button
        def save_edits():
            self.tailored_text = self.edit_text_widget.get('1.0', tk.END).strip()
            self._save_edited_resume()
            messagebox.showinfo("Saved", "Your edits have been saved!", parent=self.preview_window)
        
        save_btn = tk.Button(edit_banner, text="💾 Save Edits", command=save_edits,
                            bg=COLORS['success'], fg='white', font=('Segoe UI', 9, 'bold'),
                            relief=tk.FLAT, padx=10, pady=3)
        save_btn.pack(side=tk.RIGHT)
        
        # Editable text area
        self.edit_text_widget = tk.Text(edit_tab, wrap=tk.WORD, font=('Consolas', 10),
                           bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                           insertbackground=COLORS['text_primary'],
                           selectbackground=COLORS['accent'],
                           padx=15, pady=15, undo=True)  # Enable undo
        edit_scroll = ttk.Scrollbar(edit_tab, command=self.edit_text_widget.yview)
        self.edit_text_widget.configure(yscrollcommand=edit_scroll.set)
        edit_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.edit_text_widget.pack(fill=tk.BOTH, expand=True)
        self.edit_text_widget.insert(tk.END, self.tailored_text)
        
        # Bind Ctrl+S to save
        self.edit_text_widget.bind('<Control-s>', lambda e: save_edits())
        
        # Tab 3: Read-only full view  
        full_tab = tk.Frame(notebook, bg=COLORS['bg_dark'])
        notebook.add(full_tab, text="📄 Full Resume (Read-Only)")
        
        self.full_text_widget = tk.Text(full_tab, wrap=tk.WORD, font=('Consolas', 10),
                           bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                           padx=15, pady=15)
        full_scroll = ttk.Scrollbar(full_tab, command=self.full_text_widget.yview)
        self.full_text_widget.configure(yscrollcommand=full_scroll.set)
        full_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.full_text_widget.pack(fill=tk.BOTH, expand=True)
        self.full_text_widget.insert(tk.END, self.tailored_text)
        self.full_text_widget.config(state=tk.DISABLED)
        
        # ============ FIXED BOTTOM BUTTON BAR ============
        # This bar is placed in the grid row 1 and will always be visible
        button_bar = tk.Frame(self.preview_window, bg=COLORS['bg_card'], padx=20, pady=15)
        button_bar.grid(row=1, column=0, sticky='ew')
        
        # Add a top border line for visual separation
        separator = tk.Frame(button_bar, bg=COLORS['border'], height=2)
        separator.pack(fill=tk.X, pady=(0, 12))
        
        # Decision prompt
        decision_frame = tk.Frame(button_bar, bg=COLORS['bg_card'])
        decision_frame.pack(fill=tk.X)
        
        tk.Label(decision_frame, text="🤔 What would you like to do with this tailored resume?",
                font=('Segoe UI', 11, 'bold'), bg=COLORS['bg_card'],
                fg=COLORS['text_primary']).pack(side=tk.LEFT)
        
        # Buttons container
        buttons_row = tk.Frame(button_bar, bg=COLORS['bg_card'])
        buttons_row.pack(fill=tk.X, pady=(12, 0))
        
        # LEFT SIDE: Quick utility actions - Open PDF & DOCX
        util_frame = tk.Frame(buttons_row, bg=COLORS['bg_card'])
        util_frame.pack(side=tk.LEFT)
        
        def open_pdf():
            if self.tailored_path and os.path.exists(self.tailored_path):
                os.startfile(self.tailored_path)
            else:
                messagebox.showwarning("Not Found", "PDF file not found.", parent=self.preview_window)
        
        def open_docx():
            if self.tailored_path:
                docx_path = self.tailored_path.replace('.pdf', '.docx')
                if os.path.exists(docx_path):
                    os.startfile(docx_path)
                else:
                    messagebox.showwarning("Not Found", "DOCX file not found.", parent=self.preview_window)
        
        def open_folder():
            folder = os.path.dirname(self.tailored_path) if self.tailored_path else ""
            if folder and os.path.exists(folder):
                os.startfile(folder)
        
        ModernButton(util_frame, "📑 Open PDF", open_pdf, 
                    style='secondary', width=100, height=38).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(util_frame, "📝 Open DOCX", open_docx,
                    style='secondary', width=110, height=38).pack(side=tk.LEFT, padx=(0, 8))
        ModernButton(util_frame, "📁 Folder", open_folder,
                    style='secondary', width=80, height=38).pack(side=tk.LEFT, padx=(0, 8))
        
        # RIGHT SIDE: Main decision buttons (prominent and clear)
        action_frame = tk.Frame(buttons_row, bg=COLORS['bg_card'])
        action_frame.pack(side=tk.RIGHT)
        
        # Skip button (danger) - furthest right
        skip_btn = ModernButton(action_frame, "❌ Skip This Job", self._preview_cancel,
                               style='danger', width=130, height=45)
        skip_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Discard button (secondary) - use default instead
        discard_btn = ModernButton(action_frame, "🚫 Discard & Use Default", self._preview_default,
                                  style='secondary', width=180, height=45)
        discard_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Continue button (success, most prominent)
        continue_btn = ModernButton(action_frame, "✅ Continue with Tailored", self._preview_approve,
                                   style='success', width=200, height=45)
        continue_btn.pack(side=tk.RIGHT, padx=(0, 0))
        
        # Add keyboard shortcuts hint
        shortcuts_label = tk.Label(button_bar, 
            text="💡 Tip: Press Enter to Continue, Escape to Skip",
            font=('Segoe UI', 9), bg=COLORS['bg_card'], fg=COLORS['text_muted'])
        shortcuts_label.pack(pady=(10, 0))
        
        # Bind keyboard shortcuts
        self.preview_window.bind('<Return>', lambda e: self._preview_approve())
        self.preview_window.bind('<Escape>', lambda e: self._preview_cancel())
        self.preview_window.bind('<d>', lambda e: self._preview_default())  # 'd' for discard
        
        self.preview_window.protocol("WM_DELETE_WINDOW", self._preview_cancel)
        
        # Focus the window to ensure keyboard shortcuts work
        self.preview_window.focus_force()
    
    def _save_edited_resume(self):
        """Save the edited resume text to files (TXT, DOCX, PDF)."""
        if not self.tailored_text:
            return
        
        try:
            from modules.ai.resume_tailoring import _save_text, _write_docx, _write_pdf
            from datetime import datetime
            
            output_dir = os.path.dirname(self.tailored_path) if self.tailored_path else "all resumes/temp"
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate base name
            safe_title = "".join(c if c.isalnum() or c in ' -_' else '_' for c in (self.job_title or 'Resume')[:30])
            base_name = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_edited"
            
            # Save all formats
            _save_text(self.tailored_text, output_dir, base_name=base_name)
            _write_docx(self.tailored_text, output_dir, base_name=base_name)
            pdf_path = _write_pdf(self.tailored_text, output_dir, base_name=base_name)
            
            if pdf_path:
                self.tailored_path = pdf_path
                
        except Exception as e:
            print(f"Error saving edited resume: {e}")
    
    def _preview_approve(self):
        """Approve tailored resume and continue. Saves any edits first."""
        # Check if user made edits and save them
        if hasattr(self, 'edit_text_widget'):
            edited_text = self.edit_text_widget.get('1.0', tk.END).strip()
            if edited_text != self.tailored_text:
                self.tailored_text = edited_text
                self._save_edited_resume()
        
        self.result = RESULT_TAILOR
        self.preview_window.destroy()
        self.root.destroy()
    
    def _preview_default(self):
        """Use default resume instead."""
        self.result = RESULT_SKIP_TAILOR
        self.tailored_path = None
        self.preview_window.destroy()
        self.root.destroy()
    
    def _preview_cancel(self):
        """Cancel and skip job."""
        self.result = RESULT_CANCEL
        self.tailored_path = None
        self.preview_window.destroy()
        self.root.destroy()
    
    def _on_default(self):
        """Use default resume."""
        self.result = RESULT_SKIP_TAILOR
        self.root.destroy()
    
    def _on_cancel(self):
        """Cancel/skip job."""
        self.result = RESULT_CANCEL
        self.root.destroy()


def show_quick_tailor_popup(
    job_title: str,
    company: str,
    job_description: str,
    default_resume_path: str,
    master_resume_text: str = None,
    parent: tk.Tk = None
) -> Tuple[str, Optional[str]]:
    """
    Show the modern resume tailoring popup.
    
    Args:
        job_title: Job title
        company: Company name
        job_description: Full job description
        default_resume_path: Path to default resume
        master_resume_text: Optional pre-loaded resume text
        parent: Optional parent window (unused in modern version)
    
    Returns:
        tuple of (result, tailored_resume_path)
    """
    popup = ModernTailorPopup(
        job_title=job_title,
        company=company,
        job_description=job_description,
        default_resume_path=default_resume_path,
        master_resume_text=master_resume_text
    )
    return popup.show()


def ask_tailor_or_default(job_title: str, company: str) -> str:
    """Simple dialog asking if user wants to tailor resume."""
    try:
        import pyautogui
        result = pyautogui.confirm(
            f"Tailor resume for {job_title} at {company}?",
            "Resume Tailoring",
            ["✨ Tailor", "📄 Default", "❌ Skip"]
        )
        if result == "✨ Tailor":
            return RESULT_TAILOR
        elif result == "📄 Default":
            return RESULT_SKIP_TAILOR
        else:
            return RESULT_CANCEL
    except Exception:
        return RESULT_SKIP_TAILOR


# Test function
if __name__ == "__main__":
    result, path = show_quick_tailor_popup(
        job_title="Senior Software Engineer",
        company="Google",
        job_description="We are looking for a Senior Software Engineer with experience in Python, Machine Learning, and distributed systems. The ideal candidate will have 5+ years of experience...",
        default_resume_path=""
    )
    print(f"Result: {result}")
    print(f"Path: {path}")
