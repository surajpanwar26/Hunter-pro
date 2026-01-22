# Secrets Configuration Template
# IMPORTANT: Copy this file to secrets.py and fill in your actual credentials
# NEVER commit secrets.py to version control!

# LinkedIn Credentials
# For security, you can also set these as environment variables:
# import os
# username = os.getenv('LINKEDIN_USERNAME', 'your_email@example.com')
username = "your_email@example.com"  # Your LinkedIn login email
# password = os.getenv('LINKEDIN_PASSWORD', 'your_password')
password = "your_password_here"      # Your LinkedIn login password

# AI Configuration
use_AI = True                                 # Set to True to enable AI features (REQUIRED for resume tailoring!)
ai_provider = "ollama"                        # Options: "openai", "deepseek", "gemini", "ollama", "groq", "huggingface"

# OpenAI Configuration (if using OpenAI)
llm_api_url = "https://api.openai.com/v1"     # OpenAI API URL
# llm_api_key = os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')  # Secure way to load API key
llm_api_key = "your_openai_api_key_here"      # Your OpenAI API key
llm_model = "gpt-4o-mini"                     # Model to use (e.g., "gpt-4o-mini", "gpt-4")

# DeepSeek Configuration (if using DeepSeek)
deepseek_api_url = "https://api.deepseek.com/v1"  # DeepSeek API URL
# deepseek_api_key = os.getenv('DEEPSEEK_API_KEY', 'your_deepseek_api_key_here')  # Secure way to load API key
deepseek_api_key = "your_deepseek_api_key_here"   # Your DeepSeek API key
deepseek_model = "deepseek-chat"                  # Model to use

# Gemini Configuration (if using Gemini)
# gemini_api_key = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here')  # Secure way to load API key
gemini_api_key = "your_gemini_api_key_here"       # Your Gemini API key
gemini_model = "gemini-1.5-flash"                 # Model to use

# Groq Configuration (FREE API - Fast inference!)
# Get free API key at: https://console.groq.com/keys
groq_api_url = "https://api.groq.com/openai/v1"   # Groq API URL (OpenAI compatible)
groq_api_key = "your_groq_api_key_here"           # Your Groq API key (FREE!)
groq_model = "llama-3.3-70b-versatile"            # Updated: llama-3.1-70b-versatile was decommissioned
# FREE GROQ MODELS (Updated January 2026):
#   - llama-3.3-70b-versatile (CURRENT - Best quality, 30 req/min free)
#   - llama-3.1-8b-instant (Fast, 30 req/min free)
#   - mixtral-8x7b-32768 (Good balance)
#   - gemma2-9b-it (Google's Gemma 2)

# Hugging Face Configuration (FREE API)
# Get free API key at: https://huggingface.co/settings/tokens
huggingface_api_url = "https://api-inference.huggingface.co/models"  # HF Inference API
huggingface_api_key = "your_huggingface_api_key_here"                # Your HF API key (FREE!)
huggingface_model = "mistralai/Mistral-7B-Instruct-v0.3"             # Model to use
# FREE HUGGING FACE MODELS:
#   - mistralai/Mistral-7B-Instruct-v0.3 (Great for text)
#   - microsoft/Phi-3-mini-4k-instruct (Compact & fast)
#   - meta-llama/Llama-2-7b-chat-hf (Popular choice)
#   - google/flan-t5-large (Good for instructions)

# Ollama Configuration (LOCAL - No API key needed!)
# Download from: https://ollama.com/download
# Run: ollama pull <model_name> to download models
ollama_api_url = "http://localhost:11434"        # Ollama API URL
ollama_model = "llama3.2:1b"                     # Model loaded in Ollama (Good balance!)
# ⚠️ IMPORTANT: Large models (7B+) on CPU can timeout. Use small models or GPU.
#
# RECOMMENDED MODELS for resume tailoring (by speed):
#   FAST (CPU-friendly, <30 seconds):
#   - llama3.2:1b (1.3GB) - Fastest! Great for CPU-only systems
#   - phi3:mini (2.3GB) - Small & fast
#   - gemma2:2b (1.6GB) - Google's compact model
#
#   MEDIUM (needs good CPU/GPU, ~1-3 minutes):
#   - qwen2.5:7b (4.7GB) - Best balance of speed & quality
#   - llama3.1:8b (4.7GB) - Great quality
#   - mistral:7b (4.1GB) - Good alternative
#
#   SLOW (GPU recommended, >5 minutes on CPU):
#   - qwen3:14b (9.3GB) - High quality but VERY slow on CPU
#   - llama2:13b (7.4GB) - High quality but slow on CPU
#
# 💡 TIP: If using CPU only, use llama3.2:1b or phi3:mini for best experience

# Additional AI Settings
stream_output = True                             # Enable streaming responses
llm_spec = "openai"                              # API specification type
