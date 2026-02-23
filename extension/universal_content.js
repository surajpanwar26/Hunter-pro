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
        MAX_RETRIES: 3
    };
    
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
        
        // Combine and clean all found labels
        return labels.map(cleanLabel).filter(l => l.length > 0).join(' | ');
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
            elements.push({
                element: container || radios[0].parentElement,
                type: 'radio',
                name: name,
                label: findLabelForElement(container || radios[0]),
                radios: radios.map(r => ({
                    element: r,
                    value: r.value,
                    label: findLabelForElement(r) || r.nextSibling?.textContent?.trim()
                })),
                currentValue: radios.find(r => r.checked)?.value || ''
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
        
        // File inputs (resume, cover letter)
        container.querySelectorAll('input[type="file"]').forEach(fileInput => {
            if (isVisibleAndEnabled(fileInput)) {
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
        if (userData.customAnswers[label]) {
            return userData.customAnswers[label];
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
    
    async function selectDropdownOption(select, targetValue) {
        const options = Array.from(select.options);
        const targetLower = targetValue.toLowerCase();
        
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
        
        // Default to first valid option
        if (!matched) {
            matched = options.find(opt => opt.value && !opt.disabled);
        }
        
        if (matched) {
            select.value = matched.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            log(`Selected: "${matched.text}"`);
            return true;
        }
        
        return false;
    }
    
    async function selectRadioOption(elementInfo, targetValue) {
        const radios = elementInfo.radios || [];
        const targetLower = targetValue.toLowerCase();
        
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
        
        // Default to first option
        if (!matched && radios.length > 0) {
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
    
    // ================================
    // MAIN FILL FUNCTION (ENHANCED - JOBRIGHT STYLE)
    // ================================
    async function fillAllForms() {
        // Reload user data to ensure we have latest
        await loadUserData();
        
        const container = detectApplicationForm();
        const elements = getAllFormElements(container);
        
        let filled = 0;
        let total = elements.length;
        let skipped = 0;
        
        log(`Found ${total} form elements on ${getCurrentPortal()}`);
        log(`User data loaded: firstName="${userData.firstName}", email="${userData.email}"`);
        
        for (const info of elements) {
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
                continue;
            }
            
            try {
                let success = false;
                
                switch (info.type) {
                    case 'text':
                    case 'textarea':
                        // Skip if already filled with correct value
                        if (info.currentValue === smartAnswer) {
                            skipped++;
                            continue;
                        }
                        success = await fillTextInput(info.element, smartAnswer);
                        break;
                        
                    case 'select':
                        success = await selectDropdownOption(info.element, smartAnswer);
                        break;
                        
                    case 'radio':
                        const radioAnswer = smartAnswer || getDefaultRadioAnswer(info.label);
                        success = await selectRadioOption(info, radioAnswer);
                        break;
                        
                    case 'checkbox':
                        const shouldCheck = smartAnswer === 'yes' || smartAnswer === true || 
                                           smartAnswer === 'true' || 
                                           shouldCheckByDefault(info.label);
                        success = await fillCheckbox(info.element, shouldCheck);
                        break;
                        
                    case 'customDropdown':
                        success = await handleCustomDropdown(info.element, smartAnswer);
                        break;
                }
                
                if (success) {
                    filled++;
                    await sleep(CONFIG.FILL_DELAY);
                }
            } catch (e) {
                log(`Error filling ${info.label}: ${e.message}`);
            }
        }
        
        log(`Filled ${filled} of ${total} fields (${skipped} skipped)`);
        return { filled, total, skipped, portal: getCurrentPortal() };
    }
    
    // Smart field type detection for edge cases
    function smartDetectFieldType(label, element) {
        if (!label) return null;
        const lbl = label.toLowerCase();
        
        // Name variations
        if (/^name$|your name|applicant name|candidate name/i.test(lbl)) return 'fullName';
        if (/first|given|forename/i.test(lbl) && /name/i.test(lbl)) return 'firstName';
        if (/last|family|surname/i.test(lbl) && /name/i.test(lbl)) return 'lastName';
        
        // Contact
        if (/email|e-mail|mail/i.test(lbl)) return 'email';
        if (/phone|mobile|cell|telephone|contact.*number/i.test(lbl)) return 'phone';
        
        // Location
        if (/city|location/i.test(lbl)) return 'city';
        if (/state|province/i.test(lbl)) return 'state';
        if (/country/i.test(lbl)) return 'country';
        if (/address|street/i.test(lbl)) return 'address';
        if (/zip|postal/i.test(lbl)) return 'zip';
        
        // Professional
        if (/company|employer|organization/i.test(lbl)) return 'company';
        if (/title|position|role|designation/i.test(lbl)) return 'title';
        if (/experience|years/i.test(lbl)) return 'experience';
        if (/salary|compensation|pay|ctc/i.test(lbl)) return 'salary';
        if (/notice|availability|start.*date/i.test(lbl)) return 'noticePeriod';
        
        // Links
        if (/linkedin/i.test(lbl)) return 'linkedin';
        if (/portfolio|website/i.test(lbl)) return 'portfolio';
        if (/github/i.test(lbl)) return 'github';
        
        // Education
        if (/degree|qualification/i.test(lbl)) return 'degree';
        if (/major|field|study/i.test(lbl)) return 'major';
        if (/school|university|college|institution/i.test(lbl)) return 'school';
        if (/graduation|grad.*year/i.test(lbl)) return 'graduationYear';
        
        // Work Authorization
        if (/authorized|eligible.*work|work.*authorization/i.test(lbl)) return 'workAuth';
        if (/sponsor|visa/i.test(lbl)) return 'sponsorship';
        
        // Preferences
        if (/remote|work from home|wfh/i.test(lbl)) return 'remote';
        if (/relocate|relocation/i.test(lbl)) return 'relocate';
        if (/travel/i.test(lbl)) return 'travel';
        
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
    
    async function handleCustomDropdown(element, value) {
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
        
        let jdElement = null;
        const selectors = jdSelectors[portal] || jdSelectors.generic;
        
        // Try each selector
        for (const selector of selectors) {
            jdElement = document.querySelector(selector);
            if (jdElement && jdElement.textContent.trim().length > 200) {
                break;
            }
        }
        
        // Try generic selectors as fallback
        if (!jdElement || jdElement.textContent.trim().length < 200) {
            for (const selector of jdSelectors.generic) {
                const el = document.querySelector(selector);
                if (el && el.textContent.trim().length > 300) {
                    jdElement = el;
                    break;
                }
            }
        }
        
        // Final fallback: find largest text block with JD keywords
        if (!jdElement || jdElement.textContent.trim().length < 200) {
            const candidates = document.querySelectorAll('div, article, section, main');
            let maxScore = 0;
            
            for (const el of candidates) {
                const text = el.textContent || '';
                if (text.length < 300) continue;
                
                // Score based on JD keywords
                let score = 0;
                const keywords = [
                    'responsibilities', 'requirements', 'qualifications',
                    'experience', 'skills', 'about the role', 'about this job',
                    'what you', 'your role', 'we are looking', 'job description',
                    'duties', 'preferred', 'benefits', 'nice to have'
                ];
                
                for (const kw of keywords) {
                    if (text.toLowerCase().includes(kw)) score += 10;
                }
                score += Math.min(text.length / 100, 50); // Bonus for length
                
                if (score > maxScore) {
                    maxScore = score;
                    jdElement = el;
                }
            }
        }
        
        if (jdElement && jdElement.textContent.trim().length > 100) {
            const jd = {
                html: jdElement.innerHTML,
                text: jdElement.textContent.trim(),
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
        
        // Extract job title
        const titlePatterns = [
            document.querySelector('h1')?.textContent,
            document.querySelector('.job-title, .jobTitle, [class*="title"]')?.textContent,
            document.title
        ];
        const jobTitle = titlePatterns.find(t => t && t.length > 0)?.trim() || '';
        
        // Extract company
        const companyPatterns = [
            document.querySelector('.company-name, .companyName, [class*="company"]')?.textContent,
            document.querySelector('[data-company]')?.textContent
        ];
        const company = companyPatterns.find(c => c && c.length > 0)?.trim() || '';
        
        // Extract skills from JD
        const skillPatterns = /(?:skills?|technologies?|tools?|proficient|experience\s*(?:with|in))[\s:]+([^.]+)/gi;
        const skills = [];
        let match;
        while ((match = skillPatterns.exec(text)) !== null) {
            skills.push(...match[1].split(/[,;]/).map(s => s.trim()).filter(s => s.length > 2));
        }
        
        // Extract years of experience
        const expMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)/i);
        const yearsRequired = expMatch ? parseInt(expMatch[1]) : null;
        
        return {
            jobTitle,
            company,
            description: text,
            skills: [...new Set(skills)],
            yearsRequired,
            url: jd.url,
            portal: jd.portal
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
                _autoLoaded: true
            };
        } catch (e) {
            log('Could not load bundled config:', e.message);
            return null;
        }
    }
    
    async function loadUserData() {
        try {
            const result = await chrome.storage.sync.get([CONFIG.STORAGE_KEY, CONFIG.LEARNED_FIELDS_KEY]);
            if (result[CONFIG.STORAGE_KEY] && Object.keys(result[CONFIG.STORAGE_KEY]).length > 3) {
                // Has meaningful data (more than just default values)
                userData = { ...userData, ...result[CONFIG.STORAGE_KEY] };
                log('✓ User data loaded from Chrome storage');
            } else {
                // Try to load bundled config as fallback
                log('No storage data, trying bundled config...');
                const bundledConfig = await loadBundledConfig();
                if (bundledConfig) {
                    userData = { ...userData, ...bundledConfig };
                    await saveUserData();  // Cache in Chrome storage
                    log('✓ Auto-loaded and cached bundled config');
                } else {
                    log('ℹ️ No profile data available - form filling may be limited');
                }
            }
            
            // Load learned mappings
            if (result[CONFIG.LEARNED_FIELDS_KEY]) {
                userData.learnedMappings = { ...userData.learnedMappings, ...result[CONFIG.LEARNED_FIELDS_KEY] };
                log('Learned mappings loaded');
            }
        } catch (e) {
            log('Error loading user data:', e);
        }
    }
    
    async function saveUserData() {
        try {
            await chrome.storage.sync.set({ 
                [CONFIG.STORAGE_KEY]: userData,
                [CONFIG.LEARNED_FIELDS_KEY]: userData.learnedMappings
            });
            log('User data saved');
        } catch (e) {
            log('Error saving user data:', e);
        }
    }
    
    // ================================
    // MESSAGE HANDLING
    // ================================
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        log('Received message:', message.action);
        
        switch (message.action) {
            case 'ping':
                // Used by popup to check if content script is loaded
                sendResponse({ success: true, loaded: true, portal: getCurrentPortal() });
                break;
                
            case 'fillForm':
                fillAllForms().then(result => {
                    sendResponse({ success: true, ...result });
                }).catch(e => {
                    sendResponse({ success: false, error: e.message });
                });
                return true;
                
            case 'analyzeFields':
                const container = detectApplicationForm();
                const elements = getAllFormElements(container);
                const analysis = {
                    portal: getCurrentPortal(),
                    total: elements.length,
                    detected: elements.filter(e => e.fieldType).length,
                    undetected: elements.filter(e => !e.fieldType).length,
                    fields: elements.map(e => ({
                        label: e.label,
                        type: e.type,
                        fieldType: e.fieldType,
                        hasValue: !!e.currentValue,
                        required: e.required
                    }))
                };
                sendResponse({ success: true, analysis });
                break;
                
            case 'detectJD':
                const jdRaw = detectJobDescription();
                const jdDetails = extractJobDetails();
                // Merge into single 'jd' object matching popup.js expectations
                const jdResponse = jdRaw ? {
                    title: jdDetails ? jdDetails.jobTitle : '',
                    company: jdDetails ? jdDetails.company : '',
                    description: jdRaw.text || '',
                    skills: jdDetails ? jdDetails.skills : [],
                    yearsRequired: jdDetails ? jdDetails.yearsRequired : null,
                    url: jdRaw.url || window.location.href,
                    portal: jdRaw.portal || 'unknown',
                    html: jdRaw.html || '',
                    timestamp: jdRaw.timestamp || Date.now()
                } : null;
                sendResponse({ success: !!jdRaw, jd: jdResponse });
                break;
                
            case 'updateUserData':
                userData = { ...userData, ...message.data };
                saveUserData().then(() => {
                    sendResponse({ success: true });
                });
                return true;
                
            case 'getUserData':
                sendResponse({ success: true, data: userData });
                break;
                
            case 'getPortal':
                sendResponse({ success: true, portal: getCurrentPortal() });
                break;
                
            case 'isApplicationPage':
                const form = detectApplicationForm();
                const hasForm = form && form !== document.body;
                sendResponse({ success: true, isApplicationPage: hasForm, portal: getCurrentPortal() });
                break;
                
            case 'saveLearnedField':
                if (message.label && message.fieldType) {
                    userData.learnedMappings[message.label] = message.fieldType;
                    saveUserData().then(() => {
                        sendResponse({ success: true });
                    });
                    return true;
                }
                sendResponse({ success: false, error: 'Missing label or fieldType' });
                break;
                
            default:
                sendResponse({ success: false, error: 'Unknown action' });
        }
    });
    
    // ================================
    // INITIALIZATION
    // ================================
    async function init() {
        log('Universal Form Filler initializing...');
        await loadUserData();
        setupFieldLearning();
        
        const portal = getCurrentPortal();
        log(`Detected portal: ${portal}`);
        
        // Detect JD on load
        setTimeout(() => {
            const jd = detectJobDescription();
            if (jd) {
                chrome.runtime.sendMessage({ action: 'jobDescriptionDetected', details: extractJobDetails() }).catch(() => {});
            }
        }, 2000);
        
        // Watch for dynamic form changes
        const observer = new MutationObserver((mutations) => {
            // Check for new form elements
            for (const mutation of mutations) {
                if (mutation.addedNodes.length > 0) {
                    const form = detectApplicationForm();
                    if (form && form !== document.body) {
                        chrome.runtime.sendMessage({ action: 'applicationFormDetected', portal }).catch(() => {});
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
    
    // Start
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
