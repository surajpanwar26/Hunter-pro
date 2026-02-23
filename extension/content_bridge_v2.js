/**
 * AI Hunter pro Extension - V2 Content Bridge
 *
 * Loads before the legacy universal content script.
 * Provides a lightweight compatibility and observability bridge.
 */

(function initV2ContentBridge() {
    if (window.__AI_HUNTER_V2_BRIDGE__) {
        return;
    }

    const bridge = {
        version: '2.0.0',
        initializedAt: Date.now(),
        runtime: 'mv3-content',
    };

    window.__AI_HUNTER_V2_BRIDGE__ = bridge;

    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
        if (message && message.action === 'v2Health') {
            sendResponse({ ok: true, bridge });
            return true;
        }

        if (message && message.action === 'ping') {
            sendResponse({ pong: true, bridgeVersion: bridge.version });
            return true;
        }

        return false;
    });
})();
