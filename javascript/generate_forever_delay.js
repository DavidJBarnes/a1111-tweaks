// Adds a cooldown between "generate forever" iterations.
//
// A1111's javascript/contextMenus.js polls every 500ms and re-clicks Generate
// the instant the Interrupt button disappears, so renders run back to back. We
// replace the global generateOnRepeat with a version that waits
// opts.tweaks_generate_forever_delay seconds after each render finishes before
// clicking again. The timer is still stored in window.generateOnRepeatInterval,
// so the stock "Cancel generate forever" menu item keeps working unchanged.
//
// Extension JS is loaded after core JS, so contextMenus.js has already defined
// generateOnRepeat by the time this runs. It is a top-level `let`, i.e. a
// lexical global rather than a property of window -- it has to be reassigned by
// bare name, not via window.generateOnRepeat.

(function() {
    const LOG_PREFIX = '[Generate Forever Delay]';
    const OPTION_KEY = 'tweaks_generate_forever_delay';
    const DEFAULT_DELAY_S = 2;

    // How often the idle/busy state is sampled. Finer than the stock 500ms so a
    // short delay is honoured accurately rather than rounded up.
    const POLL_MS = 250;

    // Generate is not instantaneous: the Interrupt button takes a moment to
    // appear after the click. Treat that window as "still running" so a slow
    // startup is not mistaken for a finished render and clicked a second time.
    const START_GRACE_MS = 3000;

    function delayMs() {
        const raw = (typeof opts !== 'undefined' && opts) ? opts[OPTION_KEY] : undefined;
        const seconds = parseFloat(raw);
        return (isNaN(seconds) || seconds < 0 ? DEFAULT_DELAY_S : seconds) * 1000;
    }

    function generateOnRepeatWithDelay(genbuttonid, interruptbuttonid) {
        const genbutton = gradioApp().querySelector(genbuttonid);
        const interruptbutton = gradioApp().querySelector(interruptbuttonid);
        if (!genbutton || !interruptbutton) {
            console.error(`${LOG_PREFIX} Buttons not found: ${genbuttonid} / ${interruptbuttonid}`);
            return;
        }

        clearInterval(window.generateOnRepeatInterval);

        let busy = false;      // a render is in flight (or was just asked for)
        let clickedAt = 0;     // when Generate was last clicked
        let readyAt = 0;       // earliest time the next click may happen

        const click = function() {
            genbutton.click();
            clickedAt = Date.now();
            busy = true;
        };

        if (!interruptbutton.offsetParent) {
            click();
        } else {
            busy = true;
        }

        console.log(`${LOG_PREFIX} Generate forever started on ${genbuttonid}, ${delayMs() / 1000}s between runs`);

        window.generateOnRepeatInterval = setInterval(function() {
            if (interruptbutton.offsetParent) {  // render in progress
                busy = true;
                readyAt = 0;
                return;
            }

            if (busy) {
                // Idle, but we clicked moments ago -- the render has probably
                // not started yet, so do not call this one finished.
                if (clickedAt && Date.now() - clickedAt < START_GRACE_MS) {
                    return;
                }
                busy = false;
                readyAt = Date.now() + delayMs();  // read fresh, so Settings changes apply mid-run
                return;
            }

            if (Date.now() >= readyAt) {
                click();
            }
        }, POLL_MS);
    }

    function install() {
        let current;
        try {
            current = generateOnRepeat;
        } catch (e) {
            return false;  // not defined yet (or renamed by a fork)
        }
        if (typeof current !== 'function') {
            return false;
        }
        if (current === generateOnRepeatWithDelay) {
            return true;
        }
        generateOnRepeat = generateOnRepeatWithDelay;
        console.log(`${LOG_PREFIX} Loaded, generate forever will pause between runs`);
        return true;
    }

    if (!install()) {
        if (typeof onUiLoaded === 'function') {
            onUiLoaded(function() {
                if (!install()) {
                    console.error(`${LOG_PREFIX} generateOnRepeat not found -- generate forever is unchanged`);
                }
            });
        } else {
            console.error(`${LOG_PREFIX} generateOnRepeat not found -- generate forever is unchanged`);
        }
    }
})();
