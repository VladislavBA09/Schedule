export function setupNavigation() {
    let isNavigation = false;

    document.addEventListener('click', function (event) {
        const target = event.target;
        if (target.tagName === 'A' || target.closest('a')) {
            isNavigation = true;
        }
    });

    window.addEventListener('popstate', function () {
        isNavigation = true;
    });

    (function (history) {
        const pushState = history.pushState;
        const replaceState = history.replaceState;

        history.pushState = function () {
            isNavigation = true;
            return pushState.apply(history, arguments);
        };

        history.replaceState = function () {
            isNavigation = true;
            return replaceState.apply(history, arguments);
        };
    })(window.history);

    window.addEventListener('beforeunload', function () {
        if (!isNavigation) {
            navigator.sendBeacon('/cleanup_session');
        }
    });

    document.querySelector('form')?.addEventListener('submit', function () {
        isNavigation = true;
        window.removeEventListener('beforeunload', handleBeforeUnload);
    });
}
