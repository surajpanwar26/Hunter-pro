// @ts-nocheck
(function glBrowserCtxManagerInit() {

    // Event listeners
    window.addEventListener('GlGetBrowserCtx', (event) => {

        // Extracting object from window with target properties
        let targetProperties = [];
        let clearWindow = {};

        try {
            targetProperties = JSON.parse(event.detail);
        } catch (e){
            console.error(e)
        }

        if (!!targetProperties?.length){
            clearWindow = extractTargetProperties(window, targetProperties);
        }

        const ctx = {
            location: {
                href: window.location.href
            },
            localStorageItems: {...window.localStorage},
            sessionStorageItems: {...window.sessionStorage},
            window: clearWindow,
            customData: {},
            cookies: document.cookie
        }

        const serializedWindowCtx = stringify(ctx);

        window.dispatchEvent(new CustomEvent('GlBrowserCtxResult', {detail: serializedWindowCtx}));
    });

    window.addEventListener('GlSetCookies', (event) => {
        const cookieStr = event.detail;
        document.cookie = cookieStr;
        window.dispatchEvent(new CustomEvent('GlSetCookiesResult'));
    });

    function extractTargetProperties(obj, props) {
        const result = {};

        props.forEach(prop => {
            const keys = prop.split('.');
            let currentObj = obj;
            let currentResult = result;

            for (const [index, key] of keys.entries()) {
                if (currentObj[key] === undefined) return;

                if (index === keys.length - 1) {
                    currentResult[key] = currentObj[key];
                } else {
                    currentObj = currentObj[key];
                    currentResult = currentResult[key] = currentResult[key] || {};
                }
            }
        });

        return result;
    }

    // Helpers
    function stringify(obj) {
        // Fixed circular deps serialization errors
        let cache = [];

        const str = JSON.stringify(obj, function (key, value) {

            if (typeof value === 'object' && value !== null) {
                if (cache.indexOf(value) !== -1) {
                    return;
                }
                cache.push(value);
            }
            return value;
        });

        cache = null;

        return str;
    }
})();

