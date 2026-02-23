# Extension Update Guide

This guide explains how to update the AI Hunter pro Chrome extension (V2 runtime) after making changes to config files.

## Quick Update Steps

### 1. Regenerate Extension Config
Run this command from the project root:

```bash
python setup/update_extension.py
```

This script:
- Reads from `config/personals.py`, `config/questions.py`, and `config/secrets.py`
- Creates `extension/user_config.json` with all your profile data
- Shows what data was loaded

### 2. Clear Extension Storage (Force Reload)
The extension caches your data in Chrome storage. To force it to reload from the new config:

**Option A: Use the Extension UI (Recommended)**
1. Click the extension icon to open popup
2. Go to **Settings** tab
3. Click **🔄 Refresh from Project Config**
4. Confirm the action

**Option B: Manual Console Method**
1. Click the extension icon to open popup
2. Right-click anywhere → **Inspect**
3. Go to **Console** tab
4. Paste this code:
```javascript
chrome.storage.sync.clear(() => console.log('Storage cleared'));
chrome.storage.local.clear(() => console.log('Local storage cleared'));
```
5. Press Enter
6. Close and reopen the popup

### 3. Reload Extension (If JS Changes)
After changing any JavaScript files:

1. Go to `chrome://extensions`
2. Find "AI Hunter pro"
3. Click the **refresh** icon (↻)
4. OR toggle the extension off and on

### 4. Verify
1. Open the extension popup
2. Go to **Profile** tab
3. Your data should be auto-populated with your config values

### 5. Confirm V2 + Groq Defaults
1. Open the extension popup.
2. Verify the header shows **AI Hunter pro · V2 Runtime**.
3. In DevTools console, run:
```javascript
chrome.storage.local.get('aiProviderConfig', console.log)
```
4. Confirm provider defaults include:
	- `provider: "groq"`
	- `apiUrl: "https://api.groq.com/openai/v1"`
	- `model: "llama-3.3-70b-versatile"`

## Config File Locations

| File | Purpose |
|------|---------|
| `config/personals.py` | Personal info (name, address, phone) |
| `config/questions.py` | Application questions (visa, salary, etc.) |
| `config/secrets.py` | LinkedIn credentials, API keys |
| `extension/user_config.json` | Generated config for extension (auto-created) |

## Updating Profile Data

1. Edit `config/personals.py` with your information:
```python
# Basic Information
first_name = "Your Name"
last_name = "Your Last Name"
phone_number = "1234567890"
current_city = "Your City"
# ... etc
```

2. Run: `python setup/update_extension.py`
3. Click **Refresh from Project Config** in extension

## Troubleshooting

### Extension shows old data
- Make sure you clicked "Refresh from Project Config"
- OR manually clear storage (see step 2 above)
- Then close and reopen the popup

### Config file not found
- Ensure `extension/user_config.json` exists
- Run `python setup/update_extension.py` to generate it

### Extension not auto-filling
1. Check the extension is enabled
2. Make sure you're on a supported job site (LinkedIn, Indeed, etc.)
3. Check browser console for errors

### Fields are empty
- Verify `config/personals.py` has correct data
- Run the update script again
- Use "Refresh from Project Config" button

## Auto-Load Behavior

The extension automatically loads config in these cases:
1. **First install**: Loads from `user_config.json` automatically
2. **Empty storage**: If Chrome storage is cleared, loads from config
3. **Manual refresh**: When you click "Refresh from Project Config"

After the first load, data is stored in Chrome storage and persists across sessions.

## File Changes Workflow

```
Edit config files → Run update_extension.py → Refresh extension → Verify
```

That's it! Your extension will now use the updated configuration.
