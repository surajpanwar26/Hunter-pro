// @ts-nocheck

async function init() {
    chrome.runtime.onMessage.addListener(async (message) => {
        if (message.command === 'defaultPopupAuthRequest') {
            const { clientId, tenant, widgetClientId } = message;

            const msalConfig = {
                auth: {
                    clientId,
                    authority: `https://login.microsoftonline.com/${tenant}`,
                    redirectUri: window.location.origin + '/auth2.html'
                },
                cache: {
                    cacheLocation: 'localStorage',
                    storeAuthStateInCookie: false
                }
            };

            const msalInstance = new Msal.UserAgentApplication(msalConfig);

            function loginWithRedirect() {
                const timeoutMs = 3000;

                return new Promise((resolve, reject) => {
                    const startTime = Date.now();

                    const redirectAuthTimeout = setInterval(() => {
                        const account = getAccount();
                        if (account) {
                            clearInterval(redirectAuthTimeout);
                            redirectAuthTimeout = null;
                            return resolve();
                        }
                        const now = Date.now();

                        if (now - startTime >= timeoutMs) {
                            clearInterval(redirectAuthTimeout);
                            localStorage.clear();
                            reject('REDIRECT_AUTH_TIMEOUT');
                        }
                    }, 100);

                    msalInstance.loginRedirect({
                        scopes: ['openid', 'profile']
                    });
                });
            }

            async function loginAndGetToken() {
                await loginWithRedirect();
                await getTokenAndNotify();
            }

            async function getToken(widgetClientId) {
                const request = {
                    account: getAccount(),
                    scopes: [`${widgetClientId}/.default`]
                };

                const response = await msalInstance.acquireTokenSilent(request)

                return (response && response.accessToken)
                    ? response.accessToken
                    : null;
            }

            function getAccount() {
                return msalInstance.getAccount();
            }

            function notify(accessToken, error) {
                chrome.runtime.sendMessage({
                    command: 'defaultPopupAuthResult',
                    accessToken: accessToken,
                    authError: error
                });
                window.close();
            }

            async function getTokenAndNotify(widgetClientId) {
                const accessToken = await getToken(widgetClientId);
                const err = accessToken ? null : 'NO_ACCESS_TOKEN_FROM_AUTH_PLATFORM';
                notify(accessToken, err);
            }


            try {
                const account = getAccount();

                if (account) {
                    console.log('User authenticated:');
                    try {
                        await getTokenAndNotify(widgetClientId);
                    } catch (error) {
                        if (error.name === 'InteractionRequiredAuthError') {
                            await loginAndGetToken();
                        } else {
                            throw error;
                        }
                    }

                } else {
                    console.log('User NOT authenticated:');
                    await loginAndGetToken();
                }
            } catch (error) {
                console.log('loginWithRedirect error :>> ', error);
                notify(null, error);
            }
        }
    });
}

init();


