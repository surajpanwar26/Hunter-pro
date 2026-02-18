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
const UNRESOLVED_KEY = 'universalAutoFillUnresolvedFields';
const STORAGE_FALLBACK_KEY = 'universalAutoFillDataLocal';
const isSidePanelView = new URLSearchParams(window.location.search).get('view') === 'sidepanel';

if (isSidePanelView) {
    document.documentElement.classList.add('sidepanel-mode');
    document.body.classList.add('sidepanel-mode');
}

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
    btnAutoPilot: document.getElementById('btnAutoPilot'),
    btnQuickSidePanel: document.getElementById('btnQuickSidePanel'),
    btnNextStep: document.getElementById('btnNextStep'),
    btnReviewStep: document.getElementById('btnReviewStep'),
    btnSubmitApply: document.getElementById('btnSubmitApply'),
    autopilotProgress: document.getElementById('autopilotProgress'),
    autopilotPhase: document.getElementById('autopilotPhase'),
    autopilotStep: document.getElementById('autopilotStep'),
    autopilotFields: document.getElementById('autopilotFields'),
    autopilotAction: document.getElementById('autopilotAction'),
    autopilotWait: document.getElementById('autopilotWait'),
    autopilotNote: document.getElementById('autopilotNote'),
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
    jdStructured: document.getElementById('jdStructured'),
    jdRole: document.getElementById('jdRole'),
    jdVisa: document.getElementById('jdVisa'),
    jdSalary: document.getElementById('jdSalary'),
    jdSkills: document.getElementById('jdSkills'),
    skillTags: document.getElementById('skillTags'),
    jdActions: document.getElementById('jdActions'),
    btnTailorResume: document.getElementById('btnTailorResume'),
    instructionBox: document.getElementById('instructionBox'),
    instructionContent: document.getElementById('instructionContent'),
    btnShowInstructions: document.getElementById('btnShowInstructions'),
    tailoringInstruction: document.getElementById('tailoringInstruction'),
    reviewerInstruction: document.getElementById('reviewerInstruction'),
    btnGiveInstruction: document.getElementById('btnGiveInstruction'),
    reviewGateNote: document.getElementById('reviewGateNote'),
    
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
    useSidePanelMode: document.getElementById('useSidePanelMode'),
    fillDelay: document.getElementById('fillDelay'),
    maxRetries: document.getElementById('maxRetries'),
    btnOpenSidePanel: document.getElementById('btnOpenSidePanel'),
    autofillResumeOptions: document.querySelectorAll('input[name="autofillResumeSource"]'),
    autofillResumeUpload: document.getElementById('autofillResumeUpload'),
    autofillResumeFile: document.getElementById('autofillResumeFile'),
    autofillResumeFormat: document.getElementById('autofillResumeFormat'),
    previewBeforeUpload: document.getElementById('previewBeforeUpload'),
    autofillResumeInfo: document.getElementById('autofillResumeInfo'),
    btnResetSettings: document.getElementById('btnResetSettings'),
    
    // Learning Tab
    learnedFieldsCount: document.getElementById('learnedFieldsCount'),
    portalsUsed: document.getElementById('portalsUsed'),
    learnedFieldsList: document.getElementById('learnedFieldsList'),
    enableLearning: document.getElementById('enableLearning'),
    syncToConfig: document.getElementById('syncToConfig'),
    btnExportLearned: document.getElementById('btnExportLearned'),
    btnClearLearned: document.getElementById('btnClearLearned'),

    // Unknown fields learning panel
    unknownFieldsSection: document.getElementById('unknownFieldsSection'),
    unknownFieldsList: document.getElementById('unknownFieldsList'),
    unknownFieldsSummary: document.getElementById('unknownFieldsSummary'),
    btnSaveUnknownAnswers: document.getElementById('btnSaveUnknownAnswers'),
    unknownFieldsHomeSection: document.getElementById('unknownFieldsHomeSection'),
    unknownFieldsHomeList: document.getElementById('unknownFieldsHomeList'),
    unknownFieldsHomeSummary: document.getElementById('unknownFieldsHomeSummary'),
    btnSaveUnknownAnswersHome: document.getElementById('btnSaveUnknownAnswersHome'),
    
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
const JD_SCHEMA_VERSION = '1.1.0';

function emitTelemetry(type, data = {}) {
    try {
        chrome.runtime.sendMessage({ action: 'telemetryEvent', type, data });
    } catch {
        // ignore telemetry failures
    }
}

/**
 * Call the local Python API server.
 * Falls back to client-side scoring if server unavailable.
 */
async function callAPI(endpoint, data = null, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const timeoutMs = Number(options.timeoutMs) > 0 ? Number(options.timeoutMs) : 30000;
    const retries = Number(options.retries) > 0 ? Number(options.retries) : 0;
    const opts = {
        method: data ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json' },
    };
    if (data) opts.body = JSON.stringify(data);

    let attempt = 0;
    while (attempt <= retries) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
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
            const timedOut = e?.name === 'AbortError';
            if (timedOut && attempt < retries) {
                attempt += 1;
                continue;
            }
            if (timedOut) {
                emitTelemetry('api_timeout', { endpoint, timeoutMs, retries });
                throw new Error(`API request timed out (${Math.round(timeoutMs / 1000)}s)`);
            }
            throw e;
        }
    }
}

/**
 * Check if the local API server is running.
 */
async function checkAPIServer() {
    try {
        const result = await callAPI('/api/health', null, { timeoutMs: 8000, retries: 0 });
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
    autofillResumeSource: 'tailored',
    autofillResumeFormat: 'pdf',
    previewBeforeUpload: true,
    useSidePanelMode: false,
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
let unresolvedFields = [];
let currentPortal = null;
let currentJD = null;
let currentTailoredResume = null;
let reviewGatePassed = false;
let defaultTailoringInstructions = '';
let defaultReviewerInstructions = '';
let toastTimerId = null;
let autopilotWaitTimerId = null;
let pendingUploadPreviewResolver = null;

// ================================
// UTILITY FUNCTIONS
// ================================
function showToast(message, type = 'success') {
    const toast = elements.toast;
    toast.querySelector('.toast-message').textContent = message;
    toast.className = `toast ${type} show`;

    if (toastTimerId) {
        clearTimeout(toastTimerId);
    }

    toastTimerId = setTimeout(() => {
        toast.className = 'toast';
    }, 5000);
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

function clearAutopilotWaitCountdown() {
    if (autopilotWaitTimerId) {
        clearInterval(autopilotWaitTimerId);
        autopilotWaitTimerId = null;
    }
}

function setAutopilotProgress(state = {}) {
    if (!elements.autopilotProgress) return;
    elements.autopilotProgress.style.display = state.visible ? 'block' : 'none';
    if (!state.visible) {
        clearAutopilotWaitCountdown();
        return;
    }

    if (elements.autopilotPhase && state.phase !== undefined) elements.autopilotPhase.textContent = String(state.phase);
    if (elements.autopilotStep && state.step !== undefined) elements.autopilotStep.textContent = String(state.step);
    if (elements.autopilotFields && state.fields !== undefined) elements.autopilotFields.textContent = String(state.fields);
    if (elements.autopilotAction && state.action !== undefined) elements.autopilotAction.textContent = String(state.action);
    if (elements.autopilotWait && state.wait !== undefined) elements.autopilotWait.textContent = String(state.wait);
    if (elements.autopilotNote && state.note !== undefined) elements.autopilotNote.textContent = String(state.note);
}

function startAutopilotWaitCountdown(ms, note = 'Waiting for page to load...') {
    clearAutopilotWaitCountdown();
    const totalMs = Math.max(0, Number(ms) || 0);
    const startedAt = Date.now();

    const tick = () => {
        const elapsed = Date.now() - startedAt;
        const leftMs = Math.max(0, totalMs - elapsed);
        const leftSec = Math.ceil(leftMs / 1000);
        setAutopilotProgress({
            visible: true,
            action: 'Waiting',
            wait: `${leftSec}s`,
            note
        });
        if (leftMs <= 0) {
            clearAutopilotWaitCountdown();
            setAutopilotProgress({
                visible: true,
                wait: '0s'
            });
        }
    };

    tick();
    autopilotWaitTimerId = setInterval(tick, 250);
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

        // Apply extension settings from Python config if available
        const configSettings = config.settings || {};
        if (Object.keys(configSettings).length > 0) {
            if (configSettings.extensionEnabled === false) {
                console.log('⚠ Extension is disabled in Python config');
            }
            if (configSettings.autoSync !== undefined) settings.syncToConfig = configSettings.autoSync;
            if (configSettings.enableLearning !== undefined) settings.enableLearning = configSettings.enableLearning;
            if (configSettings.detectionMode !== undefined) settings.detectionMode = configSettings.detectionMode;
            if (configSettings.autofillResumeFormat !== undefined) settings.autofillResumeFormat = configSettings.autofillResumeFormat;
            if (configSettings.previewBeforeUpload !== undefined) settings.previewBeforeUpload = !!configSettings.previewBeforeUpload;
            await saveSettings();
            console.log('✓ Applied extension settings from Python config');
        }
        
        // Map config to userData format
        const profile = config.profile || {};
        const questions = config.questions || {};
        
        return {
            firstName: profile.firstName || '',
            lastName: profile.lastName || '',
            middleName: profile.middleName || '',
            email: profile.email || profile.emailAddress || profile.emailId || questions.email || questions.emailAddress || '',
            phone: profile.phone || '',
            currentCity: profile.currentCity || profile.city || questions.currentCity || questions.city || '',
            street: profile.street || '',
            state: profile.state || profile.currentState || questions.state || questions.currentState || '',
            zipcode: profile.zipcode || profile.zip || profile.postalCode || questions.zipcode || questions.zip || '',
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
    } catch (e) {
        console.log('Could not load bundled config:', e.message);
        return null;
    }
}

async function loadUserData() {
    try {
        const [syncResult, localResult] = await Promise.all([
            chrome.storage.sync.get(STORAGE_KEY),
            chrome.storage.local.get([STORAGE_KEY, STORAGE_FALLBACK_KEY])
        ]);

        const syncData = syncResult?.[STORAGE_KEY];
        const localData = localResult?.[STORAGE_KEY] || localResult?.[STORAGE_FALLBACK_KEY];
        const loaded = (syncData && Object.keys(syncData).length > 0)
            ? syncData
            : ((localData && Object.keys(localData).length > 0) ? localData : null);

        if (loaded) {
            userData = loaded;
            populateProfileForm();
            console.log('✓ Loaded profile from Chrome storage (sync/local)');
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
        try {
            await chrome.storage.sync.set({ [STORAGE_KEY]: userData });
            await chrome.storage.local.set({ [STORAGE_KEY]: userData });
        } catch (syncErr) {
            const msg = String(syncErr?.message || syncErr || '');
            if (/quota|kQuotaBytesPerItem|QUOTA_BYTES_PER_ITEM/i.test(msg)) {
                await chrome.storage.local.set({
                    [STORAGE_KEY]: userData,
                    [STORAGE_FALLBACK_KEY]: userData
                });
                showToast('Saved locally (sync quota reached).', 'warning');
            } else {
                throw syncErr;
            }
        }
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
    if (elements.useSidePanelMode) {
        elements.useSidePanelMode.checked = !!settings.useSidePanelMode;
    }
    elements.fillDelay.value = settings.fillDelay;
    elements.maxRetries.value = settings.maxRetries;

    const source = settings.autofillResumeSource || 'tailored';
    const uploadFormat = (settings.autofillResumeFormat || 'pdf').toLowerCase() === 'docx' ? 'docx' : 'pdf';
    if (elements.autofillResumeOptions && elements.autofillResumeOptions.length) {
        elements.autofillResumeOptions.forEach(r => {
            r.checked = r.value === source;
        });
    }
    if (elements.autofillResumeFormat) {
        elements.autofillResumeFormat.value = uploadFormat;
    }
    if (elements.previewBeforeUpload) {
        elements.previewBeforeUpload.checked = settings.previewBeforeUpload !== false;
    }
    if (elements.autofillResumeUpload) {
        elements.autofillResumeUpload.style.display = source === 'upload' ? 'block' : 'none';
    }
    if (elements.autofillResumeInfo) {
        const sourceLabel = source === 'tailored' ? 'Tailored Resume' : (source === 'master' ? 'Master Resume' : 'Uploaded Resume');
        const previewLabel = settings.previewBeforeUpload === false ? 'Off' : 'On';
        elements.autofillResumeInfo.innerHTML = `<small>Current source: ${escapeHtml(sourceLabel)} | Upload format: ${escapeHtml(uploadFormat.toUpperCase())} | Preview before upload: ${escapeHtml(previewLabel)}</small>`;
    }
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
    const selectedResumeSource = document.querySelector('input[name="autofillResumeSource"]:checked')?.value || 'tailored';
    const selectedUploadFormat = (elements.autofillResumeFormat?.value || 'pdf').toLowerCase() === 'docx' ? 'docx' : 'pdf';
    return {
        autoDetect: elements.autoDetect.checked,
        autoFill: elements.autoFill.checked,
        showNotifications: elements.showNotifications.checked,
        debugMode: elements.debugMode.checked,
        useSidePanelMode: !!elements.useSidePanelMode?.checked,
        fillDelay: parseInt(elements.fillDelay.value) || 100,
        maxRetries: parseInt(elements.maxRetries.value) || 3,
        autofillResumeSource: selectedResumeSource,
        autofillResumeFormat: selectedUploadFormat,
        previewBeforeUpload: !!elements.previewBeforeUpload?.checked
    };
}

async function openSidePanelForActiveTab() {
    const tab = await getActiveTab();
    if (!tab?.id) {
        throw new Error('No active tab found for side panel');
    }

    const viaBackground = await new Promise((resolve) => {
        try {
            chrome.runtime.sendMessage({ action: 'openSidePanel', tabId: tab.id }, (response) => {
                if (chrome.runtime.lastError) {
                    resolve({ success: false, error: chrome.runtime.lastError.message });
                    return;
                }
                resolve(response || { success: false, error: 'No response from background' });
            });
        } catch (e) {
            resolve({ success: false, error: String(e?.message || e) });
        }
    });

    if (viaBackground?.success) {
        return;
    }

    if (chrome.sidePanel && typeof chrome.sidePanel.open === 'function') {
        await chrome.sidePanel.setOptions({
            tabId: tab.id,
            enabled: true,
            path: 'sidepanel.html'
        });
        await chrome.sidePanel.open({ tabId: tab.id });
        return;
    }

    throw new Error(viaBackground?.error || 'Side panel API is not available in this browser build');
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

function normalizeFieldKey(label) {
    return String(label || '')
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\b(please|your|current|the|a|an|to|for|of|and|or|is|are)\b/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function getCountryValueForUnknownUi() {
    return String(userData?.country || userData?.currentCountry || '').trim().toLowerCase();
}

function looksLikeStateField(item) {
    const label = String(item?.label || '').toLowerCase();
    const fieldType = String(item?.fieldType || '').toLowerCase();
    return fieldType === 'state' || /state|province|region/.test(label);
}

function getDisplayOptionsForUnknownField(item) {
    const rawOptions = Array.isArray(item?.options) ? item.options.map(v => String(v || '').trim()).filter(Boolean) : [];
    if (!rawOptions.length) {
        return { options: [], note: '' };
    }

    const country = getCountryValueForUnknownUi();
    const isIndia = country.includes('india');
    if (!isIndia || !looksLikeStateField(item)) {
        return { options: rawOptions, note: '' };
    }

    const usStateNames = new Set([
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado', 'connecticut', 'delaware', 'florida',
        'georgia', 'hawaii', 'idaho', 'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana', 'maine',
        'maryland', 'massachusetts', 'michigan', 'minnesota', 'mississippi', 'missouri', 'montana', 'nebraska',
        'nevada', 'new hampshire', 'new jersey', 'new mexico', 'new york', 'north carolina', 'north dakota', 'ohio',
        'oklahoma', 'oregon', 'pennsylvania', 'rhode island', 'south carolina', 'south dakota', 'tennessee', 'texas',
        'utah', 'vermont', 'virginia', 'washington', 'west virginia', 'wisconsin', 'wyoming', 'district of columbia'
    ]);

    const filtered = rawOptions.filter(opt => !usStateNames.has(opt.toLowerCase()));
    if (filtered.length === 0 && rawOptions.length > 0) {
        return {
            options: [],
            note: 'Detected option list appears US-state based while your profile country is India. Type your state manually and save it.'
        };
    }

    return { options: filtered.slice(0, 30), note: '' };
}

function getSuggestedUnknownFieldAnswer(item) {
    const map = {
        firstName: userData?.firstName,
        lastName: userData?.lastName,
        email: userData?.email,
        phone: userData?.phone,
        city: userData?.city || userData?.currentCity,
        state: userData?.state,
        country: userData?.country,
        address: userData?.address,
        zip: userData?.zip,
        company: userData?.currentCompany,
        title: userData?.currentTitle,
        linkedin: userData?.linkedinUrl,
        github: userData?.githubUrl,
        portfolio: userData?.portfolioUrl,
        workAuth: userData?.workAuthorization,
        sponsorship: userData?.sponsorship,
    };
    const key = String(item?.fieldType || '').trim();
    const raw = map[key];
    return raw === undefined || raw === null ? '' : String(raw).trim();
}

function prettifyUnknownFieldLabel(rawLabel) {
    let text = String(rawLabel || '').trim();
    if (!text) return 'Unknown field';

    const normalizeChunk = (chunk) => {
        let value = String(chunk || '').toLowerCase();
        value = value
            .replace(/[\[\]{}()]/g, ' ')
            .replace(/\b[a-z0-9]+(?:[._-][a-z0-9]+){1,}\b/g, (token) => token.replace(/[._-]+/g, ' '))
            .replace(/\b(?:aria|labelledby|data|automation|widget|field|input|select|radio|checkbox|control|id|name)\b/g, ' ')
            .replace(/\b(true|false|required|optional)\b/g, ' ')
            .replace(/\b(please\s+select|select\s+an\s+option|choose\s+an\s+option)\b/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
        value = value.replace(/\b([a-z]{2,})\b(?:\s+\1\b)+/g, '$1').trim();
        return value;
    };

    const parts = text
        .split('|')
        .map(normalizeChunk)
        .filter(Boolean);

    const unique = [];
    const seen = new Set();
    for (const part of parts) {
        if (part.length < 2) continue;
        if (/^(label|field|input|select|radio|checkbox|option|question)$/i.test(part)) continue;
        if (seen.has(part)) continue;
        seen.add(part);
        unique.push(part);
    }

    const best = unique.sort((a, b) => {
        const score = (value) => {
            const words = value.split(/\s+/).filter(Boolean).length;
            let pts = 0;
            if (words >= 2) pts += 2;
            if (words >= 3) pts += 2;
            if (value.length >= 8) pts += 1;
            if (value.length > 120) pts -= 3;
            return pts;
        };
        return score(b) - score(a) || a.length - b.length;
    })[0] || normalizeChunk(text);

    if (!best) return 'Unknown field';
    return best.charAt(0).toUpperCase() + best.slice(1);
}

function buildUnknownFieldRow(item, index) {
    const { options, note: optionsNote } = getDisplayOptionsForUnknownField(item);
    const label = prettifyUnknownFieldLabel(item?.label || item?.name || item?.id || 'Unknown field');
    const type = item?.type || 'text';
    const fieldType = item?.fieldType ? String(item.fieldType) : 'unmapped';
    const reason = item?.reason || 'no_answer';
    const required = item?.required ? 'required' : 'optional';
    const currentValue = String(item?.currentValue || '').trim();
    const suggestedAnswer = getSuggestedUnknownFieldAnswer(item);
    const reasonMap = {
        no_answer: 'No matching saved answer',
        no_handler: 'Unsupported field type',
        not_visible: 'Field was hidden or blocked',
        unavailable: 'Field value was unavailable',
        verification_failed: 'Field did not keep the filled value after verification',
        error: 'Field interaction failed during autofill'
    };
    const reasonLabel = reasonMap[reason] || reason.replace(/_/g, ' ');
    const typeLabel = String(type).replace(/_/g, ' ');

    const optionsMarkup = options.length > 0
        ? `
            <div class="unknown-field-options">
                <small class="unknown-field-subtitle">Detected options</small>
                <select class="unknown-field-control unknown-option-select" data-index="${index}">
                    <option value="">Select an option…</option>
                    ${options.map(opt => `<option value="${escapeHtml(opt)}">${escapeHtml(opt)}</option>`).join('')}
                </select>
            </div>
        `
        : '';

    const booleanLike = type === 'checkbox' || type === 'toggle';
    const manualControl = booleanLike
        ? `
            <select class="unknown-field-control unknown-answer" data-index="${index}">
                <option value="">Choose answer…</option>
                <option value="yes">Yes / Checked</option>
                <option value="no">No / Unchecked</option>
            </select>
        `
        : `<input class="unknown-field-control unknown-answer" data-index="${index}" type="text" placeholder="Type the answer you want auto-fill to reuse">`;

    return `
        <div class="unknown-field-item" data-index="${index}">
            <div class="unknown-field-head">
                <span class="unknown-field-label">${escapeHtml(label)}</span>
                <div class="unknown-field-badges">
                    <span class="unknown-field-badge ${required === 'required' ? 'required' : 'optional'}">${escapeHtml(required)}</span>
                    <span class="unknown-field-badge">${escapeHtml(typeLabel)}</span>
                    <span class="unknown-field-badge">${escapeHtml(fieldType)}</span>
                </div>
            </div>
            <div class="unknown-field-options"><small class="unknown-field-subtitle">Why this is unfilled: ${escapeHtml(reasonLabel)}</small></div>
            ${currentValue ? `<div class="unknown-field-options"><small class="unknown-field-subtitle">Current page value: ${escapeHtml(currentValue)}</small></div>` : ''}
            ${suggestedAnswer ? `<div class="unknown-field-options"><small class="unknown-field-subtitle">Suggested from profile: ${escapeHtml(suggestedAnswer)}</small></div>` : ''}
            ${optionsNote ? `<div class="unknown-field-options"><small class="unknown-field-subtitle unknown-field-warning">${escapeHtml(optionsNote)}</small></div>` : ''}
            ${optionsMarkup}
            <div class="unknown-field-custom">
                <small class="unknown-field-subtitle">Answer to save</small>
                ${manualControl}
                ${suggestedAnswer ? `<button type="button" class="btn btn-secondary btn-small unknown-use-suggested" data-index="${index}" data-value="${escapeHtml(suggestedAnswer)}">Use suggested answer</button>` : ''}
            </div>
        </div>
    `;
}

function wireUnknownFieldOptionPrefill() {
    const rows = [
        ...(elements.unknownFieldsList?.querySelectorAll('.unknown-field-item') || []),
        ...(elements.unknownFieldsHomeList?.querySelectorAll('.unknown-field-item') || []),
    ];
    rows.forEach(row => {
        const optionSelect = row.querySelector('.unknown-option-select');
        const answerControl = row.querySelector('.unknown-answer');
        if (!optionSelect || !answerControl) return;

        optionSelect.addEventListener('change', () => {
            const value = optionSelect.value;
            if (!value) return;
            if (answerControl.tagName === 'SELECT') {
                const normalized = /^(yes|true|1|checked)$/i.test(value) ? 'yes' : /^(no|false|0|unchecked)$/i.test(value) ? 'no' : '';
                if (normalized) answerControl.value = normalized;
            } else {
                answerControl.value = value;
            }
        });

        const suggestedBtn = row.querySelector('.unknown-use-suggested');
        if (suggestedBtn) {
            suggestedBtn.addEventListener('click', () => {
                const value = String(suggestedBtn.getAttribute('data-value') || '').trim();
                if (!value) return;
                if (answerControl.tagName === 'SELECT') {
                    const normalized = /^(yes|true|1|checked)$/i.test(value) ? 'yes' : /^(no|false|0|unchecked)$/i.test(value) ? 'no' : '';
                    if (normalized) answerControl.value = normalized;
                } else {
                    answerControl.value = value;
                }
            });
        }
    });
}

function renderUnknownFields(fields = [], autoSwitchToLearning = false) {
    unresolvedFields = Array.isArray(fields) ? fields.filter(f => f && (f.label || f.name || f.id)) : [];

    const summaryText = unresolvedFields.length > 0
        ? `${unresolvedFields.length} field${unresolvedFields.length === 1 ? '' : 's'} need answers. Save once to auto-fill similar questions later.`
        : 'No unresolved fields. Autofill covered all detected fields.';

    const renderInto = (sectionEl, listEl, summaryEl) => {
        if (!sectionEl || !listEl) return;
        if (summaryEl) {
            summaryEl.textContent = summaryText;
        }
        if (!unresolvedFields.length) {
            sectionEl.style.display = 'none';
            listEl.innerHTML = '<div class="unknown-fields-empty">No unresolved fields. Autofill covered all detected fields.</div>';
            return;
        }
        sectionEl.style.display = 'block';
        listEl.innerHTML = unresolvedFields
            .map((item, index) => buildUnknownFieldRow(item, index))
            .join('');
    };

            renderInto(elements.unknownFieldsSection, elements.unknownFieldsList, elements.unknownFieldsSummary);
            renderInto(elements.unknownFieldsHomeSection, elements.unknownFieldsHomeList, elements.unknownFieldsHomeSummary);
    wireUnknownFieldOptionPrefill();

    try {
        if (unresolvedFields.length > 0) {
            chrome.storage.local.set({ [UNRESOLVED_KEY]: unresolvedFields });
        } else {
            chrome.storage.local.remove(UNRESOLVED_KEY);
        }
    } catch {
        // Non-fatal persistence
    }

    if (autoSwitchToLearning) {
        const learningTab = document.querySelector('.tab[data-tab="learning"]');
        if (learningTab) learningTab.click();
    }
}

async function hydrateUnknownFieldsFromStorage() {
    try {
        const result = await chrome.storage.local.get(UNRESOLVED_KEY);
        const stored = Array.isArray(result?.[UNRESOLVED_KEY]) ? result[UNRESOLVED_KEY] : [];
        renderUnknownFields(stored, false);
    } catch {
        renderUnknownFields([], false);
    }
}

async function saveUnknownAnswersFromUI() {
    if (!Array.isArray(unresolvedFields) || !unresolvedFields.length) {
        showToast('No unresolved fields to save', 'info');
        return;
    }
    const answersToSave = [];
    const rows = [
        ...(elements.unknownFieldsHomeList?.querySelectorAll('.unknown-field-item') || []),
        ...(elements.unknownFieldsList?.querySelectorAll('.unknown-field-item') || []),
    ];
    rows.forEach(row => {
        const index = Number(row.getAttribute('data-index'));
        const item = unresolvedFields[index];
        if (!item) return;
        const answerControl = row.querySelector('.unknown-answer');
        if (!answerControl) return;

        const rawAnswer = String(answerControl.value || '').trim();
        if (!rawAnswer) return;

        answersToSave.push({ item, answer: rawAnswer });
    });

    if (!answersToSave.length) {
        showToast('Enter at least one answer to save', 'warning');
        return;
    }

    userData.customAnswers = userData.customAnswers || {};

    for (const entry of answersToSave) {
        const item = entry.item;
        const answer = entry.answer;
        const label = String(item.label || '').trim();
        if (!label) continue;

        const normalizedLabel = String(item.normalizedLabel || normalizeFieldKey(label));
        const answerPayload = {
            value: answer,
            inputType: item.type || 'text',
            label,
            normalizedLabel,
            portal: currentPortal || 'unknown',
            updatedAt: Date.now()
        };

        userData.customAnswers[label] = answerPayload;
        if (normalizedLabel) {
            userData.customAnswers[`@norm:${normalizedLabel}`] = answerPayload;
        }

        learnedFields[label] = {
            type: item.fieldType || 'custom',
            answer,
            inputType: item.type || 'text',
            portal: currentPortal || 'unknown',
            normalizedLabel,
            updatedAt: Date.now()
        };

        if (item.fieldType) {
            try {
                await sendMessageToContent('saveLearnedField', { label, fieldType: item.fieldType });
            } catch {
                // Non-fatal if content script unavailable
            }
        }
    }

    await saveUserData();
    await saveLearnedFields();
    updateLearningUI();

    renderUnknownFields([]);

    try {
        const refill = await sendMessageToContent('fillForm', {});
        if (refill?.success) {
            const nextUnresolved = Array.isArray(refill.unresolvedFields) ? refill.unresolvedFields : [];
            renderUnknownFields(nextUnresolved, nextUnresolved.length > 0);
            if (nextUnresolved.length === 0) {
                showToast(`Saved ${answersToSave.length} answer(s) and refilled current form`, 'success');
                return;
            }
        }
    } catch {
        // Non-fatal if page no longer available for refill
    }

    showToast(`Saved ${answersToSave.length} field answer(s) for future autofill`, 'success');
}

async function executeAutofillFlow() {
    let resumeUpload = null;
    try {
        resumeUpload = await buildResumeUploadPayload();
    } catch (uploadErr) {
        showToast(`Resume upload skipped: ${uploadErr.message}`, 'warning');
    }

    const response = await sendMessageToContent('fillForm', { resumeUpload });
    if (!response?.success) {
        throw new Error(response?.error || 'Failed to fill form');
    }

    const uploadMsg = typeof response.fileUploaded === 'number'
        ? `, uploaded ${response.fileUploaded} resume field(s)`
        : '';
    showToast(`Filled ${response.filled} of ${response.total} fields${uploadMsg}`);
    addHistoryEntry(response);

    const unresolved = Array.isArray(response.unresolvedFields) ? response.unresolvedFields : [];
    if (unresolved.length > 0) {
        renderUnknownFields(unresolved, true);
        showToast(`Found ${unresolved.length} unfilled/new fields. Add answers on the home panel or Learning tab.`, 'warning');
    } else {
        renderUnknownFields([]);
    }
    return { response, unresolved };
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, Math.max(0, Number(ms) || 0)));
}

async function detectCurrentPageJDForAutopilot() {
    try {
        const response = await sendMessageToContent('detectJD');
        if (!response?.success || !response.jd) {
            return null;
        }
        const cleanedJDText = sanitizeJDDescription(response.jd.description || '');
        const normalized = validateAndNormalizeJD({
            ...response.jd,
            description: cleanedJDText,
            rawDescription: response.jd.description || '',
            structured: {
                ...(response.jd.structured || {}),
                ...parseStructuredJDText(cleanedJDText, response.jd.title || 'Position')
            }
        });
        if (!normalized) return null;
        currentJD = normalized;
        return normalized;
    } catch {
        return null;
    }
}

function cacheTailoringResult(result) {
    if (!result || !result.success) return;

    currentTailoredResume = {
        success: true,
        atsScore: result.scoresAfter?.ats || 0,
        matchScore: result.scoresAfter?.match || 0,
        reviewRounds: result.reviewIterations || 1,
        tailoredResume: result.tailoredText || '',
        masterText: result.masterText || '',
        scoresBefore: result.scoresBefore || {},
        scoresAfter: result.scoresAfter || {},
        reviewLog: result.reviewLog || [],
        reviewPassLog: result.reviewPassLog || [],
        reviewerPassed: !!result.reviewerPassed,
        reviewer: result.reviewer || {},
        skills: result.skills || {},
        files: result.files || {},
        quality: result.quality || {},
    };

    try {
        chrome.storage.local.set({
            activeTailoredResume: {
                text: currentTailoredResume.tailoredResume || '',
                files: currentTailoredResume.files || {},
                atsScore: currentTailoredResume.atsScore || 0,
                matchScore: currentTailoredResume.matchScore || 0,
                reviewerPassed: !!currentTailoredResume.reviewerPassed,
                timestamp: Date.now(),
                jobTitle: currentJD?.title || '',
            }
        });
    } catch {
        // non-fatal caching
    }
}

function startAutopilotTailoringTask(jd) {
    if (!jd) {
        return Promise.resolve({ success: false, reason: 'job description not detected on current page' });
    }

    return (async () => {
        try {
            const serverUp = await checkAPIServer();
            if (!serverUp) {
                showToast('Auto Pilot: API server not reachable, resume tailoring skipped.', 'warning');
                return { success: false, reason: 'API server not reachable' };
            }

            const resumeSourceValue = document.querySelector('input[name="resumeSource"]:checked')?.value || 'master';
            const resumeText = await resolveResumeTextForTailoring(resumeSourceValue);
            if (!resumeText || resumeText.trim().length < 120) {
                showToast('Auto Pilot: tailoring skipped (resume source too short).', 'warning');
                return { success: false, reason: 'resume source too short for tailoring' };
            }

            const instructionText = (elements.tailoringInstruction?.value || defaultTailoringInstructions || '').trim();
            const result = await callAPI('/api/tailor', {
                resumeText,
                jobDescription: jd.description || '',
                jobTitle: jd.title || 'Position',
                instructions: instructionText,
                reviewIterations: 2,
                reviewerMaxPasses: 6,
            }, { timeoutMs: 300000, retries: 1 });

            if (result?.success) {
                cacheTailoringResult(result);
                showToast('Auto Pilot: tailored resume prepared in background.', 'success');
                return { success: true, result };
            }

            showToast(`Auto Pilot: tailoring failed (${result?.error || 'unknown error'})`, 'warning');
            return { success: false, reason: result?.error || 'tailoring failed' };
        } catch (e) {
            showToast(`Auto Pilot: tailoring error (${e.message || e})`, 'warning');
            return { success: false, reason: e?.message || String(e) || 'tailoring error' };
        }
    })();
}

function shouldAutopilotWaitForTailoredResume() {
    const source = getPreferredAutofillResumeSource();
    return source === 'tailored';
}

async function getWorkflowStatus() {
    try {
        const response = await sendMessageToContent('workflowStatus');
        if (response?.success) return response;
        return {
            success: false,
            hasFillableFields: false,
            fillableFieldCount: 0,
            applyAvailable: false,
            nextAvailable: false,
            reviewAvailable: false,
            submitAvailable: false,
            actionCounts: { apply: 0, next: 0, review: 0, submit: 0 },
        };
    } catch {
        return {
            success: false,
            hasFillableFields: false,
            fillableFieldCount: 0,
            applyAvailable: false,
            nextAvailable: false,
            reviewAvailable: false,
            submitAvailable: false,
            actionCounts: { apply: 0, next: 0, review: 0, submit: 0 },
        };
    }
}

function sanitizeJDDescription(rawText) {
    let text = String(rawText || '').replace(/\r/g, '');
    for (let i = 0; i < 2; i++) {
        const hadMarkup = /<[^>]+>|&lt;\/?[a-z][^&]*&gt;/i.test(text);
        text = text
            .replace(/&nbsp;/gi, ' ')
            .replace(/&lt;/gi, '<')
            .replace(/&gt;/gi, '>')
            .replace(/&amp;/gi, '&')
            .replace(/<br\s*\/?>/gi, '\n')
            .replace(/<\/p\s*>/gi, '\n')
            .replace(/<\/?[a-z][^>]*>/gi, ' ');
        if (!hadMarkup) break;
    }

    const noiseCutoffs = [
        /\bsimilar\s+jobs\b/i,
        /\bshare\s+this\s+opportunity\b/i,
        /\bget\s+notified\s+for\s+similar\s+jobs\b/i,
        /\bjoin\s+our\s+talent\s+community\b/i,
    ];

    let cropped = text;
    for (const pattern of noiseCutoffs) {
        const match = cropped.match(pattern);
        if (match && typeof match.index === 'number' && match.index > 300) {
            cropped = cropped.slice(0, match.index);
            break;
        }
    }

    const lines = cropped.split('\n')
        .map(line => line.trim())
        .filter(Boolean)
        .filter(line => !/^[@.#][\w\-\s\[\]\(\):"'.,%]+\{?\}?$/.test(line))
        .filter(line => !/^(job\s*id|requisition|req\s*id|reference\s*id|posting\s*id|job\s*family|job\s*function|employment\s*type|work\s*type|travel\s*required|shift|schedule|application\s*deadline|posted\s*on|posted\s*date|equal opportunity|eoe|report this job|share|save job|external job link)\b/i.test(line))
        .filter(line => !/^(cookie settings|deny|allow|profile icon|see more|see less|see next|see even more|no recommendations found)$/i.test(line))
        .filter(line => !(line.includes('|') && line.length < 120));

    const merged = lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    return merged || text.trim();
}

function extractSalarySnippet(text) {
    const source = String(text || '');
    const rangeRegex = /([$€£]\s?\d[\d,]*(?:\.\d+)?\s*(?:-|–|—|to)\s*[$€£]?\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)/gi;
    const ranges = Array.from(source.matchAll(rangeRegex)).map(m => String(m[1] || '').trim());
    const uniqRanges = [...new Set(ranges)].filter(Boolean);
    if (uniqRanges.length) return uniqRanges[0];

    const singleRegex = /([$€£]\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)/i;
    const single = source.match(singleRegex);
    return single ? String(single[1] || '').trim() : '';
}

function normalizeVisaSnippet(text) {
    const source = String(text || '');
    if (!source.trim()) return '';
    if (/no\s+sponsorship|not\s+available|will\s+not\s+sponsor|cannot\s+sponsor/i.test(source)) return 'Not sponsored';
    if (/sponsorship\s+available|will\s+sponsor|can\s+sponsor|require\s+sponsorship|visa\s+support/i.test(source)) return 'Sponsorship available';
    return source;
}

function extractCompSignals(text, fallbackRole = 'Position') {
    const source = String(text || '');
    const salaryText = extractSalarySnippet(source);
    const visaMatch = source.match(/(visa\s*sponsorship[^\n.]{0,120}|sponsorship[^\n.]{0,120}|work authorization[^\n.]{0,120})/i);

    const visaSponsorship = normalizeVisaSnippet(visaMatch ? visaMatch[1] : '');

    return {
        role: fallbackRole || 'Position',
        salary: salaryText,
        visaSponsorship,
    };
}

function normalizeListItems(input, maxItems = 8) {
    if (!input) return [];
    if (Array.isArray(input)) {
        return input
            .flatMap(item => normalizeListItems(String(item || ''), maxItems))
            .filter(Boolean)
            .slice(0, maxItems);
    }
    const raw = String(input)
        .replace(/\s{2,}/g, ' ')
        .replace(/([a-z0-9])([A-Z][a-z])/g, '$1 $2')
        .trim();

    let parts = raw
        .split(/\n|•|-\s+/g)
        .map(item => item.trim())
        .filter(item => item.length > 2);

    if (parts.length <= 1 && raw.length > 220) {
        parts = raw
            .split(/(?<=[.!?])\s+(?=[A-Z])/g)
            .map(item => item.trim())
            .filter(item => item.length > 20);
    }

    return [...new Set(parts)].slice(0, maxItems);
}

function extractSectionFromText(text, headingPatterns) {
    const escaped = headingPatterns.map(pattern => pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const headingRegex = `(?:^|\\n)\\s*(?:${escaped.join('|')})\\s*:?\\s*`;
    const fullRegex = new RegExp(`${headingRegex}([\\s\\S]{40,2000}?)(?=\\n\\s*[A-Z][^\\n]{2,50}:?|$)`, 'i');
    const match = text.match(fullRegex);
    return match ? match[1].trim() : '';
}

function extractSectionByMarkers(text, startTerms, endTerms = [], maxLen = 2200) {
    const source = String(text || '');
    const lower = source.toLowerCase();

    let startIndex = -1;
    let startTerm = '';
    for (const term of startTerms) {
        const idx = lower.indexOf(String(term).toLowerCase());
        if (idx >= 0 && (startIndex === -1 || idx < startIndex)) {
            startIndex = idx;
            startTerm = term;
        }
    }
    if (startIndex < 0) return '';

    let contentStart = startIndex + startTerm.length;
    while (contentStart < source.length && /[:\s-]/.test(source[contentStart])) {
        contentStart += 1;
    }

    let endIndex = source.length;
    for (const term of endTerms) {
        const idx = lower.indexOf(String(term).toLowerCase(), contentStart + 8);
        if (idx > contentStart && idx < endIndex) {
            endIndex = idx;
        }
    }

    const slice = source.slice(contentStart, Math.min(endIndex, contentStart + maxLen)).trim();
    return sanitizeJDDescription(slice);
}

function parseStructuredJDText(rawText, fallbackTitle = 'Position') {
    const text = sanitizeJDDescription(rawText);
    const signals = extractCompSignals(text, fallbackTitle || 'Position');

    const sectionRegex = (patterns) => extractSectionFromText(text, patterns);
    const sectionMarker = (startTerms, endTerms, fallbackPatterns = []) => {
        const byMarker = extractSectionByMarkers(text, startTerms, endTerms);
        if (byMarker && byMarker.length >= 40) return byMarker;
        return sectionRegex(fallbackPatterns.length ? fallbackPatterns : startTerms);
    };

    const summaryText = sectionMarker(
        ['the opportunity', 'about this role', 'about the role', 'role summary', 'job summary'],
        ["what you'll do", 'what you will do', 'responsibilities', 'requirements', 'qualifications', 'bonus', 'benefits', 'our compensation'],
        ['The Opportunity', 'Role Summary', 'Job Summary', 'About this role', 'About the role']
    );
    const responsibilitiesText = sectionMarker(
        ["what you'll do", 'what you will do', 'responsibilities', 'key responsibilities', 'duties'],
        ['what you need to succeed', 'requirements', 'qualifications', 'preferred qualifications', 'bonus', 'benefits', 'our compensation'],
        ['Responsibilities', 'Key Responsibilities', "What you'll do", 'What you will do', 'Duties']
    );
    const requirementsText = sectionMarker(
        ['what you need to succeed', 'requirements', 'qualifications', 'must have', 'what we are looking for'],
        ['preferred qualifications', 'nice to have', 'bonus', 'benefits', 'our compensation', 'state-specific notices'],
        ['Requirements', 'Qualifications', 'Must have', 'What you need to succeed', 'What we are looking for']
    );
    const preferredText = sectionMarker(
        ['preferred qualifications', 'nice to have', 'bonus'],
        ['benefits', 'our compensation', 'state-specific notices'],
        ['Preferred Qualifications', 'Nice to have', 'Bonus']
    );
    const benefitsText = sectionMarker(
        ['benefits', 'what we offer', 'compensation and benefits', 'perks', 'our compensation'],
        ['state-specific notices', 'equal employment opportunity'],
        ['Benefits', 'What we offer', 'Compensation and benefits', 'Perks']
    );

    const responsibilities = normalizeListItems(responsibilitiesText, 10);
    const requirements = normalizeListItems(requirementsText, 10);
    const preferred = normalizeListItems(preferredText, 8);
    const benefits = normalizeListItems(benefitsText, 8);

    return {
        role: signals.role,
        visaSponsorship: signals.visaSponsorship,
        salary: signals.salary,
        summary: summaryText,
        responsibilities,
        requirements,
        preferred,
        benefits,
    };
}

function validateAndNormalizeJD(jdCandidate) {
    const jd = jdCandidate && typeof jdCandidate === 'object' ? { ...jdCandidate } : {};
    const title = String(jd.title || '').trim() || 'Position';
    const description = sanitizeJDDescription(jd.description || '');
    if (!description || description.length < 120) return null;

    const incomingStructured = jd.structured && typeof jd.structured === 'object' ? jd.structured : {};
    const parsedStructured = parseStructuredJDText(description, title);
    const structured = { ...parsedStructured, ...incomingStructured };

    return {
        schemaVersion: jd.schemaVersion || JD_SCHEMA_VERSION,
        title,
        company: String(jd.company || '').trim(),
        description,
        rawDescription: String(jd.rawDescription || jd.description || ''),
        skills: Array.isArray(jd.skills) ? jd.skills.map(s => String(s || '').trim()).filter(Boolean).slice(0, 30) : [],
        yearsRequired: jd.yearsRequired ?? null,
        location: String(jd.location || '').trim(),
        employmentType: String(jd.employmentType || '').trim(),
        salary: extractSalarySnippet(jd.salary || structured.salary || description),
        visaSponsorship: normalizeVisaSnippet(jd.visaSponsorship || structured.visaSponsorship || ''),
        structured,
        url: String(jd.url || '').trim(),
        portal: String(jd.portal || '').trim(),
        timestamp: jd.timestamp || Date.now(),
        source: jd.source || 'autodetect'
    };
}

function buildSectionBlock(title, items, fallbackText = '') {
    const safeTitle = escapeHtml(title);
    const listItems = normalizeListItems(items, 10);
    if (listItems.length > 0) {
        return `
            <div class="jd-section-block">
                <h5>${safeTitle}</h5>
                <ul class="structured-list">
                    ${listItems.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    if (fallbackText && String(fallbackText).trim()) {
        return `
            <div class="jd-section-block">
                <h5>${safeTitle}</h5>
                <p class="structured-text">${escapeHtml(String(fallbackText).trim())}</p>
            </div>
        `;
    }
    return '';
}

function renderStructuredJD(jd) {
    if (!elements.jdStructured) return;
    const structured = jd?.structured || parseStructuredJDText(jd?.description || '', jd?.title || 'Position');

    const setText = (el, value) => {
        if (!el) return;
        el.textContent = value && String(value).trim() ? String(value).trim() : '—';
    };

    setText(elements.jdRole, (structured.role || jd?.title || '').trim());
    setText(elements.jdVisa, normalizeVisaSnippet(structured.visaSponsorship || jd?.visaSponsorship || ''));
    setText(elements.jdSalary, extractSalarySnippet(structured.salary || jd?.salary || jd?.description || ''));

    elements.jdStructured.style.display = 'block';
}

function renderJDPreview(jd, sourceLabel = '') {
    if (!elements.jdPreview) return;
    const description = sanitizeJDDescription(jd?.description || '');
    const structured = {
        ...parseStructuredJDText(description, jd?.title || 'Position'),
        ...(jd?.structured || {}),
    };
    const sectionHtml = [
        buildSectionBlock('Summary', [], structured.summary),
        buildSectionBlock('Responsibilities', structured.responsibilities),
        buildSectionBlock('Requirements', structured.requirements),
        buildSectionBlock('Preferred', structured.preferred),
        buildSectionBlock('Benefits', structured.benefits),
    ].filter(Boolean).join('');

    const sourceText = sourceLabel ? `<span class="jd-source">${escapeHtml(sourceLabel)}</span>` : '';
    elements.jdPreview.innerHTML = `
        <div class="jd-title-row">
            <p><strong>${escapeHtml(jd?.title || 'Job Title')}</strong></p>
            ${sourceText}
        </div>
        ${sectionHtml || `<p class="jd-text">${escapeHtml(description)}</p>`}
    `;
}

function setInstructionPanel(expanded) {
    const isExpanded = !!expanded;
    if (elements.instructionContent) {
        elements.instructionContent.style.display = isExpanded ? 'block' : 'none';
    }
    if (elements.btnShowInstructions) {
        elements.btnShowInstructions.textContent = isExpanded ? 'Hide Instructions' : 'Show Instructions';
    }
}

function ensureReviewGate() {
    if (reviewGatePassed) return true;
    if (elements.reviewGateNote) elements.reviewGateNote.style.display = 'block';
    showToast('Run Review with AI before Preview, Download, or Use Resume', 'warning');
    return false;
}

function setReviewGateState(passed) {
    reviewGatePassed = !!passed;
    if (elements.btnPreviewResume) elements.btnPreviewResume.disabled = !reviewGatePassed;
    if (elements.btnDownloadDocx) elements.btnDownloadDocx.disabled = !reviewGatePassed;
    if (elements.btnDownloadPdf) elements.btnDownloadPdf.disabled = !reviewGatePassed;
    if (elements.btnModalDownloadDocx) elements.btnModalDownloadDocx.disabled = !reviewGatePassed;
    if (elements.btnModalDownloadPdf) elements.btnModalDownloadPdf.disabled = !reviewGatePassed;
    if (elements.btnUseResume) elements.btnUseResume.disabled = !reviewGatePassed;
    if (elements.reviewGateNote) elements.reviewGateNote.style.display = reviewGatePassed ? 'none' : 'block';
}

function guessMimeType(filename = '') {
    const name = String(filename || '').toLowerCase();
    if (name.endsWith('.pdf')) return 'application/pdf';
    if (name.endsWith('.docx')) return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    return 'text/plain';
}

function normalizeUploadFormat(value) {
    return String(value || '').toLowerCase() === 'docx' ? 'docx' : 'pdf';
}

function getPreferredUploadFormat() {
    return normalizeUploadFormat(settings.autofillResumeFormat || 'pdf');
}

async function validateResumePayloadContent(payload) {
    if (!payload || !Array.isArray(payload.fileBytes) || !payload.fileBytes.length) {
        throw new Error('Resume payload is empty');
    }

    const lowerName = String(payload.fileName || '').toLowerCase();
    if (!(lowerName.endsWith('.pdf') || lowerName.endsWith('.docx'))) {
        throw new Error('Only PDF or DOCX uploads are allowed');
    }

    const extracted = await callAPI('/api/extract-resume-text', {
        fileName: payload.fileName,
        fileType: payload.fileType || guessMimeType(payload.fileName),
        fileBytes: payload.fileBytes,
    }, { timeoutMs: 45000, retries: 0 });

    const extractedText = String(extracted?.text || '').trim();
    if (extractedText.length < 180) {
        throw new Error('Uploaded resume content is too short/invalid after extraction');
    }
}

async function validateUploadedResumeFile(file) {
    if (!file) throw new Error('Select a resume file first');

    const lowerName = String(file.name || '').toLowerCase();
    if (!(lowerName.endsWith('.pdf') || lowerName.endsWith('.docx'))) {
        throw new Error('Only PDF or DOCX files are supported');
    }

    const arrayBuffer = await file.arrayBuffer();
    const payload = {
        source: 'upload',
        fileName: file.name,
        fileType: file.type || guessMimeType(file.name),
        fileBytes: Array.from(new Uint8Array(arrayBuffer)),
    };
    await validateResumePayloadContent(payload);
    return payload;
}

function getPreferredAutofillResumeSource() {
    return (settings.autofillResumeSource || 'tailored').toLowerCase();
}

async function getTailoredResumePath() {
    const files = currentTailoredResume?.files || {};
    const preferred = getPreferredUploadFormat();
    const direct = preferred === 'pdf' ? (files.pdf || '') : (files.docx || '');
    if (direct) return direct;

    try {
        const stored = await chrome.storage.local.get('activeTailoredResume');
        const storedFiles = stored?.activeTailoredResume?.files || {};
        return preferred === 'pdf' ? (storedFiles.pdf || '') : (storedFiles.docx || '');
    } catch {
        return '';
    }
}

async function fetchResumeBlobFromApi(filePath) {
    if (!filePath) throw new Error('Resume file path is missing');
    const url = `${API_BASE_URL}/api/resume-file?path=${encodeURIComponent(filePath)}`;
    const response = await fetch(url);
    if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(`Failed to fetch resume file (${response.status}) ${text.slice(0, 120)}`);
    }
    return response.blob();
}

function isValidTailoredResumeText(text) {
    const raw = String(text || '');
    const normalized = raw.replace(/\s+/g, ' ').trim();
    if (normalized.length < 350) return false;

    const alphaNumCount = (normalized.match(/[a-z0-9]/gi) || []).length;
    const printableCount = (normalized.match(/[\x20-\x7E]/g) || []).length || 1;
    const alphaRatio = alphaNumCount / printableCount;

    if (alphaRatio < 0.45) return false;
    if (/^\[.*\]$/.test(normalized)) return false;
    if (/lorem ipsum|dummy text|\bundefined\b|\bnull\b/i.test(normalized)) return false;

    return true;
}

async function getActiveTailoredResumeRecord() {
    if (currentTailoredResume && typeof currentTailoredResume === 'object') {
        return currentTailoredResume;
    }
    const stored = await chrome.storage.local.get('activeTailoredResume');
    return stored?.activeTailoredResume || null;
}

function isPreviewBeforeUploadEnabled() {
    return settings.previewBeforeUpload !== false;
}

function showTailoredResumePreviewModal({ requireApproval = false } = {}) {
    if (!currentTailoredResume) {
        throw new Error('No tailored resume available for preview');
    }
    if (!ensureReviewGate()) {
        throw new Error('Tailored resume is not reviewer-approved');
    }

    const resume = currentTailoredResume;
    const scoresAfter = resume.scoresAfter || {};
    const scoresBefore = resume.scoresBefore || {};
    const matched = scoresAfter.found || scoresAfter.techFound || [];
    const missing = scoresAfter.missing || scoresAfter.techMissing || [];
    const improvement = window.ResumeEngine
        ? window.ResumeEngine.calculateImprovement(scoresBefore, scoresAfter)
        : { atsImprovement: 0, matchImprovement: 0, summary: '' };

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
            <p>✓ ATS-optimized with real AI tailoring</p>
        </div>
    `;

    if (elements.btnUseResume) {
        elements.btnUseResume.textContent = requireApproval ? 'Approve & Continue Upload' : 'Use This Resume';
    }

    elements.resumeModal.classList.add('show');
}

async function requestPreviewApprovalBeforeUpload() {
    showTailoredResumePreviewModal({ requireApproval: true });

    return new Promise((resolve) => {
        pendingUploadPreviewResolver = resolve;
    });
}

async function buildResumeUploadPayload() {
    const source = getPreferredAutofillResumeSource();
    const preferredFormat = getPreferredUploadFormat();

    if (source === 'upload') {
        const file = elements.autofillResumeFile?.files?.[0];
        return await validateUploadedResumeFile(file);
    }

    if (source === 'tailored') {
        const activeTailored = await getActiveTailoredResumeRecord();
        const reviewerPassed = !!activeTailored?.reviewerPassed;
        const tailoredText = String(activeTailored?.tailoredResume || activeTailored?.text || '').trim();

        if (!reviewerPassed) {
            throw new Error('Tailored resume is not reviewer-approved. Run tailoring/review first before auto-upload.');
        }

        if (!isValidTailoredResumeText(tailoredText)) {
            throw new Error('Tailored resume content looks invalid/garbled. Regenerate resume and pass reviewer before upload.');
        }

        if (isPreviewBeforeUploadEnabled()) {
            const approved = await requestPreviewApprovalBeforeUpload();
            if (!approved) {
                throw new Error('Resume upload cancelled. Preview was not approved.');
            }
        }

        const tailoredPath = await getTailoredResumePath();
        if (!tailoredPath) {
            throw new Error(`Tailored resume ${preferredFormat.toUpperCase()} file not found. Regenerate tailored resume and download assets again.`);
        }
        const blob = await fetchResumeBlobFromApi(tailoredPath);
        const fileName = tailoredPath.split(/[\\/]/).pop() || `tailored_resume.${preferredFormat}`;
        const arrayBuffer = await blob.arrayBuffer();
        const payload = {
            source,
            fileName,
            fileType: blob.type || guessMimeType(fileName),
            fileBytes: Array.from(new Uint8Array(arrayBuffer)),
        };
        await validateResumePayloadContent(payload);
        return payload;
    }

    // master
    const master = await callAPI('/api/master-resume', null, { timeoutMs: 12000, retries: 0 });
    const masterPath = master?.path || '';
    if (!masterPath) {
        throw new Error('Master resume path unavailable from API server');
    }
    const ext = String(masterPath).toLowerCase();
    if (ext.endsWith('.txt')) {
        throw new Error('Master resume is TXT. Upload/keep a PDF or DOCX master resume for auto-upload.');
    }
    if (preferredFormat === 'pdf' && !ext.endsWith('.pdf')) {
        throw new Error('Selected upload format is PDF but master resume is not PDF. Switch format to DOCX or replace master resume.');
    }
    if (preferredFormat === 'docx' && !ext.endsWith('.docx')) {
        throw new Error('Selected upload format is DOCX but master resume is not DOCX. Switch format to PDF or replace master resume.');
    }
    const blob = await fetchResumeBlobFromApi(masterPath);
    const fileName = master?.filename || masterPath.split(/[\\/]/).pop() || 'master_resume.docx';
    const arrayBuffer = await blob.arrayBuffer();
    const payload = {
        source,
        fileName,
        fileType: blob.type || guessMimeType(fileName),
        fileBytes: Array.from(new Uint8Array(arrayBuffer)),
    };
    await validateResumePayloadContent(payload);
    return payload;
}

async function resolveResumeTextForTailoring(resumeSourceValue) {
    if (resumeSourceValue === 'upload') {
        const fileInput = document.getElementById('masterResumeFile');
        const file = fileInput?.files?.[0];
        if (!file) {
            throw new Error('Please select a resume file first');
        }

        const lowerName = String(file.name || '').toLowerCase();
        if (!(lowerName.endsWith('.pdf') || lowerName.endsWith('.docx'))) {
            throw new Error('Only PDF or DOCX files are supported');
        }

        const arrayBuffer = await file.arrayBuffer();
        const payload = {
            fileName: file.name || 'resume.docx',
            fileType: file.type || guessMimeType(file.name || 'resume.docx'),
            fileBytes: Array.from(new Uint8Array(arrayBuffer)),
        };
        const extracted = await callAPI('/api/extract-resume-text', payload, { timeoutMs: 30000, retries: 0 });
        return String(extracted?.text || '');
    }

    // master source
    if (masterResumeText && masterResumeText.trim().length >= 120) {
        return masterResumeText;
    }

    const latestMaster = await callAPI('/api/master-resume', null, { timeoutMs: 12000, retries: 0 });
    const latestText = String(latestMaster?.text || '');
    if (latestText.trim().length >= 120) {
        masterResumeText = latestText;
        masterResumeFilename = latestMaster?.filename || masterResumeFilename;
        return latestText;
    }

    return latestText;
}

async function downloadResumeByPath(filePath, fallbackName) {
    if (!filePath) throw new Error('Resume file path missing');
    const blob = await fetchResumeBlobFromApi(filePath);
    const fileName = filePath.split(/[\\/]/).pop() || fallbackName;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return fileName;
}

async function loadDefaultTailoringInstructions() {
    const fallback = `=== PRIORITY FOCUS (What to Optimize) ===

1. Highlight my most relevant technical skills that match the job requirements
2. Emphasize quantifiable achievements (metrics, percentages, scale)
3. Mirror the exact keywords and terminology from the job description
4. Ensure my summary/objective aligns with the target role
5. Keep my strongest, most relevant experience bullets prominent

=== CRITICAL CONSTRAINTS (How to Do It) ===

1. Preserve originality and authentic voice
2. Keep the resume exactly one page
3. Preserve original layout/section order
4. Weave keywords naturally without stuffing
5. Never invent experience, skills, metrics, or tools`;
    const reviewerFallback = `Reviewer Agent Guardrails:
1. Fix critical/high issues first
2. Preserve one-page structure and original format
3. Keep ATS score strong and remove blockers
4. Do not invent claims or change factual employment details
5. Return clean, submission-ready resume text only`;
    try {
        const serverUp = await checkAPIServer();
        if (!serverUp) {
            defaultTailoringInstructions = fallback;
            defaultReviewerInstructions = reviewerFallback;
        } else {
            const response = await callAPI('/api/default-instructions');
            defaultTailoringInstructions = String(response.tailoringInstructions || response.instructions || '').trim() || fallback;
            defaultReviewerInstructions = String(response.reviewerInstructions || '').trim() || reviewerFallback;
        }
    } catch {
        defaultTailoringInstructions = fallback;
        defaultReviewerInstructions = reviewerFallback;
    }

    if (elements.tailoringInstruction && !elements.tailoringInstruction.value.trim()) {
        elements.tailoringInstruction.value = defaultTailoringInstructions;
    }
    if (elements.reviewerInstruction && !elements.reviewerInstruction.value.trim()) {
        elements.reviewerInstruction.value = defaultReviewerInstructions;
    }
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
        await executeAutofillFlow();
        updateStatus('success', 'Filled!');
    } catch (e) {
        updateStatus('error', 'Error');
        showToast(e.message || 'Failed to fill form', 'error');
    } finally {
        elements.btnFillForm.disabled = false;
        setTimeout(() => updateStatus('ready', 'Ready'), 2000);
    }
});

if (elements.btnAutoPilot) {
    elements.btnAutoPilot.addEventListener('click', async () => {
        try {
            updateStatus('loading', 'Auto Pilot...');
            elements.btnAutoPilot.disabled = true;
            elements.btnFillForm.disabled = true;
            setAutopilotProgress({
                visible: true,
                phase: 'Starting',
                step: '0/10',
                fields: '0',
                action: 'Initialize',
                wait: '0s',
                note: 'Preparing Auto Pilot workflow...'
            });

            updateStatus('loading', 'Auto Pilot: scanning JD...');
            setAutopilotProgress({
                visible: true,
                phase: 'JD Scan',
                action: 'Detect JD',
                note: 'Scanning current page and extracting job description...'
            });
            const jd = await detectCurrentPageJDForAutopilot();
            const tailoringTask = startAutopilotTailoringTask(jd);

            if (shouldAutopilotWaitForTailoredResume()) {
                updateStatus('loading', 'Auto Pilot: preparing tailored resume...');
                setAutopilotProgress({
                    visible: true,
                    phase: 'Tailoring',
                    action: 'AI tailoring',
                    note: 'Waiting for JD understanding and tailored resume generation before applying...'
                });
                const tailoredOutcome = await tailoringTask;
                if (!tailoredOutcome?.success) {
                    const reason = String(tailoredOutcome?.reason || 'reviewed tailored resume not ready').trim();
                    throw new Error(`Auto Pilot stopped: ${reason}. Fix tailoring/reviewer issues first.`);
                }
            }

            const initialWorkflow = await getWorkflowStatus();
            setAutopilotProgress({
                visible: true,
                phase: 'Pre-Apply',
                fields: String(initialWorkflow?.fillableFieldCount || 0),
                action: initialWorkflow?.applyAvailable ? 'Apply available' : 'No apply button',
                note: initialWorkflow?.applyAvailable
                    ? 'Found apply action on page, opening application flow...'
                    : 'No apply button detected; continuing with existing application form.'
            });
            if (initialWorkflow.applyAvailable) {
                updateStatus('loading', 'Auto Pilot: opening application...');
                await runWorkflowAction('apply', { strict: true });
                startAutopilotWaitCountdown(2500, 'Apply clicked. Waiting for application flow to open...');
                await sleep(2500);
            }

            const maxSteps = 10;
            let submitted = false;

            for (let step = 1; step <= maxSteps; step++) {
                updateStatus('loading', `Auto Pilot: step ${step}/${maxSteps}`);
                setAutopilotProgress({
                    visible: true,
                    phase: 'Filling',
                    step: `${step}/${maxSteps}`,
                    action: 'Inspect page',
                    note: 'Checking current page for fields and workflow actions...'
                });
                startAutopilotWaitCountdown(1300, 'Stabilizing page before field detection...');
                await sleep(1300);

                const workflow = await getWorkflowStatus();
                setAutopilotProgress({
                    visible: true,
                    fields: String(workflow?.fillableFieldCount || 0),
                    action: workflow?.hasFillableFields ? 'Fill fields' : 'No fields detected',
                    note: workflow?.hasFillableFields
                        ? 'Detected fillable fields and resume inputs. Running autofill now...'
                        : 'No fillable fields on this step. Moving to workflow action checks.'
                });
                if (workflow.hasFillableFields) {
                    const { unresolved } = await executeAutofillFlow();
                    if (unresolved.length > 0) {
                        updateStatus('warning', 'Needs Answers');
                        setAutopilotProgress({
                            visible: true,
                            phase: 'Paused',
                            action: 'Unresolved fields',
                            note: `Paused at step ${step}: ${unresolved.length} unresolved fields need answers.`
                        });
                        showToast('Auto Pilot paused: unresolved fields found. Save answers, then rerun Auto Pilot.', 'warning');
                        return;
                    }
                }

                const postFillWorkflow = await getWorkflowStatus();
                setAutopilotProgress({
                    visible: true,
                    fields: String(postFillWorkflow?.fillableFieldCount || 0),
                    action: 'Select next action',
                    note: `Actions: apply=${postFillWorkflow?.actionCounts?.apply || 0}, next=${postFillWorkflow?.actionCounts?.next || 0}, review=${postFillWorkflow?.actionCounts?.review || 0}, submit=${postFillWorkflow?.actionCounts?.submit || 0}`
                });

                if (postFillWorkflow.submitAvailable) {
                    setAutopilotProgress({
                        visible: true,
                        phase: 'Submitting',
                        action: 'Submit',
                        note: 'Submit button found. Sending application now...'
                    });
                    await runWorkflowAction('submit', { strict: true });
                    submitted = true;
                    break;
                }

                if (postFillWorkflow.nextAvailable) {
                    setAutopilotProgress({
                        visible: true,
                        action: 'Next',
                        note: 'Next step detected. Moving to the next page...'
                    });
                    await runWorkflowAction('next', { strict: true });
                    startAutopilotWaitCountdown(2200, 'Next clicked. Waiting for next page to load...');
                    await sleep(2200);
                    continue;
                }

                if (postFillWorkflow.reviewAvailable) {
                    setAutopilotProgress({
                        visible: true,
                        action: 'Review',
                        note: 'Review action detected. Opening review step...'
                    });
                    await runWorkflowAction('review', { strict: false });
                    startAutopilotWaitCountdown(1800, 'Review opened. Waiting for page update...');
                    await sleep(1800);
                    continue;
                }

                if (!postFillWorkflow.hasFillableFields) {
                    setAutopilotProgress({
                        visible: true,
                        phase: 'Stopped',
                        action: 'No actions',
                        note: 'No fillable fields and no next/review/submit action found on this page.'
                    });
                    break;
                }
            }

            if (!submitted) {
                throw new Error('Auto Pilot ended without finding a submit action. Please continue manually from current step.');
            }

            updateStatus('success', 'Auto Pilot Done');
            setAutopilotProgress({
                visible: true,
                phase: 'Completed',
                action: 'Done',
                wait: '0s',
                note: 'Application submitted successfully by Auto Pilot.'
            });
            showToast('Auto Pilot finished: scanned JD, applied, filled pages, and submitted.', 'success');

            await tailoringTask;
        } catch (e) {
            updateStatus('error', 'Auto Pilot Error');
            setAutopilotProgress({
                visible: true,
                phase: 'Error',
                action: 'Stopped',
                note: e?.message || 'Auto Pilot failed'
            });
            showToast(e.message || 'Auto Pilot failed', 'error');
        } finally {
            clearAutopilotWaitCountdown();
            elements.btnAutoPilot.disabled = false;
            elements.btnFillForm.disabled = false;
            setTimeout(() => updateStatus('ready', 'Ready'), 2000);
        }
    });
}

if (elements.btnQuickSidePanel) {
    elements.btnQuickSidePanel.addEventListener('click', async () => {
        try {
            elements.btnQuickSidePanel.disabled = true;
            await openSidePanelForActiveTab();
            showToast('Side panel opened', 'success');
        } catch (e) {
            showToast(`Unable to open side panel: ${e.message}`, 'error');
        } finally {
            elements.btnQuickSidePanel.disabled = false;
        }
    });
}

async function runWorkflowAction(action, { strict = false } = {}) {
    try {
        showLoading(`Running ${action} action...`);
        const response = await sendMessageToContent('workflowAction', { step: action });
        if (response?.success) {
            showToast(response.message || `${action} action completed`, 'success');
            return response;
        } else {
            throw new Error(response?.error || `${action} action not available on this page`);
        }
    } catch (e) {
        showToast(e.message || `Failed to run ${action} action`, 'error');
        if (strict) throw e;
        return { success: false, error: e?.message || String(e) };
    } finally {
        hideLoading();
    }
}

if (elements.btnNextStep) {
    elements.btnNextStep.addEventListener('click', async () => runWorkflowAction('next'));
}

if (elements.btnReviewStep) {
    elements.btnReviewStep.addEventListener('click', async () => runWorkflowAction('review'));
}

if (elements.btnSubmitApply) {
    elements.btnSubmitApply.addEventListener('click', async () => runWorkflowAction('submit'));
}

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

if (elements.autofillResumeOptions && elements.autofillResumeOptions.length) {
    elements.autofillResumeOptions.forEach(el => {
        el.addEventListener('change', async () => {
            settings = collectSettings();
            populateSettingsForm();
            await saveSettings();
        });
    });
}

if (elements.autofillResumeFile) {
    elements.autofillResumeFile.addEventListener('change', async () => {
        const hasFile = !!elements.autofillResumeFile.files?.[0];
        if (hasFile) {
            const uploadRadio = document.querySelector('input[name="autofillResumeSource"][value="upload"]');
            if (uploadRadio) uploadRadio.checked = true;
            settings = collectSettings();
            const picked = elements.autofillResumeFile.files[0];
            const lower = String(picked?.name || '').toLowerCase();
            if (!(lower.endsWith('.pdf') || lower.endsWith('.docx'))) {
                elements.autofillResumeFile.value = '';
                showToast('Only PDF or DOCX files are allowed', 'error');
                populateSettingsForm();
                return;
            }
            if (elements.autofillResumeInfo) {
                elements.autofillResumeInfo.innerHTML = `<small>Current source: Uploaded Resume (${escapeHtml(picked.name)})</small>`;
            }
            await saveSettings();
            return;
        }
        populateSettingsForm();
    });
}

if (elements.autofillResumeFormat) {
    elements.autofillResumeFormat.addEventListener('change', async () => {
        settings = collectSettings();
        populateSettingsForm();
        await saveSettings();
    });
}

if (elements.previewBeforeUpload) {
    elements.previewBeforeUpload.addEventListener('change', async () => {
        settings = collectSettings();
        populateSettingsForm();
        await saveSettings();
    });
}

if (elements.useSidePanelMode) {
    elements.useSidePanelMode.addEventListener('change', async () => {
        settings = collectSettings();
        await saveSettings();
        if (settings.useSidePanelMode) {
            try {
                await openSidePanelForActiveTab();
                showToast('Side panel mode enabled');
            } catch (e) {
                showToast(`Unable to open side panel: ${e.message}`, 'warning');
            }
        }
    });
}

if (elements.btnOpenSidePanel) {
    elements.btnOpenSidePanel.addEventListener('click', async () => {
        try {
            await openSidePanelForActiveTab();
            showToast('Side panel opened', 'success');
        } catch (e) {
            showToast(`Unable to open side panel: ${e.message}`, 'error');
        }
    });
}

// Reset settings
elements.btnResetSettings.addEventListener('click', async () => {
    settings = {
        autoDetect: true,
        autoFill: false,
        showNotifications: true,
        debugMode: false,
        fillDelay: 100,
        maxRetries: 3,
        autofillResumeSource: 'tailored',
        autofillResumeFormat: 'pdf',
        previewBeforeUpload: true,
        useSidePanelMode: false,
        syncToConfig: true
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
                    maxRetries: 3,
                    autofillResumeSource: 'tailored',
                    autofillResumeFormat: 'pdf',
                    previewBeforeUpload: true,
                    useSidePanelMode: false,
                    syncToConfig: true
                };
                history = {
                    totalFilled: 0,
                    fieldsFilled: 0,
                    entries: []
                };
                learnedFields = {};
                
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
            const cleanedJDText = sanitizeJDDescription(jdText);
            
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
            
            const normalized = validateAndNormalizeJD({
                title: title,
                description: cleanedJDText,
                rawDescription: jdText,
                skills: foundSkills,
                company: '',
                structured: parseStructuredJDText(cleanedJDText, title),
                source: 'manual'
            });

            if (!normalized) {
                emitTelemetry('jd_schema_invalid_manual', { length: cleanedJDText.length });
                throw new Error('Pasted JD is too short or malformed');
            }
            currentJD = normalized;
            
            // Show JD content
            if (elements.jdContent) elements.jdContent.style.display = 'block';

            renderJDPreview(currentJD, 'manually entered');
            renderStructuredJD(currentJD);
            
            // Show extracted skills
            if (foundSkills.length > 0 && elements.jdSkills && elements.skillTags) {
                elements.jdSkills.style.display = 'block';
                elements.skillTags.innerHTML = foundSkills.map(skill => 
                    `<span class="skill-tag">${escapeHtml(skill)}</span>`
                ).join('');
            } else if (elements.jdSkills) {
                elements.jdSkills.style.display = 'none';
            }
            
            // Show resume source and actions
            if (resumeSource) resumeSource.style.display = 'block';
            if (elements.instructionBox) elements.instructionBox.style.display = 'block';
            setInstructionPanel(false);
            if (elements.jdActions) elements.jdActions.style.display = 'block';
            setReviewGateState(false);
            
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
                const cleanedJDText = sanitizeJDDescription(response.jd.description || '');
                const normalized = validateAndNormalizeJD({
                    ...response.jd,
                    description: cleanedJDText,
                    rawDescription: response.jd.description || '',
                    structured: {
                        ...(response.jd.structured || {}),
                        ...parseStructuredJDText(cleanedJDText, response.jd.title || 'Position')
                    }
                });

                if (!normalized) {
                    emitTelemetry('jd_schema_invalid_detected', {
                        title: String(response?.jd?.title || ''),
                        hasDescription: !!response?.jd?.description,
                        schemaVersion: String(response?.jd?.schemaVersion || ''),
                    });
                    throw new Error('Detected JD payload failed schema validation');
                }
                currentJD = normalized;
                
                // Show JD content
                elements.jdContent.style.display = 'block';

                renderJDPreview(currentJD);
                renderStructuredJD(currentJD);
                
                // Show extracted skills
                if (response.jd.skills && response.jd.skills.length > 0) {
                    elements.jdSkills.style.display = 'block';
                    elements.skillTags.innerHTML = response.jd.skills.map(skill => 
                        `<span class="skill-tag">${escapeHtml(skill)}</span>`
                    ).join('');
                } else if (elements.jdSkills) {
                    elements.jdSkills.style.display = 'none';
                }
                
                // Show resume source and tailor button
                if (resumeSource) resumeSource.style.display = 'block';
                if (elements.instructionBox) elements.instructionBox.style.display = 'block';
                setInstructionPanel(false);
                elements.jdActions.style.display = 'block';
                setReviewGateState(false);
                
                showToast('Job description detected successfully!', 'success');
            } else {
                elements.jdPreview.innerHTML = '<p class="error">Could not detect job description on this page</p>';
                if (elements.jdStructured) elements.jdStructured.style.display = 'none';
                if (elements.jdSkills) elements.jdSkills.style.display = 'none';
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

if (elements.btnGiveInstruction) {
    elements.btnGiveInstruction.addEventListener('click', () => {
        if (elements.tailoringInstruction) {
            elements.tailoringInstruction.value = defaultTailoringInstructions;
            if (elements.reviewerInstruction) {
                elements.reviewerInstruction.value = defaultReviewerInstructions;
            }
            showToast('Project tailoring instructions prefilled', 'success');
        }
    });
}

if (elements.btnShowInstructions) {
    elements.btnShowInstructions.addEventListener('click', () => {
        const isExpanded = elements.instructionContent?.style.display === 'block';
        setInstructionPanel(!isExpanded);
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
            let resumeText = await resolveResumeTextForTailoring(resumeSourceValue);
            
            const jdText = currentJD.description || '';
            const jobTitle = currentJD.title || 'Position';
            const instructionText = (elements.tailoringInstruction?.value || defaultTailoringInstructions || '').trim();

            if (!resumeText || resumeText.trim().length < 120) {
                throw new Error('Resume source is too short. Use a real master/upload resume before tailoring.');
            }
            
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

            if (!serverUp) {
                throw new Error('API server is required for real tailoring. Start: python -m modules.api_server');
            }

            if (serverUp) {
                // Real AI tailoring via local API server
                if (reviewText) reviewText.textContent = '🤖 AI generating initial draft (Iteration 1)...';
                if (iterationCount) iterationCount.textContent = '1';
                
                try {
                    const apiResult = await callAPI('/api/tailor', {
                        resumeText: resumeText,
                        jobDescription: jdText,
                        jobTitle: jobTitle,
                        instructions: instructionText,
                        reviewIterations: 2,
                        reviewerMaxPasses: 6,
                    }, { timeoutMs: 300000, retries: 1 });
                    
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
                            reviewPassLog: apiResult.reviewPassLog || [],
                            reviewerPassed: !!apiResult.reviewerPassed,
                            reviewer: apiResult.reviewer || {},
                            skills: apiResult.skills || {},
                            files: apiResult.files || {},
                            quality: apiResult.quality || {},
                        };
                    }
                } catch (apiErr) {
                    throw new Error(apiErr.message || 'Tailoring failed');
                }
            }

            if (!result) {
                throw new Error('Tailoring failed to produce a valid resume');
            }
            
            if (reviewText) reviewText.textContent = '✓ Analysis complete!';
            
            if (result.success) {
                currentTailoredResume = result;

                try {
                    await chrome.storage.local.set({
                        activeTailoredResume: {
                            text: result.tailoredResume || '',
                            files: result.files || {},
                            atsScore: result.atsScore || 0,
                            matchScore: result.matchScore || 0,
                            reviewerPassed: !!result.reviewerPassed,
                            timestamp: Date.now(),
                            jobTitle: currentJD?.title || '',
                        }
                    });
                } catch {
                    // non-fatal
                }
                
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
                setReviewGateState(!!result.reviewerPassed);
                if (result.reviewerPassed) {
                    showToast('Tailored resume passed reviewer checks. Preview/download unlocked.', 'success');
                } else {
                    showToast('Tailored resume generated but reviewer still found issues. Run AI Review again.', 'warning');
                }
                
                // Show improvement summary
                if (window.ResumeEngine && result.scoresBefore && result.scoresAfter) {
                    const improvement = window.ResumeEngine.calculateImprovement(result.scoresBefore, result.scoresAfter);
                    const msg = `Resume tailored! ATS: ${result.atsScore}% (+${improvement.atsImprovement}%)`;
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
            
            if (!serverUp) {
                throw new Error('API server is required for reviewer agent. Start: python -m modules.api_server');
            }

            const reviewResult = await callAPI('/api/review', {
                tailoredText: currentTailoredResume.tailoredResume,
                masterText: currentTailoredResume.masterText || '',
                jobDescription: jdText,
                feedback: '',
            }, { timeoutMs: 180000, retries: 1 });

            if (reviewResult.success) {
                currentTailoredResume.tailoredResume = reviewResult.improvedText;
                currentTailoredResume.atsScore = reviewResult.scoresAfter?.ats || currentTailoredResume.atsScore;
                currentTailoredResume.matchScore = reviewResult.scoresAfter?.match || currentTailoredResume.matchScore;
                currentTailoredResume.scoresAfter = reviewResult.scoresAfter;
                currentTailoredResume.reviewRounds = (currentTailoredResume.reviewRounds || 0) + 1;
                currentTailoredResume.reviewerPassed = !!reviewResult.reviewerPassed;
                setReviewGateState(!!reviewResult.reviewerPassed);
                if (!reviewResult.reviewerPassed) {
                    showToast('Reviewer found issues. Please run review again or adjust instructions.', 'warning');
                    return;
                }
            } else {
                showToast('Review returned no improvements: ' + (reviewResult.error || ''), 'warning');
                return;
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
        try {
            showTailoredResumePreviewModal({ requireApproval: false });
        } catch (e) {
            showToast(e.message || 'Failed to open preview', 'error');
        }
    });
}

// Close resume modal
if (elements.closeResume) {
    elements.closeResume.addEventListener('click', () => {
        elements.resumeModal.classList.remove('show');
        if (pendingUploadPreviewResolver) {
            pendingUploadPreviewResolver(false);
            pendingUploadPreviewResolver = null;
        }
    });
}

if (elements.resumeModal) {
    elements.resumeModal.addEventListener('click', (e) => {
        if (e.target === elements.resumeModal) {
            elements.resumeModal.classList.remove('show');
            if (pendingUploadPreviewResolver) {
                pendingUploadPreviewResolver(false);
                pendingUploadPreviewResolver = null;
            }
        }
    });
}

if (elements.btnDownloadDocx) {
    elements.btnDownloadDocx.addEventListener('click', async () => {
        if (!ensureReviewGate()) return;
        if (!currentTailoredResume) {
            showToast('No resume to download', 'error');
            return;
        }
        const docxPath = currentTailoredResume.files?.docx;
        if (!docxPath) {
            showToast('DOCX file was not generated by API', 'error');
            return;
        }
        try {
            const downloaded = await downloadResumeByPath(docxPath, 'tailored_resume.docx');
            showToast(`Downloaded ${downloaded}`, 'success');
        } catch (e) {
            showToast(`DOCX download failed: ${e.message}`, 'error');
        }
    });
}

if (elements.btnDownloadPdf) {
    elements.btnDownloadPdf.addEventListener('click', async () => {
        if (!ensureReviewGate()) return;
        if (!currentTailoredResume) {
            showToast('No resume to download', 'error');
            return;
        }
        const pdfPath = currentTailoredResume.files?.pdf;
        if (!pdfPath) {
            showToast('PDF file was not generated by API', 'error');
            return;
        }
        try {
            const downloaded = await downloadResumeByPath(pdfPath, 'tailored_resume.pdf');
            showToast(`Downloaded ${downloaded}`, 'success');
        } catch (e) {
            showToast(`PDF download failed: ${e.message}`, 'error');
        }
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
        if (!ensureReviewGate()) return;
        if (!currentTailoredResume?.tailoredResume) {
            showToast('No resume available', 'error');
            return;
        }

        if (pendingUploadPreviewResolver) {
            elements.resumeModal.classList.remove('show');
            pendingUploadPreviewResolver(true);
            pendingUploadPreviewResolver = null;
            return;
        }

        // Store in extension storage for use in form filling
        try {
            await chrome.storage.local.set({
                activeTailoredResume: {
                    text: currentTailoredResume.tailoredResume,
                    files: currentTailoredResume.files || {},
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
// LEARNING TAB FUNCTIONS
// ================================

async function loadLearnedFields() {
    try {
        const [syncResult, localResult] = await Promise.all([
            chrome.storage.sync.get(LEARNED_KEY),
            chrome.storage.local.get(LEARNED_KEY)
        ]);
        const resolved = syncResult?.[LEARNED_KEY] || localResult?.[LEARNED_KEY];
        if (resolved) {
            learnedFields = resolved;
            updateLearningUI();
        }
    } catch (e) {
        console.error('Error loading learned fields:', e);
    }
}

function mergeTimestampedMaps(baseMap, incomingMap) {
    const merged = { ...(baseMap || {}) };
    for (const [key, value] of Object.entries(incomingMap || {})) {
        const current = merged[key];
        const currentTs = Number(current?.updatedAt || 0);
        const nextTs = Number(value?.updatedAt || 0);
        if (!current || nextTs >= currentTs) {
            merged[key] = value;
        }
    }
    return merged;
}

async function syncLearnedToBackend() {
    if (settings.syncToConfig === false) return;
    try {
        const payload = {
            learnedFields: learnedFields || {},
            customAnswers: userData.customAnswers || {}
        };
        const result = await callAPI('/api/extension-learning', payload, { timeoutMs: 12000, retries: 0 });
        if (result?.success) {
            if (result.learnedFields && typeof result.learnedFields === 'object') {
                learnedFields = mergeTimestampedMaps(learnedFields, result.learnedFields);
            }
            if (result.customAnswers && typeof result.customAnswers === 'object') {
                userData.customAnswers = mergeTimestampedMaps(userData.customAnswers || {}, result.customAnswers);
                await saveUserData();
            }
            await chrome.storage.sync.set({ [LEARNED_KEY]: learnedFields });
            updateLearningUI();
        }
    } catch (e) {
        console.log('Learning sync skipped:', e.message || e);
    }
}

async function hydrateLearnedFromBackend() {
    if (settings.syncToConfig === false) return;
    try {
        const result = await callAPI('/api/extension-learning', null, { timeoutMs: 12000, retries: 0 });
        if (!result?.success) return;

        let changed = false;
        if (result.learnedFields && typeof result.learnedFields === 'object') {
            const mergedFields = mergeTimestampedMaps(learnedFields || {}, result.learnedFields);
            if (JSON.stringify(mergedFields) !== JSON.stringify(learnedFields || {})) {
                learnedFields = mergedFields;
                await chrome.storage.sync.set({ [LEARNED_KEY]: learnedFields });
                changed = true;
            }
        }

        if (result.customAnswers && typeof result.customAnswers === 'object') {
            const mergedAnswers = mergeTimestampedMaps(userData.customAnswers || {}, result.customAnswers);
            if (JSON.stringify(mergedAnswers) !== JSON.stringify(userData.customAnswers || {})) {
                userData.customAnswers = mergedAnswers;
                await saveUserData();
                changed = true;
            }
        }

        if (changed) {
            updateLearningUI();
        }
    } catch (e) {
        console.log('Learning hydration skipped:', e.message || e);
    }
}

async function saveLearnedFields(syncBackend = true) {
    try {
        try {
            await chrome.storage.sync.set({ [LEARNED_KEY]: learnedFields });
            await chrome.storage.local.set({ [LEARNED_KEY]: learnedFields });
        } catch (syncErr) {
            const msg = String(syncErr?.message || syncErr || '');
            if (/quota|kQuotaBytesPerItem|QUOTA_BYTES_PER_ITEM/i.test(msg)) {
                await chrome.storage.local.set({ [LEARNED_KEY]: learnedFields });
                showToast('Learned mappings saved locally (sync quota reached).', 'warning');
            } else {
                throw syncErr;
            }
        }
        if (syncBackend) {
            await syncLearnedToBackend();
        }
    } catch (e) {
        console.error('Error saving learned fields:', e);
    }
}

function updateLearningUI() {
    if (!elements.learnedFieldsCount) return;
    
    const fieldCount = Object.keys(learnedFields).length;
    const portals = new Set(Object.values(learnedFields).map(f => f.portal).filter(Boolean));
    
    elements.learnedFieldsCount.textContent = fieldCount;
    elements.portalsUsed.textContent = portals.size;
    
    // Update learned fields list
    if (fieldCount > 0) {
        const listHtml = Object.entries(learnedFields).map(([key, value]) => `
            <div class="learned-field-item">
                <span class="field-pattern">${key}</span>
                <span class="field-type">${value.type}</span>
                <button class="btn-remove" data-key="${key}">×</button>
            </div>
        `).join('');
        
        elements.learnedFieldsList.innerHTML = listHtml;
        
        // Add remove handlers
        elements.learnedFieldsList.querySelectorAll('.btn-remove').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const key = e.target.getAttribute('data-key');
                delete learnedFields[key];
                await saveLearnedFields();
                updateLearningUI();
                showToast('Field mapping removed');
            });
        });
    } else {
        elements.learnedFieldsList.innerHTML = `
            <div class="empty-state">
                <p>No learned fields yet</p>
                <span>Fill forms manually to teach the AI</span>
            </div>
        `;
    }
}

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
        if (settings.syncToConfig) {
            await hydrateLearnedFromBackend();
            await syncLearnedToBackend();
        }
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
        a.download = 'learned_fields.json';
        a.click();
        
        URL.revokeObjectURL(url);
        showToast('Learned fields exported');
    });
}

// Clear learned fields
if (elements.btnClearLearned) {
    elements.btnClearLearned.addEventListener('click', async () => {
        if (confirm('Clear all learned field mappings?')) {
            learnedFields = {};
            await saveLearnedFields();
            updateLearningUI();
            showToast('Learned fields cleared');
        }
    });
}

if (elements.btnSaveUnknownAnswers) {
    elements.btnSaveUnknownAnswers.addEventListener('click', async () => {
        try {
            await saveUnknownAnswersFromUI();
        } catch (e) {
            showToast(`Failed to save unknown answers: ${e.message}`, 'error');
        }
    });
}

if (elements.btnSaveUnknownAnswersHome) {
    elements.btnSaveUnknownAnswersHome.addEventListener('click', async () => {
        try {
            await saveUnknownAnswersFromUI();
        } catch (e) {
            showToast(`Failed to save unknown answers: ${e.message}`, 'error');
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
        await hydrateLearnedFromBackend();
        
        // Try to load master resume from API server
        await loadMasterResume();
        await loadDefaultTailoringInstructions();
        
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

        if (settings.useSidePanelMode) {
            try {
                await openSidePanelForActiveTab();
            } catch {
                // Ignore; side panel might be unavailable in current context
            }
        }

        await hydrateUnknownFieldsFromStorage();
        
    } catch (e) {
        console.error('Initialization error:', e);
        updateStatus('error', 'Init Error');
    }
}

// Start
document.addEventListener('DOMContentLoaded', () => {
    setReviewGateState(false);
    setInstructionPanel(false);
    init();
});
