// Content script for Auto Timesheet Companion

(function() {
    let lastUrl = location.href;
    let visitTimer = null;

    // Helper to send events to background script
    function sendEvent(type, details) {
        chrome.runtime.sendMessage({
            action: "log_event",
            payload: {
                type: type,
                details: details
            }
        });
    }

    // 1. WEB VISIT TRACKING (After lingering for 3 seconds to avoid transient redirects)
    function checkPageVisit() {
        if (visitTimer) clearTimeout(visitTimer);
        visitTimer = setTimeout(() => {
            // Ignore blank or browser internal pages
            if (location.protocol.startsWith("http")) {
                sendEvent("WEB_VISIT", {
                    url: location.href,
                    title: document.title || "Untitled Webpage"
                });
            }
        }, 3000);
    }

    checkPageVisit();

    // Listen for SPA URL changes (History API)
    window.addEventListener("popstate", checkPageVisit);

    // 2. FORM SUBMISSION TRACKING
    document.addEventListener("submit", function(e) {
        try {
            const form = e.target;
            if (!form || form.tagName !== "FORM") return;

            const formName = form.name || form.id || form.getAttribute("aria-label") || "web_form";
            const fieldNames = [];

            // Collect non-sensitive field identifiers
            const inputs = form.querySelectorAll("input, textarea, select");
            inputs.forEach(input => {
                const type = (input.type || "").toLowerCase();
                // Exclude passwords, hidden inputs, credit cards
                if (type === "password" || type === "hidden") return;

                const name = input.name || input.id || input.placeholder || input.getAttribute("aria-label");
                if (name && !name.toLowerCase().includes("csrf") && !name.toLowerCase().includes("token")) {
                    fieldNames.push(name.substring(0, 30));
                }
            });

            sendEvent("WEB_FORM", {
                url: location.href,
                form_name: formName,
                fields: fieldNames.slice(0, 10)
            });
        } catch (err) {
            console.error("[AutoTimesheet] Form capture error:", err);
        }
    }, true);

    // 3. WEBMAIL SENT TRACKING (GMAIL & OUTLOOK)
    const hostname = location.hostname;

    // A. Gmail Handler
    if (hostname.includes("mail.google.com")) {
        function captureGmailSend() {
            try {
                // Find open compose windows
                const composeBoxes = document.querySelectorAll('div[role="dialog"]');
                composeBoxes.forEach(dialog => {
                    // Extract recipients
                    const toRecipients = [];
                    const emailSpans = dialog.querySelectorAll('span[email], div[name="to"] span[email], input[peoplekit-id]');
                    emailSpans.forEach(el => {
                        const email = el.getAttribute("email") || el.innerText || el.value;
                        if (email && email.includes("@")) {
                            toRecipients.push(email.trim());
                        }
                    });

                    // Alternative To search in input fields
                    if (toRecipients.length === 0) {
                        const toInputs = dialog.querySelectorAll('input[aria-label="To recipients"], div[aria-label="To"]');
                        toInputs.forEach(inp => {
                            const val = inp.value || inp.innerText;
                            if (val && val.includes("@")) toRecipients.push(val.trim());
                        });
                    }

                    // Extract Subject
                    const subjectInput = dialog.querySelector('input[name="subjectbox"], input[placeholder="Subject"]');
                    const subject = subjectInput ? subjectInput.value : "(No Subject)";

                    if (toRecipients.length > 0 || (subject && subject !== "(No Subject)")) {
                        sendEvent("WEBMAIL_SENT", {
                            service: "Gmail",
                            to: toRecipients.length > 0 ? toRecipients.join(", ") : "Recipient in Compose",
                            subject: subject
                        });
                    }
                });
            } catch (err) {
                console.error("[AutoTimesheet] Gmail capture error:", err);
            }
        }

        // Listen for Send button clicks or Ctrl+Enter
        document.addEventListener("click", function(e) {
            const btn = e.target.closest('div[role="button"], button');
            if (btn) {
                const label = (btn.getAttribute("aria-label") || btn.innerText || "").toLowerCase();
                const tooltip = (btn.getAttribute("data-tooltip") || "").toLowerCase();
                if (label.includes("send") || tooltip.includes("send")) {
                    captureGmailSend();
                }
            }
        }, true);

        document.addEventListener("keydown", function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                captureGmailSend();
            }
        }, true);
    }

    // B. Outlook Web Handler
    if (hostname.includes("outlook.live.com") || hostname.includes("outlook.office.com") || hostname.includes("outlook.office365.com")) {
        function captureOutlookSend() {
            try {
                const toRecipients = [];
                // Look for recipient chips
                const recipientChips = document.querySelectorAll('div[data-log-name="To"] [role="presentation"], div[aria-label="To"] span');
                recipientChips.forEach(chip => {
                    const txt = chip.innerText || "";
                    if (txt.includes("@") || txt.trim().length > 1) {
                        toRecipients.push(txt.trim());
                    }
                });

                // Subject
                const subjectInput = document.querySelector('input[aria-label="Add a subject"], input[placeholder="Add a subject"]');
                const subject = subjectInput ? subjectInput.value : "(No Subject)";

                sendEvent("WEBMAIL_SENT", {
                    service: "Outlook Web",
                    to: toRecipients.length > 0 ? toRecipients.join(", ") : "Recipient in Compose",
                    subject: subject
                });
            } catch (err) {
                console.error("[AutoTimesheet] Outlook capture error:", err);
            }
        }

        document.addEventListener("click", function(e) {
            const btn = e.target.closest('button');
            if (btn) {
                const label = (btn.getAttribute("aria-label") || btn.getAttribute("title") || btn.innerText || "").toLowerCase();
                if (label.includes("send") && !label.includes("discard")) {
                    captureOutlookSend();
                }
            }
        }, true);

        document.addEventListener("keydown", function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                captureOutlookSend();
            }
        }, true);
    }

})();
