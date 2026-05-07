/**
 * LinkedIn Scraper Control Panel — Full UI JavaScript
 * Handles all tabs: Scrape, Enrich, Email, CV, Schedule, Accounts, Stats
 */
const API_BASE = "http://localhost:8000";
const POLL_INTERVAL = 3000;

// ── DOM Refs ──────────────────────────────────────
const $apiStatus = document.getElementById("api-status");
const $jobBar = document.getElementById("job-status-bar");
const $jobText = document.getElementById("job-status-text");
const $jobProgress = document.getElementById("job-progress-bar");
const $jobPct = document.getElementById("job-progress-text");
const $toastContainer = document.getElementById("toast-container");

let currentJobId = null;
let pollTimer = null;

// ── Init ───────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    checkApiHealth();
    setInterval(checkApiHealth, 15000);
    initTabs();
    initScrapeForms();
    initEnrichForm();
    initCampaignForms();
    initCVForm();
    initScheduleForm();
    initAccountForm();
    initStats();
    initQuickActions();
});

// ── API Health ──────────────────────────────────────
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

// ── Tabs ────────────────────────────────────────────
function initTabs() {
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            const target = document.getElementById(`tab-${tab.dataset.tab}`);
            if (target) target.classList.add("active");
            // Refresh data when switching tabs
            if (tab.dataset.tab === "email") loadCampaigns();
            if (tab.dataset.tab === "accounts") loadAccounts();
            if (tab.dataset.tab === "stats") loadStats();
        });
    });
}

// ── Scrape Forms ────────────────────────────────────
function initScrapeForms() {
    // Google scrape
    document.getElementById("google-scrape-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            keywords: document.getElementById("gs-keywords").value.trim(),
            oblig_keywords: document.getElementById("gs-oblig").value.trim(),
            max_profiles: parseInt(document.getElementById("gs-max-profiles").value, 10),
            max_profiles_per_keyword: parseInt(document.getElementById("gs-per-kw").value, 10),
        };
        if (!data.keywords) return showToast("Keywords required", "error");
        await startJob(`${API_BASE}/api/scrape/google`, data, "Google scrape");
    });

    // Group scrape
    document.getElementById("group-scrape-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            group_url: document.getElementById("grp-url").value.trim(),
            max_members: parseInt(document.getElementById("grp-max").value, 10) || null,
            scraping_mode: document.getElementById("grp-mode").value,
        };
        if (!data.group_url) return showToast("Group URL required", "error");
        await startJob(`${API_BASE}/api/scrape/group`, data, "Group scrape");
    });
}

// ── Enrich Form ─────────────────────────────────────
function initEnrichForm() {
    document.getElementById("enrich-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            csv_file_path: document.getElementById("enrich-csv").value.trim(),
            url_column: document.getElementById("enrich-col").value.trim() || "Profile URL",
            max_profiles: parseInt(document.getElementById("enrich-max").value, 10) || null,
            generate_cv: document.getElementById("enrich-cv").checked,
        };
        if (!data.csv_file_path) return showToast("CSV path required", "error");
        await startJob(`${API_BASE}/api/enrich`, data, "Enrichment");
    });
}

// ── Campaign Forms ──────────────────────────────────
function initCampaignForms() {
    // Create campaign
    document.getElementById("campaign-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            name: document.getElementById("camp-name").value.trim(),
            subject: document.getElementById("camp-subject").value.trim(),
            body_text: document.getElementById("camp-body").value.trim(),
            cv_path: document.getElementById("camp-cv").value.trim() || null,
            cover_letter_path: document.getElementById("camp-cover").value.trim() || null,
        };
        if (!data.name || !data.subject || !data.body_text) {
            return showToast("Name, subject, body required", "error");
        }
        try {
            const res = await fetch(`${API_BASE}/api/email/campaigns`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            if (!res.ok) throw new Error(await res.text());
            const result = await res.json();
            showToast(`Campaign created! ID: ${result.campaign_id}`, "success");
            loadCampaigns();
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    // Send emails
    document.getElementById("send-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            campaign_id: parseInt(document.getElementById("send-camp-id").value, 10),
            smtp_preset: document.getElementById("send-smtp").value,
            username: document.getElementById("send-user").value.trim(),
            password: document.getElementById("send-pass").value,
            max_send: parseInt(document.getElementById("send-max").value, 10) || null,
            only_verified: document.getElementById("send-verified").checked,
        };
        try {
            const res = await fetch(`${API_BASE}/api/email/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            showToast(result.message || "Emails sent", result.success ? "success" : "error");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    loadCampaigns();
}

async function loadCampaigns() {
    const $list = document.getElementById("campaigns-list");
    try {
        const res = await fetch(`${API_BASE}/api/email/campaigns`);
        const data = await res.json();
        const campaigns = data.campaigns || [];
        if (campaigns.length === 0) {
            $list.innerHTML = '<p style="color:var(--text-muted);">No campaigns yet.</p>';
            return;
        }
        $list.innerHTML = campaigns.map(c => `
            <div class="list-item">
                <div>
                    <strong>${esc(c.name)}</strong>
                    <span class="badge badge--${c.status}">${c.status}</span>
                </div>
                <div style="font-size:0.8rem; color:var(--text-muted);">
                    Sent: ${c.total_sent || 0} | Failed: ${c.total_failed || 0}
                </div>
            </div>
        `).join("");
    } catch {
        $list.innerHTML = '<p style="color:var(--text-muted);">Failed to load campaigns.</p>';
    }
}

// ── CV Form ─────────────────────────────────────────
function initCVForm() {
    const $option = document.getElementById("cv-option");
    const $urlGroup = document.getElementById("cv-url-group");

    $option.addEventListener("change", () => {
        $urlGroup.style.display = $option.value === "single" ? "block" : "none";
    });

    document.getElementById("cv-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const option = $option.value;
        const data = { generate_all: option === "all" };
        if (option === "single") {
            data.profile_url = document.getElementById("cv-url").value.trim();
            if (!data.profile_url) return showToast("Profile URL required", "error");
        }
        try {
            showToast("Generating CVs...", "info");
            const res = await fetch(`${API_BASE}/api/cv/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            showToast(result.message || "CVs generated", result.success ? "success" : "error");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

// ── Schedule Form ───────────────────────────────────
function initScheduleForm() {
    document.getElementById("schedule-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            campaign_id: parseInt(document.getElementById("sched-camp-id").value, 10),
            scheduled_at: document.getElementById("sched-at").value.trim() || null,
            send_days: document.getElementById("sched-days").value.trim() || null,
            send_time_start: document.getElementById("sched-start").value.trim() || null,
            send_time_end: document.getElementById("sched-end").value.trim() || null,
            emails_per_day: parseInt(document.getElementById("sched-per-day").value, 10) || null,
            use_account_rotation: document.getElementById("sched-rotate").checked,
        };
        try {
            const res = await fetch(`${API_BASE}/api/email/schedule`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
            showToast(result.message || "Campaign scheduled", result.success ? "success" : "error");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });

    document.getElementById("run-scheduler-btn").addEventListener("click", async () => {
        if (!confirm("Run scheduler now? This will send due campaigns.")) return;
        try {
            showToast("Running scheduler...", "info");
            const res = await fetch(`${API_BASE}/api/email/scheduler/run`, {
                method: "POST",
            });
            const result = await res.json();
            showToast(result.message || "Scheduler completed", "success");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

// ── Account Form ───────────────────────────────────
function initAccountForm() {
    document.getElementById("account-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = {
            email: document.getElementById("acc-email").value.trim(),
            smtp_preset: document.getElementById("acc-smtp").value,
            username: document.getElementById("acc-user").value.trim(),
            password: document.getElementById("acc-pass").value,
            daily_limit: parseInt(document.getElementById("acc-limit").value, 10),
        };
        try {
            const res = await fetch(`${API_BASE}/api/email/accounts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });
            const result = await res.json();
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
        const res = await fetch(`${API_BASE}/api/email/accounts`);
        const data = await res.json();
        const accounts = data.accounts || [];
        if (accounts.length === 0) {
            $list.innerHTML = '<p style="color:var(--text-muted);">No accounts configured.</p>';
            return;
        }
        $list.innerHTML = accounts.map(acc => `
            <div class="list-item">
                <div>
                    <strong>${esc(acc.email)}</strong>
                    <span class="badge badge--${acc.is_active ? 'active' : 'inactive'}">${acc.is_active ? 'Active' : 'Inactive'}</span>
                </div>
                <div style="font-size:0.8rem; color:var(--text-muted);">
                    ${esc(acc.smtp_preset)} | Limit: ${acc.daily_limit} | Sent today: ${acc.daily_sent_today}
                </div>
            </div>
        `).join("");
    } catch {
        $list.innerHTML = '<p style="color:var(--text-muted);">Failed to load accounts.</p>';
    }
}

// ── Stats ───────────────────────────────────────────
function initStats() {
    loadStats();
}

async function loadStats() {
    const $content = document.getElementById("stats-content");
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();
        const stats = data.stats || {};
        $content.innerHTML = `
            <div class="stats-grid">
                ${renderStat("Search Profiles", stats.search_profiles || 0)}
                ${renderStat("Enriched Profiles", stats.enriched_profiles || 0)}
                ${renderStat("Group Members", stats.group_members || 0)}
                ${renderStat("Connections", stats.connections || 0)}
                ${renderStat("Messages", stats.messages || 0)}
                ${renderStat("Campaigns", stats.email_campaigns || 0)}
                ${renderStat("Emails Sent", stats.email_sends || 0)}
            </div>
        `;
    } catch {
        $content.innerHTML = '<p style="color:var(--text-muted);">Failed to load statistics.</p>';
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

// ── Quick Actions ───────────────────────────────────
function initQuickActions() {
    document.getElementById("export-csv-btn").addEventListener("click", () => {
        window.open(`${API_BASE}/api/export`, "_blank");
    });
    document.getElementById("reset-daily-btn").addEventListener("click", async () => {
        if (!confirm("Reset daily counts for all email accounts?")) return;
        try {
            const res = await fetch(`${API_BASE}/api/email/accounts/reset`, { method: "POST" });
            showToast("Daily counts reset", "success");
        } catch (err) {
            showToast(`Error: ${err.message}`, "error");
        }
    });
}

// ── Job Handling ───────────────────────────────────
async function startJob(url, data, jobName) {
    try {
        showToast(`${jobName} job starting...`, "info");
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(await res.text());
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
            const res = await fetch(`${API_BASE}/api/jobs/${currentJobId}`);
            if (!res.ok) return;
            const job = await res.json();
            const pct = job.progress || 0;
            $jobProgress.style.width = `${pct}%`;
            $jobPct.textContent = `${pct}%`;
            $jobText.textContent = `${job.status}: ${job.message || ''}`;
            if (job.status === "completed" || job.status === "failed") {
                stopPolling();
                showToast(`Job ${job.status}: ${job.message || ''}`, job.status === "completed" ? "success" : "error");
                // Refresh relevant data
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

// ── Toast Notifications ─────────────────────────────
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    $toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ── Helpers ────────────────────────────────────────
function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}
