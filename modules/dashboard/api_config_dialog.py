"""
API Configuration Dialog with Validation
Allows users to configure and validate API keys for all AI providers.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
import threading
import json
from typing import Dict, Tuple
import urllib.request
import urllib.error

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
FIELD_API_URL = "API URL"
FIELD_API_KEY = "API Key"
API_KEY_NOT_SET = "API key not set"


class APIConfigDialog(tk.Toplevel):
    """Dialog for configuring and testing API keys for all providers."""
    
    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("🔑 AI Provider Configuration")
        self.geometry("900x750")
        self.minsize(850, 700)
        self.configure(bg=COLORS['bg'])
        
        # State variables
        self.provider_configs = self._load_current_configs()
        self.validation_status = {}
        self.entry_widgets = {}
        self.status_labels = {}
        self.test_buttons = {}
        
        self._build_ui()
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.winfo_screenheight() // 2) - (750 // 2)
        self.geometry(f"900x750+{x}+{y}")
        
        # Load and display current status
        self.after(100, self._check_all_providers)
    
    def _load_current_configs(self) -> Dict:
        """Load current API configurations from secrets.py"""
        configs = {}
        try:
            from config import secrets
            
            configs['openai'] = {
                'api_key': getattr(secrets, 'llm_api_key', ''),
                'api_url': getattr(secrets, 'llm_api_url', 'https://api.openai.com/v1'),
                'model': getattr(secrets, 'llm_model', 'gpt-4o-mini'),
            }
            configs['deepseek'] = {
                'api_key': getattr(secrets, 'deepseek_api_key', ''),
                'api_url': getattr(secrets, 'deepseek_api_url', 'https://api.deepseek.com/v1'),
                'model': getattr(secrets, 'deepseek_model', 'deepseek-chat'),
            }
            configs['gemini'] = {
                'api_key': getattr(secrets, 'gemini_api_key', ''),
                'model': getattr(secrets, 'gemini_model', 'gemini-1.5-flash'),
            }
            configs['groq'] = {
                'api_key': getattr(secrets, 'groq_api_key', ''),
                'api_url': getattr(secrets, 'groq_api_url', 'https://api.groq.com/openai/v1'),
                'model': getattr(secrets, 'groq_model', 'llama-3.3-70b-versatile'),
            }
            configs['huggingface'] = {
                'api_key': getattr(secrets, 'huggingface_api_key', ''),
                'api_url': getattr(secrets, 'huggingface_api_url', 'https://api-inference.huggingface.co/models'),
                'model': getattr(secrets, 'huggingface_model', 'mistralai/Mistral-7B-Instruct-v0.3'),
            }
            configs['ollama'] = {
                'api_url': getattr(secrets, 'ollama_api_url', 'http://localhost:11434'),
                'model': getattr(secrets, 'ollama_model', 'llama3.2:1b'),
            }
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configurations:\n{e}")
        
        return configs
    
    def _build_ui(self):
        """Build the complete UI."""
        
        # Header
        header_frame = tk.Frame(self, bg=COLORS['bg'])
        header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(
            header_frame,
            text="🔑 AI Provider Configuration",
            font=(UI_FONT, 18, "bold"),
            fg=COLORS['accent'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header_frame,
            text="Configure and test your API keys",
            font=(UI_FONT, 10),
            fg=COLORS['text_secondary'],
            bg=COLORS['bg']
        ).pack(side=tk.LEFT, padx=20)
        
        # Main content with scrollbar
        main_container = tk.Frame(self, bg=COLORS['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_container, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Build provider sections
        self._build_provider_section(scrollable_frame, "openai", "OpenAI", "🤖",
                                     ["api_url", "api_key", "model"],
                                     {
                                         'api_url': FIELD_API_URL,
                                         'api_key': FIELD_API_KEY,
                                         'model': 'Model (e.g., gpt-4o-mini, gpt-4o)'
                                     })
        
        self._build_provider_section(scrollable_frame, "deepseek", "DeepSeek", "🧠",
                                     ["api_url", "api_key", "model"],
                                     {
                                         'api_url': FIELD_API_URL,
                                         'api_key': FIELD_API_KEY,
                                         'model': 'Model (deepseek-chat, deepseek-reasoner)'
                                     })
        
        self._build_provider_section(scrollable_frame, "gemini", "Google Gemini", "✨",
                                     ["api_key", "model"],
                                     {
                                         'api_key': FIELD_API_KEY,
                                         'model': 'Model (gemini-1.5-flash, gemini-1.5-pro)'
                                     })
        
        self._build_provider_section(scrollable_frame, "groq", "Groq (FREE & Fast!)", "⚡",
                                     ["api_url", "api_key", "model"],
                                     {
                                         'api_url': FIELD_API_URL,
                                         'api_key': 'API Key (FREE at console.groq.com)',
                                         'model': 'Model (llama-3.3-70b-versatile, llama-3.1-8b-instant)'
                                     },
                                     highlight=True)
        
        self._build_provider_section(scrollable_frame, "huggingface", "Hugging Face (FREE)", "🤗",
                                     ["api_url", "api_key", "model"],
                                     {
                                         'api_url': FIELD_API_URL,
                                         'api_key': 'API Key (FREE at huggingface.co)',
                                         'model': 'Model (mistralai/Mistral-7B-Instruct-v0.3)'
                                     })
        
        self._build_provider_section(scrollable_frame, "ollama", "Ollama (Local)", "🦙",
                                     ["api_url", "model"],
                                     {
                                         'api_url': 'API URL (local server)',
                                         'model': 'Model (must be pulled: ollama pull model_name)'
                                     })
        
        # Bottom action buttons
        button_frame = tk.Frame(self, bg='#0f3460', pady=12)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttkb.Button(
            button_frame,
            text="🧪 Test All Providers",
            command=self._check_all_providers,
            bootstyle="info",
            width=20
        ).pack(side=tk.LEFT, padx=10)
        
        ttkb.Button(
            button_frame,
            text="💾 Save Configuration",
            command=self._save_configuration,
            bootstyle="success",
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttkb.Button(
            button_frame,
            text="📖 Get API Keys Help",
            command=self._show_api_keys_help,
            bootstyle="warning-outline",
            width=18
        ).pack(side=tk.LEFT, padx=5)
        
        ttkb.Button(
            button_frame,
            text="✖️ Close",
            command=self.destroy,
            bootstyle="danger-outline",
            width=10
        ).pack(side=tk.RIGHT, padx=10)
    
    def _build_provider_section(self, parent: tk.Frame, provider_id: str, 
                                provider_name: str, icon: str, fields: list,
                                field_labels: dict, highlight: bool = False):
        """Build a configuration section for one provider."""
        
        frame_color = "#2d4a2b" if highlight else COLORS['card']
        border_color = COLORS['success'] if highlight else COLORS['border']
        
        # Provider frame
        provider_frame = tk.Frame(parent, bg=frame_color, highlightbackground=border_color, 
                                 highlightthickness=2)
        provider_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Header
        header = tk.Frame(provider_frame, bg=frame_color)
        header.pack(fill=tk.X, padx=15, pady=(12, 8))
        
        tk.Label(
            header,
            text=f"{icon} {provider_name}",
            font=(UI_FONT, 14, "bold"),
            fg=COLORS['text'],
            bg=frame_color
        ).pack(side=tk.LEFT)
        
        # Status indicator
        status_label = tk.Label(
            header,
            text="⚫ Not tested",
            font=(UI_FONT, 10),
            fg=COLORS['text_secondary'],
            bg=frame_color
        )
        status_label.pack(side=tk.RIGHT, padx=10)
        self.status_labels[provider_id] = status_label
        
        # Test button
        test_btn = ttkb.Button(
            header,
            text="🧪 Test",
            command=lambda: self._test_provider(provider_id),
            bootstyle="info-outline",
            width=8
        )
        test_btn.pack(side=tk.RIGHT, padx=5)
        self.test_buttons[provider_id] = test_btn
        
        # Fields
        self.entry_widgets[provider_id] = {}
        
        for field in fields:
            field_frame = tk.Frame(provider_frame, bg=frame_color)
            field_frame.pack(fill=tk.X, padx=15, pady=5)
            
            label_text = field_labels.get(field, field)
            entry = self._create_field_entry(field_frame, frame_color, field, label_text)
            
            # Load current value
            current_value = self.provider_configs.get(provider_id, {}).get(field, '')
            if current_value and current_value not in ['your_', 'YOUR_']:
                entry.insert(0, current_value)
            
            self.entry_widgets[provider_id][field] = entry

    def _create_field_entry(self, field_frame: tk.Frame, frame_color: str, field: str, label_text: str) -> tk.Entry:
        tk.Label(
            field_frame,
            text=label_text + ":",
            font=(UI_FONT, 9),
            fg=COLORS['text'],
            bg=frame_color,
            width=40,
            anchor='w'
        ).pack(side=tk.TOP, anchor='w')

        entry_width = 70 if field == 'api_key' or 'url' in field.lower() else 50

        entry = tk.Entry(
            field_frame,
            font=("Consolas", 9),
            bg='#0d1b2a',
            fg=COLORS['text'],
            insertbackground='white',
            width=entry_width,
            show='*' if field == 'api_key' else None
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
        # Show/Hide button for API keys
        if field == 'api_key':
            def toggle_visibility(e=entry):
                e.config(show='' if e.cget('show') == '*' else '*')
            
            ttkb.Button(
                field_frame,
                text="👁️",
                command=toggle_visibility,
                bootstyle="secondary-outline",
                width=3
            ).pack(side=tk.LEFT, padx=5)
        
        return entry
        
        # Spacer
        tk.Frame(provider_frame, bg=frame_color, height=8).pack()
    
    def _test_provider(self, provider_id: str):
        """Test a specific provider's configuration."""
        self.status_labels[provider_id].config(text="🔄 Testing...", fg=COLORS['warning'])
        self.test_buttons[provider_id].config(state='disabled')
        
        def test_thread():
            success, message = self._validate_provider(provider_id)
            
            # Update UI in main thread
            self.after(0, lambda: self._update_provider_status(provider_id, success, message))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _validate_provider(self, provider_id: str) -> Tuple[bool, str]:
        """Validate provider configuration by making a test API call."""
        try:
            # Get values from entry widgets
            config = {}
            for field, entry in self.entry_widgets[provider_id].items():
                config[field] = entry.get().strip()
            
            if provider_id == "openai":
                return self._test_openai(config)
            elif provider_id == "deepseek":
                return self._test_deepseek(config)
            elif provider_id == "gemini":
                return self._test_gemini(config)
            elif provider_id == "groq":
                return self._test_groq(config)
            elif provider_id == "huggingface":
                return self._test_huggingface(config)
            elif provider_id == "ollama":
                return self._test_ollama(config)
            
            return False, "Unknown provider"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _test_openai(self, config: dict) -> Tuple[bool, str]:
        """Test OpenAI API."""
        try:
            from openai import OpenAI
            
            api_key = config.get('api_key', '')
            api_url = config.get('api_url', 'https://api.openai.com/v1')
            model = config.get('model', 'gpt-4o-mini')
            
            if not api_key or 'your_' in api_key.lower():
                return False, API_KEY_NOT_SET
            
            client = OpenAI(api_key=api_key, base_url=api_url)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            return True, f"✅ Connected | Model: {model}"
        except Exception as e:
            return False, f"❌ Failed: {str(e)[:50]}"
    
    def _test_deepseek(self, config: dict) -> Tuple[bool, str]:
        """Test DeepSeek API."""
        try:
            from openai import OpenAI
            
            api_key = config.get('api_key', '')
            api_url = config.get('api_url', 'https://api.deepseek.com/v1')
            model = config.get('model', 'deepseek-chat')
            
            if not api_key or 'your_' in api_key.lower():
                return False, API_KEY_NOT_SET
            
            client = OpenAI(api_key=api_key, base_url=api_url)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            return True, f"✅ Connected | Model: {model}"
        except Exception as e:
            return False, f"❌ Failed: {str(e)[:50]}"
    
    def _test_gemini(self, config: dict) -> Tuple[bool, str]:
        """Test Gemini API."""
        try:
            import google.generativeai as genai
            
            api_key = config.get('api_key', '')
            model = config.get('model', 'gemini-1.5-flash')
            
            if not api_key or 'your_' in api_key.lower():
                return False, API_KEY_NOT_SET
            
            genai.configure(api_key=api_key)
            model_obj = genai.GenerativeModel(model)
            model_obj.generate_content("Hello")
            
            return True, f"✅ Connected | Model: {model}"
        except Exception as e:
            return False, f"❌ Failed: {str(e)[:50]}"
    
    def _test_groq(self, config: dict) -> Tuple[bool, str]:
        """Test Groq API."""
        try:
            from openai import OpenAI
            
            api_key = config.get('api_key', '')
            api_url = config.get('api_url', 'https://api.groq.com/openai/v1')
            model = config.get('model', 'llama-3.3-70b-versatile')
            
            if not api_key or 'your_' in api_key.lower():
                return False, API_KEY_NOT_SET
            
            client = OpenAI(api_key=api_key, base_url=api_url)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            return True, f"✅ Connected | Model: {model} | FREE & FAST!"
        except Exception as e:
            error_msg = str(e)
            if "decommissioned" in error_msg.lower():
                return False, "❌ Model deprecated. Try: llama-3.3-70b-versatile"
            return False, f"❌ Failed: {error_msg[:50]}"
    
    def _test_huggingface(self, config: dict) -> Tuple[bool, str]:
        """Test Hugging Face API."""
        try:
            api_key = config.get('api_key', '')
            api_url = config.get('api_url', 'https://api-inference.huggingface.co/models')
            model = config.get('model', 'mistralai/Mistral-7B-Instruct-v0.3')
            
            if not api_key or 'your_' in api_key.lower():
                return False, API_KEY_NOT_SET
            
            url = f"{api_url}/{model}"
            headers = {"Authorization": f"Bearer {api_key}"}
            data = json.dumps({"inputs": "Hello"}).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                json.loads(response.read().decode('utf-8'))
            
            return True, f"✅ Connected | Model: {model.split('/')[-1]}"
        except Exception as e:
            return False, f"❌ Failed: {str(e)[:50]}"
    
    def _test_ollama(self, config: dict) -> Tuple[bool, str]:
        """Test Ollama local server."""
        try:
            api_url = config.get('api_url', 'http://localhost:11434')
            model = config.get('model', 'llama3.2:1b')
            
            # Check if server is running
            url = f"{api_url}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                
                model_base = model.split(":")[0]
                if model in models or any(model_base in m for m in models):
                    return True, f"✅ Connected | Model: {model}"
                else:
                    available = ", ".join([m.split(":")[0] for m in models[:3]])
                    return False, f"❌ Model '{model}' not found. Available: {available}"
        except Exception as e:
            return False, f"❌ Ollama offline: {str(e)[:30]}"
    
    def _update_provider_status(self, provider_id: str, success: bool, message: str):
        """Update provider status in UI."""
        status_label = self.status_labels[provider_id]
        test_button = self.test_buttons[provider_id]
        
        if success:
            status_label.config(text=message, fg=COLORS['success'])
        else:
            status_label.config(text=message, fg=COLORS['danger'])
        
        test_button.config(state='normal')
        self.validation_status[provider_id] = success
    
    def _check_all_providers(self):
        """Test all providers at once."""
        for provider_id in self.entry_widgets.keys():
            self._test_provider(provider_id)
    
    def _save_configuration(self):
        """Save configurations to secrets.py file."""
        try:
            var_mapping = {
                ('openai', 'api_key'): 'llm_api_key',
                ('openai', 'api_url'): 'llm_api_url',
                ('openai', 'model'): 'llm_model',
                ('deepseek', 'api_key'): 'deepseek_api_key',
                ('deepseek', 'api_url'): 'deepseek_api_url',
                ('deepseek', 'model'): 'deepseek_model',
                ('gemini', 'api_key'): 'gemini_api_key',
                ('gemini', 'model'): 'gemini_model',
                ('groq', 'api_key'): 'groq_api_key',
                ('groq', 'api_url'): 'groq_api_url',
                ('groq', 'model'): 'groq_model',
                ('huggingface', 'api_key'): 'huggingface_api_key',
                ('huggingface', 'api_url'): 'huggingface_api_url',
                ('huggingface', 'model'): 'huggingface_model',
                ('ollama', 'api_url'): 'ollama_api_url',
                ('ollama', 'model'): 'ollama_model',
            }

            values_by_var = {}
            for provider_id, fields in self.entry_widgets.items():
                for field, entry in fields.items():
                    value = entry.get().strip()
                    if not value:
                        continue
                    var_name = var_mapping.get((provider_id, field))
                    if var_name:
                        values_by_var[var_name] = value

            # Read current secrets.py
            secrets_path = "config/secrets.py"
            with open(secrets_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Update values
            updated_lines = []
            for line in lines:
                updated_line = line
                for var_name, value in values_by_var.items():
                    if line.lstrip().startswith(f"{var_name} ="):
                        indent = line[:line.index(var_name)]
                        comment = ''
                        if '#' in line:
                            comment_start = line.index('#')
                            comment = ' ' + line[comment_start:].rstrip()
                        updated_line = f'{indent}{var_name} = "{value}"{comment}\n'
                        break
                updated_lines.append(updated_line)
            
            # Write back to file
            with open(secrets_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            
            messagebox.showinfo(
                "Success",
                "✅ Configuration saved successfully!\n\n"
                "Your API keys have been saved to config/secrets.py.\n\n"
                "⚠️ SECURITY REMINDER:\n"
                "Make sure config/secrets.py is in your .gitignore!"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{e}")
    
    def _show_api_keys_help(self):
        """Show help for getting API keys."""
        help_text = """
🔑 How to Get API Keys:

🤖 OpenAI:
   • Visit: https://platform.openai.com/api-keys
   • Sign up and create an API key
   • Costs: Pay-per-use (starting at $0.002/1K tokens)

🧠 DeepSeek:
   • Visit: https://platform.deepseek.com
   • Sign up and generate API key
   • Costs: Competitive pricing

✨ Google Gemini:
   • Visit: https://makersuite.google.com/app/apikey
   • Create API key with Google account
   • Free tier available

⚡ Groq (RECOMMENDED - FREE & FAST!):
   • Visit: https://console.groq.com/keys
   • Sign up and create API key
   • FREE tier: 30 requests/min, 6000 tokens/min
   • Blazing fast inference!

🤗 Hugging Face (FREE):
   • Visit: https://huggingface.co/settings/tokens
   • Create account and generate token
   • FREE for inference API
   • Rate limited but completely free

🦙 Ollama (LOCAL - NO API KEY):
   • Visit: https://ollama.com/download
   • Install Ollama on your computer
   • Run: ollama pull llama3.2:1b
   • 100% free, runs locally

💡 RECOMMENDATION:
   Start with Groq (free & fast) or Ollama (local & private)
"""
        
        help_window = tk.Toplevel(self)
        help_window.title("API Keys Help")
        help_window.geometry("600x700")
        help_window.configure(bg=COLORS['bg'])
        
        text_widget = tk.Text(
            help_window,
            font=("Consolas", 10),
            bg=COLORS['card'],
            fg=COLORS['text'],
            wrap=tk.WORD,
            padx=20,
            pady=20
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", help_text)
        text_widget.config(state=tk.DISABLED)
        
        ttkb.Button(
            help_window,
            text="Close",
            command=help_window.destroy,
            bootstyle="secondary"
        ).pack(pady=10)


def open_api_config_dialog(parent: tk.Misc):
    """Open the API configuration dialog."""
    dialog = APIConfigDialog(parent)
    dialog.grab_set()
    parent.wait_window(dialog)
