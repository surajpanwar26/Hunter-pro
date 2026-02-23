const PROVIDER_KEY = 'aiProviderConfig';

const DEFAULT_PROVIDER = {
    provider: 'groq',
    apiUrl: 'https://api.groq.com/openai/v1',
    model: 'llama-3.3-70b-versatile',
    preloaded: true
};

const isSidePanelView = new URLSearchParams(window.location.search).get('view') === 'sidepanel';

async function ensureProviderDefaults() {
    const existing = await chrome.storage.local.get(PROVIDER_KEY);
    const merged = {
        ...DEFAULT_PROVIDER,
        ...(existing[PROVIDER_KEY] || {})
    };
    await chrome.storage.local.set({ [PROVIDER_KEY]: merged });
}

async function checkBridgeHealth() {
    const statusNode = document.getElementById('v2Status');
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.id) {
            statusNode.textContent = 'No Active Tab';
            return;
        }

        const response = await chrome.tabs.sendMessage(tab.id, { action: 'v2Health' });
        if (response && response.ok) {
            statusNode.textContent = 'Connected';
            statusNode.style.color = '#86efac';
        } else {
            statusNode.textContent = 'Partial';
            statusNode.style.color = '#facc15';
        }
    } catch {
        statusNode.textContent = 'Disconnected';
        statusNode.style.color = '#f87171';
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    if (isSidePanelView) {
        document.documentElement.classList.add('sidepanel-mode');
        document.body.classList.add('sidepanel-mode');
    }

    const legacyPopup = document.getElementById('legacyPopup');
    if (legacyPopup) {
        legacyPopup.src = isSidePanelView ? 'popup.html?view=sidepanel' : 'popup.html';
    }

    await ensureProviderDefaults();
    await checkBridgeHealth();
});
