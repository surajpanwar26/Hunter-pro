/**
 * Universal Job Auto-Fill Extension - Background Service Worker
 * Handles extension lifecycle, notifications, API relay, and cross-script communication
 */

// ================================
// CONSTANTS
// ================================
const SETTINGS_KEY = 'universalAutoFillSettings';
const API_BASE_URL = 'http://127.0.0.1:5001';

// ================================
// INSTALLATION HANDLER
// ================================
chrome.runtime.onInstalled.addListener((details) => {
    console.log('LinkedIn AutoFill Extension installed:', details.reason);
    
    if (details.reason === 'install') {
        // First install - set default settings
        chrome.storage.sync.set({
            [SETTINGS_KEY]: {
                autoDetect: true,
                autoFill: false,
                showNotifications: true,
                debugMode: false,
                fillDelay: 100,
                maxRetries: 3
            }
        });
        
        // Open welcome/setup page
        chrome.tabs.create({
            url: 'popup.html#setup'
        });
    }
    
    // Create context menu item (on install AND update)
    chrome.contextMenus.create({
        id: 'fillForm',
        title: 'Auto-Fill This Form',
        contexts: ['page'],
        documentUrlPatterns: [
            '*://*.linkedin.com/*',
            '*://*.indeed.com/*',
            '*://*.glassdoor.com/*',
            '*://*.greenhouse.io/*',
            '*://*.lever.co/*',
            '*://*.workday.com/*',
            '*://*.myworkday.com/*'
        ]
    });
});

// ================================
// MESSAGE HANDLING
// ================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Background received message:', message, 'from:', sender);
    
    switch (message.action) {
        case 'easyApplyDetected':
            handleEasyApplyDetected(sender.tab);
            break;
            
        case 'showNotification':
            showNotification(message.title, message.body, message.iconUrl);
            break;
            
        case 'getSettings':
            chrome.storage.sync.get(SETTINGS_KEY).then(result => {
                sendResponse({ settings: result[SETTINGS_KEY] || {} });
            });
            return true; // Async response
            
        case 'apiRelay':
            // Relay requests from content scripts to local API server
            handleAPIRelay(message.endpoint, message.data)
                .then(result => sendResponse(result))
                .catch(err => sendResponse({ error: err.message }));
            return true; // Async response
            
        default:
            console.log('Unknown action:', message.action);
    }
});

// ================================
// EASY APPLY DETECTION
// ================================
async function handleEasyApplyDetected(tab) {
    try {
        // Get settings
        const result = await chrome.storage.sync.get(SETTINGS_KEY);
        const settings = result[SETTINGS_KEY] || {};
        
        // Auto-fill if enabled
        if (settings.autoFill) {
            // Small delay to ensure modal is fully loaded
            await sleep(500);
            
            chrome.tabs.sendMessage(tab.id, { action: 'fillForm' }, response => {
                if (response && response.success) {
                    if (settings.showNotifications) {
                        showNotification(
                            'Form Auto-Filled',
                            `Filled ${response.filled} of ${response.total} fields`,
                            'icons/icon48.png'
                        );
                    }
                }
            });
        } else if (settings.showNotifications) {
            // Just notify that Easy Apply was detected
            showNotification(
                'Easy Apply Detected',
                'Click the extension icon to auto-fill',
                'icons/icon48.png'
            );
        }
        
        // Update badge to show Easy Apply detected
        chrome.action.setBadgeText({ text: '!', tabId: tab.id });
        chrome.action.setBadgeBackgroundColor({ color: '#0073b1' });
        
        // Clear badge after 3 seconds
        setTimeout(() => {
            chrome.action.setBadgeText({ text: '', tabId: tab.id });
        }, 3000);
        
    } catch (e) {
        console.error('Error handling Easy Apply detection:', e);
    }
}

// ================================
// NOTIFICATIONS
// ================================
function showNotification(title, body, iconUrl = 'icons/icon48.png') {
    chrome.notifications.create({
        type: 'basic',
        iconUrl: iconUrl,
        title: title,
        message: body,
        priority: 1
    }, (notificationId) => {
        // Auto-close after 5 seconds
        setTimeout(() => {
            chrome.notifications.clear(notificationId);
        }, 5000);
    });
}

// ================================
// ================================
// CONTEXT MENU CLICK HANDLER
// ================================

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'fillForm') {
        chrome.tabs.sendMessage(tab.id, { action: 'fillForm' }, response => {
            if (response && response.success) {
                showNotification(
                    'Form Filled',
                    `Filled ${response.filled} of ${response.total} fields`
                );
            }
        });
    }
});

// ================================
// TAB UPDATES
// ================================
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // Only act on complete load of LinkedIn pages
    if (changeInfo.status === 'complete' && tab.url && tab.url.includes('linkedin.com')) {
        // Clear any existing badge
        chrome.action.setBadgeText({ text: '', tabId: tabId });
    }
});

// ================================
// KEYBOARD SHORTCUTS
// ================================
// Only register if commands API is available (requires commands in manifest)
if (chrome.commands && chrome.commands.onCommand) {
    chrome.commands.onCommand.addListener((command, tab) => {
        console.log('Command received:', command);
        
        if (command === 'fill-form') {
            chrome.tabs.sendMessage(tab.id, { action: 'fillForm' }, response => {
                if (response && response.success) {
                    showNotification(
                        'Form Filled',
                        `Filled ${response.filled} of ${response.total} fields`
                    );
                }
            });
        }
    });
} else {
    console.log('chrome.commands API not available - keyboard shortcuts disabled');
}

// ================================
// UTILITY FUNCTIONS
// ================================
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ================================
// API RELAY
// ================================
async function handleAPIRelay(endpoint, data) {
    const url = `${API_BASE_URL}${endpoint}`;
    const opts = {
        method: data ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) opts.body = JSON.stringify(data);
    
    try {
        const response = await fetch(url, opts);
        if (!response.ok) {
            const errBody = await response.json().catch(() => ({}));
            return { error: errBody.error || `API returned ${response.status}` };
        }
        return await response.json();
    } catch (e) {
        return { error: `API server unreachable: ${e.message}` };
    }
}

// ================================
// STARTUP
// ================================
console.log('Universal Job AutoFill Pro - background service worker started');
