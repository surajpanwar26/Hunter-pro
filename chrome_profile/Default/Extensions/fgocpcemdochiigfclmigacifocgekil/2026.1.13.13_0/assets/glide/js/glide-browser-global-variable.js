// @ts-nocheck
(function glGlobalVariableInit() {
    class Glide {
        startTour (tourId) {
            if (!tourId) {
                console.warn('Tour Id is required');
                return
            }
            if (typeof tourId !== 'number' && typeof tourId !== 'string') {
                console.warn('Tour Id should be number or string');
                return
            }
            this.#sendMessageToContentScript({type : "GlGlobalVarMessage", action : "GlStartTour", data : tourId});
        }

        stopAllTours () {
            this.#sendMessageToContentScript({type : "GlGlobalVarMessage", action : "GlStopAllTours"});
        }

        startTourByName (tourName) {
            if (!tourName?.length) {
                console.warn('Tour Name is required');
                return
            }
            if (typeof tourName !== 'string') {
                console.warn('Tour Name should be number');
                return
            }
            this.#sendMessageToContentScript({type : "GlGlobalVarMessage", action : "GlStartTourByName", data : tourName});
        }

        openMenu () {
            this.#sendMessageToContentScript({type : "GlGlobalVarMessage", action : "GlOpenMenu"});
        }

        closeMenu () {
            this.#sendMessageToContentScript({type : "GlGlobalVarMessage", action : "GlCloseMenu"});
        }

        #sendMessageToContentScript (message) {
            window.postMessage(message, "*");
        }
    }

    if (window.glide) return; // Do not override if there are already a global variable accessible
    window.glide = new Glide();
})()
