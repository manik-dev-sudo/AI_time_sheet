document.addEventListener("DOMContentLoaded", () => {
    const badge = document.getElementById("statusBadge");
    const statusText = document.getElementById("statusText");
    const toggle = document.getElementById("trackingToggle");

    // Check status
    chrome.runtime.sendMessage({ action: "get_status" }, (res) => {
        if (chrome.runtime.lastError || !res) {
            updateStatus(false);
            return;
        }

        updateStatus(res.connected);
        toggle.checked = res.enabled !== false;
    });

    function updateStatus(connected) {
        if (connected) {
            badge.className = "status-badge connected";
            statusText.textContent = "Connected to Desktop App (58432)";
        } else {
            badge.className = "status-badge disconnected";
            statusText.textContent = "Desktop App Offline / Paused";
        }
    }

    toggle.addEventListener("change", () => {
        chrome.runtime.sendMessage({
            action: "toggle_tracking",
            enabled: toggle.checked
        });
    });
});
