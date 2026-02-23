(function (globalScope) {
    'use strict';

    function escapeHtml(str) {
        if (str === undefined || str === null) return '';
        const div = (typeof document !== 'undefined') ? document.createElement('div') : null;
        if (div) {
            div.textContent = String(str);
            return div.innerHTML;
        }
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function sanitizeFilename(name, fallbackName = 'tailored_resume.pdf') {
        const fallback = String(fallbackName || 'tailored_resume.pdf').trim() || 'tailored_resume.pdf';
        const raw = String(name || '').trim();
        if (!raw) return fallback;

        const cleaned = raw
            .replace(/[\\/:*?"<>|\x00-\x1F]/g, '_')
            .replace(/\s+/g, ' ')
            .replace(/^\.+/, '')
            .slice(0, 120)
            .trim();

        if (!cleaned) return fallback;
        return cleaned;
    }

    function anonymizeTelemetryData(input) {
        const blockedKeys = new Set([
            'resumeText', 'masterText', 'tailoredText', 'jobDescription', 'description', 'rawDescription',
            'email', 'phone', 'firstName', 'lastName', 'address', 'city', 'linkedinUrl', 'portfolioUrl', 'githubUrl'
        ]);

        function maskString(value) {
            const text = String(value || '');
            const withoutEmail = text.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[redacted-email]');
            const withoutPhone = withoutEmail.replace(/\+?[\d\s().-]{8,}/g, '[redacted-phone]');
            if (withoutPhone.length > 220) {
                return `${withoutPhone.slice(0, 220)}…`;
            }
            return withoutPhone;
        }

        function walk(value) {
            if (value === null || value === undefined) return value;
            if (typeof value === 'string') return maskString(value);
            if (typeof value === 'number' || typeof value === 'boolean') return value;
            if (Array.isArray(value)) {
                return value.slice(0, 30).map(walk);
            }
            if (typeof value === 'object') {
                const out = {};
                for (const [k, v] of Object.entries(value)) {
                    if (blockedKeys.has(String(k))) {
                        out[k] = '[redacted]';
                    } else {
                        out[k] = walk(v);
                    }
                }
                return out;
            }
            return '[redacted]';
        }

        return walk(input || {});
    }

    function getExponentialBackoffMs(attempt, baseMs = 500, maxMs = 10000) {
        const safeAttempt = Math.max(1, Number(attempt) || 1);
        const safeBase = Math.max(100, Number(baseMs) || 500);
        const safeMax = Math.max(safeBase, Number(maxMs) || 10000);
        const factor = Math.pow(2, safeAttempt - 1);
        const jitter = Math.floor(Math.random() * Math.max(50, Math.round(safeBase * 0.25)));
        return Math.min(safeBase * factor + jitter, safeMax);
    }

    const exported = {
        escapeHtml,
        sanitizeFilename,
        anonymizeTelemetryData,
        getExponentialBackoffMs,
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = exported;
    }

    globalScope.PopupHelpers = exported;
})(typeof window !== 'undefined' ? window : globalThis);
