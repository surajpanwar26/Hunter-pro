
// PASTE THIS IN BROWSER CONSOLE TO CLEAR EXTENSION STORAGE
// =========================================================
// 1. Open extension popup
// 2. Right-click > Inspect
// 3. Paste this in Console tab
// 4. Refresh extension popup

chrome.storage.sync.clear(function() {
    console.log('[+] Sync storage cleared');
});

chrome.storage.local.clear(function() {
    console.log('[+] Local storage cleared');
});

console.log('Storage cleared! Refresh the extension popup to reload from user_config.json');
