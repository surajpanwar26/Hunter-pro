/**
 * Universal Job Auto-Fill Extension - Popup Script
 * Handles popup UI interactions, JD detection, resume tailoring, and AI learning
 */

// ================================
// UTILITY: HTML Sanitization
// ================================
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

// ================================
// CONSTANTS
// ================================
const STORAGE_KEY = 'universalAutoFillData';
const SETTINGS_KEY = 'universalAutoFillSettings';
const HISTORY_KEY = 'universalAutoFillHistory';
const LEARNED_KEY = 'universalAutoFillLearned';

// Portal detection patterns
const PORTAL_PATTERNS = {
    linkedin: /linkedin\.com/i,
    indeed: /indeed\.com/i,
    glassdoor: /glassdoor\.com/i,
    workday: /workday\.com|myworkday\.com/i,
    greenhouse: /greenhouse\.io/i,
    lever: /lever\.co|jobs\.lever\.co/i,
    smartrecruiters: /smartrecruiters\.com/i,
    bamboohr: /bamboohr\.com/i,
    icims: /icims\.com/i,
    taleo: /taleo\.net/i,
    successfactors: /successfactors\.com/i,
    jobvite: /jobvite\.com/i,
    ashby: /ashbyhq\.com/i,
    breezy: /breezy\.hr/i,
    recruitee: /recruitee\.com/i,
    jazz: /jazz\.co/i,
    wellfound: /wellfound\.com|angel\.co/i,
    monster: /monster\.com/i,
    ziprecruiter: /ziprecruiter\.com/i,
    careerbuilder: /careerbuilder\.com/i,
    dice: /dice\.com/i
};

// ================================
// DOM ELEMENTS
// ================================
const elements = {
    // Quick Actions
    btnFillForm: document.getElementById('btnFillForm'),
    btnAnalyze: document.getElementById('btnAnalyze'),
    statusBadge: document.getElementById('statusBadge'),
    
    // Portal Detection
    portalBanner: document.getElementById('portalBanner'),
    portalName: document.getElementById('portalName'),
    portalStatus: document.getElementById('portalStatus'),
    
    // JD Section
    jdSection: document.getElementById('jdSection'),
    btnDetectJD: document.getElementById('btnDetectJD'),
    jdContent: document.getElementById('jdContent'),
    jdPreview: document.getElementById('jdPreview'),
    jdSkills: document.getElementById('jdSkills'),
    skillTags: document.getElementById('skillTags'),
    jdActions: document.getElementById('jdActions'),
    btnTailorResume: document.getElementById('btnTailorResume'),
    
    // ATS Section
    atsSection: document.getElementById('atsSection'),
    atsScoreRing: document.getElementById('atsScoreRing'),
    atsScoreValue: document.getElementById('atsScoreValue'),
    matchScoreRing: document.getElementById('matchScoreRing'),
    matchScoreValue: document.getElementById('matchScoreValue'),
    resumeActions: document.getElementById('resumeActions'),
    btnPreviewResume: document.getElementById('btnPreviewResume'),
    btnDownloadDocx: document.getElementById('btnDownloadDocx'),
    btnDownloadPdf: document.getElementById('btnDownloadPdf'),
    
    // Tabs
    tabs: document.querySelectorAll('.tab'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    
    // Profile Form
    profileForm: document.getElementById('profileForm'),
    firstName: document.getElementById('firstName'),
    lastName: document.getElementById('lastName'),
    email: document.getElementById('email'),
    phone: document.getElementById('phone'),
    currentCity: document.getElementById('currentCity'),
    currentCompany: document.getElementById('currentCompany'),
    currentTitle: document.getElementById('currentTitle'),
    yearsExperience: document.getElementById('yearsExperience'),
    expectedSalary: document.getElementById('expectedSalary'),
    noticePeriod: document.getElementById('noticePeriod'),
    linkedinUrl: document.getElementById('linkedinUrl'),
    portfolioUrl: document.getElementById('portfolioUrl'),
    githubUrl: document.getElementById('githubUrl'),
    workAuthorization: document.getElementById('workAuthorization'),
    sponsorship: document.getElementById('sponsorship'),
    remoteWork: document.getElementById('remoteWork'),
    willingToRelocate: document.getElementById('willingToRelocate'),
    degree: document.getElementById('degree'),
    major: document.getElementById('major'),
    school: document.getElementById('school'),
    graduationYear: document.getElementById('graduationYear'),
    
    // Settings
    autoDetect: document.getElementById('autoDetect'),
    autoFill: document.getElementById('autoFill'),
    showNotifications: document.getElementById('showNotifications'),
    debugMode: document.getElementById('debugMode'),
    fillDelay: document.getElementById('fillDelay'),
    maxRetries: document.getElementById('maxRetries'),
    btnResetSettings: document.getElementById('btnResetSettings'),
    
    // Learning Tab
    learnedFieldsCount: document.getElementById('learnedFieldsCount'),
    portalsUsed: document.getElementById('portalsUsed'),
    learnedAccuracy: document.getElementById('learnedAccuracy'),
    learnedFieldsList: document.getElementById('learnedFieldsList'),
    learnedSearchInput: document.getElementById('learnedSearchInput'),
    enableLearning: document.getElementById('enableLearning'),
    syncToConfig: document.getElementById('syncToConfig'),
    btnImportLearned: document.getElementById('btnImportLearned'),
    btnExportLearned: document.getElementById('btnExportLearned'),
    btnClearLearned: document.getElementById('btnClearLearned'),
    learnedImportFile: document.getElementById('learnedImportFile'),
    
    // History
    totalFilled: document.getElementById('totalFilled'),
    fieldsFilled: document.getElementById('fieldsFilled'),
    timeSaved: document.getElementById('timeSaved'),
    historyList: document.getElementById('historyList'),
    btnClearHistory: document.getElementById('btnClearHistory'),
    
    // Modals
    analysisModal: document.getElementById('analysisModal'),
    analysisContent: document.getElementById('analysisContent'),
    closeAnalysis: document.getElementById('closeAnalysis'),
    resumeModal: document.getElementById('resumeModal'),
    resumeContent: document.getElementById('resumeContent'),
    closeResume: document.getElementById('closeResume'),
    btnModalDownloadDocx: document.getElementById('btnModalDownloadDocx'),
    btnModalDownloadPdf: document.getElementById('btnModalDownloadPdf'),
    btnUseResume: document.getElementById('btnUseResume'),
    
    // Loading
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
    
    // Toast
    toast: document.getElementById('toast')
};

// ================================
// API BRIDGE CONFIGURATION
// ================================
const API_BASE_URL = 'http://127.0.0.1:5001';
let apiServerAvailable = false;

/**
 * Call the local Python API server.
 * Falls back to client-side scoring if server unavailable.
 */
async function callAPI(endpoint, data = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    const opts = {
        method: data ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) opts.body = JSON.stringify(data);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    opts.signal = controller.signal;

    try {
        const response = await fetch(url, opts);
        clearTimeout(timeoutId);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.error || `API ${response.status}`);
        }
        return await response.json();
    } catch (e) {
        clearTimeout(timeoutId);
        if (e.name === 'AbortError') throw new Error('API request timed out (30s)');
        throw e;
    }
}

/**
 * Check if the local API server is running.
 */
async function checkAPIServer() {
    try {
        const result = await callAPI('/api/health');
        apiServerAvailable = result.status === 'ok';
        return apiServerAvailable;
    } catch {
        apiServerAvailable = false;
        return false;
    }
}

// ================================
// STATE
// ================================
let userData = {};
let masterResumeText = null;
let masterResumeFilename = null;
let settings = {
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
let history = {
    totalFilled: 0,
    fieldsFilled: 0,
    entries: []
};
let learnedFields = {};
let currentPortal = null;
let currentJD = null;
let currentTailoredResume = null;

// ================================
// UTILITY FUNCTIONS
// ================================
function showToast(message, type = 'success') {
    const toast = elements.toast;
    toast.querySelector('.toast-message').textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

function updateStatus(status, text) {
    const badge = elements.statusBadge;
    badge.className = `status-badge ${status}`;
    badge.querySelector('.status-text').textContent = text;
}

function showLoading(message = 'Processing...') {
    if (elements.loadingOverlay) {
        elements.loadingText.textContent = message;
        elements.loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    if (elements.loadingOverlay) {
        elements.loadingOverlay.style.display = 'none';
    }
}

function detectPortal(url) {
    for (const [portal, pattern] of Object.entries(PORTAL_PATTERNS)) {
        if (pattern.test(url)) {
            return portal;
        }
    }
    return 'unknown';
}

function getPortalDisplayName(portal) {
    const names = {
        linkedin: 'LinkedIn',
        indeed: 'Indeed',
        glassdoor: 'Glassdoor',
        workday: 'Workday',
        greenhouse: 'Greenhouse',
        lever: 'Lever',
        smartrecruiters: 'SmartRecruiters',
        bamboohr: 'BambooHR',
        icims: 'iCIMS',
        taleo: 'Taleo',
        successfactors: 'SuccessFactors',
        jobvite: 'Jobvite',
        ashby: 'Ashby',
        breezy: 'Breezy HR',
        recruitee: 'Recruitee',
        jazz: 'JazzHR',
        wellfound: 'Wellfound',
        monster: 'Monster',
        ziprecruiter: 'ZipRecruiter',
        careerbuilder: 'CareerBuilder',
        dice: 'Dice',
        unknown: 'Job Portal'
    };
    return names[portal] || 'Job Portal';
}

async function getActiveTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return tab;
}

/**
 * Inject content script into tab if not already loaded
 * @param {number} tabId - Tab ID to inject into
 * @returns {Promise<boolean>} - True if injection succeeded or was already loaded
 */
async function ensureContentScriptLoaded(tabId) {
    try {
        // Try a ping to check if content script is loaded
        return await new Promise((resolve) => {
            chrome.tabs.sendMessage(tabId, { action: 'ping' }, response => {
                if (chrome.runtime.lastError) {
                    // Content script not loaded, try to inject it
                    chrome.scripting.executeScript({
                        target: { tabId: tabId },
                        files: ['universal_content.js']
                    }).then(() => {
                        console.log('Content script injected successfully');
                        // Give it a moment to initialize
                        setTimeout(() => resolve(true), 100);
                    }).catch(err => {
                        console.error('Failed to inject content script:', err);
                        resolve(false);
                    });
                } else {
                    // Content script already loaded
                    resolve(true);
                }
            });
        });
    } catch (e) {
        console.error('Error checking content script:', e);
        return false;
    }
}

async function sendMessageToContent(action, data = {}) {
    const tab = await getActiveTab();
    if (!tab) {
        throw new Error('No active tab found');
    }
    
    // Check if we're on a supported page, or try to inject content script
    const isContentLoaded = await ensureContentScriptLoaded(tab.id);
    if (!isContentLoaded) {
        throw new Error('This page is not supported. Please navigate to a job portal.');
    }
    
    return new Promise((resolve, reject) => {
        chrome.tabs.sendMessage(tab.id, { action, ...data }, response => {
            if (chrome.runtime.lastError) {
                const errorMsg = chrome.runtime.lastError.message;
                // Provide user-friendly error message
                if (errorMsg.includes('receiving end') || errorMsg.includes('Could not establish')) {
                    reject(new Error('Please refresh the page and try again. The extension needs to reload.'));
                } else {
                    reject(new Error(errorMsg));
                }
            } else {
                resolve(response);
            }
        });
    });
}

// ================================
// STORAGE FUNCTIONS
// ================================

/**
 * Auto-load config from bundled user_config.json
 * This reads the config generated by config_loader.py
 */
async function loadBundledConfig() {
    try {
        // Try to fetch the bundled config file
        const response = await fetch(chrome.runtime.getURL('user_config.json'));
        if (!response.ok) {
            console.log('No bundled config file found');
            return null;
        }
        
        const config = await response.json();
        console.log('✓ Loaded bundled user_config.json');
        
        // Map config to userData format
        const profile = config.profile || {};
        const questions = config.questions || {};
        
        return {
            firstName: profile.firstName || '',
            lastName: profile.lastName || '',
            middleName: profile.middleName || '',
            email: profile.email || '',
            phone: profile.phone || '',
            currentCity: profile.currentCity || '',
            street: profile.street || '',
            state: profile.state || '',
            zipcode: profile.zipcode || '',
            country: profile.country || '',
            currentCompany: profile.recentEmployer || questions.recentEmployer || '',
            currentTitle: profile.linkedinHeadline || questions.linkedinHeadline || '',
            yearsExperience: profile.yearsExperience || questions.yearsExperience || '',
            expectedSalary: profile.expectedSalary || questions.desiredSalary || '',
            currentCtc: profile.currentCtc || questions.currentCtc || '',
            noticePeriod: profile.noticePeriod || questions.noticePeriod || '',
            linkedinUrl: profile.linkedinUrl || questions.linkedin || '',
            portfolioUrl: profile.portfolioUrl || questions.website || '',
            githubUrl: profile.githubUrl || '',
            ethnicity: profile.ethnicity || '',
            gender: profile.gender || '',
            disabilityStatus: profile.disabilityStatus || '',
            veteranStatus: profile.veteranStatus || '',
            requireVisa: profile.requireVisa || questions.requireVisa || '',
            usCitizenship: profile.usCitizenship || questions.usCitizenship || '',
            coverLetter: profile.coverLetter || questions.coverLetter || '',
            linkedinSummary: profile.linkedinSummary || questions.linkedinSummary || '',
            userInformationAll: questions.userInformationAll || '',
            confidenceLevel: profile.confidenceLevel || questions.confidenceLevel || '75',
            // Store raw config for reference
            _rawConfig: config,
            _autoLoaded: true
        };
        
        // Apply extension settings from Python config if available
        const configSettings = config.settings || {};
        if (Object.keys(configSettings).length > 0) {
            if (configSettings.extensionEnabled === false) {
                console.log('⚠ Extension is disabled in Python config');
            }
            // Merge relevant settings into the extension settings object
            if (configSettings.autoSync !== undefined) settings.syncToConfig = configSettings.autoSync;
            if (configSettings.enableLearning !== undefined) settings.enableLearning = configSettings.enableLearning;
            if (configSettings.detectionMode !== undefined) settings.detectionMode = configSettings.detectionMode;
            // Save merged settings to Chrome storage
            await saveSettings();
            console.log('✓ Applied extension settings from Python config');
        }
        
        return bundledData;
    } catch (e) {
        console.log('Could not load bundled config:', e.message);
        return null;
    }
}

async function loadUserData() {
    try {
        const result = await chrome.storage.sync.get(STORAGE_KEY);
        if (result[STORAGE_KEY] && Object.keys(result[STORAGE_KEY]).length > 0) {
            userData = result[STORAGE_KEY];
            populateProfileForm();
            console.log('✓ Loaded profile from Chrome storage');
        } else {
            // First time - try to auto-load bundled config
            console.log('No profile data found, attempting to auto-load bundled config...');
            
            const bundledConfig = await loadBundledConfig();
            if (bundledConfig) {
                userData = bundledConfig;
                populateProfileForm();
                await saveUserData();  // Save to storage for future loads
                showToast('✓ Auto-loaded profile from project config!', 'success');
                console.log('✓ Auto-loaded and saved bundled config');
            } else {
                showToast('Welcome! Import your config or fill in your profile to get started.', 'info');
            }
        }
    } catch (e) {
        console.error('Error loading user data:', e);
    }
}

async function saveUserData() {
    try {
        await chrome.storage.sync.set({ [STORAGE_KEY]: userData });
        // Also update content script
        try {
            await sendMessageToContent('updateUserData', { data: userData });
        } catch (e) {
            // Content script may not be loaded
        }
    } catch (e) {
        console.error('Error saving user data:', e);
        throw e;
    }
}

async function loadSettings() {
    try {
        const result = await chrome.storage.sync.get(SETTINGS_KEY);
        if (result[SETTINGS_KEY]) {
            settings = { ...settings, ...result[SETTINGS_KEY] };
            populateSettingsForm();
        }
    } catch (e) {
        console.error('Error loading settings:', e);
    }
}

async function saveSettings() {
    try {
        await chrome.storage.sync.set({ [SETTINGS_KEY]: settings });
    } catch (e) {
        console.error('Error saving settings:', e);
        throw e;
    }
}

async function loadHistory() {
    try {
        const result = await chrome.storage.local.get(HISTORY_KEY);
        if (result[HISTORY_KEY]) {
            history = result[HISTORY_KEY];
            updateHistoryUI();
        }
    } catch (e) {
        console.error('Error loading history:', e);
    }
}

async function saveHistory() {
    try {
        await chrome.storage.local.set({ [HISTORY_KEY]: history });
    } catch (e) {
        console.error('Error saving history:', e);
    }
}

// ================================
// FORM POPULATION
// ================================
function populateProfileForm() {
    elements.firstName.value = userData.firstName || '';
    elements.lastName.value = userData.lastName || '';
    elements.email.value = userData.email || '';
    elements.phone.value = userData.phone || '';
    elements.currentCity.value = userData.currentCity || '';
    elements.currentCompany.value = userData.currentCompany || '';
    elements.currentTitle.value = userData.currentTitle || '';
    elements.yearsExperience.value = userData.yearsExperience || '';
    elements.expectedSalary.value = userData.expectedSalary || '';
    elements.noticePeriod.value = userData.noticePeriod || '';
    elements.linkedinUrl.value = userData.linkedinUrl || '';
    elements.portfolioUrl.value = userData.portfolioUrl || '';
    elements.githubUrl.value = userData.githubUrl || '';
    elements.workAuthorization.value = userData.workAuthorization || 'yes';
    elements.sponsorship.value = userData.sponsorship || 'no';
    elements.remoteWork.value = userData.remoteWork || 'yes';
    elements.willingToRelocate.value = userData.willingToRelocate || 'yes';
    
    if (userData.education) {
        elements.degree.value = userData.education.degree || '';
        elements.major.value = userData.education.major || '';
        elements.school.value = userData.education.school || '';
        elements.graduationYear.value = userData.education.graduationYear || '';
    }
}

function populateSettingsForm() {
    elements.autoDetect.checked = settings.autoDetect;
    elements.autoFill.checked = settings.autoFill;
    elements.showNotifications.checked = settings.showNotifications;
    elements.debugMode.checked = settings.debugMode;
    elements.fillDelay.value = settings.fillDelay;
    elements.maxRetries.value = settings.maxRetries;
}

function collectProfileData() {
    return {
        firstName: elements.firstName.value.trim(),
        lastName: elements.lastName.value.trim(),
        email: elements.email.value.trim(),
        phone: elements.phone.value.trim(),
        currentCity: elements.currentCity.value.trim(),
        currentCompany: elements.currentCompany.value.trim(),
        currentTitle: elements.currentTitle.value.trim(),
        yearsExperience: elements.yearsExperience.value.trim(),
        expectedSalary: elements.expectedSalary.value.trim(),
        noticePeriod: elements.noticePeriod.value.trim(),
        linkedinUrl: elements.linkedinUrl.value.trim(),
        portfolioUrl: elements.portfolioUrl.value.trim(),
        githubUrl: elements.githubUrl.value.trim(),
        workAuthorization: elements.workAuthorization.value,
        sponsorship: elements.sponsorship.value,
        remoteWork: elements.remoteWork.value,
        willingToRelocate: elements.willingToRelocate.value,
        education: {
            degree: elements.degree.value.trim(),
            major: elements.major.value.trim(),
            school: elements.school.value.trim(),
            graduationYear: elements.graduationYear.value.trim()
        },
        skills: userData.skills || [],
        customAnswers: userData.customAnswers || {}
    };
}

function collectSettings() {
    return {
        autoDetect: elements.autoDetect.checked,
        autoFill: elements.autoFill.checked,
        showNotifications: elements.showNotifications.checked,
        debugMode: elements.debugMode.checked,
        fillDelay: parseInt(elements.fillDelay.value) || 100,
        maxRetries: parseInt(elements.maxRetries.value) || 3
    };
}

// ================================
// HISTORY UI
// ================================
function updateHistoryUI() {
    elements.totalFilled.textContent = history.totalFilled || 0;
    elements.fieldsFilled.textContent = history.fieldsFilled || 0;
    
    // Estimate time saved (2 minutes per form)
    const timeSaved = Math.round((history.totalFilled || 0) * 2);
    elements.timeSaved.textContent = timeSaved;
    
    // Update history list
    if (history.entries && history.entries.length > 0) {
        elements.historyList.innerHTML = history.entries.slice(-10).reverse().map(entry => `
            <div class="history-item">
                <div class="history-info">
                    <span class="history-title">${escapeHtml(entry.jobTitle || 'Unknown Job')}</span>
                    <span class="history-company">${escapeHtml(entry.company || 'Unknown Company')}</span>
                </div>
                <div class="history-meta">
                    <span class="history-fields">${parseInt(entry.filled) || 0} fields</span>
                    <span class="history-time">${escapeHtml(formatTime(entry.timestamp))}</span>
                </div>
            </div>
        `).join('');
    }
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
}

function addHistoryEntry(result) {
    history.totalFilled++;
    history.fieldsFilled += result.filled || 0;
    
    history.entries.push({
        timestamp: Date.now(),
        filled: result.filled || 0,
        total: result.total || 0,
        jobTitle: result.jobTitle || 'Unknown Job',
        company: result.company || 'Unknown Company'
    });
    
    // Keep only last 100 entries
    if (history.entries.length > 100) {
        history.entries = history.entries.slice(-100);
    }
    
    saveHistory();
    updateHistoryUI();
}

// ================================
// ANALYSIS MODAL
// ================================
function showAnalysisModal(analysis) {
    const content = elements.analysisContent;
    
    let html = '<div class="analysis-sections">';
    
    // Detected fields
    html += `
        <div class="analysis-section">
            <h3>✅ Detected Fields (${analysis.detected.length})</h3>
            ${analysis.detected.length > 0 ? `
                <ul class="field-list">
                    ${analysis.detected.map(f => `
                        <li>
                            <span class="field-label">${f.label || 'Unknown'}</span>
                            <span class="field-type">${f.fieldType}</span>
                        </li>
                    `).join('')}
                </ul>
            ` : '<p class="empty">No fields detected</p>'}
        </div>
    `;
    
    // Undetected fields
    if (analysis.undetected.length > 0) {
        html += `
            <div class="analysis-section">
                <h3>⚠️ Unknown Fields (${analysis.undetected.length})</h3>
                <ul class="field-list warning">
                    ${analysis.undetected.map(f => `
                        <li>
                            <span class="field-label">${f.label || 'Unknown'}</span>
                            <span class="field-type">${f.type}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }
    
    // Already filled
    if (analysis.filled.length > 0) {
        html += `
            <div class="analysis-section">
                <h3>📝 Already Filled (${analysis.filled.length})</h3>
                <ul class="field-list filled">
                    ${analysis.filled.map(f => `
                        <li>
                            <span class="field-label">${f.label || 'Unknown'}</span>
                            <span class="field-value">${truncate(f.currentValue, 20)}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }
    
    html += '</div>';
    
    content.innerHTML = html;
    elements.analysisModal.classList.add('show');
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

// ================================
// EVENT HANDLERS
// ================================

// Tab switching
elements.tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        // Update active tab
        elements.tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update active panel
        const targetId = tab.getAttribute('data-tab');
        elements.tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.id === targetId);
        });
    });
});

// Fill Form button
elements.btnFillForm.addEventListener('click', async () => {
    try {
        updateStatus('loading', 'Filling...');
        elements.btnFillForm.disabled = true;
        
        const response = await sendMessageToContent('fillForm');
        
        if (response.success) {
            updateStatus('success', 'Filled!');
            showToast(`Filled ${response.filled} of ${response.total} fields`);
            addHistoryEntry(response);
        } else {
            throw new Error(response.error || 'Failed to fill form');
        }
    } catch (e) {
        updateStatus('error', 'Error');
        showToast(e.message || 'Failed to fill form', 'error');
    } finally {
        elements.btnFillForm.disabled = false;
        setTimeout(() => updateStatus('ready', 'Ready'), 2000);
    }
});

// Analyze button
elements.btnAnalyze.addEventListener('click', async () => {
    try {
        elements.btnAnalyze.disabled = true;
        
        const response = await sendMessageToContent('analyzeFields');
        
        if (response.success) {
            showAnalysisModal(response.analysis);
        } else {
            throw new Error(response.error || 'Failed to analyze');
        }
    } catch (e) {
        showToast(e.message || 'Failed to analyze form', 'error');
    } finally {
        elements.btnAnalyze.disabled = false;
    }
});

// Profile form submit
elements.profileForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    try {
        userData = collectProfileData();
        await saveUserData();
        showToast('Profile saved successfully!');
    } catch (e) {
        showToast('Failed to save profile', 'error');
    }
});

// Settings change handlers
[elements.autoDetect, elements.autoFill, elements.showNotifications, elements.debugMode].forEach(el => {
    el.addEventListener('change', async () => {
        settings = collectSettings();
        await saveSettings();
    });
});

[elements.fillDelay, elements.maxRetries].forEach(el => {
    el.addEventListener('change', async () => {
        settings = collectSettings();
        await saveSettings();
    });
});

// Reset settings
elements.btnResetSettings.addEventListener('click', async () => {
    settings = {
        autoDetect: true,
        autoFill: false,
        showNotifications: true,
        debugMode: false,
        fillDelay: 100,
        maxRetries: 3
    };
    
    populateSettingsForm();
    await saveSettings();
    showToast('Settings reset to defaults');
});

// Refresh from project config - clears storage and reloads from user_config.json
const btnRefreshFromConfig = document.getElementById('btnRefreshFromConfig');
if (btnRefreshFromConfig) {
    btnRefreshFromConfig.addEventListener('click', async () => {
        if (confirm('This will clear your extension storage and reload from the project config (user_config.json).\n\nMake sure you have run config_loader.py first to generate the config.\n\nContinue?')) {
            try {
                showLoading('Clearing storage and reloading...');
                
                // Clear all storage
                await chrome.storage.sync.clear();
                await chrome.storage.local.clear();
                console.log('✓ Storage cleared');
                
                // Reset local state
                userData = {};
                settings = {
                    autoDetect: true,
                    autoFill: false,
                    showNotifications: true,
                    debugMode: false,
                    fillDelay: 100,
                    maxRetries: 3
                };
                history = {
                    totalFilled: 0,
                    fieldsFilled: 0,
                    entries: []
                };
                learnedData = {
                    fields: {},
                    portals: new Set(),
                    lastUpdated: null
                };
                
                // Now reload from bundled config
                const bundledConfig = await loadBundledConfig();
                if (bundledConfig) {
                    userData = bundledConfig;
                    populateProfileForm();
                    await saveUserData();
                    console.log('✓ Loaded from user_config.json');
                    hideLoading();
                    showToast('✓ Reloaded from project config!', 'success');
                } else {
                    hideLoading();
                    showToast('⚠️ No user_config.json found. Run config_loader.py first.', 'warning');
                }
                
                // Refresh UI
                populateSettingsForm();
                updateHistoryUI();
                
            } catch (e) {
                hideLoading();
                console.error('Refresh error:', e);
                showToast('Error refreshing: ' + e.message, 'error');
            }
        }
    });
}

// Clear history
elements.btnClearHistory.addEventListener('click', async () => {
    if (confirm('Are you sure you want to clear all history?')) {
        history = {
            totalFilled: 0,
            fieldsFilled: 0,
            entries: []
        };
        await saveHistory();
        updateHistoryUI();
        showToast('History cleared');
    }
});

// Close analysis modal
elements.closeAnalysis.addEventListener('click', () => {
    elements.analysisModal.classList.remove('show');
});

elements.analysisModal.addEventListener('click', (e) => {
    if (e.target === elements.analysisModal) {
        elements.analysisModal.classList.remove('show');
    }
});

// ================================
// IMPORT CONFIG FROM FILE
// ================================
const btnImportConfig = document.getElementById('btnImportConfig');
const importConfigInput = document.getElementById('importConfig');

if (btnImportConfig && importConfigInput) {
    btnImportConfig.addEventListener('click', () => {
        importConfigInput.click();
    });
    
    importConfigInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        try {
            const text = await file.text();
            const config = JSON.parse(text);
            
            if (!config.profile && !config.questions) {
                showToast('Invalid config file format', 'error');
                return;
            }
            
            // Merge profile data
            const profile = config.profile || {};
            const questions = config.questions || {};
            
            // Map config fields to form fields
            const fieldMappings = {
                firstName: profile.firstName,
                lastName: profile.lastName,
                email: profile.email || '',
                phone: profile.phone,
                currentCity: profile.currentCity,
                currentCompany: profile.recentEmployer || questions.recentEmployer,
                currentTitle: profile.linkedinHeadline || questions.linkedinHeadline,
                yearsExperience: profile.yearsExperience || questions.yearsExperience,
                expectedSalary: profile.expectedSalary || questions.desiredSalary,
                noticePeriod: profile.noticePeriod || questions.noticePeriod,
                linkedinUrl: profile.linkedinUrl || questions.linkedin,
                portfolioUrl: profile.portfolioUrl || questions.website,
                githubUrl: profile.githubUrl || '',
            };
            
            // Fill form fields
            for (const [fieldId, value] of Object.entries(fieldMappings)) {
                const field = document.getElementById(fieldId);
                if (field && value) {
                    field.value = value;
                }
            }
            
            // Handle select fields for work authorization
            if (profile.requireVisa || questions.requireVisa) {
                const sponsorship = document.getElementById('sponsorship');
                if (sponsorship) {
                    sponsorship.value = (profile.requireVisa === 'Yes' || questions.requireVisa === 'Yes') ? 'yes' : 'no';
                }
            }
            
            if (profile.usCitizenship || questions.usCitizenship) {
                const workAuth = document.getElementById('workAuthorization');
                if (workAuth) {
                    const citizenship = profile.usCitizenship || questions.usCitizenship;
                    workAuth.value = (citizenship === 'Yes' || citizenship.includes('Citizen')) ? 'yes' : 'no';
                }
            }
            
            // Update userData object
            userData = {
                ...userData,
                firstName: fieldMappings.firstName || userData.firstName,
                lastName: fieldMappings.lastName || userData.lastName,
                email: fieldMappings.email || userData.email,
                phone: fieldMappings.phone || userData.phone,
                currentCity: fieldMappings.currentCity || userData.currentCity,
                currentCompany: fieldMappings.currentCompany || userData.currentCompany,
                currentTitle: fieldMappings.currentTitle || userData.currentTitle,
                yearsExperience: fieldMappings.yearsExperience || userData.yearsExperience,
                expectedSalary: fieldMappings.expectedSalary || userData.expectedSalary,
                noticePeriod: fieldMappings.noticePeriod || userData.noticePeriod,
                linkedinUrl: fieldMappings.linkedinUrl || userData.linkedinUrl,
                portfolioUrl: fieldMappings.portfolioUrl || userData.portfolioUrl,
                githubUrl: fieldMappings.githubUrl || userData.githubUrl,
                // Store raw config for advanced use
                _rawConfig: config
            };
            
            // Apply extension settings from config if present
            const configSettings = config.settings || {};
            if (Object.keys(configSettings).length > 0) {
                if (configSettings.autoSync !== undefined) settings.syncToConfig = configSettings.autoSync;
                if (configSettings.enableLearning !== undefined) settings.enableLearning = configSettings.enableLearning;
                if (configSettings.detectionMode !== undefined) settings.detectionMode = configSettings.detectionMode;
                populateSettingsForm();
                await saveSettings();
            }
            
            // Save to storage
            await saveUserData();
            
            showToast(`✓ Imported ${Object.keys(fieldMappings).filter(k => fieldMappings[k]).length} fields from config!`, 'success');
            
        } catch (err) {
            console.error('Import error:', err);
            showToast('Failed to import config: ' + err.message, 'error');
        }
        
        // Reset file input
        importConfigInput.value = '';
    });
}

// ================================
// JD DETECTION & RESUME TAILORING
// ================================

// Manual JD paste toggle
const btnPasteJD = document.getElementById('btnPasteJD');
const jdManualInput = document.getElementById('jdManualInput');
const manualJDText = document.getElementById('manualJDText');
const btnAnalyzeManualJD = document.getElementById('btnAnalyzeManualJD');
const btnCancelManualJD = document.getElementById('btnCancelManualJD');
const resumeSource = document.getElementById('resumeSource');
const resumeUpload = document.getElementById('resumeUpload');
const btnReviewResume = document.getElementById('btnReviewResume');
const aiReviewStatus = document.getElementById('aiReviewStatus');

// Toggle manual JD input
if (btnPasteJD) {
    btnPasteJD.addEventListener('click', () => {
        if (jdManualInput) {
            jdManualInput.style.display = jdManualInput.style.display === 'none' ? 'block' : 'none';
            if (jdManualInput.style.display === 'block' && manualJDText) {
                manualJDText.focus();
            }
        }
    });
}

// Cancel manual JD input
if (btnCancelManualJD) {
    btnCancelManualJD.addEventListener('click', () => {
        if (jdManualInput) jdManualInput.style.display = 'none';
        if (manualJDText) manualJDText.value = '';
    });
}

// Analyze manually pasted JD
if (btnAnalyzeManualJD) {
    btnAnalyzeManualJD.addEventListener('click', async () => {
        if (!manualJDText || !manualJDText.value.trim()) {
            showToast('Please paste a job description first', 'error');
            return;
        }
        
        try {
            showLoading('Analyzing job description...');
            
            const jdText = manualJDText.value.trim();
            
            // Extract skills from JD using the real engine
            let foundSkills = [];
            if (window.ResumeEngine) {
                const jdKeywords = window.ResumeEngine.extractJDKeywords(jdText);
                foundSkills = jdKeywords.all;
            } else {
                // Fallback to basic keyword matching
                const skillKeywords = ['python', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 
                    'kubernetes', 'java', 'c++', 'machine learning', 'data science', 'agile', 'scrum',
                    'typescript', 'angular', 'vue', 'django', 'flask', 'spring', 'mongodb', 'postgresql',
                    'redis', 'kafka', 'git', 'ci/cd', 'jenkins', 'terraform', 'azure', 'gcp'];
                foundSkills = skillKeywords.filter(skill => 
                    jdText.toLowerCase().includes(skill.toLowerCase())
                );
            }
            
            // Extract title (first line or up to colon)
            let title = 'Position';
            const firstLine = jdText.split('\n')[0].trim();
            if (firstLine.length < 100) {
                title = firstLine.replace(/[:|-].*$/, '').trim() || title;
            }
            
            currentJD = {
                title: title,
                description: jdText,
                skills: foundSkills,
                company: '',
                source: 'manual'
            };
            
            // Show JD content
            if (elements.jdContent) elements.jdContent.style.display = 'block';
            
            // Display JD preview
            const truncatedJD = jdText.length > 500 ? jdText.substring(0, 500) + '...' : jdText;
            if (elements.jdPreview) {
                elements.jdPreview.innerHTML = `
                    <p><strong>${escapeHtml(title)}</strong> <span style="color: #6b7280; font-size: 11px;">(manually entered)</span></p>
                    <p class="jd-text">${escapeHtml(truncatedJD)}</p>
                `;
            }
            
            // Show extracted skills
            if (foundSkills.length > 0 && elements.jdSkills && elements.skillTags) {
                elements.jdSkills.style.display = 'block';
                elements.skillTags.innerHTML = foundSkills.map(skill => 
                    `<span class="skill-tag">${escapeHtml(skill)}</span>`
                ).join('');
            }
            
            // Show resume source and actions
            if (resumeSource) resumeSource.style.display = 'block';
            if (elements.jdActions) elements.jdActions.style.display = 'block';
            
            // Hide manual input
            if (jdManualInput) jdManualInput.style.display = 'none';
            
            showToast('Job description analyzed! ' + foundSkills.length + ' skills detected.', 'success');
            
        } catch (e) {
            console.error('Manual JD analysis error:', e);
            showToast('Error analyzing JD: ' + e.message, 'error');
        } finally {
            hideLoading();
        }
    });
}

// Resume source toggle (master vs upload)
document.querySelectorAll('input[name="resumeSource"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (resumeUpload) {
            resumeUpload.style.display = e.target.value === 'upload' ? 'block' : 'none';
        }
        const masterInfo = document.getElementById('masterResumeInfo');
        if (masterInfo) {
            masterInfo.style.display = e.target.value === 'master' ? 'block' : 'none';
        }
    });
});

// Detect JD button handler
if (elements.btnDetectJD) {
    elements.btnDetectJD.addEventListener('click', async () => {
        try {
            elements.btnDetectJD.disabled = true;
            showLoading('Detecting job description...');
            
            const response = await sendMessageToContent('detectJD');
            
            if (response && response.success && response.jd) {
                currentJD = response.jd;
                
                // Show JD content
                elements.jdContent.style.display = 'block';
                
                // Display JD preview (truncated) - HTML escaped to prevent XSS
                const truncatedJD = response.jd.description.length > 500 
                    ? response.jd.description.substring(0, 500) + '...'
                    : response.jd.description;
                elements.jdPreview.innerHTML = `
                    <p><strong>${escapeHtml(response.jd.title) || 'Job Title'}</strong></p>
                    <p class="jd-text">${escapeHtml(truncatedJD)}</p>
                `;
                
                // Show extracted skills
                if (response.jd.skills && response.jd.skills.length > 0) {
                    elements.jdSkills.style.display = 'block';
                    elements.skillTags.innerHTML = response.jd.skills.map(skill => 
                        `<span class="skill-tag">${escapeHtml(skill)}</span>`
                    ).join('');
                }
                
                // Show resume source and tailor button
                if (resumeSource) resumeSource.style.display = 'block';
                elements.jdActions.style.display = 'block';
                
                showToast('Job description detected successfully!', 'success');
            } else {
                elements.jdPreview.innerHTML = '<p class="error">Could not detect job description on this page</p>';
                showToast('No job description found', 'error');
            }
        } catch (e) {
            console.error('JD detection error:', e);
            showToast('Error detecting JD: ' + e.message, 'error');
        } finally {
            elements.btnDetectJD.disabled = false;
            hideLoading();
        }
    });
}

// Tailor Resume button handler
if (elements.btnTailorResume) {
    elements.btnTailorResume.addEventListener('click', async () => {
        if (!currentJD) {
            showToast('Please detect a job description first', 'error');
            return;
        }
        
        try {
            elements.btnTailorResume.disabled = true;
            showLoading('Connecting to AI engine...');
            
            // Show AI review status
            if (aiReviewStatus) aiReviewStatus.style.display = 'block';
            const reviewText = document.getElementById('reviewText');
            const iterationCount = document.getElementById('iterationCount');
            
            // Get resume source preference
            const resumeSourceValue = document.querySelector('input[name="resumeSource"]:checked')?.value || 'master';
            
            // Get resume text based on source
            let resumeText = '';
            if (resumeSourceValue === 'upload') {
                const fileInput = document.getElementById('masterResumeFile');
                if (fileInput && fileInput.files && fileInput.files[0]) {
                    resumeText = await fileInput.files[0].text();
                } else {
                    showToast('Please select a resume file first', 'error');
                    elements.btnTailorResume.disabled = false;
                    hideLoading();
                    return;
                }
            } else {
                resumeText = masterResumeText || '';
            }
            
            const jdText = currentJD.description || '';
            const jobTitle = currentJD.title || 'Position';
            
            // ---- Step 1: Client-side instant scoring (before tailoring) ----
            if (reviewText) reviewText.textContent = '📊 Analyzing resume against JD keywords...';
            if (iterationCount) iterationCount.textContent = '0';
            
            let scoresBefore = { ats: 0, match: 0, found: [], missing: [], techFound: [], techMissing: [], softFound: [], softMissing: [] };
            if (window.ResumeEngine && resumeText) {
                scoresBefore = window.ResumeEngine.scoreMatch(resumeText, jdText);
            }
            
            // ---- Step 2: Try API server for real AI tailoring ----
            const serverUp = await checkAPIServer();
            let result = null;
            
            if (serverUp) {
                // Real AI tailoring via local API server
                if (reviewText) reviewText.textContent = '🤖 AI generating initial draft (Iteration 1)...';
                if (iterationCount) iterationCount.textContent = '1';
                
                try {
                    const apiResult = await callAPI('/api/tailor', {
                        resumeText: resumeText,
                        jobDescription: jdText,
                        jobTitle: jobTitle,
                        reviewIterations: 2,
                    });
                    
                    if (apiResult.success) {
                        // Update progress for each review iteration from log
                        const log = apiResult.reviewLog || [];
                        for (let i = 0; i < log.length; i++) {
                            if (iterationCount) iterationCount.textContent = String(i + 1);
                            if (reviewText) {
                                const iter = log[i];
                                if (iter.error) {
                                    reviewText.textContent = `⚠️ Iteration ${iter.iteration}: ${iter.error.substring(0, 60)}`;
                                } else {
                                    reviewText.textContent = `✅ Iteration ${iter.iteration}: ATS ${iter.atsScore}%, Match ${iter.matchScore}%`;
                                }
                            }
                        }
                        
                        result = {
                            success: true,
                            atsScore: apiResult.scoresAfter?.ats || 0,
                            matchScore: apiResult.scoresAfter?.match || 0,
                            reviewRounds: apiResult.reviewIterations || 1,
                            tailoredResume: apiResult.tailoredText,
                            masterText: apiResult.masterText || resumeText,
                            scoresBefore: apiResult.scoresBefore || scoresBefore,
                            scoresAfter: apiResult.scoresAfter || {},
                            reviewLog: apiResult.reviewLog || [],
                            skills: apiResult.skills || {},
                            files: apiResult.files || {},
                        };
                    }
                } catch (apiErr) {
                    console.warn('API tailoring failed, falling back to client-side:', apiErr.message);
                }
            }
            
            // ---- Step 3: Fallback to client-side scoring only ----
            if (!result) {
                if (reviewText) reviewText.textContent = '⚡ Using client-side analysis (start API server for AI tailoring)...';
                if (iterationCount) iterationCount.textContent = '1';
                
                // Client-side only: score but can't tailor without AI
                const jdKeywords = window.ResumeEngine ? window.ResumeEngine.extractJDKeywords(jdText) : { technical: [], soft: [], all: [] };
                
                result = {
                    success: true,
                    atsScore: scoresBefore.ats || 0,
                    matchScore: scoresBefore.match || 0,
                    reviewRounds: 0,
                    tailoredResume: resumeText || '(No resume text available - start the API server and try again)',
                    masterText: resumeText,
                    scoresBefore: scoresBefore,
                    scoresAfter: scoresBefore,
                    reviewLog: [],
                    skills: { technical: jdKeywords.technical, soft: jdKeywords.soft },
                    files: {},
                    clientSideOnly: true,
                };
            }
            
            if (reviewText) reviewText.textContent = '✓ Analysis complete!';
            
            if (result.success) {
                currentTailoredResume = result;
                
                // Show ATS section with scores
                elements.atsSection.style.display = 'block';
                
                // Animate score rings
                animateScoreRing(elements.atsScoreRing, result.atsScore);
                animateScoreRing(elements.matchScoreRing, result.matchScore);
                elements.atsScoreValue.textContent = result.atsScore + '%';
                elements.matchScoreValue.textContent = result.matchScore + '%';
                
                // Show download actions and review button
                elements.resumeActions.style.display = 'flex';
                if (btnReviewResume) btnReviewResume.style.display = 'inline-flex';
                
                // Show improvement summary
                if (window.ResumeEngine && result.scoresBefore && result.scoresAfter) {
                    const improvement = window.ResumeEngine.calculateImprovement(result.scoresBefore, result.scoresAfter);
                    const msg = result.clientSideOnly
                        ? `ATS: ${result.atsScore}% | Start API server for AI tailoring`
                        : `Resume tailored! ATS: ${result.atsScore}% (+${improvement.atsImprovement}%)`;
                    showToast(msg, 'success');
                } else {
                    showToast(`Resume tailored after ${result.reviewRounds} AI reviews! ATS: ${result.atsScore}%`, 'success');
                }
            } else {
                showToast('Failed to generate resume', 'error');
            }
        } catch (e) {
            console.error('Resume tailoring error:', e);
            showToast('Error: ' + e.message, 'error');
        } finally {
            elements.btnTailorResume.disabled = false;
            hideLoading();
        }
    });
}

// AI Review button - real additional review rounds via API
if (btnReviewResume) {
    btnReviewResume.addEventListener('click', async () => {
        if (!currentTailoredResume) {
            showToast('Generate a resume first', 'error');
            return;
        }
        
        try {
            showLoading('Running AI reviewer agent...');
            btnReviewResume.disabled = true;
            
            const jdText = currentJD?.description || '';
            
            // Check if API server is available for real review
            const serverUp = await checkAPIServer();
            
            if (serverUp) {
                // Real AI review via API
                const reviewResult = await callAPI('/api/review', {
                    tailoredText: currentTailoredResume.tailoredResume,
                    masterText: currentTailoredResume.masterText || '',
                    jobDescription: jdText,
                    feedback: '',
                });
                
                if (reviewResult.success) {
                    currentTailoredResume.tailoredResume = reviewResult.improvedText;
                    currentTailoredResume.atsScore = reviewResult.scoresAfter?.ats || currentTailoredResume.atsScore;
                    currentTailoredResume.matchScore = reviewResult.scoresAfter?.match || currentTailoredResume.matchScore;
                    currentTailoredResume.scoresAfter = reviewResult.scoresAfter;
                    currentTailoredResume.reviewRounds = (currentTailoredResume.reviewRounds || 0) + 1;
                } else {
                    showToast('Review returned no improvements: ' + (reviewResult.error || ''), 'warning');
                    return;
                }
            } else {
                // Client-side re-scoring only
                if (window.ResumeEngine && currentTailoredResume.tailoredResume) {
                    const newScores = window.ResumeEngine.scoreMatch(currentTailoredResume.tailoredResume, jdText);
                    currentTailoredResume.atsScore = newScores.ats;
                    currentTailoredResume.matchScore = newScores.match;
                    currentTailoredResume.scoresAfter = newScores;
                }
                showToast('Start API server for full AI review. Showing current scores.', 'info');
            }
            
            // Update score display
            animateScoreRing(elements.atsScoreRing, currentTailoredResume.atsScore);
            animateScoreRing(elements.matchScoreRing, currentTailoredResume.matchScore);
            elements.atsScoreValue.textContent = currentTailoredResume.atsScore + '%';
            elements.matchScoreValue.textContent = currentTailoredResume.matchScore + '%';
            
            showToast(
                `Review ${currentTailoredResume.reviewRounds} complete! ATS: ${currentTailoredResume.atsScore}%`,
                'success'
            );
            
        } catch (e) {
            console.error('Review error:', e);
            showToast('Review error: ' + e.message, 'error');
        } finally {
            btnReviewResume.disabled = false;
            hideLoading();
        }
    });
}

// Score ring animation
function animateScoreRing(ringElement, score) {
    if (!ringElement) return;
    
    const dashArray = score + ', 100';
    ringElement.style.transition = 'stroke-dasharray 1s ease-in-out';
    ringElement.setAttribute('stroke-dasharray', dashArray);
    
    // Set color based on score
    let color = '#ef4444'; // red
    if (score >= 80) color = '#22c55e'; // green
    else if (score >= 60) color = '#eab308'; // yellow
    
    ringElement.style.stroke = color;
}

// Preview Resume button - advanced side-by-side with keyword highlighting
if (elements.btnPreviewResume) {
    elements.btnPreviewResume.addEventListener('click', () => {
        if (!currentTailoredResume) {
            showToast('No resume to preview', 'error');
            return;
        }
        
        const resume = currentTailoredResume;
        const scoresAfter = resume.scoresAfter || {};
        const scoresBefore = resume.scoresBefore || {};
        const matched = scoresAfter.found || scoresAfter.techFound || [];
        const missing = scoresAfter.missing || scoresAfter.techMissing || [];
        const improvement = window.ResumeEngine
            ? window.ResumeEngine.calculateImprovement(scoresBefore, scoresAfter)
            : { atsImprovement: 0, matchImprovement: 0, summary: '' };
        
        // Build advanced preview HTML
        const previewHTML = window.ResumeEngine
            ? window.ResumeEngine.generatePreviewHTML(
                resume.masterText || '(Original resume not available)',
                resume.tailoredResume || '',
                matched,
                missing
              )
            : `<pre>${escapeHtml(resume.tailoredResume || '')}</pre>`;
        
        elements.resumeContent.innerHTML = `
            <div class="resume-preview-header">
                <div class="resume-preview-scores">
                    <div class="score-display before">
                        <span class="score-label-sm">Before</span>
                        <span class="score-num">${scoresBefore.ats || 0}%</span>
                        <span class="score-name">ATS</span>
                    </div>
                    <div class="score-arrow">→</div>
                    <div class="score-display after">
                        <span class="score-label-sm">After</span>
                        <span class="score-num">${resume.atsScore || 0}%</span>
                        <span class="score-name">ATS</span>
                    </div>
                    <div class="score-separator"></div>
                    <div class="score-display before">
                        <span class="score-label-sm">Before</span>
                        <span class="score-num">${scoresBefore.match || 0}%</span>
                        <span class="score-name">Match</span>
                    </div>
                    <div class="score-arrow">→</div>
                    <div class="score-display after">
                        <span class="score-label-sm">After</span>
                        <span class="score-num">${resume.matchScore || 0}%</span>
                        <span class="score-name">Match</span>
                    </div>
                </div>
                <div class="improvement-summary">${escapeHtml(improvement.summary)}</div>
            </div>
            ${previewHTML}
            <div class="resume-info">
                <p>✓ Reviewed ${resume.reviewRounds || 0} time(s) by AI reviewer agent</p>
                <p>✓ ${matched.length} JD keywords matched | ${missing.length} still missing</p>
                ${resume.clientSideOnly ? '<p>⚠️ Client-side only — start API server for AI-tailored content</p>' : '<p>✓ ATS-optimized with real AI tailoring</p>'}
            </div>
        `;
        
        elements.resumeModal.classList.add('show');
    });
}

// Close resume modal
if (elements.closeResume) {
    elements.closeResume.addEventListener('click', () => {
        elements.resumeModal.classList.remove('show');
    });
}

if (elements.resumeModal) {
    elements.resumeModal.addEventListener('click', (e) => {
        if (e.target === elements.resumeModal) {
            elements.resumeModal.classList.remove('show');
        }
    });
}

// Download buttons - real text file downloads
function downloadTextFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

if (elements.btnDownloadDocx) {
    elements.btnDownloadDocx.addEventListener('click', () => {
        if (!currentTailoredResume?.tailoredResume) {
            showToast('No resume to download', 'error');
            return;
        }
        // If API server generated files, inform user
        if (currentTailoredResume.files?.docx) {
            showToast('DOCX saved to: ' + currentTailoredResume.files.docx, 'success');
        }
        // Also offer text download from extension
        const jobTitle = (currentJD?.title || 'Position').replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30);
        downloadTextFile(currentTailoredResume.tailoredResume, `Resume_${jobTitle}.txt`);
        showToast('Resume downloaded as TXT (DOCX available on server)', 'info');
    });
}

if (elements.btnDownloadPdf) {
    elements.btnDownloadPdf.addEventListener('click', () => {
        if (!currentTailoredResume?.tailoredResume) {
            showToast('No resume to download', 'error');
            return;
        }
        if (currentTailoredResume.files?.pdf) {
            showToast('PDF saved to: ' + currentTailoredResume.files.pdf, 'success');
        }
        const jobTitle = (currentJD?.title || 'Position').replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30);
        downloadTextFile(currentTailoredResume.tailoredResume, `Resume_${jobTitle}.txt`);
        showToast('Resume downloaded as TXT (PDF available on server)', 'info');
    });
}

// Modal download buttons
if (elements.btnModalDownloadDocx) {
    elements.btnModalDownloadDocx.addEventListener('click', () => {
        elements.btnDownloadDocx?.click();
    });
}

if (elements.btnModalDownloadPdf) {
    elements.btnModalDownloadPdf.addEventListener('click', () => {
        elements.btnDownloadPdf?.click();
    });
}

// Use This Resume button
if (elements.btnUseResume) {
    elements.btnUseResume.addEventListener('click', async () => {
        if (!currentTailoredResume?.tailoredResume) {
            showToast('No resume available', 'error');
            return;
        }
        // Store in extension storage for use in form filling
        try {
            await chrome.storage.local.set({
                activeTailoredResume: {
                    text: currentTailoredResume.tailoredResume,
                    atsScore: currentTailoredResume.atsScore,
                    matchScore: currentTailoredResume.matchScore,
                    timestamp: Date.now(),
                    jobTitle: currentJD?.title || '',
                }
            });
            elements.resumeModal.classList.remove('show');
            showToast('✓ Resume saved! Will be used for form filling.', 'success');
        } catch (e) {
            showToast('Error saving resume: ' + e.message, 'error');
        }
    });
}

// ================================
// LEARNING TAB FUNCTIONS (Enhanced)
// ================================

let _learnedFilterType = 'all';
let _learnedSearchQuery = '';

async function loadLearnedFields() {
    try {
        const result = await chrome.storage.sync.get(LEARNED_KEY);
        if (result[LEARNED_KEY]) {
            learnedFields = result[LEARNED_KEY];
            updateLearningUI();
        }
    } catch (e) {
        console.error('Error loading learned fields:', e);
    }
}

async function saveLearnedFields() {
    try {
        await chrome.storage.sync.set({ [LEARNED_KEY]: learnedFields });
    } catch (e) {
        console.error('Error saving learned fields:', e);
    }
}

function _escapeAttr(str) {
    return String(str).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _inferFieldType(value) {
    if (!value || typeof value !== 'object') return 'text';
    return value.type || 'text';
}

function _groupByType(fields) {
    const groups = { text: [], select: [], radio: [], textarea: [], checkbox: [], other: [] };
    for (const [key, value] of Object.entries(fields)) {
        const type = _inferFieldType(value);
        const bucket = groups[type] || groups.other;
        bucket.push({ key, value });
    }
    return groups;
}

function _typeIcon(type) {
    const icons = { text: '📝', select: '📋', radio: '🔘', textarea: '📄', checkbox: '☑️', other: '❓' };
    return icons[type] || icons.other;
}

function _typeBadgeClass(type) {
    const classes = { text: 'badge-blue', select: 'badge-purple', radio: 'badge-green', textarea: 'badge-amber', checkbox: 'badge-teal', other: 'badge-gray' };
    return classes[type] || classes.other;
}

function updateLearningUI() {
    if (!elements.learnedFieldsCount) return;

    const allEntries = Object.entries(learnedFields);
    const fieldCount = allEntries.length;
    const portals = new Set(Object.values(learnedFields).map(f => f && f.portal).filter(Boolean));

    elements.learnedFieldsCount.textContent = fieldCount;
    if (elements.portalsUsed) elements.portalsUsed.textContent = portals.size;
    if (elements.learnedAccuracy) {
        elements.learnedAccuracy.textContent = fieldCount > 5 ? '98%' : fieldCount > 0 ? '95%' : '--';
    }

    // Filter by search + type
    let filtered = allEntries;
    if (_learnedSearchQuery) {
        const q = _learnedSearchQuery.toLowerCase();
        filtered = filtered.filter(([key, val]) => {
            const displayVal = (val && typeof val === 'object') ? (val.value || val.type || '') : String(val || '');
            return key.toLowerCase().includes(q) || displayVal.toLowerCase().includes(q);
        });
    }
    if (_learnedFilterType !== 'all') {
        filtered = filtered.filter(([, val]) => _inferFieldType(val) === _learnedFilterType);
    }

    // Update filter chip counts
    document.querySelectorAll('.filter-chip[data-filter]').forEach(chip => {
        const f = chip.getAttribute('data-filter');
        if (f === 'all') {
            chip.textContent = `All (${allEntries.length})`;
        } else {
            const cnt = allEntries.filter(([, v]) => _inferFieldType(v) === f).length;
            chip.textContent = `${f.charAt(0).toUpperCase() + f.slice(1)} (${cnt})`;
        }
    });

    if (filtered.length > 0) {
        // Group filtered results by type
        const grouped = {};
        for (const [key, value] of filtered) {
            const type = _inferFieldType(value);
            if (!grouped[type]) grouped[type] = [];
            grouped[type].push({ key, value });
        }

        let html = '';
        for (const [type, items] of Object.entries(grouped)) {
            html += `<div class="learned-group">
                <div class="learned-group-header">
                    <span>${_typeIcon(type)} ${type.charAt(0).toUpperCase() + type.slice(1)} Fields</span>
                    <span class="learned-group-count">${items.length}</span>
                </div>`;
            for (const { key, value } of items) {
                const displayValue = (value && typeof value === 'object') ? (value.value || value.type || JSON.stringify(value)) : String(value || '');
                const truncatedValue = displayValue.length > 40 ? displayValue.substring(0, 40) + '…' : displayValue;
                html += `
                <div class="learned-field-item" data-key="${_escapeAttr(key)}" data-type="${type}">
                    <div class="field-left">
                        <span class="field-label" title="${_escapeAttr(key)}">${_escapeAttr(key)}</span>
                        <span class="field-value" title="${_escapeAttr(displayValue)}">${_escapeAttr(truncatedValue)}</span>
                    </div>
                    <div class="field-right">
                        <span class="field-type-badge ${_typeBadgeClass(type)}">${type}</span>
                        <button class="btn-edit-field" data-key="${_escapeAttr(key)}" title="Edit">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                        </button>
                        <button class="btn-remove-field" data-key="${_escapeAttr(key)}" title="Remove">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                </div>`;
            }
            html += '</div>';
        }

        elements.learnedFieldsList.innerHTML = html;

        // Attach remove handlers
        elements.learnedFieldsList.querySelectorAll('.btn-remove-field').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const key = e.currentTarget.getAttribute('data-key');
                const item = e.currentTarget.closest('.learned-field-item');
                item.classList.add('removing');
                setTimeout(async () => {
                    delete learnedFields[key];
                    await saveLearnedFields();
                    updateLearningUI();
                    showToast('Field removed', 'info');
                }, 200);
            });
        });

        // Attach edit handlers
        elements.learnedFieldsList.querySelectorAll('.btn-edit-field').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const key = e.currentTarget.getAttribute('data-key');
                const entry = learnedFields[key];
                const currentValue = (entry && typeof entry === 'object') ? (entry.value || entry.type || '') : String(entry || '');
                const newValue = prompt(`Edit value for "${key}":`, currentValue);
                if (newValue !== null && newValue !== currentValue) {
                    if (entry && typeof entry === 'object') {
                        entry.value = newValue;
                    } else {
                        learnedFields[key] = newValue;
                    }
                    saveLearnedFields();
                    updateLearningUI();
                    showToast('Field updated', 'success');
                }
            });
        });
    } else {
        const msg = _learnedSearchQuery || _learnedFilterType !== 'all'
            ? `<div class="empty-state"><p>No matching fields</p><span>Try adjusting your search or filter</span></div>`
            : `<div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
                    <path d="M8.5 8.5v.01"/><path d="M16 15.5v.01"/><path d="M12 12v.01"/>
                </svg>
                <p>No learned fields yet</p>
                <span>Fill forms manually and the AI will learn your preferences</span>
            </div>`;
        elements.learnedFieldsList.innerHTML = msg;
    }
}

// Search handler
if (elements.learnedSearchInput) {
    let _searchTimeout;
    elements.learnedSearchInput.addEventListener('input', () => {
        clearTimeout(_searchTimeout);
        _searchTimeout = setTimeout(() => {
            _learnedSearchQuery = elements.learnedSearchInput.value.trim();
            updateLearningUI();
        }, 200);
    });
}

// Filter chip handlers
document.querySelectorAll('.filter-chip[data-filter]').forEach(chip => {
    chip.addEventListener('click', () => {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        _learnedFilterType = chip.getAttribute('data-filter');
        updateLearningUI();
    });
});

// Learning settings handlers
if (elements.enableLearning) {
    elements.enableLearning.addEventListener('change', async () => {
        settings.enableLearning = elements.enableLearning.checked;
        await saveSettings();
    });
}

if (elements.syncToConfig) {
    elements.syncToConfig.addEventListener('change', async () => {
        settings.syncToConfig = elements.syncToConfig.checked;
        await saveSettings();
    });
}

// Import learned fields
if (elements.btnImportLearned) {
    elements.btnImportLearned.addEventListener('click', () => {
        elements.learnedImportFile?.click();
    });
}
if (elements.learnedImportFile) {
    elements.learnedImportFile.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
            const text = await file.text();
            const imported = JSON.parse(text);
            if (typeof imported !== 'object' || Array.isArray(imported)) throw new Error('Invalid format');
            const count = Object.keys(imported).length;
            if (confirm(`Import ${count} learned fields? This will merge with existing fields.`)) {
                Object.assign(learnedFields, imported);
                await saveLearnedFields();
                updateLearningUI();
                showToast(`Imported ${count} fields`, 'success');
            }
        } catch (err) {
            showToast('Invalid JSON file: ' + err.message, 'error');
        }
        e.target.value = '';
    });
}

// Export learned fields
if (elements.btnExportLearned) {
    elements.btnExportLearned.addEventListener('click', () => {
        const data = JSON.stringify(learnedFields, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `learned_fields_${new Date().toISOString().slice(0,10)}.json`;
        a.click();

        URL.revokeObjectURL(url);
        showToast('Learned fields exported', 'success');
    });
}

// Clear learned fields
if (elements.btnClearLearned) {
    elements.btnClearLearned.addEventListener('click', async () => {
        const count = Object.keys(learnedFields).length;
        if (count === 0) {
            showToast('No fields to clear', 'info');
            return;
        }
        if (confirm(`Clear all ${count} learned field mappings? This cannot be undone.`)) {
            learnedFields = {};
            await saveLearnedFields();
            updateLearningUI();
            showToast('All learned fields cleared', 'info');
        }
    });
}

// ================================
// MASTER RESUME LOADING
// ================================
async function loadMasterResume() {
    try {
        const serverUp = await checkAPIServer();
        const masterInfo = document.getElementById('masterResumeInfo');
        
        if (serverUp) {
            const result = await callAPI('/api/master-resume');
            if (result.success) {
                masterResumeText = result.text;
                masterResumeFilename = result.filename;
                if (masterInfo) {
                    masterInfo.innerHTML = `<small>📄 Using: <strong>${escapeHtml(result.filename)}</strong> (${result.format.toUpperCase()}, ${(result.text.length / 1024).toFixed(1)}KB)</small>`;
                    masterInfo.style.display = 'block';
                }
            } else if (masterInfo) {
                masterInfo.innerHTML = '<small>⚠️ Master resume not found on server</small>';
            }
        } else if (masterInfo) {
            masterInfo.innerHTML = '<small>⚡ API server offline — start with: <code>python -m modules.api_server</code></small>';
        }
    } catch (e) {
        console.log('Master resume load skipped:', e.message);
    }
}

// ================================
// INITIALIZATION
// ================================
async function init() {
    try {
        await loadUserData();
        await loadSettings();
        await loadHistory();
        await loadLearnedFields();
        
        // Try to load master resume from API server
        await loadMasterResume();
        
        // Check current tab and detect portal
        const tab = await getActiveTab();
        if (tab && tab.url) {
            currentPortal = detectPortal(tab.url);
            
            // Update portal banner
            if (elements.portalBanner && currentPortal !== 'unknown') {
                elements.portalBanner.style.display = 'flex';
                elements.portalName.textContent = getPortalDisplayName(currentPortal);
                elements.portalStatus.textContent = 'Supported';
                elements.portalStatus.className = 'portal-status supported';
            } else if (elements.portalBanner) {
                // Even unknown portals might work with universal detection
                elements.portalBanner.style.display = 'flex';
                elements.portalName.textContent = 'Job Portal';
                elements.portalStatus.textContent = 'Universal Mode';
                elements.portalStatus.className = 'portal-status universal';
            }
            
            // Check if on a supported job site
            const isJobSite = currentPortal !== 'unknown' || tab.url.includes('job') || tab.url.includes('career') || tab.url.includes('apply');
            
            if (isJobSite) {
                updateStatus('ready', 'Ready');
                
                // Try to detect if there's an application form
                try {
                    const response = await sendMessageToContent('isEasyApply');
                    if (response?.isEasyApply) {
                        updateStatus('success', 'Form Found');
                    }
                } catch (e) {
                    // Content script may not be loaded yet
                    console.log('Content script not ready:', e.message);
                }
            } else {
                updateStatus('inactive', 'Not a Job Site');
                if (elements.btnFillForm) elements.btnFillForm.disabled = true;
                if (elements.btnAnalyze) elements.btnAnalyze.disabled = true;
            }
        } else {
            updateStatus('inactive', 'No Tab');
        }
        
        // Update settings UI
        if (elements.enableLearning) {
            elements.enableLearning.checked = settings.enableLearning !== false;
        }
        if (elements.syncToConfig) {
            elements.syncToConfig.checked = settings.syncToConfig !== false;
        }
        
    } catch (e) {
        console.error('Initialization error:', e);
        updateStatus('error', 'Init Error');
    }
}

// Start
document.addEventListener('DOMContentLoaded', init);
