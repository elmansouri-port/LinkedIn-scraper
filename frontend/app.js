/**
 * LinkedIn Scraper — Control Panel JS
 * Connects to the FastAPI backend to run Google → LinkedIn scraping jobs.
 */

const API_BASE = "http://localhost:8000";
const POLL_INTERVAL = 3000; // ms

// ── DOM refs ────────────────────────────────────────────
const $form         = document.getElementById("scrape-form");
const $startBtn     = document.getElementById("start-btn");
const $apiStatus    = document.getElementById("api-status");
const $statusSection= document.getElementById("status-section");
const $resultsSection=document.getElementById("results-section");
const $errorSection = document.getElementById("error-section");

const $jobId        = document.getElementById("job-id");
const $jobStatus    = document.getElementById("job-status");
const $jobProgress  = document.getElementById("job-progress");
const $jobMessage   = document.getElementById("job-message");
const $progressBar  = document.getElementById("progress-bar");
const $resultsBody  = document.getElementById("results-body");
const $resultsCount = document.getElementById("results-count");
const $exportBtn    = document.getElementById("export-btn");
const $errorMsg     = document.getElementById("error-message");
const $statsBar     = document.getElementById("stats-bar");

let currentJobId = null;
let pollTimer    = null;
let collectedProfiles = [];

// ── Check API health ────────────────────────────────────
async function checkApiHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            $apiStatus.innerHTML = `<span class="dot dot--online"></span><span class="status-text">API Online</span>`;
        } else throw new Error();
    } catch {
        $apiStatus.innerHTML = `<span class="dot dot--offline"></span><span class="status-text">API Offline</span>`;
    }
}

// ── Start scrape ────────────────────────────────────────
$form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const keywords     = document.getElementById("keywords").value.trim();
    const obligKw      = document.getElementById("oblig_keywords").value.trim();
    const maxProfiles  = parseInt(document.getElementById("max_profiles").value, 10);
    const maxPerKw     = parseInt(document.getElementById("max_per_keyword").value, 10);
    const apiKey       = document.getElementById("api_key").value.trim();

    if (!keywords) return;

    // Reset UI
    hideSection($errorSection);
    hideSection($resultsSection);
    showSection($statusSection);
    collectedProfiles = [];
    renderProfiles([]);

    setProgress(0, "pending", "Submitting job…");

    try {
        const res = await fetch(`${API_BASE}/api/v1/scrape/google`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": apiKey,
            },
            body: JSON.stringify({
                keywords,
                oblig_keywords: obligKw,
                max_profiles: maxProfiles,
                max_profiles_per_keyword: maxPerKw,
            }),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || errData.message || `HTTP ${res.status}`);
        }

        const data = await res.json();
        currentJobId = data.job_id;
        $jobId.textContent = currentJobId;
        setProgress(0, "pending", data.message || "Job created");

        // Start polling
        startPolling(apiKey);

    } catch (err) {
        showError(err.message);
    }
});

// ── Polling ─────────────────────────────────────────────
function startPolling(apiKey) {
    if (pollTimer) clearInterval(pollTimer);
    $startBtn.disabled = true;
    $startBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg> Running…`;

    pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/scrape/status/${currentJobId}`, {
                headers: { "X-API-Key": apiKey },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const job = await res.json();
            setProgress(job.progress || 0, job.status, job.message || "");

            if (job.status === "completed") {
                stopPolling();
                handleCompleted(job.result);
            } else if (job.status === "failed") {
                stopPolling();
                showError(job.error || "Job failed");
            }
        } catch (err) {
            // Don't stop polling on transient fetch errors
            console.warn("Poll error:", err);
        }
    }, POLL_INTERVAL);
}

function stopPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = null;
    $startBtn.disabled = false;
    $startBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Scraping`;
}

// ── Handle completed ────────────────────────────────────
function handleCompleted(result) {
    if (!result) return;

    const profiles = result.profiles || [];
    collectedProfiles = profiles;

    // Show stats bar
    const stats = result.stats || {};
    document.getElementById("stat-saved").textContent    = result.profiles_saved || profiles.length;
    document.getElementById("stat-pages").textContent    = stats.total_pages_scraped || 0;
    document.getElementById("stat-dupes").textContent    = stats.duplicate_urls_found || 0;
    document.getElementById("stat-rate").textContent     = stats.rate || "—";
    document.getElementById("stat-duration").textContent = stats.duration || "—";
    $statsBar.classList.remove("hidden");

    renderProfiles(profiles);
    showSection($resultsSection);
    $exportBtn.disabled = profiles.length === 0;
}

// ── Render profiles table ───────────────────────────────
function renderProfiles(profiles) {
    $resultsCount.textContent = profiles.length;
    $resultsBody.innerHTML = "";

    profiles.forEach((p, i) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${i + 1}</td>
            <td title="${esc(p.name)}">${esc(p.name)}</td>
            <td title="${esc(p.title)}">${esc(p.title || "—")}</td>
            <td title="${esc(p.company)}">${esc(p.company || "—")}</td>
            <td title="${esc(p.location)}">${esc(p.location || "—")}</td>
            <td><a href="${esc(p.profile_url)}" target="_blank" rel="noopener">View</a></td>
        `;
        $resultsBody.appendChild(tr);
    });
}

// ── Export CSV ───────────────────────────────────────────
$exportBtn.addEventListener("click", () => {
    if (!collectedProfiles.length) return;

    const headers = ["name", "title", "company", "location", "profile_url", "description"];
    const csvRows = [headers.join(",")];

    collectedProfiles.forEach(p => {
        const row = headers.map(h => `"${(p[h] || '').replace(/"/g, '""')}"`);
        csvRows.push(row.join(","));
    });

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scraped_profiles_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
});

// ── Helpers ─────────────────────────────────────────────
function setProgress(pct, status, message) {
    const p = Math.min(100, Math.max(0, pct));
    $progressBar.style.width = `${p}%`;
    $jobProgress.textContent = `${p}%`;
    $jobStatus.textContent = status;
    $jobMessage.textContent = message;

    // Badge color
    $jobStatus.style.background =
        status === "completed" ? "rgba(63,185,80,.15)" :
        status === "failed"    ? "rgba(248,81,73,.15)" :
        status === "running"   ? "rgba(88,166,255,.15)" :
        "rgba(139,148,158,.12)";
    $jobStatus.style.color =
        status === "completed" ? "var(--green)" :
        status === "failed"    ? "var(--red)" :
        status === "running"   ? "var(--accent)" :
        "var(--text-muted)";
}

function showSection(el) { el.classList.remove("hidden"); }
function hideSection(el) { el.classList.add("hidden"); }

function showError(msg) {
    $errorMsg.textContent = msg;
    showSection($errorSection);
    stopPolling();
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// ── Init ────────────────────────────────────────────────
checkApiHealth();
setInterval(checkApiHealth, 15000);
