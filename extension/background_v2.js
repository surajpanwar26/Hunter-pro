/**
 * AI Hunter pro Extension - V2 Background Entry
 *
 * Responsibilities:
 * 1) Enforce V2 default settings and provider defaults.
 * 2) Keep full backward compatibility by loading legacy background worker.
 */

const V2_SETTINGS_KEY = 'universalAutoFillSettings';
const V2_PROVIDER_KEY = 'aiProviderConfig';
const V2_TELEMETRY_KEY = 'v2TelemetryEvents';

const V2_DEFAULT_SETTINGS = {
    autoDetect: true,
    autoFill: false,
    showNotifications: true,
    debugMode: false,
    fillDelay: 100,
    maxRetries: 3,
    enableLearning: true,
    syncToConfig: true,
    detectionMode: 'universal',
    extensionEnabled: true
};

const V2_DEFAULT_PROVIDER = {
    provider: 'groq',
    apiUrl: 'https://api.groq.com/openai/v1',
    model: 'llama-3.3-70b-versatile',
    preloaded: true
};

async function mergeSyncDefaults() {
    const current = await chrome.storage.sync.get(V2_SETTINGS_KEY);
    const existing = current[V2_SETTINGS_KEY] || {};
    const merged = { ...V2_DEFAULT_SETTINGS, ...existing };
    await chrome.storage.sync.set({ [V2_SETTINGS_KEY]: merged });
}

async function mergeLocalProviderDefaults() {
    const current = await chrome.storage.local.get(V2_PROVIDER_KEY);
    const existing = current[V2_PROVIDER_KEY] || {};
    const merged = { ...V2_DEFAULT_PROVIDER, ...existing };
    await chrome.storage.local.set({ [V2_PROVIDER_KEY]: merged });
}

async function bootstrapV2Defaults() {
    try {
        await Promise.all([mergeSyncDefaults(), mergeLocalProviderDefaults()]);
    } catch (e) {
        console.warn('V2 default bootstrap failed:', e);
    }
}

chrome.runtime.onInstalled.addListener(() => {
    bootstrapV2Defaults();
});

bootstrapV2Defaults();

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.action === 'openSidePanel') {
        (async () => {
            try {
                if (!chrome.sidePanel || typeof chrome.sidePanel.open !== 'function') {
                    sendResponse({ success: false, error: 'Side panel API is not available in this browser build' });
                    return;
                }

                const tabId = Number(message?.tabId);
                if (!tabId) {
                    sendResponse({ success: false, error: 'Missing active tab for side panel' });
                    return;
                }

                await chrome.sidePanel.setOptions({
                    tabId,
                    enabled: true,
                    path: 'sidepanel.html'
                });
                await chrome.sidePanel.open({ tabId });
                sendResponse({ success: true });
            } catch (e) {
                sendResponse({ success: false, error: String(e?.message || e) });
            }
        })();
        return true;
    }

    if (!message || message.action !== 'telemetryEvent') return false;

    (async () => {
        try {
            const payload = {
                type: String(message.type || 'unknown'),
                data: message.data || {},
                ts: Date.now(),
            };
            const current = await chrome.storage.local.get(V2_TELEMETRY_KEY);
            const existing = Array.isArray(current[V2_TELEMETRY_KEY]) ? current[V2_TELEMETRY_KEY] : [];
            const next = [...existing, payload].slice(-200);
            await chrome.storage.local.set({ [V2_TELEMETRY_KEY]: next });
            sendResponse({ success: true });
        } catch (e) {
            sendResponse({ success: false, error: String(e?.message || e) });
        }
    })();

    return true;
});

importScripts('background.js');
