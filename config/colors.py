"""
Shared Color Constants
======================
Centralises every colour literal used across the dashboard and tailor UIs
so changes propagate from a single source of truth.

Two palettes:
  TAILOR_COLORS — used by the Tkinter quick_tailor_popup (purple/crimson theme)
  DASHBOARD_COLORS — used by the PySide6 operator dashboard (dark navy theme)
"""

# ── Tkinter Quick Tailor Popup palette ────────────────────────────────
TAILOR_COLORS: dict[str, str] = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_input": "#0f3460",
    "accent": "#e94560",
    "accent_hover": "#ff6b6b",
    "success": "#00d9a5",
    "warning": "#ffc107",
    "error": "#ff4757",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "text_muted": "#6c757d",
    "diff_added_bg": "#1e4620",
    "diff_added_fg": "#7fff7f",
    "diff_removed_bg": "#4a1515",
    "diff_removed_fg": "#ff7f7f",
    "diff_changed_bg": "#4a4a15",
    "diff_changed_fg": "#ffff7f",
    "border": "#2d3748",
}

# ── PySide6 Dashboard palette ────────────────────────────────────────
DASHBOARD_COLORS: dict[str, str] = {
    "bg_main": "#0b1220",
    "bg_card": "#121a2f",
    "bg_topbar": "#111a2e",
    "bg_input": "#0f172a",
    "bg_tab": "#17243a",
    "bg_tab_selected": "#1d4ed8",
    "bg_button": "#18233a",
    "bg_button_hover": "#22304a",
    "bg_toggle": "#1f2937",
    "bg_toggle_checked": "#0f3b2e",
    "bg_progress_track": "#0b1324",
    "bg_statusbar": "#0f172a",
    "bg_btn_success": "#14532d",
    "bg_btn_success_hover": "#166534",
    "bg_btn_danger": "#4c1d1d",
    "bg_btn_danger_hover": "#7f1d1d",
    "bg_btn_warn": "#4a330f",
    "bg_btn_warn_hover": "#6b4612",
    "bg_btn_info": "#0c4a6e",
    "bg_btn_info_hover": "#075985",
    "bg_btn_neutral": "#1f2937",
    "bg_btn_neutral_hover": "#334155",
    "border_card": "#22324a",
    "border_group": "#26354d",
    "border_tab": "#2a3b56",
    "border_input": "#2a3b56",
    "border_button": "#2b3b55",
    "border_toggle": "#475569",
    "border_toggle_checked": "#22c55e",
    "border_progress": "#334155",
    "border_btn_success": "#22c55e",
    "border_btn_danger": "#ef4444",
    "border_btn_warn": "#f59e0b",
    "border_btn_info": "#38bdf8",
    "border_btn_neutral": "#64748b",
    "text_primary": "#e2e8f0",
    "text_title": "#f8fafc",
    "text_subtitle": "#94a3b8",
    "text_group_title": "#cbd5e1",
    "text_card_title": "#94a3b8",
    "text_tab": "#cbd5e1",
    "text_toggle": "#cbd5e1",
    "text_toggle_checked": "#dcfce7",
    "text_selected_row": "#1e40af",
    "gradient_progress_start": "#06b6d4",
    "gradient_progress_end": "#22c55e",
    # Metric card accent colors
    "card_jobs_accent": "#38bdf8",
    "card_applied_accent": "#22c55e",
    "card_failed_accent": "#ef4444",
    "card_rate_accent": "#a78bfa",
}

# Convenience alias — backwards-compatible with existing quick_tailor_popup imports
COLORS = TAILOR_COLORS
