// Background service worker for Auto Timesheet Companion

const PYTHON_API_URL = "http://127.0.0.1:58432/api/event";
let isEnabled = true;

// Load toggle state from storage
chrome.storage.local.get(["trackingEnabled"], (res) => {
    if (res.trackingEnabled !== undefined) {
        isEnabled = res.trackingEnabled;
    }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "log_event") {
        if (!isEnabled) {
            sendResponse({ status: "disabled" });
            return true;
        }

        const payload = message.payload;
        forwardToPythonApp(payload)
            .then(ok => sendResponse({ status: ok ? "sent" : "queued" }))
            .catch(() => sendResponse({ status: "failed" }));

        return true; // Keep channel open for async response
    }

    if (message.action === "get_status") {
        checkAppConnection().then(connected => {
            sendResponse({ connected: connected, enabled: isEnabled });
        });
        return true;
    }

    if (message.action === "toggle_tracking") {
        isEnabled = message.enabled;
        chrome.storage.local.set({ trackingEnabled: isEnabled });
        sendResponse({ enabled: isEnabled });
        return true;
    }
});

async function checkAppConnection() {
    try {
        const resp = await fetch("http://127.0.0.1:58432/api/status", { method: "GET" });
        return resp.ok;
    } catch (e) {
        return false;
    }
}

async function forwardToPythonApp(payload) {
    try {
        const resp = await fetch(PYTHON_API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonStringifySafe(payload)
        });
        return resp.ok;
    } catch (err) {
        // App is likely closed or tracking paused; ignore silently
        return false;
    }
}

function jsonStringifySafe(obj) {
    try {
        return JSON.stringify(obj);
    } catch (e) {
        return "{}";
    }
}
