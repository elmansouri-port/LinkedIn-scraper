/**
 * LinkedIn Scraper Control Panel — app.js
 * Handles all tabs: Scrape, Enrich, Connections, Messaging, Email, CV, Schedule, Accounts, Stats
 */
const API_BASE = "";
const POLL_INTERVAL = 3000;

// ── DOM refs ──────────────────────────────────────────────
const $apiStatus   = document.getElementById("api-status");
const $jobBar      = document.getElementById("job-status-bar");
const $jobText     = document.getElementById("job-status-text");
const $jobProgress = document.getElementById("job-progress-bar");
const $jobPct      = document.getElementById("job-progress-text");
const $toasts      = document.getElementById("toast-container");

let currentJobId = null;
let pollTimer    = null;

// ── Bootstrap ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    checkApiHealth();
    setInterval(checkApiHealth, 15000);
    initTabs();
    initScrapeForms();
    initEnrichForms();
    initConnectionsForms();
    initMessagingForm();
    initCampaignForms();
    initCVForm();
    initScheduleForm();
    initAccountForm();
    initAuth();
    initStats();
    initQuickActions();
    initProfiles();
});

// ── API health ────────────────────────────────────────────
async function checkApiHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
            $apiStatus.innerHTML = `<span class="dot dot--online"></span><span class="status-text">API Online</span>`;
        } else throw new Error();
    } catch {
        $apiStatus.innerHTML = `<span class="dot dot--offline"></span><span class="status-text">API Offline</span>`;
    }
}

// ── Tab switching ─────────────────────────────────────────
function initTabs() {
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            const panel = document.getElementById(`tab-${tab.dataset.tab}`);
            if (panel) panel.classList.add("active");

            // Lazy-load data when switching
            if (tab.dataset.tab === "email")    loadCampaigns();
            if (tab.dataset.tab === "accounts") loadAccounts();
            if (tab.dataset.tab === "auth")     loadAuthStatus();
            if (tab.dataset.tab === "stats")    loadStats();
            if (tab.dataset.tab === "profiles") loadProfiles();
        });
    });
}

// ── Scrape Forms ──────────────────────────────────────────
function initScrapeForms() {
    // Google scrape
    document.getElementById("google-scrape-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = {
            keywords:                 document.getElementById("gs-keywords").value.trim(),
            oblig_keywords:           document.getElementById("gs-oblig").value.trim(),
            max_profiles:             parseInt(document.getElementById("gs-max-profiles").value, 10),
            max_profiles_per_keyword: parseInt(document.getElementById("gs-per-kw").value, 10),
            max_pages:                parseInt(document.getElementById("gs-max-pages").value, 10),
            verbose:                  true,
        };
        if (!data.keywords) return showToast("Keywords required", "error");
        await startJob(`${API_BASE}/api/scrape/google`, data, "Google scrape");
    });

    // Group scrape
    document.getElementById("group-scrape-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = {
            group_url:     document.getElementById("grp-url").value.trim(),
            max_members:   parseInt(document.getElementById("grp-max").value, 10) || null,
            scraping_mode: document.getElementById("grp-mode").value,
        };
        if (!data.group_url) return showToast("Group URL required", "error");
        await startJob(`${API_BASE}/api/scrape/group`, data, "Group scrape");
    });

    // LinkedIn people search
    document.getElementById("search-scrape-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = {
            keywords:     document.getElementById("ss-keywords").value.trim(),
            max_profiles: parseInt(document.getElementById("ss-max-profiles").value, 10),
            start_page:   parseInt(document.getElementById("ss-start-page").value, 10),
        };
        if (!data.keywords) return showToast("Keywords required", "error");
        await startJob(`${API_BASE}/api/scrape/search`, data, "LinkedIn search scrape");
    });
}

// ── Enrich Forms ──────────────────────────────────────────
function initEnrichForms() {
    // Enrich from CSV
    document.getElementById("enrich-form").addEventListener("submit", async e => {
        e.preventDefault();
        const maxRaw = parseInt(document.getElementById("enrich-max").value, 10);
        const data = {
            csv_file_path: document.getElementById("enrich-csv").value.trim(),
            url_column:    document.getElementById("enrich-col").value.trim() || "Profile URL",
            max_profiles:  maxRaw > 0 ? maxRaw : null,
        };
        if (!data.csv_file_path) return showToast("CSV path required", "error");
        await startJob(`${API_BASE}/api/enrich`, data, "CSV Enrichment");
    });

    // Enrich from DB
    document.getElementById("enrich-db-form").addEventListener("submit", async e => {
        e.preventDefault();
        const maxRaw   = parseInt(document.getElementById("enrich-db-max").value, 10);
        const startRaw = parseInt(document.getElementById("enrich-db-start").value, 10);
        const endRaw   = parseInt(document.getElementById("enrich-db-end").value, 10);
        const data = {
            max_profiles: maxRaw > 0 ? maxRaw : null,
            range_start:  startRaw > 0 ? startRaw : null,
            range_end:    endRaw   > 0 ? endRaw   : null,
        };
        await startJob(`${API_BASE}/api/enrich/db`, data, "DB Enrichment");
    });
}

// ── Connections Forms ─────────────────────────────────────
function initConnectionsForms() {
    // Single connection
    document.getElementById("single-conn-form").addEventListener("submit", async e => {
        e.preventDefault();
        const note = document.getElementById("conn-note").value.trim();
        const data = {
            profile_url:  document.getElementById("conn-url").value.trim(),
            note_message: note || null,
        };
        if (!data.profile_url) return showToast("Profile URL required", "error");
        await startJob(`${API_BASE}/api/connections/send`, data, "Single connection");
    });

    // Mass connections
    document.getElementById("mass-conn-form").addEventListener("submit", async e => {
        e.preventDefault();
        const note = document.getElementById("mass-conn-note").value.trim();
        const data = {
            csv_file_path: document.getElementById("mass-conn-csv").value.trim(),
            note_message:  note || null,
            use_note:      document.getElementById("mass-conn-use-note").checked,
        };
        if (!data.csv_file_path) return showToast("CSV path required", "error");
        await startJob(`${API_BASE}/api/connections/mass-send`, data, "Mass connections");
    });
}

// ── Messaging Form ────────────────────────────────────────
function initMessagingForm() {
    document.getElementById("group-msg-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = {
            group_data_file: document.getElementById("grp-msg-file").value.trim() || null,
        };
        await startJob(`${API_BASE}/api/messages/group`, data, "Group messaging");
    });
}

// ── Email Campaigns ───────────────────────────────────────
let activeSendCampaignId  = null;
let activeTestCampaignId  = null;

function initCampaignForms() {
    // Toggle new-campaign card
    document.getElementById("new-campaign-toggle").addEventListener("click", () => {
        const card = document.getElementById("new-campaign-card");
        card.style.display = card.style.display === "none" ? "block" : "none";
        if (card.style.display === "block") card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    // Create campaign
    document.getElementById("campaign-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = {
            name:              document.getElementById("camp-name").value.trim(),
            subject:           document.getElementById("camp-subject").value.trim(),
            body_text:         document.getElementById("camp-body").value.trim(),
            cv_path:           document.getElementById("camp-cv").value.trim() || null,
            cover_letter_path: document.getElementById("camp-cover").value.trim() || null,
            from_name:         document.getElementById("camp-from-name").value.trim() || null,
        };
        if (!data.name || !data.subject || !data.body_text)
            return showToast("Name, subject, and body are required", "error");
        try {
            const res    = await apiFetch(`${API_BASE}/api/email/campaigns`, "POST", data);
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
            showToast(`Campaign "${data.name}" created (ID ${result.campaign_id})`, "success");
            document.getElementById("new-campaign-card").style.display = "none";
            document.getElementById("campaign-form").reset();
            loadCampaigns();
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    // Verify emails button
    document.getElementById("verify-emails-btn").addEventListener("click", async () => {
        if (!confirm("Start email verification for all unverified profiles? This may take several minutes.")) return;
        try {
            showToast("Starting email verification…", "info");
            const res  = await apiFetch(`${API_BASE}/api/email/verify`, "POST", { method: "dns" });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed");
            if (data.job_id) {
                currentJobId = data.job_id;
                showJobBar(data.job_id, "Email Verification");
                startPolling();
            } else {
                showToast(data.message || "Done", "success");
            }
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    // Send modal confirm
    document.getElementById("send-modal-confirm").addEventListener("click", () => doSendCampaign());

    // Test modal confirm
    document.getElementById("test-modal-confirm").addEventListener("click", () => doTestEmail());

    loadCampaigns();
}

async function loadCampaigns() {
    const $c = document.getElementById("campaigns-container");
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns`);
        const data = await res.json();
        const campaigns = data.campaigns || [];
        if (!campaigns.length) {
            $c.innerHTML = '<div class="card"><p style="color:var(--text-muted);">No campaigns yet. Click "+ New Campaign" to get started.</p></div>';
            return;
        }
        $c.innerHTML = campaigns.map(c => renderCampaignCard(c)).join("");
    } catch (err) {
        $c.innerHTML = `<div class="card"><p style="color:var(--red);">Failed to load campaigns: ${esc(err.message)}</p></div>`;
    }
}

function renderCampaignCard(c) {
    const s = c.send_stats || {};
    const prepared = (s.pending || 0) + (s.sent || 0) + (s.failed || 0);
    const statusClass = {
        draft: "badge--draft", prepared: "badge--scheduled",
        sending: "badge--running", paused: "badge--running",
        completed: "badge--completed", scheduled: "badge--scheduled",
        failed: "badge--failed",
    }[c.status] || "badge--draft";

    return `
    <div class="campaign-card" id="camp-card-${c.id}">
        <div class="campaign-card-header">
            <div class="campaign-card-meta">
                <span class="campaign-name">${esc(c.name)}</span>
                <span class="badge ${statusClass}">${c.status}</span>
                <span class="campaign-id">ID: ${c.id}</span>
            </div>
            <div class="campaign-send-stats">
                <span class="stat-chip">Queued: ${prepared}</span>
                <span class="stat-chip stat-chip--pending">Pending: ${s.pending || 0}</span>
                <span class="stat-chip stat-chip--sent">Sent: ${s.sent || 0}</span>
                <span class="stat-chip stat-chip--failed">Failed: ${s.failed || 0}</span>
            </div>
        </div>
        <div class="campaign-subject">${esc(c.subject)}</div>
        <div class="campaign-actions">
            <button class="btn btn--outline btn--sm" onclick="prepareCampaign(${c.id})">Prepare</button>
            <button class="btn btn--outline btn--sm" onclick="previewCampaign(${c.id})">Preview</button>
            <button class="btn btn--outline btn--sm" onclick="openTestModal(${c.id})">Test</button>
            <button class="btn btn--primary btn--sm" onclick="openSendModal(${c.id}, '${esc(c.name)}', ${s.pending || 0})">Send</button>
            ${(s.failed || 0) > 0 ? `<button class="btn btn--outline btn--sm" style="color:var(--yellow);" onclick="openRetryModal(${c.id})">Retry (${s.failed})</button>` : ""}
            <button class="btn btn--outline btn--sm" onclick="toggleSendsList(${c.id})">Sends ▾</button>
            <button class="btn btn--outline btn--sm" style="color:var(--red);" onclick="deleteCampaign(${c.id}, '${esc(c.name)}')">Delete</button>
        </div>
        <div class="campaign-sends-list" id="sends-list-${c.id}" style="display:none;"></div>
    </div>`;
}

async function prepareCampaign(id) {
    showToast("Preparing emails…", "info");
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${id}/prepare`, "POST", {});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        showToast(data.message, data.prepared > 0 ? "success" : "info");
        loadCampaigns();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function previewCampaign(id) {
    const $body = document.getElementById("preview-modal-body");
    document.getElementById("preview-modal-overlay").classList.add("open");
    $body.innerHTML = '<p style="color:var(--text-muted);">Loading preview…</p>';
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${id}/preview`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "No preview available");
        const sample = data.sample_profile || {};
        $body.innerHTML = `
            <div style="margin-bottom:.75rem; font-size:.8rem; color:var(--text-muted);">
                Sample profile: <strong>${esc(sample.name)}</strong> · ${esc(sample.email)} · ${esc(sample.company)}
            </div>
            <div class="preview-field"><span class="preview-label">Subject</span>${esc(data.subject)}</div>
            <div class="preview-body">${esc(data.body_text)}</div>
            ${data.attachments && data.attachments.length ? `
            <div class="preview-field" style="margin-top:.75rem;"><span class="preview-label">Attachments</span>
                ${data.attachments.map(a => `<span class="email-chip">${esc(a.split(/[\\/]/).pop())}</span>`).join(" ")}
            </div>` : ""}
        `;
    } catch (err) {
        $body.innerHTML = `<p style="color:var(--red);">${esc(err.message)}</p>`;
    }
}

function closePreviewModal() {
    document.getElementById("preview-modal-overlay").classList.remove("open");
}

async function toggleSendsList(id) {
    const $list = document.getElementById(`sends-list-${id}`);
    if ($list.style.display !== "none") {
        $list.style.display = "none";
        return;
    }
    $list.style.display = "block";
    $list.innerHTML = '<p style="color:var(--text-muted); padding:.5rem 0; font-size:.82rem;">Loading sends…</p>';
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${id}/sends?limit=20`);
        const data = await res.json();
        const sends = data.sends || [];
        if (!sends.length) {
            $list.innerHTML = '<p style="color:var(--text-muted); padding:.5rem 0; font-size:.82rem;">No sends yet.</p>';
            return;
        }
        $list.innerHTML = `
            <table class="profiles-table" style="margin-top:.75rem;">
                <thead><tr>
                    <th>Email</th><th>Name</th><th>Company</th><th>Status</th><th>Sent At</th><th>Error</th>
                </tr></thead>
                <tbody>${sends.map(s => `
                    <tr>
                        <td style="font-family:monospace; font-size:.78rem;">${esc(s.email)}</td>
                        <td>${esc((s.first_name || "") + " " + (s.last_name || ""))}</td>
                        <td>${esc(s.company || "")}</td>
                        <td><span class="badge badge--${s.status === "sent" ? "completed" : s.status === "failed" ? "failed" : "draft"}">${s.status}</span></td>
                        <td style="font-size:.75rem; color:var(--text-muted);">${esc((s.sent_at || "—").slice(0, 16))}</td>
                        <td style="font-size:.72rem; color:var(--red);">${esc(s.error_message || "")}</td>
                    </tr>
                `).join("")}</tbody>
            </table>
            ${data.total > 20 ? `<p style="font-size:.78rem; color:var(--text-muted); margin-top:.5rem;">${data.total} total — showing last 20</p>` : ""}
        `;
    } catch (err) {
        $list.innerHTML = `<p style="color:var(--red); font-size:.82rem;">Error: ${esc(err.message)}</p>`;
    }
}

async function deleteCampaign(id, name) {
    if (!confirm(`Delete campaign "${name}"? All queued emails will also be removed.`)) return;
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${id}`, "DELETE");
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        showToast("Campaign deleted", "success");
        loadCampaigns();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

// ── Send Modal ────────────────────────────────────────────
async function openSendModal(campaignId, name, pending) {
    activeSendCampaignId = campaignId;
    document.getElementById("send-modal-title").textContent = `Send: ${name}`;
    document.getElementById("send-modal-subtitle").textContent =
        pending > 0 ? `${pending} emails queued and ready to send`
                    : "No pending emails — will auto-prepare from enriched profiles";
    document.getElementById("send-modal-overlay").classList.add("open");
    await _populateAccountSelect("send-account-select", true);
    onSendAccountChange();
}

function closeSendModal() {
    document.getElementById("send-modal-overlay").classList.remove("open");
    activeSendCampaignId = null;
}

function onSendAccountChange() {
    const val = document.getElementById("send-account-select").value;
    document.getElementById("send-manual-smtp").style.display = val === "__manual" ? "block" : "none";
}

async function doSendCampaign() {
    if (!activeSendCampaignId) return;
    const accountVal = document.getElementById("send-account-select").value;
    const maxRaw     = parseInt(document.getElementById("send-max").value, 10);
    const body = {
        only_verified: document.getElementById("send-verified").checked,
        max_send: maxRaw > 0 ? maxRaw : null,
    };
    if (accountVal === "__manual") {
        body.smtp_preset = document.getElementById("send-smtp").value;
        body.username    = document.getElementById("send-user").value.trim();
        body.password    = document.getElementById("send-pass").value;
        if (!body.username || !body.password)
            return showToast("Username and password required for manual SMTP", "error");
    } else if (accountVal === "__auto_rotate") {
        body.use_account_rotation = true;
    } else {
        body.use_saved_account = true;
        body.account_id = parseInt(accountVal, 10);
    }
    closeSendModal();
    try {
        showToast("Sending emails…", "info");
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${activeSendCampaignId}/send`, "POST", body);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
        showToast(data.message || "Done", data.success !== false ? "success" : "error");
        loadCampaigns();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function openRetryModal(campaignId) {
    // Reuse send modal for retry
    activeSendCampaignId = campaignId;
    document.getElementById("send-modal-title").textContent = "Retry Failed Emails";
    document.getElementById("send-modal-subtitle").textContent = "Failed sends will be reset and re-attempted";
    document.getElementById("send-modal-overlay").classList.add("open");
    await _populateAccountSelect("send-account-select", false); // Rotation currently just supported for normal send API directly
    onSendAccountChange();
    document.getElementById("send-modal-confirm").onclick = () => doRetryCampaign();
}

async function doRetryCampaign() {
    if (!activeSendCampaignId) return;
    const accountVal = document.getElementById("send-account-select").value;
    const body = {};
    if (accountVal === "__manual") {
        body.smtp_preset = document.getElementById("send-smtp").value;
        body.username    = document.getElementById("send-user").value.trim();
        body.password    = document.getElementById("send-pass").value;
    } else {
        body.use_saved_account = true;
        body.account_id = parseInt(accountVal, 10);
    }
    closeSendModal();
    // Reset confirm button
    document.getElementById("send-modal-confirm").onclick = () => doSendCampaign();
    try {
        showToast("Retrying failed emails…", "info");
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${activeSendCampaignId}/retry`, "POST", body);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
        showToast(data.message || "Done", "success");
        loadCampaigns();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

// ── Test Modal ────────────────────────────────────────────
async function openTestModal(campaignId) {
    activeTestCampaignId = campaignId;
    document.getElementById("test-modal-overlay").classList.add("open");
    await _populateAccountSelect("test-account-select");
    onTestAccountChange();
}

function closeTestModal() {
    document.getElementById("test-modal-overlay").classList.remove("open");
    activeTestCampaignId = null;
}

function onTestAccountChange() {
    const val = document.getElementById("test-account-select").value;
    document.getElementById("test-manual-smtp").style.display = val === "__manual" ? "block" : "none";
}

async function doTestEmail() {
    if (!activeTestCampaignId) return;
    const toEmail = document.getElementById("test-to-email").value.trim();
    if (!toEmail) return showToast("Enter a recipient email for the test", "error");
    const accountVal = document.getElementById("test-account-select").value;
    const body = { to_email: toEmail };
    if (accountVal === "__manual") {
        body.smtp_preset = document.getElementById("test-smtp").value;
        body.username    = document.getElementById("test-user").value.trim();
        body.password    = document.getElementById("test-pass").value;
        if (!body.username || !body.password)
            return showToast("SMTP credentials required", "error");
    } else {
        body.use_saved_account = true;
        body.account_id = parseInt(accountVal, 10);
    }
    closeTestModal();
    try {
        showToast(`Sending test to ${toEmail}…`, "info");
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns/${activeTestCampaignId}/test`, "POST", body);
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
        showToast(data.success ? `Test email sent to ${toEmail}` : `Test failed: ${data.message}`,
                  data.success ? "success" : "error");
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

// ── Account selector helper ───────────────────────────────
async function _populateAccountSelect(selectId, showAutoRotate = false) {
    const $sel = document.getElementById(selectId);
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/accounts`);
        const data = await res.json();
        const accounts = data.accounts || [];
        
        let html = '<option value="__manual">Manual SMTP credentials</option>';
        if (showAutoRotate && accounts.length > 0) {
            html += '<option value="__auto_rotate">🌟 Auto-Rotate (Spread across active accounts)</option>';
        }
        
        html += accounts.map(a =>
            `<option value="${a.id}">${esc(a.email)} (${esc(a.smtp_preset)}) — ${a.daily_limit - a.daily_sent_today} left today</option>`
        ).join("");
        
        $sel.innerHTML = html;
    } catch {
        // Keep default
    }
}

// ── CV Form ───────────────────────────────────────────────
function initCVForm() {
    const $option   = document.getElementById("cv-option");
    const $urlGroup = document.getElementById("cv-url-group");

    $option.addEventListener("change", () => {
        $urlGroup.style.display = $option.value === "single" ? "block" : "none";
    });

    document.getElementById("cv-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = { generate_all: $option.value === "all" };
        if ($option.value === "single") {
            data.profile_url = document.getElementById("cv-url").value.trim();
            if (!data.profile_url) return showToast("Profile URL required", "error");
        }
        try {
            showToast("Generating CVs…", "info");
            const res    = await apiFetch(`${API_BASE}/api/cv/generate`, "POST", data);
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
            showToast(result.message || "CVs generated", result.success ? "success" : "error");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

// ── Schedule Form ─────────────────────────────────────────
async function _populateSchedCampaigns() {
    const $sel = document.getElementById("sched-camp-id");
    if (!$sel) return;
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/campaigns`);
        const data = await res.json();
        const campaigns = data.campaigns || [];
        const current = $sel.value;
        $sel.innerHTML = '<option value="">— select a campaign —</option>' +
            campaigns.map(c =>
                `<option value="${c.id}" ${c.id == current ? "selected" : ""}>${esc(c.name)} (ID ${c.id})</option>`
            ).join("");
    } catch { /* keep placeholder */ }
}

function initScheduleForm() {
    // Reload campaign list when this tab becomes active
    document.querySelectorAll('.tab[data-tab="schedule"]').forEach(btn =>
        btn.addEventListener("click", _populateSchedCampaigns)
    );
    _populateSchedCampaigns();

    document.getElementById("schedule-form").addEventListener("submit", async e => {
        e.preventDefault();
        const campId = parseInt(document.getElementById("sched-camp-id").value, 10);
        if (!campId) return showToast("Select a campaign first", "error");

        const days = [...document.querySelectorAll(".day-cb:checked")]
            .map(cb => cb.value).join(",");

        const perDay = parseInt(document.getElementById("sched-per-day").value, 10);
        const data = {
            scheduled_at:         document.getElementById("sched-at").value.trim()    || null,
            send_days:            days || null,
            send_time_start:      document.getElementById("sched-start").value.trim() || null,
            send_time_end:        document.getElementById("sched-end").value.trim()   || null,
            emails_per_day:       perDay > 0 ? perDay : null,
            use_account_rotation: document.getElementById("sched-rotate").checked,
        };
        try {
            const res    = await apiFetch(`${API_BASE}/api/email/campaigns/${campId}/schedule`, "POST", data);
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
            showToast(result.message || "Scheduled", result.success ? "success" : "error");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    document.getElementById("run-scheduler-btn").addEventListener("click", async () => {
        if (!confirm("Run scheduler now? This will send all due campaigns.")) return;
        try {
            showToast("Running scheduler…", "info");
            const res    = await apiFetch(`${API_BASE}/api/email/scheduler/run`, "POST", {});
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
            showToast(result.message || "Scheduler completed", "success");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

// ── Account Form ──────────────────────────────────────────
function initAccountForm() {
    document.getElementById("account-form").addEventListener("submit", async e => {
        e.preventDefault();
        const data = {
            email:       document.getElementById("acc-email").value.trim(),
            smtp_preset: document.getElementById("acc-smtp").value,
            username:    document.getElementById("acc-user").value.trim(),
            password:    document.getElementById("acc-pass").value,
            daily_limit: parseInt(document.getElementById("acc-limit").value, 10),
        };
        try {
            const res    = await apiFetch(`${API_BASE}/api/email/accounts`, "POST", data);
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
            showToast(result.message || "Account added", result.success ? "success" : "error");
            loadAccounts();
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    loadAccounts();
}

async function loadAccounts() {
    const $list = document.getElementById("accounts-list");
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/accounts`);
        const data = await res.json();
        const accounts = data.accounts || [];
        if (!accounts.length) {
            $list.innerHTML = '<p style="color:var(--text-muted);">No accounts configured.</p>';
            return;
        }
        $list.innerHTML = accounts.map(acc => `
            <div class="list-item" style="display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap;">
                <div style="flex:1; min-width:0;">
                    <strong>${esc(acc.email)}</strong>
                    <span class="badge badge--${acc.is_active ? "active" : "inactive"}" style="margin-left:.4rem;">${acc.is_active ? "Active" : "Inactive"}</span>
                    <div style="font-size:.8rem; color:var(--text-muted); margin-top:.25rem;">
                        ${esc(acc.smtp_preset)} &middot; Limit: ${acc.daily_limit}/day &middot; Sent today: ${acc.daily_sent_today}
                    </div>
                </div>
                <div style="display:flex; gap:.4rem; flex-shrink:0;">
                    <button class="btn btn--outline btn--sm" onclick="toggleAccount(${acc.id}, ${acc.is_active ? 0 : 1})">
                        ${acc.is_active ? "Pause" : "Activate"}
                    </button>
                    <button class="btn btn--outline btn--sm" style="color:var(--red);"
                        onclick="deleteAccount(${acc.id}, '${esc(acc.email)}')">Delete</button>
                </div>
            </div>
        `).join("");
    } catch {
        $list.innerHTML = '<p style="color:var(--text-muted);">Failed to load accounts.</p>';
    }
}

async function toggleAccount(id, newActive) {
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/accounts/${id}`, "PATCH", { is_active: newActive === 1 });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        showToast(data.message, "success");
        loadAccounts();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function deleteAccount(id, email) {
    if (!confirm(`Delete account "${email}"? This cannot be undone.`)) return;
    try {
        const res  = await apiFetch(`${API_BASE}/api/email/accounts/${id}`, "DELETE");
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        showToast("Account deleted", "success");
        loadAccounts();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

// ── Auth / Profile Selection ──────────────────────────────
function initAuth() {
    loadAuthStatus();

    document.getElementById("auth-detect-btn").addEventListener("click", async () => {
        const $list = document.getElementById("auth-profiles-list");
        $list.innerHTML = '<p style="color:var(--text-muted);">Scanning...</p>';
        try {
            const res  = await apiFetch("/api/auth/profiles");
            const data = await res.json();
            const profiles = data.profiles || [];
            const activeDir = data.active_profile_dir;

            if (!profiles.length) {
                $list.innerHTML = '<p style="color:var(--text-muted);">No Chrome profiles found. Make sure Chrome is installed.</p>';
                return;
            }
            $list.innerHTML = profiles.map(p => {
                const isActive = p.dir === activeDir;
                return `
                <div class="list-item">
                    <div>
                        <strong>${esc(p.name)}</strong>
                        ${isActive ? '<span class="badge badge--active" style="margin-left:.5rem;">Active</span>' : ""}
                        <div style="font-size:.75rem; color:var(--text-muted); margin-top:.2rem;">${esc(p.dir)} &mdash; ${esc(p.path)}</div>
                    </div>
                    <button class="btn btn--outline" style="width:auto; flex-shrink:0;"
                        onclick="selectProfile(${JSON.stringify(p.data_dir)}, ${JSON.stringify(p.dir)}, ${JSON.stringify(p.name)})">
                        Use this profile
                    </button>
                </div>`;
            }).join("");
        } catch (err) {
            $list.innerHTML = `<p style="color:var(--red);">Error: ${esc(err.message)}</p>`;
        }
    });

    document.getElementById("auth-clear-btn").addEventListener("click", async () => {
        if (!confirm("Clear saved profile? The scraper will fall back to .env credentials.")) return;
        try {
            const res = await apiFetch("/api/auth/profile", "DELETE");
            const data = await res.json();
            showToast(data.message, "success");
            loadAuthStatus();
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

async function selectProfile(dataDir, profileDir, profileName) {
    try {
        const res = await apiFetch("/api/auth/profile", "POST", {
            data_dir: dataDir,
            profile_dir: profileDir,
            profile_name: profileName,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
        showToast(data.message, "success");
        loadAuthStatus();
        // Re-scan so the Active badge updates
        document.getElementById("auth-detect-btn").click();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function loadAuthStatus() {
    const $el = document.getElementById("auth-status-content");
    try {
        const res  = await apiFetch("/api/auth/status");
        const data = await res.json();

        if (data.method === "browser_profile") {
            $el.innerHTML = `
                <div class="list-item" style="background:rgba(63,185,80,.06); border-radius:var(--radius-sm); border:1px solid rgba(63,185,80,.2);">
                    <div>
                        <span class="badge badge--active">Browser Profile</span>
                        <strong style="margin-left:.5rem;">${esc(data.profile_name)}</strong>
                        <div style="font-size:.75rem; color:var(--text-muted); margin-top:.3rem;">
                            ${esc(data.data_dir)} &rsaquo; ${esc(data.profile_dir)}
                        </div>
                        <div style="font-size:.75rem; color:var(--green); margin-top:.2rem;">
                            Chrome will open with this profile — no login required if already signed into LinkedIn.
                        </div>
                    </div>
                </div>`;
        } else if (data.method === "credentials") {
            $el.innerHTML = `
                <div class="list-item" style="background:rgba(88,166,255,.06); border-radius:var(--radius-sm); border:1px solid rgba(88,166,255,.2);">
                    <div>
                        <span class="badge badge--scheduled">Credentials</span>
                        <strong style="margin-left:.5rem;">${esc(data.email)}</strong>
                        <div style="font-size:.75rem; color:var(--text-muted); margin-top:.3rem;">
                            Using LINKEDIN_EMAIL / LINKEDIN_PASSWORD from .env
                        </div>
                    </div>
                </div>`;
        } else {
            $el.innerHTML = `
                <div class="list-item" style="background:rgba(248,81,73,.06); border-radius:var(--radius-sm); border:1px solid rgba(248,81,73,.2);">
                    <span class="badge badge--failed">Not configured</span>
                    <span style="margin-left:.5rem; color:var(--text-muted);">
                        No profile selected and no credentials in .env — LinkedIn scraping will fail.
                    </span>
                </div>`;
        }
    } catch {
        $el.innerHTML = '<p style="color:var(--text-muted);">Failed to load status.</p>';
    }
}

// ── Stats ─────────────────────────────────────────────────
function initStats() {
    loadStats();
}

async function loadStats() {
    const $c = document.getElementById("stats-content");
    try {
        const res  = await apiFetch(`${API_BASE}/api/stats`);
        const data = await res.json();
        const s    = data.stats || {};
        $c.innerHTML = `
            <div class="stats-grid">
                ${renderStat("Search Profiles",   s.search_profiles   || 0)}
                ${renderStat("Enriched Profiles", s.enriched_profiles || 0)}
                ${renderStat("Group Members",     s.group_members     || 0)}
                ${renderStat("Connections",        s.connections       || 0)}
                ${renderStat("Messages",           s.messages          || 0)}
                ${renderStat("Campaigns",          s.email_campaigns   || 0)}
                ${renderStat("Email Sends",        s.email_sends       || 0)}
            </div>
        `;
    } catch {
        $c.innerHTML = '<p style="color:var(--text-muted);">Failed to load statistics.</p>';
    }
}

function renderStat(label, value) {
    return `
        <div class="stat-card">
            <div class="stat-card__value">${value}</div>
            <div class="stat-card__label">${label}</div>
        </div>
    `;
}

// ── Quick Actions ─────────────────────────────────────────
function initQuickActions() {
    document.getElementById("export-csv-btn").addEventListener("click", () => {
        window.open(`${API_BASE}/api/export`, "_blank");
    });

    document.getElementById("reset-daily-btn").addEventListener("click", async () => {
        if (!confirm("Reset daily send counts for all email accounts?")) return;
        try {
            const res    = await apiFetch(`${API_BASE}/api/email/accounts/reset`, "POST", {});
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || JSON.stringify(result));
            showToast("Daily counts reset", "success");
            loadAccounts();
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

// ── Background Job Handling ───────────────────────────────
async function startJob(url, data, jobName) {
    try {
        showToast(`${jobName} starting…`, "info");
        const res = await apiFetch(url, "POST", data);
        if (!res.ok) {
            const errBody = await res.json().catch(() => ({}));
            throw new Error(errBody.detail || `HTTP ${res.status}`);
        }
        const result = await res.json();
        currentJobId = result.job_id;
        showJobBar(result.job_id, jobName);
        startPolling();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

function showJobBar(jobId, name) {
    $jobBar.classList.remove("hidden");
    $jobText.textContent = `${name} (${jobId})`;
    $jobProgress.style.width = "0%";
    $jobPct.textContent = "0%";
}

function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
        if (!currentJobId) return;
        try {
            const res = await apiFetch(`${API_BASE}/api/jobs/${currentJobId}`);
            if (!res.ok) return;
            const job = await res.json();
            const pct = job.progress || 0;
            $jobProgress.style.width = `${pct}%`;
            $jobPct.textContent = `${pct}%`;
            $jobText.textContent = `${job.type || ""} — ${job.status}`;

            // Live log feed
            const logs = job.logs || [];
            const $logFeed = document.getElementById("job-log-feed");
            if ($logFeed && logs.length) {
                $logFeed.innerHTML = logs.slice(-8).map(l =>
                    `<div class="log-line log-line--${l.level}"><span class="log-ts">${esc(l.ts)}</span> ${esc(l.msg)}</div>`
                ).join("");
                $logFeed.scrollTop = $logFeed.scrollHeight;
            }

            if (job.status === "completed" || job.status === "failed") {
                stopPolling();
                // Determine real success: job failed OR scrape result indicates failure
                const scrapeOk = job.status === "completed" && (job.result ? job.result.success !== false : true);
                const saved = job.result && job.result.profiles_saved != null ? job.result.profiles_saved : null;
                const errMsg = job.error || (job.result && job.result.error) || null;
                let msg;
                if (errMsg) {
                    msg = errMsg;
                } else if (saved != null) {
                    msg = `${saved} profile${saved !== 1 ? "s" : ""} saved`;
                } else {
                    msg = job.result && job.result.message ? job.result.message : job.status;
                }
                showToast(`${scrapeOk ? "Done" : "Error"}: ${msg}`, scrapeOk ? "success" : "error");
                loadStats();
                loadCampaigns();
            }
        } catch (err) {
            console.warn("Poll error:", err);
        }
    }, POLL_INTERVAL);
}

function stopPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    setTimeout(() => $jobBar.classList.add("hidden"), 3000);
}

// ── Profiles ─────────────────────────────────────────────
let profilesPage = 0;
const PROFILES_PER_PAGE = 50;
let profilesSearch = "";
let profilesStatusFilter = "";
let selectedProfileIds = new Set();
let currentDrawerProfileId = null;

function initProfiles() {
    const searchInput = document.getElementById("profiles-search");
    searchInput.addEventListener("input", debounce(() => {
        profilesSearch = searchInput.value.trim();
        profilesPage = 0;
        loadProfiles();
    }, 400));

    document.getElementById("profiles-status-filter").addEventListener("change", e => {
        profilesStatusFilter = e.target.value;
        profilesPage = 0;
        loadProfiles();
    });

    document.getElementById("profiles-refresh-btn").addEventListener("click", () => loadProfiles());

    document.getElementById("profiles-enrich-all-btn").addEventListener("click", async () => {
        if (!confirm("Enrich all unenriched profiles? A browser window will open.")) return;
        try {
            const res = await apiFetch(`${API_BASE}/api/profiles/enrich`, "POST", {});
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
            currentJobId = data.job_id;
            showJobBar(data.job_id, "Profile Enrichment");
            startPolling();
            showToast("Enrichment job started", "info");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    document.getElementById("bulk-deselect-btn").addEventListener("click", () => {
        selectedProfileIds.clear();
        updateBulkBar();
        renderSelectionState();
    });

    document.getElementById("bulk-delete-btn").addEventListener("click", async () => {
        const count = selectedProfileIds.size;
        if (!count || !confirm(`Delete ${count} profile(s)? This cannot be undone.`)) return;
        let deleted = 0;
        for (const id of selectedProfileIds) {
            try {
                const res = await apiFetch(`${API_BASE}/api/profiles/${id}`, "DELETE");
                if (res.ok) deleted++;
            } catch {}
        }
        selectedProfileIds.clear();
        showToast(`${deleted} profile(s) deleted`, deleted > 0 ? "success" : "error");
        loadProfiles();
    });
}

async function loadProfiles() {
    const $container = document.getElementById("profiles-table-container");
    $container.innerHTML = '<p style="color:var(--text-muted); padding:.5rem 0;">Loading…</p>';

    const params = new URLSearchParams({
        limit: PROFILES_PER_PAGE,
        offset: profilesPage * PROFILES_PER_PAGE,
        search: profilesSearch,
        status: profilesStatusFilter,
    });

    try {
        const res = await apiFetch(`${API_BASE}/api/profiles?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const profiles = data.profiles || [];
        const total = data.total || 0;

        if (!profiles.length) {
            $container.innerHTML = '<p style="color:var(--text-muted); padding:.5rem 0;">No profiles found.</p>';
            document.getElementById("profiles-pagination").innerHTML = "";
            return;
        }

        $container.innerHTML = `
            <table class="profiles-table">
                <thead>
                    <tr>
                        <th><input type="checkbox" id="profiles-select-all" onchange="toggleSelectAll(this)"></th>
                        <th>Name / Title</th>
                        <th>Company</th>
                        <th>Location</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>${profiles.map(p => renderProfileRow(p)).join("")}</tbody>
            </table>
        `;

        renderPagination(total);
        renderSelectionState();

        $container.querySelectorAll("tr[data-profile-id]").forEach(row => {
            row.addEventListener("click", e => {
                if (e.target.type === "checkbox" || e.target.tagName === "BUTTON") return;
                openDrawer(parseInt(row.dataset.profileId));
            });
        });

    } catch (err) {
        $container.innerHTML = `<p style="color:var(--red);">Error: ${esc(err.message)}</p>`;
    }
}

function renderProfileRow(p) {
    const name = p.full_name || p.name || "—";
    const title = p.current_job_title || p.title || "—";
    const company = p.current_company || p.company || "—";
    const location = p.location || "—";
    const email = p.generated_email || "—";
    const isEnriched = p.enrichment_status === "success";
    const connStatus = p.connection_status;
    const isSelected = selectedProfileIds.has(p.id);

    const statusBadge = isEnriched
        ? `<span class="badge badge--completed">Enriched</span>`
        : `<span class="badge badge--draft">Raw</span>`;
    const connBadge = connStatus
        ? `<span class="badge badge--active" style="margin-left:.3rem;">${esc(connStatus)}</span>`
        : "";

    return `
        <tr data-profile-id="${p.id}" class="profiles-row${isSelected ? " selected" : ""}">
            <td><input type="checkbox" class="profile-checkbox" data-id="${p.id}"
                ${isSelected ? "checked" : ""} onchange="toggleProfileSelection(${p.id}, this)"></td>
            <td>
                <div class="profile-name">${esc(name)}</div>
                <div class="profile-title">${esc(title)}</div>
            </td>
            <td>${esc(company)}</td>
            <td>${esc(location)}</td>
            <td class="profile-email">${email !== "—" ? esc(email) : '<span style="color:var(--text-dim)">—</span>'}</td>
            <td>${statusBadge}${connBadge}</td>
            <td><button class="btn btn--outline btn--sm" onclick="openDrawer(${p.id})">View</button></td>
        </tr>
    `;
}

function renderPagination(total) {
    const totalPages = Math.ceil(total / PROFILES_PER_PAGE);
    const $pag = document.getElementById("profiles-pagination");
    if (totalPages <= 1) { $pag.innerHTML = ""; return; }

    let html = '<div class="pagination">';
    html += `<button class="page-btn" onclick="goToPage(${profilesPage - 1})" ${profilesPage === 0 ? "disabled" : ""}>Previous</button>`;

    for (let i = 0; i < totalPages; i++) {
        const nearCurrent = Math.abs(i - profilesPage) <= 2;
        const isEdge = i === 0 || i === totalPages - 1;
        if (!nearCurrent && !isEdge) {
            if (i === 1 || i === totalPages - 2) html += '<span class="page-ellipsis">…</span>';
            continue;
        }
        html += `<button class="page-btn${i === profilesPage ? " active" : ""}" onclick="goToPage(${i})">${i + 1}</button>`;
    }

    html += `<button class="page-btn" onclick="goToPage(${profilesPage + 1})" ${profilesPage >= totalPages - 1 ? "disabled" : ""}>Next</button>`;
    html += `<span class="page-info">${total} total</span></div>`;
    $pag.innerHTML = html;
}

function goToPage(page) {
    profilesPage = page;
    loadProfiles();
}

function toggleSelectAll(checkbox) {
    document.querySelectorAll(".profile-checkbox").forEach(cb => {
        const id = parseInt(cb.dataset.id);
        cb.checked = checkbox.checked;
        if (checkbox.checked) selectedProfileIds.add(id);
        else selectedProfileIds.delete(id);
    });
    document.querySelectorAll("tr[data-profile-id]").forEach(row => {
        row.classList.toggle("selected", checkbox.checked);
    });
    updateBulkBar();
}

function toggleProfileSelection(id, checkbox) {
    if (checkbox.checked) selectedProfileIds.add(id);
    else selectedProfileIds.delete(id);
    const row = document.querySelector(`tr[data-profile-id="${id}"]`);
    if (row) row.classList.toggle("selected", checkbox.checked);
    updateBulkBar();
}

function renderSelectionState() {
    document.querySelectorAll(".profile-checkbox").forEach(cb => {
        const id = parseInt(cb.dataset.id);
        cb.checked = selectedProfileIds.has(id);
        const row = document.querySelector(`tr[data-profile-id="${id}"]`);
        if (row) row.classList.toggle("selected", selectedProfileIds.has(id));
    });
    updateBulkBar();
}

function updateBulkBar() {
    const $bar = document.getElementById("profiles-bulk-bar");
    const count = selectedProfileIds.size;
    $bar.classList.toggle("visible", count > 0);
    document.getElementById("profiles-selection-count").textContent = `${count} selected`;
}

async function openDrawer(profileId) {
    currentDrawerProfileId = profileId;
    document.getElementById("profile-drawer").classList.add("open");
    document.getElementById("drawer-overlay").classList.add("visible");
    const $body = document.getElementById("drawer-body");
    const $name = document.getElementById("drawer-name");
    $body.innerHTML = '<p style="color:var(--text-muted);">Loading…</p>';

    try {
        const res = await apiFetch(`${API_BASE}/api/profiles/${profileId}`);
        if (!res.ok) throw new Error("Profile not found");
        const p = await res.json();

        $name.textContent = p.full_name || p.name || "Profile";

        const variants = (() => { try { return JSON.parse(p.all_email_variants || "[]"); } catch { return []; } })();
        const experiences = (() => { try { return JSON.parse(p.experiences || "[]"); } catch { return []; } })();

        $body.innerHTML = `
            <div class="drawer-section">
                <div class="drawer-field">
                    <span class="drawer-label">LinkedIn</span>
                    <a href="${esc(p.profile_url)}" target="_blank" rel="noopener" class="drawer-link">${esc(p.profile_url)}</a>
                </div>
                <div class="drawer-field"><span class="drawer-label">Title</span><span>${esc(p.current_job_title || p.title || "—")}</span></div>
                <div class="drawer-field"><span class="drawer-label">Company</span><span>${esc(p.current_company || p.company || "—")}</span></div>
                <div class="drawer-field"><span class="drawer-label">Location</span><span>${esc(p.location || "—")}</span></div>
                <div class="drawer-field"><span class="drawer-label">Domain</span><span>${esc(p.current_company_domain || "—")}</span></div>
            </div>
            <div class="drawer-section">
                <div class="drawer-section-title">Contact</div>
                <div class="drawer-field">
                    <span class="drawer-label">Email</span>
                    <strong style="color:var(--green)">${esc(p.generated_email || "—")}</strong>
                </div>
                ${variants.length > 1 ? `
                <div class="drawer-field">
                    <span class="drawer-label">Variants</span>
                    <div>${variants.map(v => `<span class="email-chip">${esc(v)}</span>`).join(" ")}</div>
                </div>` : ""}
            </div>
            ${p.about_text ? `
            <div class="drawer-section">
                <div class="drawer-section-title">About</div>
                <p class="drawer-about">${esc(p.about_text)}</p>
            </div>` : ""}
            ${experiences.length ? `
            <div class="drawer-section">
                <div class="drawer-section-title">Experience</div>
                ${experiences.slice(0, 4).map(exp => `
                    <div class="exp-item">
                        <div class="exp-title">${esc(exp.title || exp.position || "")}</div>
                        <div class="exp-company">${esc(exp.company || "")}</div>
                        <div class="exp-dates">${esc(exp.dates || exp.duration || "")}</div>
                    </div>
                `).join("")}
            </div>` : ""}
            <div class="drawer-section">
                <div class="drawer-section-title">Metadata</div>
                <div class="drawer-field">
                    <span class="drawer-label">Enrichment</span>
                    <span class="badge badge--${p.enrichment_status === "success" ? "completed" : p.enrichment_status ? "failed" : "draft"}">
                        ${p.enrichment_status || "not enriched"}
                    </span>
                </div>
                <div class="drawer-field">
                    <span class="drawer-label">Connection</span>
                    <span>${esc(p.connection_status || "—")}</span>
                </div>
                <div class="drawer-field">
                    <span class="drawer-label">Keyword</span>
                    <span>${esc(p.search_keyword || "—")}</span>
                </div>
                <div class="drawer-field">
                    <span class="drawer-label">Scraped</span>
                    <span style="font-size:.78rem;">${esc((p.scraped_at || "—").replace("T", " ").slice(0, 19))}</span>
                </div>
            </div>
        `;

        document.getElementById("drawer-enrich-btn").onclick = () => enrichSingle(profileId);
        document.getElementById("drawer-connect-btn").onclick = () => connectSingle(p.profile_url);
        document.getElementById("drawer-cv-btn").onclick = () => generateCvFor(p.profile_url);
        document.getElementById("drawer-delete-btn").onclick = () => deleteSingle(profileId);

    } catch (err) {
        $body.innerHTML = `<p style="color:var(--red);">Failed to load: ${esc(err.message)}</p>`;
    }
}

function closeDrawer() {
    document.getElementById("profile-drawer").classList.remove("open");
    document.getElementById("drawer-overlay").classList.remove("visible");
    currentDrawerProfileId = null;
}

async function enrichSingle(profileId) {
    showToast("Starting enrichment…", "info");
    try {
        const res = await apiFetch(`${API_BASE}/api/profiles/enrich`, "POST", { max_profiles: 1 });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        currentJobId = data.job_id;
        showJobBar(data.job_id, "Profile Enrichment");
        startPolling();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function connectSingle(profileUrl) {
    if (!profileUrl || !confirm(`Send connection request to this profile?`)) return;
    try {
        await startJob(`${API_BASE}/api/connections/send`, { profile_url: profileUrl, note_message: null }, "Connection");
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function generateCvFor(profileUrl) {
    if (!profileUrl) return showToast("No profile URL", "error");
    showToast("Generating CV…", "info");
    try {
        const res = await apiFetch(`${API_BASE}/api/cv/generate`, "POST", { profile_url: profileUrl });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        showToast(data.message || "CV generated", data.success ? "success" : "error");
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

async function deleteSingle(profileId) {
    if (!confirm("Delete this profile from the database? This cannot be undone.")) return;
    try {
        const res = await apiFetch(`${API_BASE}/api/profiles/${profileId}`, "DELETE");
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed");
        showToast("Profile deleted", "success");
        closeDrawer();
        loadProfiles();
    } catch (err) {
        showToast(`Error: ${err.message}`, "error");
    }
}

function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

// ── Toasts ────────────────────────────────────────────────
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    $toasts.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Helpers ───────────────────────────────────────────────
function apiFetch(url, method = "GET", body = null) {
    const opts = {
        method,
        headers: { "Content-Type": "application/json" },
    };
    if (body !== null && method !== "GET") {
        opts.body = JSON.stringify(body);
    }
    return fetch(url, opts);
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}
