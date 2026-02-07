"""
HTML Diff Viewer - Generate beautiful side-by-side resume comparisons

This module creates HTML-based diff views that work better than Tkinter's
limited text highlighting capabilities.

Author: Suraj Panwar
Version: 1.0.0
"""
from __future__ import annotations

import os
import difflib
import webbrowser
from datetime import datetime
from typing import Optional

from modules.helpers import print_lg


def generate_html_diff(
    master_text: str,
    tailored_text: str,
    job_title: str = "Resume",
    output_dir: Optional[str] = None,
    open_in_browser: bool = True,
) -> str:
    """
    Generate an HTML diff view comparing master and tailored resumes.
    
    Args:
        master_text: Original resume text
        tailored_text: Tailored resume text
        job_title: Job title for the header
        output_dir: Directory to save HTML file (defaults to temp)
        open_in_browser: Whether to open in browser automatically
        
    Returns:
        Path to generated HTML file
    """
    # Generate unified diff
    master_lines = master_text.splitlines(keepends=True)
    tailored_lines = tailored_text.splitlines(keepends=True)
    
    diff = difflib.HtmlDiff(wrapcolumn=80)
    
    # Generate side-by-side HTML table
    diff_table = diff.make_table(
        master_lines, 
        tailored_lines,
        fromdesc="📋 ORIGINAL RESUME",
        todesc="✨ TAILORED RESUME",
        context=True,
        numlines=3
    )
    
    # Calculate statistics
    matcher = difflib.SequenceMatcher(None, master_lines, tailored_lines)
    ratio = matcher.ratio()
    
    added_lines = 0
    removed_lines = 0
    changed_lines = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            added_lines += j2 - j1
        elif tag == 'delete':
            removed_lines += i2 - i1
        elif tag == 'replace':
            changed_lines += max(i2 - i1, j2 - j1)
    
    # Build complete HTML document with modern styling
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Diff - {job_title}</title>
    <style>
        :root {{
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --accent: #6366f1;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --added-bg: #14532d;
            --added-text: #86efac;
            --removed-bg: #7f1d1d;
            --removed-text: #fca5a5;
            --changed-bg: #713f12;
            --changed-text: #fde047;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        header {{
            background: var(--bg-card);
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .header-title {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .header-title h1 {{
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--accent);
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--bg-dark);
            border-radius: 8px;
            font-size: 0.875rem;
        }}
        
        .stat-value {{
            font-weight: 700;
            font-size: 1rem;
        }}
        
        .stat-added {{ color: var(--success); }}
        .stat-removed {{ color: var(--danger); }}
        .stat-changed {{ color: var(--warning); }}
        .stat-similarity {{ color: var(--accent); }}
        
        .legend {{
            background: var(--bg-card);
            padding: 15px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.875rem;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .legend-added {{ background: var(--added-bg); border: 2px solid var(--added-text); }}
        .legend-removed {{ background: var(--removed-bg); border: 2px solid var(--removed-text); }}
        .legend-changed {{ background: var(--changed-bg); border: 2px solid var(--changed-text); }}
        
        .diff-container {{
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        /* Override difflib table styles */
        table.diff {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
            font-size: 0.8rem;
            line-height: 1.5;
        }}
        
        table.diff th {{
            background: var(--accent);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        
        table.diff td {{
            padding: 4px 10px;
            vertical-align: top;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        
        table.diff colgroup {{
            width: 2%;
        }}
        
        /* Line numbers */
        table.diff td:nth-child(1),
        table.diff td:nth-child(2),
        table.diff td:nth-child(4),
        table.diff td:nth-child(5) {{
            background: var(--bg-dark);
            color: var(--text-secondary);
            text-align: right;
            width: 40px;
            font-size: 0.75rem;
            user-select: none;
        }}
        
        /* Content columns */
        table.diff td:nth-child(3),
        table.diff td:nth-child(6) {{
            background: var(--bg-card);
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        /* Diff highlighting */
        .diff_add {{
            background: var(--added-bg) !important;
            color: var(--added-text) !important;
        }}
        
        .diff_sub {{
            background: var(--removed-bg) !important;
            color: var(--removed-text) !important;
            text-decoration: line-through;
        }}
        
        .diff_chg {{
            background: var(--changed-bg) !important;
            color: var(--changed-text) !important;
        }}
        
        /* Hide expand/collapse links */
        table.diff a {{
            display: none;
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 0.8rem;
        }}
        
        @media (max-width: 768px) {{
            header {{
                flex-direction: column;
                text-align: center;
            }}
            
            .stats {{
                justify-content: center;
            }}
            
            table.diff {{
                font-size: 0.7rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <span style="font-size: 2rem;">📄</span>
                <h1>Resume Diff Viewer</h1>
            </div>
            <div class="stats">
                <div class="stat">
                    <span>🎯 Job:</span>
                    <span class="stat-value" style="color: var(--accent);">{job_title}</span>
                </div>
                <div class="stat">
                    <span>➕</span>
                    <span class="stat-value stat-added">{added_lines}</span>
                    <span>Added</span>
                </div>
                <div class="stat">
                    <span>➖</span>
                    <span class="stat-value stat-removed">{removed_lines}</span>
                    <span>Removed</span>
                </div>
                <div class="stat">
                    <span>✏️</span>
                    <span class="stat-value stat-changed">{changed_lines}</span>
                    <span>Changed</span>
                </div>
                <div class="stat">
                    <span>📊</span>
                    <span class="stat-value stat-similarity">{ratio*100:.0f}%</span>
                    <span>Similarity</span>
                </div>
            </div>
        </header>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color legend-added"></div>
                <span>Added Content (Green)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color legend-removed"></div>
                <span>Removed Content (Red)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color legend-changed"></div>
                <span>Modified Content (Yellow)</span>
            </div>
        </div>
        
        <div class="diff-container">
            {diff_table}
        </div>
        
        <footer>
            Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | LinkedIn Auto Job Applier
        </footer>
    </div>
</body>
</html>'''
    
    # Save to file
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'all resumes', 'temp')
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() or c in ' -_' else '_' for c in job_title)[:30]
    filename = f"resume_diff_{safe_title}_{timestamp}.html"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print_lg(f"📄 HTML diff saved: {filepath}")
    
    # Open in browser
    if open_in_browser:
        webbrowser.open(f'file://{os.path.abspath(filepath)}')
    
    return filepath


def generate_inline_diff(
    master_text: str,
    tailored_text: str,
) -> str:
    """
    Generate a simple inline diff view as text.
    Useful for logging or terminal display.
    
    Returns:
        Unified diff as string
    """
    master_lines = master_text.splitlines(keepends=True)
    tailored_lines = tailored_text.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        master_lines,
        tailored_lines,
        fromfile='Original Resume',
        tofile='Tailored Resume',
        lineterm=''
    )
    
    return '\n'.join(diff)


def calculate_diff_stats(master_text: str, tailored_text: str) -> dict:
    """
    Calculate statistics about the differences between two texts.
    
    Returns:
        Dict with: added, removed, changed, similarity_ratio
    """
    master_lines = master_text.splitlines()
    tailored_lines = tailored_text.splitlines()
    
    matcher = difflib.SequenceMatcher(None, master_lines, tailored_lines)
    
    added = 0
    removed = 0
    changed = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            added += j2 - j1
        elif tag == 'delete':
            removed += i2 - i1
        elif tag == 'replace':
            changed += max(i2 - i1, j2 - j1)
    
    return {
        'added_lines': added,
        'removed_lines': removed,
        'changed_lines': changed,
        'similarity_ratio': matcher.ratio(),
        'total_master_lines': len(master_lines),
        'total_tailored_lines': len(tailored_lines),
    }
