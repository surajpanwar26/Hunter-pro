# 🔒 Security Setup Guide

## ⚠️ IMPORTANT: First Time Setup

Before running this project, you MUST configure your credentials securely:

### Step 1: Copy the Example File
```bash
cp config/secrets.example.py config/secrets.py
```

Or on Windows:
```powershell
copy config\secrets.example.py config\secrets.py
```

### Step 2: Edit config/secrets.py
Open `config/secrets.py` and add your actual credentials:

1. **LinkedIn Credentials**
   - `username`: Your LinkedIn email
   - `password`: Your LinkedIn password

2. **AI Provider (Choose One)**
   - **Groq** (Recommended - FREE & Fast): Get key at https://console.groq.com/keys
   - **Ollama** (Local - No key needed): Download at https://ollama.com
   - **OpenAI**: Get key at https://platform.openai.com/api-keys
   - **DeepSeek**: Get key at https://platform.deepseek.com
   - **Gemini**: Get key at https://makersuite.google.com/app/apikey
   - **Hugging Face** (FREE): Get key at https://huggingface.co/settings/tokens

### Step 3: Verify .gitignore
Make sure `config/secrets.py` is in `.gitignore` to prevent accidental commits.

### Step 4: Test Configuration
```bash
python -c "from modules.validator import validate_config; validate_config()"
```

## 🔐 Security Best Practices

1. **NEVER commit secrets.py to git**
   - Always use secrets.example.py as a template
   - Keep your actual secrets.py file local only

2. **Use Environment Variables (Recommended)**
   ```python
   import os
   username = os.getenv('LINKEDIN_USERNAME', 'default@example.com')
   password = os.getenv('LINKEDIN_PASSWORD', 'default_password')
   ```

3. **Rotate API Keys Regularly**
   - Change your keys every 3-6 months
   - Immediately rotate if you suspect exposure

4. **Check for Exposed Credentials**
   ```bash
   git log --all --full-history -- config/secrets.py
   ```

## 🚨 If You Accidentally Committed Secrets

1. **Change all passwords and API keys immediately**
2. **Remove from git history**:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config/secrets.py" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. **Force push** (⚠️ Warning: This rewrites history):
   ```bash
   git push origin --force --all
   ```

## 📝 What's Safe to Commit

✅ **Safe:**
- config/secrets.example.py
- config/settings.py
- config/search.py
- config/questions.py (if no sensitive data)

❌ **Never Commit:**
- config/secrets.py
- config/personals.py (contains personal info)
- Any file with real credentials
- API keys, passwords, tokens

## 🆘 Need Help?

If you're unsure about security or have exposed credentials:
1. Check GitHub's secret scanning alerts
2. Rotate all affected credentials immediately
3. Review this guide carefully
4. Consider using a secrets manager like HashiCorp Vault or AWS Secrets Manager

---

**Remember: Security is not optional. Protect your credentials!**
