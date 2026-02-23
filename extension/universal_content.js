/**
 * Universal Job Application Form Filler - Content Script
 * Works on ANY job portal: LinkedIn, Indeed, Glassdoor, Workday, Greenhouse, Lever, etc.
 * 
 * Features:
 * - Universal form detection using AI-powered pattern matching
 * - Job Description (JD) detection and extraction
 * - Field learning: saves new fields when user fills them manually
 * - Config sync with Python backend
 * 
 * @author Suraj Panwar
 * @version 2.0.0
 */

(function() {
    'use strict';
    const JD_SCHEMA_VERSION = '1.1.0';
    
    // ================================
    // CONFIGURATION
    // ================================
    const CONFIG = {
        DEBUG: false,  // Set to true only for development
        FILL_DELAY: 80,
        DETECTION_INTERVAL: 2000,
        STORAGE_KEY: 'universalAutoFillData',  // Must match popup.js storage key!
        LEARNED_FIELDS_KEY: 'learnedFieldMappings',
        JD_STORAGE_KEY: 'lastDetectedJD',
        AI_ENDPOINT: null, // Set by Groq API
        MAX_RETRIES: 3,
        STRICT_VERIFY_PASS: true,
        VERIFY_RETRY_COUNT: 1
    };
    const STORAGE_FALLBACK_KEY = 'universalAutoFillDataLocal';
    const RUNTIME_SETTINGS_KEY = 'universalAutoFillSettings';
    let runtimeSettings = {
        extensionEnabled: true,
        detectionMode: 'universal',
    };
    let lastFormDetectedAt = 0;

    let __extensionContextAlive = true;
    // mark context dead on unload/navigation so background calls stop early
    try {
        window.addEventListener('unload', () => { __extensionContextAlive = false; });
        window.addEventListener('beforeunload', () => { __extensionContextAlive = false; });
    } catch {
        // ignore if page restricts listeners
    }

    function isExtensionContextValid() {
        try {
            return __extensionContextAlive && !!(chrome?.runtime?.id);
        } catch {
            return false;
        }
    }

    function safeRuntimeSendMessage(payload) {
        if (!isExtensionContextValid() || !chrome?.runtime?.sendMessage) {
            return Promise.resolve(null);
        }
        try {
            const maybePromise = chrome.runtime.sendMessage(payload);
            if (maybePromise && typeof maybePromise.then === 'function') {
                return maybePromise.catch(() => null);
            }
            return Promise.resolve(maybePromise || null);
        } catch (e) {
            const msg = String(e?.message || e || '');
            if (/Extension context invalidated/i.test(msg)) {
                log('Extension context invalidated while sending runtime message');
                return Promise.resolve(null);
            }
            throw e;
        }
    }

    function safeSendResponse(sendResponse, payload) {
        try {
            if (typeof sendResponse === 'function') {
                sendResponse(payload);
            }
        } catch (e) {
            const msg = String(e?.message || e || '');
            if (/Extension context invalidated/i.test(msg)) {
                log('Extension context invalidated while sending response to runtime message');
                return;
            }
            // swallow other sendResponse errors to avoid breaking the page
            log('Error in safeSendResponse:', msg);
        }
    }

    function applyRuntimeSettings(nextSettings = {}) {
        runtimeSettings = {
            ...runtimeSettings,
            ...(nextSettings || {}),
        };
    }

    async function refreshRuntimeSettings() {
        try {
            const result = await chrome.storage.sync.get(RUNTIME_SETTINGS_KEY);
            applyRuntimeSettings(result?.[RUNTIME_SETTINGS_KEY] || {});
        } catch {
            // keep defaults if settings are unavailable
        }
    }

    function isAutomationEnabled() {
        return runtimeSettings.extensionEnabled !== false;
    }

    function isDetectionModeEnabled() {
        const mode = String(runtimeSettings.detectionMode || 'universal').trim().toLowerCase();
        return !mode || mode === 'universal';
    }

    function getRuntimeGateError(actionName = 'action') {
        if (!isAutomationEnabled()) {
            return `Extension automation is disabled by settings (${actionName} blocked)`;
        }
        if (!isDetectionModeEnabled()) {
            return `Detection mode "${String(runtimeSettings.detectionMode || '')}" is not supported in universal content runtime`;
        }
        return '';
    }
    
    // ================================
    // SUPPORTED JOB PORTALS
    // ================================
    const PORTAL_PATTERNS = {
        linkedin: /linkedin\.com/i,
        indeed: /indeed\.com/i,
        glassdoor: /glassdoor\.com/i,
        workday: /myworkday|workday\.com/i,
        greenhouse: /greenhouse\.io|boards\.greenhouse/i,
        lever: /lever\.co|jobs\.lever/i,
        smartrecruiters: /smartrecruiters\.com/i,
        bamboohr: /bamboohr\.com/i,
        icims: /icims\.com/i,
        taleo: /taleo\.net/i,
        successfactors: /successfactors\.com/i,
        jobvite: /jobvite\.com/i,
        ashbyhq: /ashbyhq\.com/i,
        breezyhr: /breezy\.hr/i,
        recruitee: /recruitee\.com/i,
        jazzyhr: /jazz\.co/i,
        angel: /angel\.co|wellfound\.com/i,
        monster: /monster\.com/i,
        ziprecruiter: /ziprecruiter\.com/i,
        careerbuilder: /careerbuilder\.com/i,
        dice: /dice\.com/i,
        stackoverflow: /stackoverflow\.com\/jobs/i,
        github: /github\.com\/jobs|github\.careers/i,
        remoteok: /remoteok\.com/i,
        weworkremotely: /weworkremotely\.com/i,
        flexjobs: /flexjobs\.com/i,
        generic: /.*/  // Catch-all
    };
    
    // ================================
    // UNIVERSAL FIELD PATTERNS
    // ================================
    const FIELD_PATTERNS = {
        // Personal Info
        firstName: /first\s*name|fname|given\s*name|forename/i,
        lastName: /last\s*name|lname|surname|family\s*name/i,
        fullName: /full\s*name|^name$|your\s*name|applicant\s*name|candidate\s*name/i,
        email: /e?-?mail|email\s*address/i,
        phone: /phone|mobile|cell|telephone|contact\s*number|tel/i,
        
        // Location
        city: /city|current\s*city|location|where.*located|current\s*location/i,
        state: /state|province|region/i,
        country: /country|nation/i,
        address: /address|street|residence/i,
        zip: /zip|postal|postcode|pin\s*code/i,
        
        // Professional
        company: /current\s*company|employer|organization|company\s*name|where.*work/i,
        title: /current\s*title|job\s*title|position|role|designation|current\s*position/i,
        experience: /experience|years?\s*(?:of\s*)?(?:experience|exp)|total\s*exp|work\s*exp/i,
        
        // Compensation
        salary: /salary|compensation|pay|ctc|expected\s*salary|desired\s*salary|current\s*salary/i,
        noticePeriod: /notice\s*period|availability|start\s*date|when.*start|join.*date/i,
        
        // Links
        linkedin: /linkedin|linked\s*in\s*(?:url|profile)?/i,
        portfolio: /portfolio|website|personal\s*site|personal\s*website/i,
        github: /github|git\s*hub|code\s*repository/i,
        twitter: /twitter|x\.com/i,
        otherUrl: /url|link|website/i,
        
        // Education
        degree: /degree|qualification|highest\s*education/i,
        major: /major|field\s*of\s*study|specialization|branch|stream/i,
        school: /school|university|college|institution|alma\s*mater/i,
        graduationYear: /graduation|grad\s*year|year\s*of\s*(?:graduation|passing)|passing\s*year/i,
        gpa: /gpa|cgpa|grade|percentage|marks/i,
        
        // Work Authorization
        workAuth: /work\s*(?:authorization|permit)|authorized|legally\s*(?:work|authorized)|eligible.*work/i,
        sponsorship: /sponsor|visa\s*sponsor|require.*sponsor|need.*visa/i,
        citizenship: /citizen|nationality|citizenship/i,
        
        // Preferences
        remote: /remote|work\s*from\s*home|wfh|hybrid|on-?site/i,
        relocate: /relocate|relocation|willing\s*to\s*move|open\s*to\s*relocation/i,
        travel: /travel|travelling|willing.*travel/i,
        
        // Skills
        skills: /skill|technology|proficien|expertise|competenc/i,
        languages: /language|fluent|speak/i,
        certifications: /certif|license|credential/i,
        
        // Documents
        resume: /resume|cv|curriculum\s*vitae/i,
        coverLetter: /cover\s*letter|motivation|application\s*letter/i,
        
        // Diversity & Demographics (optional)
        gender: /gender|sex/i,
        ethnicity: /ethnic|race|background/i,
        veteran: /veteran|military/i,
        disability: /disab|accommodation/i,
        
        // Application specific
        referral: /referr|how.*hear|source|where.*find/i,
        availability: /availab|when.*start|earliest.*start/i,
        reason: /why.*(?:apply|interest|join)|motivation|what.*attract/i
    };
    
    // ================================
    // YES/NO FIELD DETECTION
    // ================================
    const YES_NO_PATTERNS = {
        workAuth: { yes: /yes|authorized|eligible|have.*right/i, no: /no|not.*authorized|need.*visa/i },
        sponsorship: { yes: /yes|will\s*need|require/i, no: /no|don't\s*need|not.*require/i },
        remote: { yes: /yes|prefer.*remote|open.*remote/i, no: /no|prefer.*office|on-?site/i },
        relocate: { yes: /yes|willing|open/i, no: /no|not.*willing|prefer.*current/i },
        travel: { yes: /yes|willing|open/i, no: /no|not.*willing|prefer.*not/i },
        veteran: { yes: /yes|am.*veteran|served/i, no: /no|not.*veteran|never.*served/i },
        disability: { yes: /yes|have.*disability/i, no: /no|don't.*have/i }
    };
    
    // ================================
    // USER DATA STORAGE
    // ================================
    let userData = {
        // Personal
        firstName: '',
        lastName: '',
        email: '',
        phone: '',
        
        // Location
        city: '',
        state: '',
        country: 'United States',
        address: '',
        zip: '',
        
        // Professional
        currentCompany: '',
        currentTitle: '',
        yearsExperience: '',
        
        // Compensation
        expectedSalary: '',
        noticePeriod: '',
        
        // Links
        linkedinUrl: '',
        portfolioUrl: '',
        githubUrl: '',
        twitterUrl: '',
        
        // Education
        degree: '',
        major: '',
        school: '',
        graduationYear: '',
        gpa: '',
        
        // Work Auth
        workAuthorization: 'yes',
        sponsorship: 'no',
        citizenship: '',
        
        // Preferences
        remoteWork: 'yes',
        willingToRelocate: 'yes',
        willingToTravel: 'yes',
        
        // Skills (comma-separated)
        skills: '',
        languages: 'English',
        certifications: '',
        
        // Custom answers for specific questions
        customAnswers: {},
        
        // Learned field mappings
        learnedMappings: {}
    };
    
    // Track detected JD
    let currentJobDescription = null;
    
    // ================================
    // UTILITY FUNCTIONS
    // ================================
    function log(message, ...args) {
        if (CONFIG.DEBUG) {
            console.log(`[UniversalFormFiller] ${message}`, ...args);
        }
    }
    
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    function getCurrentPortal() {
        const url = window.location.href;
        for (const [portal, pattern] of Object.entries(PORTAL_PATTERNS)) {
            if (pattern.test(url)) {
                return portal;
            }
        }
        return 'generic';
    }
    
    function getTextContent(element) {
        if (!element) return '';
        // Get all text including aria-label and placeholder
        const text = [
            element.textContent,
            element.innerText,
            element.getAttribute('aria-label'),
            element.getAttribute('placeholder'),
            element.getAttribute('title'),
            element.getAttribute('name'),
            element.getAttribute('id')
        ].filter(Boolean).join(' ');
        return text.trim().toLowerCase();
    }
    
    function cleanLabel(text) {
        return text
            .replace(/[*:?]/g, '')  // Remove special chars
            .replace(/\s+/g, ' ')    // Normalize whitespace
            .trim()
            .toLowerCase();
    }

    function normalizeLabelCandidate(text) {
        let value = cleanLabel(String(text || ''));
        if (!value) return '';

        value = value
            .replace(/\s*\|\s*/g, ' ')
            .replace(/[\[\]{}()]/g, ' ')
            .replace(/\b[a-z0-9]+(?:[._-][a-z0-9]+){1,}\b/g, (token) => token.replace(/[._-]+/g, ' '))
            .replace(/\b(?:aria|labelledby|data|automation|widget|field|input|select|radio|checkbox|control|id|name)\b/g, ' ')
            .replace(/\b(true|false|required|optional)\b/g, ' ')
            .replace(/\b(please\s+select|select\s+an\s+option|choose\s+an\s+option)\b/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();

        value = value.replace(/\b([a-z]{2,})\b(?:\s+\1\b)+/g, '$1').trim();
        if (!value) return '';

        const alphaChars = (value.match(/[a-z]/g) || []).length;
        const totalChars = (value.match(/[a-z0-9]/g) || []).length || 1;
        if ((alphaChars / totalChars) < 0.5) return '';

        return value;
    }

    function isGarbageLabelCandidate(value) {
        const text = String(value || '').trim();
        if (!text) return true;
        if (text.length < 2) return true;
        if (/^(label|field|input|select|radio|checkbox|option|question)$/i.test(text)) return true;
        return false;
    }

    function pickBestLabelCandidate(candidates) {
        if (!Array.isArray(candidates) || !candidates.length) return '';

        const scored = candidates.map(candidate => {
            const words = candidate.split(/\s+/).filter(Boolean);
            let score = 0;

            if (words.length >= 2) score += 2;
            if (words.length >= 3) score += 2;
            if (candidate.length >= 8) score += 1;
            if (candidate.length > 120) score -= 3;
            if (/country phone code|device type|state|region|hear about us|employed/i.test(candidate)) score += 2;

            return { candidate, score };
        });

        scored.sort((a, b) => b.score - a.score || a.candidate.length - b.candidate.length);
        return scored[0]?.candidate || '';
    }

    function normalizeFieldLabelKey(label) {
        return String(label || '')
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, ' ')
            .replace(/\b(please|your|current|the|a|an|to|for|of|and|or|is|are)\b/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function getLabelTokens(label) {
        return normalizeFieldLabelKey(label)
            .split(' ')
            .map(token => token.trim())
            .filter(token => token.length > 1);
    }

    function labelSimilarity(left, right) {
        const leftTokens = getLabelTokens(left);
        const rightTokens = getLabelTokens(right);
        if (!leftTokens.length || !rightTokens.length) return 0;

        const leftSet = new Set(leftTokens);
        const rightSet = new Set(rightTokens);
        let intersection = 0;
        leftSet.forEach(token => {
            if (rightSet.has(token)) intersection += 1;
        });
        const union = new Set([...leftSet, ...rightSet]).size || 1;
        return intersection / union;
    }

    function extractCustomAnswerValue(answer) {
        if (answer === undefined || answer === null) return '';
        if (typeof answer === 'object') {
            if (answer.value !== undefined && answer.value !== null) return answer.value;
            return '';
        }
        return answer;
    }

    function resolveCustomAnswer(label) {
        const customAnswers = userData.customAnswers || {};
        if (!label || !customAnswers || typeof customAnswers !== 'object') return '';

        const direct = customAnswers[label];
        const directValue = extractCustomAnswerValue(direct);
        if (directValue !== '' && directValue !== undefined && directValue !== null) {
            return directValue;
        }

        const normalized = normalizeFieldLabelKey(label);
        if (!normalized) return '';

        const normalizedDirect = customAnswers[`@norm:${normalized}`] ?? customAnswers[normalized];
        const normalizedValue = extractCustomAnswerValue(normalizedDirect);
        if (normalizedValue !== '' && normalizedValue !== undefined && normalizedValue !== null) {
            return normalizedValue;
        }

        let bestScore = 0;
        let bestValue = '';
        for (const [key, rawVal] of Object.entries(customAnswers)) {
            const candidateValue = extractCustomAnswerValue(rawVal);
            if (candidateValue === '' || candidateValue === undefined || candidateValue === null) continue;

            const keyLabel = key.startsWith('@norm:') ? key.slice(6) : key;
            const score = labelSimilarity(normalized, keyLabel);
            if (score > bestScore) {
                bestScore = score;
                bestValue = candidateValue;
            }
        }

        if (bestScore >= 0.65) {
            log(`Using similar custom answer for "${label}" (score=${bestScore.toFixed(2)})`);
            return bestValue;
        }

        return '';
    }

    function sanitizeOptionText(value) {
        return cleanText(String(value || ''))
            .replace(/[\u00A0\t\r\n]+/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function isOptionPlaceholder(text) {
        return /^(select|choose|please select|--|none|n\/a|na)$/i.test(String(text || '').trim());
    }

    function shouldSkipEchoOption(optionText, fieldInfo) {
        const candidate = sanitizeOptionText(optionText).toLowerCase();
        if (!candidate) return true;

        const questionLabel = sanitizeOptionText(fieldInfo?.label || '').toLowerCase();
        const currentValue = sanitizeOptionText(fieldInfo?.currentValue || '').toLowerCase();

        if (questionLabel && candidate === questionLabel) return true;
        if (currentValue && candidate === currentValue) return true;

        const similarityToQuestion = questionLabel ? labelSimilarity(candidate, questionLabel) : 0;
        if (similarityToQuestion >= 0.85 && candidate.split(/\s+/).length >= 5) return true;

        if (!/\b(yes|no|true|false|decline|accept|prefer|option\s+[a-z0-9]+)\b/i.test(candidate)) {
            if (candidate.length > 80) return true;
            if (!/[a-z]/i.test(candidate)) return true;
        }

        return false;
    }

    function dedupeOptions(options, fieldInfo) {
        const unique = [];
        const seen = new Set();

        for (const raw of options || []) {
            const normalized = sanitizeOptionText(raw);
            if (!normalized) continue;
            if (isOptionPlaceholder(normalized)) continue;
            if (shouldSkipEchoOption(normalized, fieldInfo)) continue;

            const key = normalized.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            unique.push(normalized);
        }

        return unique;
    }

    function extractRadioOptionLabel(radioEl, groupLabel = '') {
        if (!radioEl) return '';

        const candidates = [];

        if (radioEl.id) {
            const explicit = document.querySelector(`label[for="${radioEl.id}"]`);
            if (explicit) candidates.push(getTextContent(explicit));
        }

        if (radioEl.getAttribute('aria-label')) {
            candidates.push(radioEl.getAttribute('aria-label'));
        }

        const parentLabel = radioEl.closest('label');
        if (parentLabel) {
            let text = getTextContent(parentLabel);
            const nested = parentLabel.querySelector('input, [role="radio"]');
            if (nested) {
                const nestedText = getTextContent(nested);
                if (nestedText) {
                    text = text.replace(nestedText, ' ').replace(/\s+/g, ' ').trim();
                }
            }
            candidates.push(text);
        }

        const siblingText = radioEl.nextElementSibling ? getTextContent(radioEl.nextElementSibling) : '';
        if (siblingText) candidates.push(siblingText);

        const rawValue = sanitizeOptionText(radioEl.value || radioEl.getAttribute('value') || '');
        if (rawValue) candidates.push(rawValue);

        const groupNormalized = sanitizeOptionText(groupLabel).toLowerCase();
        const normalizedCandidates = dedupeOptions(candidates, { label: groupLabel });

        for (const option of normalizedCandidates) {
            const optionLower = option.toLowerCase();
            if (groupNormalized && optionLower === groupNormalized) continue;
            if (groupNormalized && labelSimilarity(optionLower, groupNormalized) >= 0.85 && optionLower.split(/\s+/).length >= 4) continue;
            return option;
        }

        return '';
    }

    function getFieldOptions(info) {
        if (!info) return [];

        if (info.type === 'select') {
            const liveOptions = info.element?.options
                ? Array.from(info.element.options).map(opt => ({ value: opt.value, text: opt.text }))
                : [];
            const sourceOptions = liveOptions.length > 0
                ? liveOptions
                : (Array.isArray(info.options) ? info.options : []);

            const extracted = sourceOptions
                .map(opt => cleanText(opt?.text || opt?.value || ''))
                .filter(Boolean);
            return dedupeOptions(extracted, info);
        }

        if ((info.type === 'radio' || info.type === 'radioCustom') && Array.isArray(info.radios)) {
            const extracted = info.radios
                .map(opt => cleanText(opt?.label || opt?.value || ''))
                .filter(Boolean)
                ;
            return dedupeOptions(extracted, info);
        }

        if (info.type === 'checkbox' || info.type === 'toggle') {
            return ['yes', 'no'];
        }

        return [];
    }

    function buildUnknownFieldEntry(info, reason = 'no_answer') {
        const label = cleanText(info?.label || info?.name || info?.id || 'Unknown field');
        return {
            label,
            normalizedLabel: normalizeFieldLabelKey(label),
            type: info?.type || 'text',
            fieldType: info?.fieldType || null,
            reason,
            required: !!info?.required,
            currentValue: cleanText(readCurrentValueForVerify(info)),
            options: getFieldOptions(info),
            id: info?.id || '',
            name: info?.name || ''
        };
    }

    function findMatchingFieldInfoForUnknown(unknownField, latestElements = []) {
        if (!unknownField || !Array.isArray(latestElements) || latestElements.length === 0) return null;

        const targetNorm = normalizeFieldLabelKey(unknownField.normalizedLabel || unknownField.label || '');
        const targetType = String(unknownField.type || '').toLowerCase();
        const targetName = String(unknownField.name || '').toLowerCase();
        const targetId = String(unknownField.id || '').toLowerCase();

        let best = null;
        let bestScore = -1;

        for (const info of latestElements) {
            const infoNorm = normalizeFieldLabelKey(info?.label || info?.name || info?.id || '');
            const infoType = String(info?.type || '').toLowerCase();
            const infoName = String(info?.name || '').toLowerCase();
            const infoId = String(info?.id || '').toLowerCase();

            let score = 0;
            if (targetNorm && infoNorm) {
                if (targetNorm === infoNorm) score += 10;
                else score += labelSimilarity(targetNorm, infoNorm) * 6;
            }
            if (targetType && infoType && targetType === infoType) score += 3;
            if (targetName && infoName && targetName === infoName) score += 4;
            if (targetId && infoId && targetId === infoId) score += 4;

            if (score > bestScore) {
                bestScore = score;
                best = info;
            }
        }

        if (bestScore >= 5) return best;

        const fallback = latestElements.find(info => {
            const infoNorm = normalizeFieldLabelKey(info?.label || info?.name || info?.id || '');
            if (!targetNorm || !infoNorm) return false;
            return labelSimilarity(targetNorm, infoNorm) >= 0.45;
        });

        return fallback || null;
    }

    function refreshUnresolvedFieldsWithLatestOptions(unresolvedFields, latestElements = []) {
        if (!Array.isArray(unresolvedFields) || unresolvedFields.length === 0) return unresolvedFields;

        return unresolvedFields.map((item) => {
            const matched = findMatchingFieldInfoForUnknown(item, latestElements);
            if (!matched) return item;

            const refreshedOptions = getFieldOptions(matched);
            const refreshedValue = cleanText(readCurrentValueForVerify(matched));

            return {
                ...item,
                options: Array.isArray(refreshedOptions) ? refreshedOptions : (item.options || []),
                currentValue: refreshedValue || item.currentValue || '',
                label: cleanText(matched.label || item.label || item.name || item.id || 'Unknown field'),
                normalizedLabel: normalizeFieldLabelKey(matched.label || item.label || item.name || item.id || 'Unknown field'),
                id: matched.id || item.id || '',
                name: matched.name || item.name || '',
            };
        });
    }

    async function refreshUnresolvedFieldSnapshot(unresolvedFields) {
        if (!Array.isArray(unresolvedFields) || unresolvedFields.length === 0) return unresolvedFields;
        try {
            await sleep(Math.max(CONFIG.FILL_DELAY, 120));
            const latestContainer = detectApplicationForm();
            const latestElements = getAllFormElements(latestContainer);
            return refreshUnresolvedFieldsWithLatestOptions(unresolvedFields, latestElements);
        } catch (e) {
            log(`Unable to refresh unresolved field snapshot: ${e.message}`);
            return unresolvedFields;
        }
    }


    function normalizeUserDataForFill(data = {}) {
        const next = { ...data };
        // Coerce all expected fields to string or default
        const stringFields = [
            'firstName', 'lastName', 'middleName', 'email', 'emailAddress', 'city', 'currentCity', 'street', 'address', 'state', 'zip', 'zipcode', 'country',
            'currentCompany', 'recentEmployer', 'currentTitle', 'linkedinHeadline', 'yearsExperience', 'expectedSalary', 'desiredSalary', 'currentCtc', 'noticePeriod',
            'linkedinUrl', 'portfolioUrl', 'githubUrl', 'ethnicity', 'gender', 'disabilityStatus', 'veteranStatus', 'sponsorship', 'requireVisa', 'workAuthorization', 'usCitizenship',
            'coverLetter', 'linkedinSummary', 'userInformationAll', 'confidenceLevel'
        ];
        for (const key of stringFields) {
            if (next[key] === undefined || next[key] === null) {
                next[key] = '';
            } else if (typeof next[key] !== 'string') {
                next[key] = String(next[key]);
            }
        }

        if (!next.email && (next.emailAddress || next.emailId || next.mail)) {
            next.email = next.emailAddress || next.emailId || next.mail;
        }
        if (!next.emailAddress && next.email) next.emailAddress = next.email;

        if (!next.city && next.currentCity) next.city = next.currentCity;
        if (!next.currentCity && next.city) next.currentCity = next.city;

        if (!next.state && (next.currentState || next.stateName || next.province)) {
            next.state = next.currentState || next.stateName || next.province;
        }

        if (!next.address && (next.street || next.streetAddress || next.address1)) {
            next.address = next.street || next.streetAddress || next.address1;
        }

        if (!next.zip && (next.zipcode || next.postalCode || next.pinCode)) {
            next.zip = next.zipcode || next.postalCode || next.pinCode;
        }

        if (!next.currentCompany && next.recentEmployer) next.currentCompany = next.recentEmployer;
        if (!next.currentTitle && next.linkedinHeadline) next.currentTitle = next.linkedinHeadline;

        if (!next.country) next.country = 'United States';

        if (!next.workAuthorization && next.usCitizenship) {
            next.workAuthorization = /yes|citizen|authorized/i.test(String(next.usCitizenship)) ? 'yes' : 'no';
        }
        if (!next.sponsorship && next.requireVisa) {
            next.sponsorship = /yes|require/i.test(String(next.requireVisa)) ? 'yes' : 'no';
        }

        return next;
    }
    
    // ================================
    // LABEL DETECTION (UNIVERSAL)
    // ================================
    function findLabelForElement(element) {
        const labels = [];
        
        // 1. Explicit label via 'for' attribute
        if (element.id) {
            const explicitLabel = document.querySelector(`label[for="${element.id}"]`);
            if (explicitLabel) labels.push(getTextContent(explicitLabel));
        }
        
        // 2. Parent label
        const parentLabel = element.closest('label');
        if (parentLabel) labels.push(getTextContent(parentLabel));
        
        // 3. Aria attributes
        if (element.getAttribute('aria-label')) {
            labels.push(element.getAttribute('aria-label').toLowerCase());
        }
        if (element.getAttribute('aria-labelledby')) {
            const labelEl = document.getElementById(element.getAttribute('aria-labelledby'));
            if (labelEl) labels.push(getTextContent(labelEl));
        }
        
        // 4. Placeholder
        if (element.placeholder) {
            labels.push(element.placeholder.toLowerCase());
        }
        
        // 5. Title attribute
        if (element.title) {
            labels.push(element.title.toLowerCase());
        }
        
        // 6. Name/ID (useful for Workday, etc.)
        if (element.name) {
            labels.push(element.name.replace(/[_-]/g, ' ').toLowerCase());
        }
        if (element.id) {
            labels.push(element.id.replace(/[_-]/g, ' ').toLowerCase());
        }
        
        // 7. Search parent containers for label-like elements
        const containers = [
            element.closest('.form-group'),
            element.closest('.form-field'),
            element.closest('.field'),
            element.closest('.question'),
            element.closest('[data-field]'),
            element.closest('[class*="input"]'),
            element.closest('div')?.parentElement
        ].filter(Boolean);
        
        for (const container of containers) {
            // Look for label elements
            const containerLabels = container.querySelectorAll('label, .label, [class*="label"], legend, .question-text, h3, h4, strong');
            for (const lbl of containerLabels) {
                if (lbl !== element && !lbl.contains(element)) {
                    labels.push(getTextContent(lbl));
                }
            }
        }
        
        // 8. Previous sibling with label content
        let prev = element.previousElementSibling;
        for (let i = 0; i < 3 && prev; i++) {
            if (prev.tagName === 'LABEL' || prev.classList?.contains('label')) {
                labels.push(getTextContent(prev));
            }
            prev = prev.previousElementSibling;
        }
        
        // Prefer one clean, human-readable label instead of concatenating noisy metadata
        const normalizedCandidates = [];
        const seen = new Set();
        for (const raw of labels) {
            const candidate = normalizeLabelCandidate(raw);
            if (isGarbageLabelCandidate(candidate)) continue;
            if (seen.has(candidate)) continue;
            seen.add(candidate);
            normalizedCandidates.push(candidate);
        }

        const best = pickBestLabelCandidate(normalizedCandidates);
        if (best) return best;

        const fallback = normalizeLabelCandidate(element?.name || element?.id || element?.getAttribute?.('aria-label') || '');
        return fallback || 'unknown field';
    }
    
    // ================================
    // FIELD TYPE DETECTION
    // ================================
    function detectFieldType(label, element) {
        // Check for learned mappings first
        const learnedType = userData.learnedMappings[label];
        if (learnedType) {
            log(`Using learned mapping for "${label}": ${learnedType}`);
            return learnedType;
        }
        
        // Standard pattern matching
        for (const [fieldType, pattern] of Object.entries(FIELD_PATTERNS)) {
            if (pattern.test(label)) {
                return fieldType;
            }
        }
        
        // Check input type hints
        if (element) {
            const type = element.getAttribute('type');
            if (type === 'email') return 'email';
            if (type === 'tel') return 'phone';
            if (type === 'url') return 'otherUrl';

            const attrs = [
                element.getAttribute('autocomplete'),
                element.getAttribute('name'),
                element.getAttribute('id'),
                element.getAttribute('aria-label'),
                element.getAttribute('placeholder')
            ].filter(Boolean).join(' ').toLowerCase();

            if (/\bemail\b|e-?mail|mail\b/.test(attrs)) return 'email';
            if (/\bphone\b|mobile|cell|telephone|tel\b/.test(attrs)) return 'phone';
            if (/first.?name|given.?name|forename/.test(attrs)) return 'firstName';
            if (/last.?name|family.?name|surname/.test(attrs)) return 'lastName';
        }
        
        return null;
    }
    
    // ================================
    // UNIVERSAL FORM DETECTION
    // ================================
    function detectApplicationForm() {
        const portal = getCurrentPortal();
        log(`Detected portal: ${portal}`);
        
        // Portal-specific selectors
        const formSelectors = {
            linkedin: '.jobs-easy-apply-modal, .jobs-easy-apply-content, .artdeco-modal, .jobs-apply-form',
            indeed: '.ia-BasePage, .ia-Questions, [data-testid="questions-form"]',
            glassdoor: '.applicationForm, .apply-modal, [data-test="application-form"]',
            workday: '.mainPanelContent, [data-automation-id="applicationForm"]',
            greenhouse: '#application_form, .application--form',
            lever: '.application-form, .main-content-wrapper',
            smartrecruiters: '.jobad-application, .apply-form',
            bamboohr: '.application-form, #application-form',
            icims: '.iCIMS_MainWrapper, .apply-widget',
            generic: 'form, [role="form"]'
        };
        
        // Try portal-specific selector first
        let formContainer = null;
        if (formSelectors[portal]) {
            formContainer = document.querySelector(formSelectors[portal]);
        }
        
        // Fallback to generic form detection
        if (!formContainer) {
            // Look for forms with application-related keywords
            const forms = document.querySelectorAll('form, [role="form"], .application-form, .apply-form');
            for (const form of forms) {
                const text = getTextContent(form);
                if (text.includes('apply') || text.includes('application') || 
                    text.includes('resume') || text.includes('submit') ||
                    text.includes('candidate') || text.includes('experience')) {
                    formContainer = form;
                    break;
                }
            }
        }
        
        // Ultimate fallback - scan entire page
        if (!formContainer) {
            formContainer = document.body;
        }
        
        return formContainer;
    }
    
    // ================================
    // GET ALL FORM ELEMENTS
    // ================================
    function getAllFormElements(container = null) {
        container = container || detectApplicationForm() || document.body;
        const elements = [];
        
        // Text inputs
        container.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input:not([type])').forEach(input => {
            if (isVisibleAndEnabled(input)) {
                elements.push(createElementInfo(input, 'text'));
            }
        });
        
        // Textareas
        container.querySelectorAll('textarea').forEach(textarea => {
            if (isVisibleAndEnabled(textarea)) {
                elements.push(createElementInfo(textarea, 'textarea'));
            }
        });
        
        // Select dropdowns
        container.querySelectorAll('select').forEach(select => {
            if (isVisibleAndEnabled(select)) {
                const info = createElementInfo(select, 'select');
                info.options = Array.from(select.options).map(opt => ({
                    value: opt.value,
                    text: opt.text
                }));
                elements.push(info);
            }
        });
        
        // Radio button groups
        const radioGroups = new Map();
        container.querySelectorAll('input[type="radio"]').forEach(radio => {
            if (isVisibleAndEnabled(radio)) {
                const name = radio.name || radio.id;
                if (!radioGroups.has(name)) {
                    radioGroups.set(name, []);
                }
                radioGroups.get(name).push(radio);
            }
        });
        
        radioGroups.forEach((radios, name) => {
            const container = radios[0].closest('fieldset, .radio-group, div');
            const groupLabel = findLabelForElement(container || radios[0]);
            elements.push({
                element: container || radios[0].parentElement,
                type: 'radio',
                name: name,
                label: groupLabel,
                radios: radios.map(r => ({
                    element: r,
                    value: r.value,
                    label: extractRadioOptionLabel(r, groupLabel) || cleanText(r.value || '')
                })),
                currentValue: radios.find(r => r.checked)?.value || ''
            });
        });

        // ARIA/custom radio groups (role="radio")
        const ariaRadios = Array.from(container.querySelectorAll('[role="radio"]'))
            .filter(r => isVisibleAndEnabled(r) && !r.closest('input[type="radio"]'));
        const ariaRadioGroups = new Map();
        ariaRadios.forEach(radioEl => {
            const groupName = radioEl.getAttribute('name')
                || radioEl.getAttribute('data-name')
                || radioEl.closest('[role="radiogroup"]')?.getAttribute('aria-label')
                || radioEl.closest('[role="radiogroup"]')?.id
                || findLabelForElement(radioEl.closest('[role="radiogroup"]') || radioEl)
                || `aria-radio-${Math.random().toString(36).slice(2, 10)}`;

            if (!ariaRadioGroups.has(groupName)) ariaRadioGroups.set(groupName, []);
            ariaRadioGroups.get(groupName).push(radioEl);
        });

        ariaRadioGroups.forEach((groupOptions, name) => {
            const groupContainer = groupOptions[0].closest('[role="radiogroup"], fieldset, .radio-group, div') || groupOptions[0].parentElement;
            elements.push({
                element: groupContainer,
                type: 'radioCustom',
                name,
                label: findLabelForElement(groupContainer || groupOptions[0]),
                radios: groupOptions.map(opt => ({
                    element: opt,
                    value: cleanText(opt.getAttribute('data-value') || opt.getAttribute('value') || opt.innerText || opt.textContent || ''),
                    label: cleanText(opt.getAttribute('aria-label') || opt.innerText || opt.textContent || ''),
                    checked: opt.getAttribute('aria-checked') === 'true'
                })),
                currentValue: cleanText((groupOptions.find(opt => opt.getAttribute('aria-checked') === 'true')?.innerText || ''))
            });
        });
        
        // Checkboxes
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            if (isVisibleAndEnabled(checkbox)) {
                const info = createElementInfo(checkbox, 'checkbox');
                info.checked = checkbox.checked;
                elements.push(info);
            }
        });

        // ARIA/custom checkbox or switch controls
        container.querySelectorAll('[role="checkbox"], [role="switch"], [aria-checked]').forEach(control => {
            if (!isVisibleAndEnabled(control)) return;
            if (control.matches('input[type="checkbox"], input[type="radio"]')) return;

            const role = (control.getAttribute('role') || '').toLowerCase();
            if (role === 'radio') return;

            const info = createElementInfo(control, 'toggle');
            info.checked = control.getAttribute('aria-checked') === 'true';
            info.role = role || 'toggle';
            elements.push(info);
        });
        
        // File inputs (resume, cover letter)
        container.querySelectorAll('input[type="file"]').forEach(fileInput => {
            if (isVisibleAndEnabled(fileInput) || isFileInputCandidate(fileInput)) {
                elements.push(createElementInfo(fileInput, 'file'));
            }
        });
        
        // Custom dropdown components (Workday, etc.)
        container.querySelectorAll('[role="listbox"], [role="combobox"], .custom-select, [data-automation-id="select"]').forEach(el => {
            if (isVisibleAndEnabled(el) && !el.querySelector('select')) {
                elements.push(createElementInfo(el, 'customDropdown'));
            }
        });
        
        return elements;
    }
    
    function isVisibleAndEnabled(element) {
        if (!element) return false;
        if (element.disabled) return false;
        if (element.getAttribute('aria-hidden') === 'true') return false;
        
        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        
        // Check if element is in viewport (scrolled into view)
        const rect = element.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return false;
        
        return true;
    }

    function isFileInputCandidate(element) {
        if (!element || String(element.tagName || '').toLowerCase() !== 'input') return false;
        if (String(element.type || '').toLowerCase() !== 'file') return false;
        if (element.disabled) return false;
        if (element.getAttribute('aria-hidden') === 'true') return false;
        return true;
    }
    
    function createElementInfo(element, type) {
        const label = findLabelForElement(element);
        return {
            element: element,
            type: type,
            label: label,
            fieldType: detectFieldType(label, element),
            currentValue: type === 'checkbox' ? element.checked : (element.value || ''),
            required: element.required || element.getAttribute('aria-required') === 'true',
            id: element.id,
            name: element.name
        };
    }
    
    // ================================
    // GET ANSWER FOR FIELD
    // ================================
    function getAnswerForField(fieldType, label, elementInfo) {
        // First check custom answers
        const customAnswer = resolveCustomAnswer(label);
        if (customAnswer !== '' && customAnswer !== undefined && customAnswer !== null) {
            return customAnswer;
        }
        
        // Map field type to user data
        const fieldMapping = {
            firstName: () => userData.firstName,
            lastName: () => userData.lastName,
            fullName: () => `${userData.firstName} ${userData.lastName}`.trim(),
            email: () => userData.email,
            phone: () => userData.phone,
            city: () => userData.city,
            state: () => userData.state,
            country: () => userData.country,
            address: () => userData.address,
            zip: () => userData.zip,
            company: () => userData.currentCompany,
            title: () => userData.currentTitle,
            experience: () => userData.yearsExperience,
            salary: () => userData.expectedSalary,
            noticePeriod: () => userData.noticePeriod,
            linkedin: () => userData.linkedinUrl,
            portfolio: () => userData.portfolioUrl,
            github: () => userData.githubUrl,
            twitter: () => userData.twitterUrl,
            otherUrl: () => userData.portfolioUrl || userData.linkedinUrl,
            degree: () => userData.degree,
            major: () => userData.major,
            school: () => userData.school,
            graduationYear: () => userData.graduationYear,
            gpa: () => userData.gpa,
            workAuth: () => userData.workAuthorization,
            sponsorship: () => userData.sponsorship,
            citizenship: () => userData.citizenship,
            remote: () => userData.remoteWork,
            relocate: () => userData.willingToRelocate,
            travel: () => userData.willingToTravel,
            skills: () => userData.skills,
            languages: () => userData.languages,
            certifications: () => userData.certifications,
            veteran: () => 'no',  // Default
            disability: () => 'no',  // Default
            gender: () => '',  // Leave blank for privacy
            ethnicity: () => '',  // Leave blank for privacy
            referral: () => 'Online Job Search',
            availability: () => userData.noticePeriod || 'Immediately',
            reason: () => ''  // Leave for custom or AI
        };
        
        if (fieldMapping[fieldType]) {
            return fieldMapping[fieldType]();
        }
        
        return '';
    }
    
    // ================================
    // FORM FILLING LOGIC
    // ================================
    async function fillTextInput(element, value) {
        if (!value || element.value === value) return false;
        
        element.focus();
        await sleep(30);
        
        // Clear existing value
        element.value = '';
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(20);
        
        // Set value
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        element.dispatchEvent(new Event('blur', { bubbles: true }));
        
        log(`Filled text: "${value.substring(0, 30)}..."`);
        return true;
    }
    
    async function selectDropdownOption(select, targetValue, info = null) {
        if (!select || targetValue === undefined || targetValue === null || String(targetValue).trim() === '') {
            return false;
        }

        const options = Array.from(select.options);
        const targetLower = String(targetValue).toLowerCase().trim();
        const label = cleanText(info?.label || info?.name || info?.id || '').toLowerCase();
        const isLocationField = /state|province|region|country|nation|city|location/.test(label)
            || ['state', 'country', 'city'].includes(String(info?.fieldType || '').toLowerCase());
        
        // Exact match
        let matched = options.find(opt => 
            opt.value.toLowerCase() === targetLower ||
            opt.text.toLowerCase() === targetLower
        );
        
        // Partial match
        if (!matched) {
            matched = options.find(opt => 
                opt.text.toLowerCase().includes(targetLower) ||
                targetLower.includes(opt.text.toLowerCase())
            );
        }
        
        // Numeric match (for experience, etc.)
        if (!matched && !isNaN(targetValue)) {
            const num = parseInt(targetValue);
            matched = options.find(opt => {
                const optNum = parseInt(opt.text);
                return !isNaN(optNum) && Math.abs(optNum - num) <= 2;
            });
        }

        // Yes/No semantic match for boolean-like answers
        if (!matched) {
            const isYes = /^(yes|true|1|checked|y)$/i.test(String(targetValue || '').trim());
            const isNo = /^(no|false|0|unchecked|n)$/i.test(String(targetValue || '').trim());
            if (isYes || isNo) {
                const yesPattern = /\b(yes|true|authorized|agree|accept|eligible)\b/i;
                const noPattern = /\b(no|false|decline|disagree|not\s+authorized|ineligible)\b/i;
                matched = options.find(opt => {
                    const candidate = `${opt.text || ''} ${opt.value || ''}`.trim();
                    return isYes ? yesPattern.test(candidate) : noPattern.test(candidate);
                });
            }
        }
        
        // Never force-select arbitrary fallback for location-like fields
        if (!matched && isLocationField) {
            log(`No safe location match for "${label}" with value "${targetValue}"`);
            return false;
        }
        
        if (matched) {
            select.value = matched.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            log(`Selected: "${matched.text}"`);
            return true;
        }
        
        return false;
    }
    
    async function selectRadioOption(elementInfo, targetValue, options = {}) {
        const radios = elementInfo.radios || [];
        const targetLower = String(targetValue || '').toLowerCase();
        const allowUnsafeFallback = options.allowUnsafeFallback !== false;
        
        // Find matching radio
        let matched = radios.find(r => {
            const rVal = r.value.toLowerCase();
            const rLabel = (r.label || '').toLowerCase();
            return rVal === targetLower || rLabel.includes(targetLower);
        });
        
        // Yes/No logic
        if (!matched) {
            const yesPatterns = /^yes$|^y$|^true$|agree|accept|authorized|eligible/i;
            const noPatterns = /^no$|^n$|^false$|disagree|decline|not.*authorized/i;
            
            if (yesPatterns.test(targetValue)) {
                matched = radios.find(r => yesPatterns.test(r.value) || yesPatterns.test(r.label));
            } else if (noPatterns.test(targetValue)) {
                matched = radios.find(r => noPatterns.test(r.value) || noPatterns.test(r.label));
            }
        }
        
        // Default to first option only for generic autofill (not explicit saved unknown answers)
        if (!matched && allowUnsafeFallback && radios.length > 0) {
            matched = radios[0];
        }
        
        if (matched) {
            matched.element.click();
            log(`Selected radio: "${matched.label || matched.value}"`);
            return true;
        }
        
        return false;
    }
    
    async function fillCheckbox(element, shouldCheck) {
        const isChecked = element.checked;
        if ((shouldCheck && !isChecked) || (!shouldCheck && isChecked)) {
            element.click();
            log(`Toggled checkbox`);
            return true;
        }
        return false;
    }

    async function fillAriaToggle(element, shouldCheck) {
        if (!element) return false;
        const current = element.getAttribute('aria-checked') === 'true';
        if (current === shouldCheck) return false;

        element.scrollIntoView({ block: 'center', behavior: 'smooth' });
        element.click();
        await sleep(80);

        // Fallback for custom controls that require keyboard interaction
        const nowChecked = element.getAttribute('aria-checked') === 'true';
        if (nowChecked !== shouldCheck) {
            element.focus();
            element.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
            element.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', bubbles: true }));
        }

        log(`Toggled aria control to ${shouldCheck ? 'checked' : 'unchecked'}`);
        return true;
    }

    async function selectAriaRadioOption(elementInfo, targetValue, options = {}) {
        const radios = elementInfo.radios || [];
        if (!radios.length) return false;
        const allowUnsafeFallback = options.allowUnsafeFallback !== false;

        const targetLower = String(targetValue || '').toLowerCase().trim();
        let matched = radios.find(r => {
            const val = String(r.value || '').toLowerCase();
            const lbl = String(r.label || '').toLowerCase();
            return val === targetLower || lbl === targetLower || lbl.includes(targetLower) || targetLower.includes(lbl);
        });

        if (!matched) {
            const yesPatterns = /^yes$|^y$|^true$|agree|accept|authorized|eligible/i;
            const noPatterns = /^no$|^n$|^false$|disagree|decline|not.*authorized/i;
            if (yesPatterns.test(targetValue)) {
                matched = radios.find(r => yesPatterns.test(r.value || '') || yesPatterns.test(r.label || ''));
            } else if (noPatterns.test(targetValue)) {
                matched = radios.find(r => noPatterns.test(r.value || '') || noPatterns.test(r.label || ''));
            }
        }

        if (!matched && allowUnsafeFallback) matched = radios[0];
        if (!matched || !matched.element) return false;

        matched.element.scrollIntoView({ block: 'center', behavior: 'smooth' });
        matched.element.click();
        await sleep(80);
        log(`Selected custom radio: "${matched.label || matched.value}"`);
        return true;
    }

    function isResumeFileField(label = '', element = null) {
        const source = String(label || '') + ' ' + String(element?.name || '') + ' ' + String(element?.id || '');
        const normalized = source.toLowerCase();
        if (!normalized.trim()) return true;
        if (FIELD_PATTERNS.resume.test(normalized) || /curriculum|cv\b/i.test(normalized)) return true;
        return /attach|upload|document|supporting|cover\s*letter|file/i.test(normalized);
    }

    function buildFileFromPayload(resumeUpload) {
        if (!resumeUpload || !Array.isArray(resumeUpload.fileBytes) || !resumeUpload.fileBytes.length) {
            return null;
        }
        const bytes = new Uint8Array(resumeUpload.fileBytes);
        const fileName = String(resumeUpload.fileName || 'resume.docx');
        const fileType = String(resumeUpload.fileType || 'application/octet-stream');
        return new File([bytes], fileName, { type: fileType, lastModified: Date.now() });
    }

    async function fillResumeFileInputs(elements, resumeUpload) {
        const file = buildFileFromPayload(resumeUpload);
        if (!file) return 0;

        let fileInputs = (elements || []).filter(info => info && info.type === 'file' && info.element);
        if (!fileInputs.length) {
            const fallbackInputs = Array.from(document.querySelectorAll('input[type="file"]'))
                .filter(input => isFileInputCandidate(input))
                .map(input => createElementInfo(input, 'file'));
            fileInputs = fallbackInputs;
        }
        if (!fileInputs.length) return 0;

        let uploaded = 0;
        for (const info of fileInputs) {
            const input = info.element;
            if (!input || input.tagName !== 'INPUT' || String(input.type).toLowerCase() !== 'file') continue;

            if (!isResumeFileField(info.label, input)) {
                continue;
            }

            try {
                const dt = new DataTransfer();
                dt.items.add(file);
                input.files = dt.files;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                uploaded++;
                log(`Uploaded resume file to field: "${info.label || input.name || input.id || 'file input'}"`);
                await sleep(Math.max(80, CONFIG.FILL_DELAY));
            } catch (e) {
                log(`Failed to upload resume in field "${info.label}": ${e.message}`);
            }
        }

        if (uploaded === 0 && fileInputs.length > 0) {
            // Fallback: when portals do not clearly label the file input as resume,
            // attach to first available upload control so Auto Pilot can proceed.
            const first = fileInputs.find(info => info?.element && String(info.element.type).toLowerCase() === 'file');
            if (first?.element) {
                try {
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    first.element.files = dt.files;
                    first.element.dispatchEvent(new Event('input', { bubbles: true }));
                    first.element.dispatchEvent(new Event('change', { bubbles: true }));
                    uploaded = 1;
                } catch {
                    // keep uploaded=0
                }
            }
        }

        return uploaded;
    }
    
    // ================================
    // MAIN FILL FUNCTION (ENHANCED - JOBRIGHT STYLE)
    // ================================
    async function fillAllForms(options = {}) {
        // Reload user data to ensure we have latest
        await loadUserData();
        
        const container = detectApplicationForm();
        const elements = getAllFormElements(container);
        const prioritizedElements = [...elements].sort((a, b) => getFieldFillPriority(a) - getFieldFillPriority(b));
        
        let filled = 0;
        let total = elements.length;
        let skipped = 0;
        let verified = 0;
        let retried = 0;
        let verificationFailed = 0;
        let fileUploaded = 0;
        const unresolvedFields = [];
        const unresolvedKeys = new Set();
        const strictVerify = CONFIG.STRICT_VERIFY_PASS === true;
        const maxAttempts = 1 + Math.max(0, Number(CONFIG.VERIFY_RETRY_COUNT) || 0);
        const verificationTargets = [];
        
        log(`Found ${total} form elements on ${getCurrentPortal()}`);
        log(`User data loaded: firstName="${userData.firstName}", email="${userData.email}"`);
        
        for (const info of prioritizedElements) {
            // Skip file inputs - need separate handling
            if (info.type === 'file') {
                continue;
            }
            
            // Get field type
            let fieldType = info.fieldType;
            
            // Smart field type detection if not detected
            if (!fieldType) {
                fieldType = smartDetectFieldType(info.label, info.element);
                if (fieldType) {
                    log(`Smart detected field type for "${info.label}": ${fieldType}`);
                }
            }
            
            // Get answer
            const answer = getAnswerForField(fieldType, info.label, info);
            
            // Even if no fieldType, try smart default answers
            const smartAnswer = answer || getSmartDefaultAnswer(info.label, info);
            
            if (!smartAnswer && info.type !== 'checkbox') {
                log(`No answer for: "${info.label}" (type: ${fieldType || 'unknown'})`);
                const unknown = buildUnknownFieldEntry(info, 'no_answer');
                const key = `${unknown.normalizedLabel}::${unknown.type}::${unknown.name || unknown.id || ''}`;
                if (!unresolvedKeys.has(key)) {
                    unresolvedKeys.add(key);
                    unresolvedFields.push(unknown);
                }
                continue;
            }
            
            try {
                let expectedValue = smartAnswer;
                if (info.type === 'radio' || info.type === 'radioCustom') {
                    expectedValue = smartAnswer || getDefaultRadioAnswer(info.label);
                } else if (info.type === 'checkbox' || info.type === 'toggle') {
                    expectedValue = smartAnswer === 'yes' || smartAnswer === true || smartAnswer === 'true' || shouldCheckByDefault(info.label);
                }

                if (strictVerify) {
                    verificationTargets.push({ info, expectedValue, label: info.label || info.name || info.id || 'unknown field' });
                }

                if ((info.type === 'text' || info.type === 'textarea') && info.currentValue === smartAnswer) {
                    skipped++;
                    if (strictVerify && verifyFieldFilled(info, expectedValue)) {
                        verified++;
                    }
                    continue;
                }

                let fieldVerified = !strictVerify;
                let countedFilled = false;

                for (let attempt = 0; attempt < maxAttempts; attempt++) {
                    let success = false;

                    switch (info.type) {
                        case 'text':
                        case 'textarea':
                            success = await fillTextInput(info.element, smartAnswer);
                            break;

                        case 'select':
                            success = await selectDropdownOption(info.element, smartAnswer, info);
                            break;

                        case 'radio':
                            success = await selectRadioOption(info, expectedValue);
                            break;

                        case 'radioCustom':
                            success = await selectAriaRadioOption(info, expectedValue);
                            break;

                        case 'checkbox':
                            success = await fillCheckbox(info.element, expectedValue === true);
                            break;

                        case 'toggle':
                            success = await fillAriaToggle(info.element, expectedValue === true);
                            break;

                        case 'customDropdown':
                            success = await handleCustomDropdown(info.element, smartAnswer);
                            break;
                    }

                    if (success && !countedFilled) {
                        filled++;
                        countedFilled = true;
                    }

                    if (success) {
                        await sleep(CONFIG.FILL_DELAY);
                    }

                    if (!strictVerify) {
                        break;
                    }

                    fieldVerified = verifyFieldFilled(info, expectedValue);
                    if (fieldVerified) {
                        verified++;
                        break;
                    }

                    if (attempt < maxAttempts - 1) {
                        retried++;
                        log(`Verification retry ${attempt + 1}/${maxAttempts - 1} for: "${info.label}"`);
                        await sleep(120);
                    }
                }

                if (strictVerify && !fieldVerified) {
                    verificationFailed++;
                    log(`Verification failed for: "${info.label}"`);
                    const unknown = buildUnknownFieldEntry(info, 'verification_failed');
                    const key = `${unknown.normalizedLabel}::${unknown.type}::${unknown.name || unknown.id || ''}`;
                    if (!unresolvedKeys.has(key)) {
                        unresolvedKeys.add(key);
                        unresolvedFields.push(unknown);
                    }
                }
            } catch (e) {
                log(`Error filling ${info.label}: ${e.message}`);
                const unknown = buildUnknownFieldEntry(info, 'error');
                const key = `${unknown.normalizedLabel}::${unknown.type}::${unknown.name || unknown.id || ''}`;
                if (!unresolvedKeys.has(key)) {
                    unresolvedKeys.add(key);
                    unresolvedFields.push(unknown);
                }
            }
        }

        if (strictVerify && verificationTargets.length) {
            let postPassFailures = 0;
            for (const target of verificationTargets) {
                if (!verifyFieldFilled(target.info, target.expectedValue)) {
                    postPassFailures++;
                    log(`Post-pass verification failed: "${target.label}"`);
                }
            }
            verificationFailed = Math.max(verificationFailed, postPassFailures);
        }

        if (options.resumeUpload) {
            fileUploaded = await fillResumeFileInputs(elements, options.resumeUpload);
        }

        const finalUnresolvedFields = await refreshUnresolvedFieldSnapshot(unresolvedFields);
        
        log(`Filled ${filled} of ${total} fields (${skipped} skipped)`);
        if (strictVerify) {
            log(`Verification summary: verified=${verified}, retried=${retried}, failed=${verificationFailed}`);
        }
        return {
            filled,
            total,
            skipped,
            verified,
            retried,
            verificationFailed,
            fileUploaded,
            unresolvedFields: finalUnresolvedFields,
            strictVerify,
            portal: getCurrentPortal()
        };
    }

    async function fillUnknownAnswersInPage(answers = []) {
        await loadUserData();

        const validAnswers = Array.isArray(answers)
            ? answers.filter(item => item && String(item.answer || '').trim())
            : [];

        if (!validAnswers.length) {
            return {
                success: true,
                filled: 0,
                total: 0,
                unresolvedFields: [],
                portal: getCurrentPortal(),
            };
        }

        const container = detectApplicationForm();
        const elements = getAllFormElements(container);
        const unresolvedFields = [];
        const unresolvedKeys = new Set();
        let filled = 0;

        for (const entry of validAnswers) {
            const unknown = {
                label: cleanText(entry.label || entry.normalizedLabel || entry.name || entry.id || 'Unknown field'),
                normalizedLabel: normalizeFieldLabelKey(entry.normalizedLabel || entry.label || ''),
                type: entry.type || 'text',
                fieldType: entry.fieldType || null,
                name: entry.name || '',
                id: entry.id || '',
            };

            const info = findMatchingFieldInfoForUnknown(unknown, elements);
            if (!info) {
                const fallbackUnknown = {
                    ...unknown,
                    reason: 'field_not_found',
                    required: false,
                    currentValue: '',
                    options: [],
                };
                const key = `${fallbackUnknown.normalizedLabel}::${fallbackUnknown.type}::${fallbackUnknown.name || fallbackUnknown.id || ''}`;
                if (!unresolvedKeys.has(key)) {
                    unresolvedKeys.add(key);
                    unresolvedFields.push(fallbackUnknown);
                }
                continue;
            }

            const rawAnswer = String(entry.answer || '').trim();
            let success = false;
            try {
                switch (info.type) {
                    case 'text':
                    case 'textarea':
                        success = await fillTextInput(info.element, rawAnswer);
                        break;
                    case 'select':
                        success = await selectDropdownOption(info.element, rawAnswer, info);
                        break;
                    case 'radio':
                        success = await selectRadioOption(info, rawAnswer, { allowUnsafeFallback: false });
                        break;
                    case 'radioCustom':
                        success = await selectAriaRadioOption(info, rawAnswer, { allowUnsafeFallback: false });
                        break;
                    case 'checkbox': {
                        const shouldCheck = /^(yes|true|1|checked)$/i.test(rawAnswer);
                        success = await fillCheckbox(info.element, shouldCheck);
                        break;
                    }
                    case 'toggle': {
                        const shouldCheck = /^(yes|true|1|checked)$/i.test(rawAnswer);
                        success = await fillAriaToggle(info.element, shouldCheck);
                        break;
                    }
                    case 'customDropdown':
                        success = await handleCustomDropdown(info.element, rawAnswer);
                        break;
                    default:
                        success = await fillTextInput(info.element, rawAnswer);
                        break;
                }
            } catch {
                success = false;
            }

            const expectedValue = (info.type === 'checkbox' || info.type === 'toggle')
                ? /^(yes|true|1|checked)$/i.test(rawAnswer)
                : rawAnswer;
            const verified = verifyFieldFilled(info, expectedValue);
            if (success || verified) {
                filled += 1;
                await sleep(Math.max(CONFIG.FILL_DELAY, 80));
                continue;
            }

            const unresolved = buildUnknownFieldEntry(info, 'verification_failed');
            const key = `${unresolved.normalizedLabel}::${unresolved.type}::${unresolved.name || unresolved.id || ''}`;
            if (!unresolvedKeys.has(key)) {
                unresolvedKeys.add(key);
                unresolvedFields.push(unresolved);
            }
        }

        const finalUnresolvedFields = await refreshUnresolvedFieldSnapshot(unresolvedFields);
        return {
            success: true,
            filled,
            total: validAnswers.length,
            unresolvedFields: finalUnresolvedFields,
            portal: getCurrentPortal(),
        };
    }
    
    // Smart field type detection for edge cases
    function getFieldFillPriority(info) {
        const fieldType = String(info?.fieldType || '').toLowerCase();
        const label = cleanText(info?.label || info?.name || info?.id || '').toLowerCase();

        if (fieldType === 'country' || /country|nation/.test(label)) return 1;
        if (fieldType === 'state' || /state|province|region/.test(label)) return 2;
        if (fieldType === 'city' || /city|location/.test(label)) return 3;
        if (fieldType === 'zip' || /zip|postal|pin/.test(label)) return 4;
        return 50;
    }

    function smartDetectFieldType(label, element) {
        const lbl = String(label || '').toLowerCase();
        const attrText = [
            element?.getAttribute?.('name') || '',
            element?.getAttribute?.('id') || '',
            element?.getAttribute?.('aria-label') || '',
            element?.getAttribute?.('placeholder') || '',
            element?.getAttribute?.('autocomplete') || '',
            element?.getAttribute?.('type') || ''
        ].join(' ').toLowerCase();
        const source = `${lbl} ${attrText}`.trim();
        if (!source) return null;
        
        // Name variations
        if (/^name$|your name|applicant name|candidate name/i.test(source)) return 'fullName';
        if (/first|given|forename/i.test(source) && /name/i.test(source)) return 'firstName';
        if (/last|family|surname/i.test(source) && /name/i.test(source)) return 'lastName';
        
        // Contact
        if (/email|e-mail|mail|autocomplete\s*email|\btype\s*email\b/i.test(source)) return 'email';
        if (/phone|mobile|cell|telephone|contact.*number|autocomplete\s*tel|\btype\s*tel\b/i.test(source)) return 'phone';
        
        // Location
        if (/city|location/i.test(source)) return 'city';
        if (/state|province/i.test(source)) return 'state';
        if (/country/i.test(source)) return 'country';
        if (/address|street/i.test(source)) return 'address';
        if (/zip|postal/i.test(source)) return 'zip';
        
        // Professional
        if (/company|employer|organization/i.test(source)) return 'company';
        if (/title|position|role|designation/i.test(source)) return 'title';
        if (/experience|years/i.test(source)) return 'experience';
        if (/salary|compensation|pay|ctc/i.test(source)) return 'salary';
        if (/notice|availability|start.*date/i.test(source)) return 'noticePeriod';
        
        // Links
        if (/linkedin/i.test(source)) return 'linkedin';
        if (/portfolio|website/i.test(source)) return 'portfolio';
        if (/github/i.test(source)) return 'github';
        
        // Education
        if (/degree|qualification/i.test(source)) return 'degree';
        if (/major|field|study/i.test(source)) return 'major';
        if (/school|university|college|institution/i.test(source)) return 'school';
        if (/graduation|grad.*year/i.test(source)) return 'graduationYear';
        
        // Work Authorization
        if (/authorized|eligible.*work|work.*authorization/i.test(source)) return 'workAuth';
        if (/sponsor|visa/i.test(source)) return 'sponsorship';
        
        // Preferences
        if (/remote|work from home|wfh/i.test(source)) return 'remote';
        if (/relocate|relocation/i.test(source)) return 'relocate';
        if (/travel/i.test(source)) return 'travel';
        
        return null;
    }
    
    // Smart default answers for common questions
    function getSmartDefaultAnswer(label, info) {
        if (!label) return '';
        const lbl = label.toLowerCase();
        
        // Common yes/no questions
        const yesQuestions = [
            'authorized', 'eligible', 'legally', 'right to work',
            'over 18', '18 years', 'legal age', 'willing to',
            'agree', 'accept', 'acknowledge', 'consent',
            'can you', 'able to', 'available'
        ];
        
        const noQuestions = [
            'require sponsor', 'need visa', 'convicted', 'felony',
            'terminated', 'fired', 'disciplinary'
        ];
        
        for (const q of yesQuestions) {
            if (lbl.includes(q)) return 'yes';
        }
        
        for (const q of noQuestions) {
            if (lbl.includes(q)) return 'no';
        }
        
        // How did you hear about us
        if (/how.*hear|how.*find|source|referral|where.*find/i.test(lbl)) {
            return 'Online Job Search';
        }
        
        // Reason for leaving/applying
        if (/reason.*applying|why.*interested/i.test(lbl)) {
            return 'Looking for new opportunities to grow professionally';
        }
        
        return '';
    }
    
    // Default radio answer based on question
    function getDefaultRadioAnswer(label) {
        if (!label) return 'yes';
        const lbl = label.toLowerCase();
        
        // Questions where "yes" is usually appropriate
        if (/authorized|eligible|willing|available|agree|accept|can you|able to/i.test(lbl)) {
            return 'yes';
        }
        
        // Questions where "no" is usually appropriate
        if (/sponsor|convicted|felony|terminated/i.test(lbl)) {
            return 'no';
        }
        
        return 'yes'; // Default to yes
    }
    
    // Should checkbox be checked by default
    function shouldCheckByDefault(label) {
        if (!label) return false;
        const lbl = label.toLowerCase();
        
        // Agree/accept checkboxes should be checked
        if (/agree|accept|acknowledge|consent|terms|policy|certify|confirm/i.test(lbl)) {
            return true;
        }
        
        return false;
    }

    function normalizeForVerify(value) {
        if (value === undefined || value === null) return '';
        if (typeof value === 'boolean') return value;
        const normalized = String(value).toLowerCase().trim();
        if (normalized === 'true' || normalized === 'yes' || normalized === 'y' || normalized === '1') return true;
        if (normalized === 'false' || normalized === 'no' || normalized === 'n' || normalized === '0') return false;
        return normalized.replace(/\s+/g, ' ');
    }

    function readCurrentValueForVerify(info) {
        if (!info || !info.element) return '';

        if (info.type === 'text' || info.type === 'textarea') {
            return info.element.value || '';
        }

        if (info.type === 'select') {
            const selected = info.element.options?.[info.element.selectedIndex];
            return selected ? (selected.text || selected.value || '') : (info.element.value || '');
        }

        if (info.type === 'radio' || info.type === 'radioCustom') {
            const options = info.radios || [];
            const selected = options.find(opt => {
                const el = opt.element;
                if (!el) return false;
                if (el.type === 'radio') return !!el.checked;
                return el.getAttribute('aria-checked') === 'true';
            });
            return selected ? (selected.label || selected.value || '') : '';
        }

        if (info.type === 'checkbox') {
            return !!info.element.checked;
        }

        if (info.type === 'toggle') {
            return info.element.getAttribute('aria-checked') === 'true';
        }

        if (info.type === 'customDropdown') {
            return info.element.getAttribute('aria-label')
                || info.element.textContent
                || info.element.innerText
                || '';
        }

        return info.element.value || '';
    }

    function verifyFieldFilled(info, expectedValue) {
        if (!info || !info.element) return true;
        if (expectedValue === undefined || expectedValue === null) return true;

        const expected = normalizeForVerify(expectedValue);
        const current = normalizeForVerify(readCurrentValueForVerify(info));

        if (typeof expected === 'boolean') {
            return current === expected;
        }

        const expectedText = String(expected || '').trim();
        if (!expectedText) return true;

        const currentText = String(current || '').trim();
        if (!currentText) return false;

        return currentText === expectedText
            || currentText.includes(expectedText)
            || expectedText.includes(currentText);
    }
    
    async function handleCustomDropdown(element, value) {
        if (!value) return false;
        // Click to open dropdown
        element.click();
        await sleep(200);
        
        // Look for options
        const options = document.querySelectorAll('[role="option"], .dropdown-item, .option, li[data-value]');
        const targetLower = value.toLowerCase();
        
        for (const opt of options) {
            const optText = getTextContent(opt);
            if (optText.includes(targetLower) || targetLower.includes(optText)) {
                opt.click();
                log(`Selected custom dropdown: ${optText}`);
                return true;
            }
        }
        
        // Close dropdown if not matched
        document.body.click();
        return false;
    }

    function cleanText(value) {
        return String(value || '').replace(/\s+/g, ' ').trim();
    }

    function normalizeJdText(value) {
        return String(value || '')
            .replace(/\r/g, '\n')
            .replace(/[ \t]+/g, ' ')
            .replace(/\n{3,}/g, '\n\n')
            .trim();
    }

    function dedupeParagraphs(value) {
        const seen = new Set();
        const out = [];
        const blocks = String(value || '')
            .split(/\n{2,}|(?=\b(?:Our Company|The Opportunity|What you(?:\'|’)ll do|What you will do|What you need to succeed|Requirements|Responsibilities|Bonus)\b)/gi)
            .map(block => normalizeJdText(block))
            .filter(Boolean);

        for (const block of blocks) {
            const key = block.toLowerCase().replace(/[^a-z0-9\s]/g, '').slice(0, 180);
            if (!key || seen.has(key)) continue;
            seen.add(key);
            out.push(block);
        }

        return out.join('\n\n').trim();
    }

    function extractSalaryRange(text, jsonLdSalary) {
        const fromLd = (() => {
            const raw = jsonLdSalary;
            if (!raw) return '';
            if (typeof raw === 'object') {
                const minVal = raw?.minValue || raw?.value?.minValue;
                const maxVal = raw?.maxValue || raw?.value?.maxValue;
                const unit = raw?.unitText || raw?.value?.unitText || '';
                if (minVal && maxVal) {
                    const minFmt = Number(minVal).toLocaleString('en-US');
                    const maxFmt = Number(maxVal).toLocaleString('en-US');
                    const unitSuffix = unit ? ` ${String(unit).trim()}` : '';
                    return `$${minFmt} - $${maxFmt}${unitSuffix}`;
                }
            }
            return cleanText(raw);
        })();
        if (fromLd) return fromLd;

        const source = String(text || '');
        const rangeRegex = /([$€£]\s?\d[\d,]*(?:\.\d+)?\s*(?:-|–|—|to)\s*[$€£]?\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)/gi;
        const ranges = Array.from(source.matchAll(rangeRegex)).map(m => cleanText(m[1] || ''));
        const unique = [...new Set(ranges)].filter(Boolean);
        if (unique.length) return unique[0];

        const singleRegex = /([$€£]\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)/i;
        const single = source.match(singleRegex);
        return single ? cleanText(single[1]) : '';
    }

    function extractVisaStatus(text) {
        const source = String(text || '');
        const line = source.match(/(visa\s*sponsorship[^\n.]{0,140}|sponsorship[^\n.]{0,140}|work\s+authorization[^\n.]{0,140})/i);
        if (!line) return 'Not specified';
        const sentence = cleanText(line[1]);
        if (/no\s+sponsorship|not\s+available|will\s+not\s+sponsor|cannot\s+sponsor/i.test(sentence)) {
            return 'Not sponsored';
        }
        if (/sponsorship\s+available|will\s+sponsor|can\s+sponsor|require\s+sponsorship|visa\s+support/i.test(sentence)) {
            return 'Sponsorship available';
        }
        return sentence || 'Not specified';
    }

    function extractSectionFromJD(text, headings) {
        const escaped = headings.map(h => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const pattern = new RegExp(`(?:^|\\n)\\s*(?:${escaped.join('|')})\\s*:?\\s*([\\s\\S]{40,2200}?)(?=\\n\\s*[A-Z][^\\n]{2,50}:?|$)`, 'i');
        const match = text.match(pattern);
        return match ? cleanText(match[1]) : '';
    }

    function splitStructuredList(value, maxItems = 10) {
        if (!value) return [];
        return String(value)
            .split(/\n|•|-\s+/g)
            .map(item => cleanText(item))
            .filter(item => item.length > 2)
            .slice(0, maxItems);
    }

    function parseJobPostingJsonLd() {
        const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
        for (const script of scripts) {
            try {
                const parsed = JSON.parse(script.textContent || '{}');
                const candidates = Array.isArray(parsed)
                    ? parsed
                    : parsed['@graph'] && Array.isArray(parsed['@graph'])
                        ? parsed['@graph']
                        : [parsed];

                const posting = candidates.find(item => {
                    const typeValue = item?.['@type'];
                    if (!typeValue) return false;
                    if (Array.isArray(typeValue)) {
                        return typeValue.some(type => String(type).toLowerCase() === 'jobposting');
                    }
                    return String(typeValue).toLowerCase() === 'jobposting';
                });

                if (posting) {
                    return posting;
                }
            } catch {
                continue;
            }
        }
        return null;
    }

    function decodeHtmlToText(value) {
        if (!value) return '';
        const div = document.createElement('div');
        const normalized = String(value)
            .replace(/<\s*br\s*\/?>/gi, '\n')
            .replace(/<\s*\/\s*(p|div|li|h1|h2|h3|h4|h5|h6|section|article)\s*>/gi, '\n');
        div.innerHTML = normalized;
        return cleanText(div.textContent || div.innerText || '');
    }

    function extractTextFromPageData() {
        const scriptCandidates = [
            document.getElementById('__NEXT_DATA__'),
            document.querySelector('script#__NEXT_DATA__'),
            ...Array.from(document.querySelectorAll('script[type="application/json"]')),
        ].filter(Boolean);

        for (const script of scriptCandidates) {
            try {
                const raw = script.textContent || '';
                if (!raw || raw.length < 200) continue;
                const parsed = JSON.parse(raw);
                const bag = [];

                const walk = (node, depth = 0) => {
                    if (!node || depth > 10) return;
                    if (typeof node === 'string') {
                        const val = decodeHtmlToText(node);
                        if (val.length > 250 && /(responsibilities|requirements|qualifications|experience|about the role|what you[’']?ll do|skills)/i.test(val)) {
                            bag.push(val);
                        }
                        return;
                    }
                    if (Array.isArray(node)) {
                        node.forEach(item => walk(item, depth + 1));
                        return;
                    }
                    if (typeof node === 'object') {
                        for (const [key, value] of Object.entries(node)) {
                            if (/description|jobdescription|job_description|responsibilit|qualification|requirement/i.test(String(key))) {
                                walk(value, depth + 1);
                            }
                        }
                    }
                };

                walk(parsed);
                const best = bag.sort((a, b) => b.length - a.length)[0] || '';
                if (best.length > 300) {
                    return best;
                }
            } catch {
                continue;
            }
        }

        return '';
    }

    function mergeUniqueParagraphs(primaryText, secondaryText) {
        const normalize = value => cleanText(value).toLowerCase().replace(/[^a-z0-9\s]/g, '').trim();
        const existing = new Set();
        const merged = [];

        const ingest = (text) => {
            const parts = String(text || '')
                .split(/\n{2,}|\n(?=[•\-*])|(?<=[.!?])\s+(?=[A-Z])/g)
                .map(p => cleanText(p))
                .filter(p => p.length > 30);
            for (const part of parts) {
                const key = normalize(part);
                if (!key || key.length < 25 || existing.has(key)) continue;
                existing.add(key);
                merged.push(part);
            }
        };

        ingest(primaryText);
        ingest(secondaryText);
        return merged.join('\n\n').trim();
    }

    function trimToCoreJobDescription(text) {
        const source = String(text || '');
        if (!source.trim()) return '';

        const startPatterns = [
            /\bjob\s+description\b/i,
            /\bour\s+company\b/i,
            /\bthe\s+opportunity\b/i,
            /\bwhat\s+you\s+(?:will\s+)?do\b/i,
        ];
        const endPatterns = [
            /\bsimilar\s+jobs\b/i,
            /\bshare\s+this\s+opportunity\b/i,
            /\bget\s+notified\s+for\s+similar\s+jobs\b/i,
            /\bjoin\s+our\s+talent\s+community\b/i,
            /\bcookie\s+settings\b/i,
            /\bsee\s+more\b/i,
            /\bexplore\s+location\b/i,
            /\bclose\s+the\s+popup\b/i,
            /\bapply\s+now\b/i,
            /\bsave\s+job\b/i,
        ];

        let startIndex = 0;
        for (const pattern of startPatterns) {
            const match = source.match(pattern);
            if (match && typeof match.index === 'number') {
                startIndex = Math.max(startIndex, match.index);
                break;
            }
        }

        let trimmed = source.slice(startIndex).trim();

        for (const pattern of endPatterns) {
            const match = trimmed.match(pattern);
            if (match && typeof match.index === 'number' && match.index > 300) {
                trimmed = trimmed.slice(0, match.index).trim();
                break;
            }
        }

        // Remove immediate repeated long clauses introduced by merged extraction sources
        trimmed = trimmed.replace(/(.{180,}?)(\s*\1){1,}/gis, '$1');

        // Ensure key headings are separated so dedupe logic can work effectively
        trimmed = trimmed
            .replace(/(Our Company|The Opportunity|What you(?:\'|’)ll do|What you will do|What you need to succeed|Requirements|Responsibilities|Bonus)(?=[A-Z])/g, '$1\n')
            .replace(/\n{3,}/g, '\n\n');

        return dedupeParagraphs(normalizeJdText(trimmed));
    }
    
    // ================================
    // JOB DESCRIPTION DETECTION (ENHANCED)
    // ================================
    function detectJobDescription() {
        const portal = getCurrentPortal();
        
        // Portal-specific JD selectors - comprehensive list
        const jdSelectors = {
            linkedin: [
                '.jobs-description-content__text',
                '.jobs-box__html-content',
                '.jobs-description',
                '.description__text',
                '[data-job-id] .description',
                '.jobs-details__main-content',
                '#job-details'
            ],
            indeed: [
                '#jobDescriptionText',
                '.jobsearch-JobComponent-description',
                '.jobsearch-jobDescriptionText',
                '[data-testid="jobDescriptionText"]'
            ],
            glassdoor: [
                '.desc',
                '.jobDescriptionContent', 
                '[data-test="description"]',
                '.JobDetails_jobDescription'
            ],
            workday: [
                '.WJYQ',
                '[data-automation-id="job-description"]',
                '[data-automation-id="jobPostingDescription"]',
                '.css-cygeeu'
            ],
            greenhouse: [
                '#content',
                '.job__description',
                '.job-description',
                '#job_description'
            ],
            lever: [
                '.section-wrapper .content',
                '.posting-page .content',
                '[data-qa="job-description"]'
            ],
            smartrecruiters: [
                '.job-description',
                '.jobad-description',
                '[data-ui="job-description"]'
            ],
            generic: [
                '[class*="job-description"]',
                '[class*="jobDescription"]',
                '[class*="description"]',
                '[id*="description"]',
                'article',
                'main'
            ]
        };
        
        const selectorPriority = [
            ...(jdSelectors[portal] || []),
            ...jdSelectors.generic,
            '[data-automation-id="jobPostingDescription"]',
            '[data-automation-id="job-description"]',
            '[class*="jobDescription"]',
            '[class*="job-desc"]',
            '[class*="job-posting"]',
            '[data-testid*="description"]'
        ];

        const keywordSet = [
            'responsibilities', 'requirements', 'qualifications',
            'experience', 'skills', 'about the role', 'about this job',
            'what you', 'your role', 'we are looking', 'job description',
            'duties', 'preferred', 'benefits', 'nice to have'
        ];

        const excludedHints = ['header', 'footer', 'nav', 'menu', 'cookie', 'privacy', 'related jobs'];

        const candidateMap = new Map();
        selectorPriority.forEach(selector => {
            try {
                document.querySelectorAll(selector).forEach(node => {
                    if (!node || candidateMap.has(node)) return;
                    candidateMap.set(node, selector);
                });
            } catch {
                // ignore invalid selectors from dynamic portals
            }
        });

        document.querySelectorAll('main, article, section, div[role="main"], [data-job-id]').forEach(node => {
            if (!candidateMap.has(node)) candidateMap.set(node, 'generic-block');
        });

        let bestElement = null;
        let bestScore = -Infinity;

        for (const [el, sourceSelector] of candidateMap.entries()) {
            const text = cleanText(el.textContent || '');
            if (text.length < 180) continue;

            let score = 0;
            const lowered = text.toLowerCase();
            const elMarker = `${(el.id || '')} ${(el.className || '')}`.toLowerCase();

            score += Math.min(text.length / 80, 260);
            score += Math.min((text.match(/\n|•|-\s+/g) || []).length * 2, 40);

            keywordSet.forEach(keyword => {
                if (lowered.includes(keyword)) score += 18;
            });

            if (/job|description|posting|detail|content|role|position/i.test(sourceSelector)) score += 26;
            if (/job|description|posting|detail|content|role|position/i.test(elMarker)) score += 24;
            if (excludedHints.some(h => lowered.includes(h) || elMarker.includes(h))) score -= 80;
            if (el.querySelector('h1, h2, h3')) score += 8;

            if (score > bestScore) {
                bestScore = score;
                bestElement = el;
            }
        }

        const jsonLd = parseJobPostingJsonLd();
        const jsonLdDescription = decodeHtmlToText(jsonLd?.description || '');
        const pageDataDescription = extractTextFromPageData();

        const bestElementText = bestElement ? cleanText(bestElement.textContent || '') : '';
        const mergedText = mergeUniqueParagraphs(
            bestElementText,
            mergeUniqueParagraphs(jsonLdDescription, pageDataDescription)
        );

        const finalText = trimToCoreJobDescription(
            mergedText.length > bestElementText.length ? mergedText : bestElementText
        );

        if (bestElement && finalText.length > 100) {
            const jd = {
                html: bestElement.innerHTML,
                text: finalText,
                url: window.location.href,
                portal: portal,
                timestamp: Date.now()
            };
            
            currentJobDescription = jd;
            log('Job description detected:', jd.text.substring(0, 200) + '...');
            return jd;
        }
        
        return null;
    }
    
    function extractJobDetails() {
        const jd = currentJobDescription || detectJobDescription();
        if (!jd) return null;
        
        const text = jd.text;
        const jsonLd = parseJobPostingJsonLd();

        const titlePatterns = [
            jsonLd?.title,
            document.querySelector('h1')?.textContent,
            document.querySelector('.job-title, .jobTitle, [class*="title"]')?.textContent,
            document.title
        ];
        const jobTitle = cleanText(titlePatterns.find(t => t && String(t).trim().length > 0) || '');

        const companyPatterns = [
            jsonLd?.hiringOrganization?.name,
            document.querySelector('.company-name, .companyName, [class*="company"]')?.textContent,
            document.querySelector('[data-company]')?.textContent,
            document.querySelector('a[href*="/company/"]')?.textContent
        ];
        const company = cleanText(companyPatterns.find(c => c && String(c).trim().length > 0) || '');

        const locationPatterns = [
            jsonLd?.jobLocation?.address?.addressLocality,
            jsonLd?.jobLocation?.address?.addressRegion,
            document.querySelector('[class*="location"], [data-location]')?.textContent
        ];
        const location = cleanText(locationPatterns.find(l => l && String(l).trim().length > 0) || '');

        const employmentType = cleanText(jsonLd?.employmentType || (text.match(/(?:employment\s*type|job\s*type|work\s*type)\s*:?\s*([^\n.,]{2,80})/i)?.[1] || ''));
        const salary = extractSalaryRange(text, jsonLd?.baseSalary);
        const visaSponsorship = extractVisaStatus(text);

        const roleSummary = extractSectionFromJD(text, ['about the role', 'about this role', 'role summary', 'position summary', 'job summary']) || cleanText(text.slice(0, 450));
        const aboutCompany = extractSectionFromJD(text, ['about company', 'about us', 'who we are', 'company overview']);

        const responsibilities = splitStructuredList(
            extractSectionFromJD(text, ['responsibilities', 'key responsibilities', 'what you will do', "what you'll do", 'duties'])
        );
        const requirements = splitStructuredList(
            extractSectionFromJD(text, ['requirements', 'qualifications', 'must have', 'what we are looking for', 'skills & qualifications'])
        );
        const preferred = splitStructuredList(
            extractSectionFromJD(text, ['preferred qualifications', 'nice to have'])
        );
        const benefits = splitStructuredList(
            extractSectionFromJD(text, ['benefits', 'what we offer', 'perks', 'compensation and benefits'])
        );

        const skillPatterns = /(?:skills?|technologies?|tools?|proficient|experience\s*(?:with|in))[\s:]+([^.\n]+)/gi;
        const skills = [];
        let match;
        while ((match = skillPatterns.exec(text)) !== null) {
            skills.push(...match[1].split(/[,;|]/).map(s => cleanText(s)).filter(s => s.length > 2));
        }

        const yearsFromText = text.match(/(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)/i);
        const yearsFromLd = jsonLd?.experienceRequirements && String(jsonLd.experienceRequirements).match(/(\d+)\+?/);
        const yearsRequired = yearsFromText ? parseInt(yearsFromText[1]) : (yearsFromLd ? parseInt(yearsFromLd[1]) : null);

        const uniqueSkills = [...new Set(skills.map(s => s.toLowerCase()))]
            .map(skill => skills.find(s => s.toLowerCase() === skill))
            .filter(Boolean)
            .slice(0, 20);

        const compactRoleSummary = cleanText(roleSummary)
            .replace(/\s+/g, ' ')
            .trim();

        return {
            schemaVersion: JD_SCHEMA_VERSION,
            jobTitle,
            company,
            description: text,
            skills: uniqueSkills,
            yearsRequired,
            location,
            employmentType,
            salary,
            visaSponsorship,
            structured: {
                role: jobTitle,
                salary,
                visaSponsorship,
                summary: compactRoleSummary,
                aboutCompany,
                responsibilities,
                requirements,
                preferred,
                benefits,
            },
            url: jd.url,
            portal: jd.portal
        };
    }

    function getWorkflowMatchers(actionType) {
        const include = actionType === 'submit' ? /(submit|send application|finish|confirm|apply( now)?$)/i
            : actionType === 'next' ? /(next|continue|proceed|review application|->)/i
            : actionType === 'review' ? /(review|preview|application review|review your application)/i
            : /(apply|easy apply|apply now|start application|continue application)/i;
        const exclude = /(cancel|close|dismiss|back|previous|upload resume|save draft|learn more|share|report)/i;
        return { include, exclude };
    }

    function findWorkflowCandidates(actionType) {
        const { include, exclude } = getWorkflowMatchers(actionType);
        return Array.from(document.querySelectorAll('button, [role="button"], a'))
            .filter(el => {
                const text = cleanText(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
                if (!text) return false;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return false;
                if (el.disabled || el.getAttribute('aria-disabled') === 'true') return false;
                if (!include.test(text) || exclude.test(text)) return false;
                return true;
            });
    }

    function pickBestWorkflowCandidate(actionType, candidates) {
        if (!Array.isArray(candidates) || candidates.length === 0) return null;

        const scoreCandidate = (el) => {
            const text = cleanText(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
            let score = 0;

            if (actionType === 'submit' && /(submit|send application|confirm|finish|apply now)/i.test(text)) score += 6;
            if (actionType === 'next' && /(next|continue|proceed|->)/i.test(text)) score += 6;
            if (actionType === 'review' && /(review|preview)/i.test(text)) score += 6;
            if (actionType === 'apply' && /(apply|easy apply|start application)/i.test(text)) score += 6;

            if (/primary|submit|next|continue|review|apply|action/.test((el.className || '').toLowerCase())) score += 2;

            const rect = el.getBoundingClientRect();
            if (rect.top >= 0 && rect.bottom <= (window.innerHeight || 900)) score += 1;

            return score;
        };

        return candidates
            .map(el => ({ el, score: scoreCandidate(el) }))
            .sort((a, b) => b.score - a.score)[0].el;
    }

    function getWorkflowStatusInPage() {
        const container = detectApplicationForm();
        const elements = getAllFormElements(container);
        const actionableFields = elements.filter(info => info && info.type !== 'file');

        const applyCandidates = findWorkflowCandidates('apply');
        const nextCandidates = findWorkflowCandidates('next');
        const reviewCandidates = findWorkflowCandidates('review');
        const submitCandidates = findWorkflowCandidates('submit');

        return {
            success: true,
            portal: getCurrentPortal(),
            hasFillableFields: actionableFields.length > 0,
            fillableFieldCount: actionableFields.length,
            applyAvailable: applyCandidates.length > 0,
            nextAvailable: nextCandidates.length > 0,
            reviewAvailable: reviewCandidates.length > 0,
            submitAvailable: submitCandidates.length > 0,
            actionCounts: {
                apply: applyCandidates.length,
                next: nextCandidates.length,
                review: reviewCandidates.length,
                submit: submitCandidates.length,
            }
        };
    }

    function runWorkflowActionInPage(actionType) {
        const candidates = findWorkflowCandidates(actionType);

        if (!candidates.length) {
            return { success: false, error: `${actionType} action button not found` };
        }

        const target = pickBestWorkflowCandidate(actionType, candidates);
        if (!target) {
            return { success: false, error: `${actionType} action button not found` };
        }
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.click();

        return {
            success: true,
            message: `Clicked ${actionType} action: ${cleanText(target.innerText || target.textContent || target.getAttribute('aria-label') || actionType)}`
        };
    }
    
    // ================================
    // FIELD LEARNING
    // ================================
    function setupFieldLearning() {
        // Listen for user input on undetected fields
        document.addEventListener('change', handleUserInput, true);
        document.addEventListener('blur', handleUserInput, true);
    }
    
    function handleUserInput(event) {
        const element = event.target;
        if (!element || !element.value) return;
        
        // Get the label for this field
        const label = findLabelForElement(element);
        if (!label) return;
        
        // Check if we already know this field
        const existingType = detectFieldType(label, element);
        if (existingType) return;
        
        // Store the user's answer for learning
        const value = element.value;
        
        // Try to infer field type from value
        const inferredType = inferFieldTypeFromValue(value);
        
        if (inferredType) {
            // Store learned mapping
            userData.learnedMappings[label] = inferredType;
            saveUserData();
            log(`Learned new field mapping: "${label}" -> ${inferredType}`);
        }
        
        // Store as custom answer
        userData.customAnswers[label] = value;
        saveUserData();
        log(`Saved custom answer for "${label}": "${value.substring(0, 50)}..."`);
    }
    
    function inferFieldTypeFromValue(value) {
        if (!value) return null;
        
        // Email pattern
        if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'email';
        
        // Phone pattern
        if (/^[\d\s\-\+\(\)]{10,}$/.test(value)) return 'phone';
        
        // URL pattern
        if (/^https?:\/\//.test(value)) {
            if (/linkedin/i.test(value)) return 'linkedin';
            if (/github/i.test(value)) return 'github';
            return 'portfolio';
        }
        
        // Numeric (experience, salary)
        if (/^\d+$/.test(value) && parseInt(value) <= 50) return 'experience';
        if (/^\d{4,}$/.test(value)) return 'salary';
        
        return null;
    }
    
    // ================================
    // STORAGE MANAGEMENT
    // ================================
    
    /**
     * Load bundled config from user_config.json (generated by config_loader.py)
     */
    async function loadBundledConfig() {
        try {
            if (!chrome?.runtime?.getURL) throw new Error('Extension context invalidated');
            const response = await fetch(chrome.runtime.getURL('user_config.json'));
            if (!response.ok) return null;
            const config = await response.json();
            log('✓ Loaded bundled user_config.json');
            const profile = config.profile || {};
            const questions = config.questions || {};
            return {
                firstName: profile.firstName || '',
                lastName: profile.lastName || '',
                middleName: profile.middleName || '',
                email: profile.email || '',
                phone: profile.phone || '',
                city: profile.currentCity || '',
                currentCity: profile.currentCity || '',
                street: profile.street || '',
                address: profile.street || '',
                state: profile.state || '',
                zip: profile.zipcode || '',
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
                sponsorship: /yes|require/i.test(String(profile.requireVisa || questions.requireVisa || '')) ? 'yes' : 'no',
                requireVisa: profile.requireVisa || questions.requireVisa || '',
                workAuthorization: /yes|citizen|authorized/i.test(String(profile.usCitizenship || questions.usCitizenship || '')) ? 'yes' : 'no',
                usCitizenship: profile.usCitizenship || questions.usCitizenship || '',
                coverLetter: profile.coverLetter || questions.coverLetter || '',
                linkedinSummary: profile.linkedinSummary || questions.linkedinSummary || '',
                userInformationAll: questions.userInformationAll || '',
                confidenceLevel: profile.confidenceLevel || questions.confidenceLevel || '75',
                _autoLoaded: true
            };
        } catch (e) {
            if (String(e).includes('Extension context invalidated')) {
                log('Extension context invalidated: reload the page or extension.');
            } else {
                log('Could not load bundled config:', e.message || e);
            }
            return null;
        }
    }
    
    async function loadUserData() {
        try {
            if (!chrome?.storage?.sync || !chrome?.storage?.local) throw new Error('Extension context invalidated');
            const [syncResult, localResult] = await Promise.all([
                chrome.storage.sync.get([CONFIG.STORAGE_KEY, CONFIG.LEARNED_FIELDS_KEY]),
                chrome.storage.local.get([CONFIG.STORAGE_KEY, STORAGE_FALLBACK_KEY, CONFIG.LEARNED_FIELDS_KEY])
            ]);

            const syncData = syncResult?.[CONFIG.STORAGE_KEY];
            const localData = localResult?.[CONFIG.STORAGE_KEY] || localResult?.[STORAGE_FALLBACK_KEY];
            const resolvedData = (syncData && Object.keys(syncData).length > 3)
                ? syncData
                : ((localData && Object.keys(localData).length > 3) ? localData : null);

            if (resolvedData) {
                // Has meaningful data (more than just default values)
                userData = normalizeUserDataForFill({ ...userData, ...resolvedData });
                log('✓ User data loaded from Chrome storage');
            } else {
                // Try to load bundled config as fallback
                log('No storage data, trying bundled config...');
                const bundledConfig = await loadBundledConfig();
                if (bundledConfig) {
                    userData = normalizeUserDataForFill({ ...userData, ...bundledConfig });
                    await saveUserData();  // Cache in Chrome storage
                    log('✓ Auto-loaded and cached bundled config');
                } else {
                    log('ℹ️ No profile data available - form filling may be limited');
                }
            }
            // Load learned mappings
            const learnedMappings = syncResult?.[CONFIG.LEARNED_FIELDS_KEY] || localResult?.[CONFIG.LEARNED_FIELDS_KEY];
            if (learnedMappings) {
                userData.learnedMappings = { ...userData.learnedMappings, ...learnedMappings };
                log('Learned mappings loaded');
            }
            userData = normalizeUserDataForFill(userData);
        } catch (e) {
            if (String(e).includes('Extension context invalidated')) {
                log('Extension context invalidated: reload the page or extension.');
            } else {
                log('Error loading user data:', e.message || e);
            }
        }
    }
    
    async function saveUserData() {
        try {
            try {
                await chrome.storage.sync.set({ 
                    [CONFIG.STORAGE_KEY]: userData,
                    [CONFIG.LEARNED_FIELDS_KEY]: userData.learnedMappings
                });
                await chrome.storage.local.set({
                    [CONFIG.STORAGE_KEY]: userData,
                    [CONFIG.LEARNED_FIELDS_KEY]: userData.learnedMappings
                });
            } catch (syncErr) {
                const msg = String(syncErr?.message || syncErr || '');
                if (/quota|kQuotaBytesPerItem|QUOTA_BYTES_PER_ITEM/i.test(msg)) {
                    await chrome.storage.local.set({
                        [CONFIG.STORAGE_KEY]: userData,
                        [STORAGE_FALLBACK_KEY]: userData,
                        [CONFIG.LEARNED_FIELDS_KEY]: userData.learnedMappings
                    });
                } else {
                    throw syncErr;
                }
            }
            log('User data saved');
        } catch (e) {
            log('Error saving user data:', e);
        }
    }
    
    // ================================
    // MESSAGE HANDLING
    // ================================
    function registerMessageListener() {
        if (!isExtensionContextValid() || !chrome?.runtime?.onMessage?.addListener) {
            log('Extension context unavailable; runtime listener not registered.');
            return;
        }

        try {
            chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
                try {
                    const actionName = typeof message?.action === 'string' ? message.action : '';
                    if (!actionName) {
                        safeSendResponse(sendResponse, { success: false, error: 'Invalid message payload' });
                        return;
                    }
                    log('Received message:', actionName);

                    switch (actionName) {
                        case 'ping':
                            // Used by popup to check if content script is loaded
                            safeSendResponse(sendResponse, { success: true, loaded: true, portal: getCurrentPortal() });
                            break;

                        case 'fillForm':
                            {
                                const gateError = getRuntimeGateError('fillForm');
                                if (gateError) {
                                    safeSendResponse(sendResponse, { success: false, error: gateError });
                                    break;
                                }
                            }
                            fillAllForms({ resumeUpload: message.resumeUpload || null }).then(result => {
                                safeSendResponse(sendResponse, { success: true, ...result });
                            }).catch(e => {
                                safeSendResponse(sendResponse, { success: false, error: e?.message || String(e) });
                            });
                            return true;

                        case 'fillUnknownAnswers':
                            {
                                const gateError = getRuntimeGateError('fillUnknownAnswers');
                                if (gateError) {
                                    safeSendResponse(sendResponse, { success: false, error: gateError });
                                    break;
                                }
                            }
                            fillUnknownAnswersInPage(Array.isArray(message.answers) ? message.answers : []).then(result => {
                                safeSendResponse(sendResponse, result);
                            }).catch(e => {
                                safeSendResponse(sendResponse, { success: false, error: e?.message || String(e) });
                            });
                            return true;

                        case 'analyzeFields': {
                            const gateError = getRuntimeGateError('analyzeFields');
                            if (gateError) {
                                safeSendResponse(sendResponse, { success: false, error: gateError });
                                break;
                            }
                            const container = detectApplicationForm();
                            const elements = getAllFormElements(container);
                            const detectedFields = elements.filter(e => e.fieldType).map(e => ({
                                label: e.label,
                                type: e.type,
                                fieldType: e.fieldType,
                                currentValue: cleanText(readCurrentValueForVerify(e)),
                                required: !!e.required,
                                options: getFieldOptions(e),
                                normalizedLabel: normalizeFieldLabelKey(e.label || e.name || e.id || '')
                            }));
                            const undetectedFields = elements.filter(e => !e.fieldType).map(e => ({
                                label: e.label,
                                type: e.type,
                                fieldType: null,
                                currentValue: cleanText(readCurrentValueForVerify(e)),
                                required: !!e.required,
                                options: getFieldOptions(e),
                                normalizedLabel: normalizeFieldLabelKey(e.label || e.name || e.id || '')
                            }));
                            const filledFields = elements.filter(e => cleanText(readCurrentValueForVerify(e)) !== '').map(e => ({
                                label: e.label,
                                type: e.type,
                                fieldType: e.fieldType,
                                currentValue: cleanText(readCurrentValueForVerify(e)),
                                required: !!e.required,
                                options: getFieldOptions(e),
                                normalizedLabel: normalizeFieldLabelKey(e.label || e.name || e.id || '')
                            }));
                            const analysis = {
                                portal: getCurrentPortal(),
                                total: elements.length,
                                detectedCount: detectedFields.length,
                                undetectedCount: undetectedFields.length,
                                detected: detectedFields,
                                undetected: undetectedFields,
                                filled: filledFields,
                                fields: [...detectedFields, ...undetectedFields]
                            };
                            safeSendResponse(sendResponse, { success: true, analysis });
                            break;
                        }

                        case 'detectJD': {
                            const gateError = getRuntimeGateError('detectJD');
                            if (gateError) {
                                safeSendResponse(sendResponse, { success: false, error: gateError });
                                break;
                            }
                            const jdRaw = detectJobDescription();
                            const jdDetails = extractJobDetails();
                            // Merge into single 'jd' object matching popup.js expectations
                            const jdResponse = jdRaw ? {
                                schemaVersion: JD_SCHEMA_VERSION,
                                title: jdDetails ? jdDetails.jobTitle : '',
                                company: jdDetails ? jdDetails.company : '',
                                description: jdRaw.text || '',
                                skills: jdDetails ? jdDetails.skills : [],
                                yearsRequired: jdDetails ? jdDetails.yearsRequired : null,
                                location: jdDetails ? jdDetails.location : '',
                                employmentType: jdDetails ? jdDetails.employmentType : '',
                                structured: jdDetails ? jdDetails.structured : null,
                                url: jdRaw.url || window.location.href,
                                portal: jdRaw.portal || 'unknown',
                                html: jdRaw.html || '',
                                timestamp: jdRaw.timestamp || Date.now()
                            } : null;
                            safeSendResponse(sendResponse, { success: !!jdRaw, jd: jdResponse });
                            break;
                        }

                        case 'workflowAction': {
                            const gateError = getRuntimeGateError('workflowAction');
                            if (gateError) {
                                safeSendResponse(sendResponse, { success: false, error: gateError });
                                break;
                            }
                            const action = (message.step || '').toLowerCase();
                            if (!['apply', 'next', 'review', 'submit'].includes(action)) {
                                safeSendResponse(sendResponse, { success: false, error: 'Invalid workflow action' });
                                break;
                            }
                            safeSendResponse(sendResponse, runWorkflowActionInPage(action));
                            break;
                        }

                        case 'workflowStatus':
                            safeSendResponse(sendResponse, getWorkflowStatusInPage());
                            break;

                        case 'updateUserData':
                            userData = { ...userData, ...message.data };
                            saveUserData().then(() => {
                                safeSendResponse(sendResponse, { success: true });
                            });
                            return true;

                        case 'getUserData':
                            safeSendResponse(sendResponse, { success: true, data: userData });
                            break;

                        case 'getPortal':
                            safeSendResponse(sendResponse, { success: true, portal: getCurrentPortal() });
                            break;

                        case 'isApplicationPage': {
                            const form = detectApplicationForm();
                            const hasForm = form && form !== document.body;
                            safeSendResponse(sendResponse, { success: true, isApplicationPage: hasForm, portal: getCurrentPortal() });
                            break;
                        }

                        case 'saveLearnedField':
                            {
                                const gateError = getRuntimeGateError('saveLearnedField');
                                if (gateError) {
                                    safeSendResponse(sendResponse, { success: false, error: gateError });
                                    break;
                                }
                            }
                            if (message.label && message.fieldType) {
                                userData.learnedMappings[message.label] = message.fieldType;
                                saveUserData().then(() => {
                                    safeSendResponse(sendResponse, { success: true });
                                });
                                return true;
                            }
                            safeSendResponse(sendResponse, { success: false, error: 'Missing label or fieldType' });
                            break;

                        case 'setRuntimeSettings':
                            applyRuntimeSettings(message.settings || {});
                            safeSendResponse(sendResponse, {
                                success: true,
                                runtimeSettings,
                            });
                            break;

                        default:
                            safeSendResponse(sendResponse, { success: false, error: 'Unknown action' });
                    }
                } catch (e) {
                    safeSendResponse(sendResponse, { success: false, error: String(e?.message || e) });
                }
            });
        } catch (e) {
            log('Failed to register runtime listener:', e?.message || e);
        }
    }
    
    // ================================
    // INITIALIZATION
    // ================================
    async function init() {
        log('Universal Form Filler initializing...');
        if (!isExtensionContextValid()) {
            log('Extension context invalidated before init; aborting content script startup.');
            return;
        }
        await refreshRuntimeSettings();
        if (!isAutomationEnabled()) {
            log('Automation disabled by settings; content runtime initialized in passive mode.');
        }
        await loadUserData();
        setupFieldLearning();
        
        const portal = getCurrentPortal();
        log(`Detected portal: ${portal}`);
        
        // Detect JD on load
        setTimeout(() => {
            const jd = detectJobDescription();
            if (jd) {
                safeRuntimeSendMessage({ action: 'jobDescriptionDetected', details: extractJobDetails() });
            }
        }, 2000);
        
        // Watch for dynamic form changes
        const observer = new MutationObserver((mutations) => {
            // Check for new form elements
            for (const mutation of mutations) {
                if (mutation.addedNodes.length > 0) {
                    const form = detectApplicationForm();
                    if (form && form !== document.body) {
                        const now = Date.now();
                        if ((now - lastFormDetectedAt) >= 1500) {
                            lastFormDetectedAt = now;
                            safeRuntimeSendMessage({ action: 'applicationFormDetected', portal });
                        }
                    }
                }
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        log('Universal Form Filler initialized');
    }

    registerMessageListener();
    
    // Start
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
