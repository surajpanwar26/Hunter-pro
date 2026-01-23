// @ts-nocheck
(function () {
    window.addEventListener('load', () => {
        const params = new URLSearchParams(window.location.search);
        const loginUrl = params.get('loginUrl');

        if (!loginUrl) {
            chrome.runtime.sendMessage({
                command: 'AuthRedirectUrlChanged',
                url: window.location.href
            });
        } else {
            const loginUrlDecoded = decodeURIComponent(loginUrl);
            const iframe = document.getElementById('authFrame');
            // Redirected URL will be handled by this script
            iframe.src = loginUrlDecoded;
        }
    });
})()
