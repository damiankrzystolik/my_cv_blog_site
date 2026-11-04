/*
 * JS banera zgody na ciasteczka.
 *
 * PLAN.md E3/E4: zero inline <script>, zero onclick="" - zdarzenia podłączone
 * przez delegację na document, akcje sterowane atrybutami data-*. Żadnego
 * eval() (w przeciwieństwie do starego cookie_consent/cookiebar.js, który
 * używał eval(script.innerHTML) - usunięty, PLAN.md B3).
 */
(function () {
    "use strict";

    function getCsrfCookie() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function sendConsent(url, action) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfCookie(),
            },
            body: JSON.stringify({ action: action }),
        }).then(function (response) {
            return response.json();
        });
    }

    document.addEventListener("click", function (event) {
        const actionEl = event.target.closest("[data-cookie-action]");
        if (actionEl) {
            const banner = actionEl.closest("[data-cookie-banner]");
            const url = banner ? banner.getAttribute("data-consent-url") : null;
            if (!url) {
                return;
            }
            sendConsent(url, actionEl.getAttribute("data-cookie-action"))
                .then(function (data) {
                    if (data.success) {
                        banner.style.display = "none";
                        window.location.reload();
                    }
                })
                .catch(function (error) {
                    console.error("Cookie consent error:", error);
                });
            return;
        }

        const confirmEl = event.target.closest("[data-confirm]");
        if (confirmEl) {
            if (!window.confirm(confirmEl.getAttribute("data-confirm"))) {
                event.preventDefault();
            }
        }
    });
})();
