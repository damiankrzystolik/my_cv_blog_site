// Przycisk "Kopiuj link" pod wpisem. Bez inline JS — działa z CSP script-src 'self'.
document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy-url]");
    if (!button) {
        return;
    }
    const label = button.querySelector("[data-copy-label]");
    try {
        await navigator.clipboard.writeText(button.dataset.copyUrl);
        label.textContent = "Skopiowano!";
    } catch {
        label.textContent = "Nie udało się skopiować";
    }
    setTimeout(() => {
        label.textContent = "Kopiuj link";
    }, 2000);
});
