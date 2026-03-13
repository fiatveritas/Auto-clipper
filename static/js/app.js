// State
let currentJobId = null;
let currentClips = [];
let previewClipData = null;

// Socket.IO connection
const socket = io();

socket.on("job_update", (data) => {
    if (data.job_id !== currentJobId) return;
    updateProgress(data.status, data.progress, data.message);

    if (data.status === "complete") {
        fetchClips(data.job_id);
    } else if (data.status === "error") {
        showError(data.message);
        resetUI();
    }
});

// Start analysis
function startAnalysis() {
    const urlInput = document.getElementById("vod-url");
    const url = urlInput.value.trim();

    if (!url) {
        showError("Please paste a Twitch VOD link");
        return;
    }

    if (!url.includes("twitch.tv")) {
        showError("That doesn't look like a Twitch URL. Please use a link like https://www.twitch.tv/videos/...");
        return;
    }

    hideError();
    setAnalyzing(true);
    showProgress();

    fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
    })
    .then((res) => res.json())
    .then((data) => {
        if (data.error) {
            showError(data.error);
            resetUI();
            return;
        }
        currentJobId = data.job_id;
    })
    .catch((err) => {
        showError("Failed to start analysis. Please try again.");
        resetUI();
    });
}

// Allow Enter key to submit
document.getElementById("vod-url").addEventListener("keydown", (e) => {
    if (e.key === "Enter") startAnalysis();
});

// Progress updates
function showProgress() {
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("clips-section").classList.add("hidden");
}

function updateProgress(status, progress, message) {
    const bar = document.getElementById("progress-bar");
    const pct = document.getElementById("progress-pct");
    const title = document.getElementById("progress-title");
    const msg = document.getElementById("progress-message");

    bar.style.width = progress + "%";
    pct.textContent = progress + "%";
    msg.textContent = message || "";

    const titles = {
        queued: "Queued...",
        downloading: "Downloading VOD",
        analyzing: "Analyzing Gameplay",
        clipping: "Extracting Clips",
        complete: "Complete!",
        error: "Error",
    };
    title.textContent = titles[status] || "Processing...";
}

// Fetch and display clips
function fetchClips(jobId) {
    fetch(`/api/clips/${jobId}`)
        .then((res) => res.json())
        .then((data) => {
            currentClips = data.clips || [];
            renderClips();
            setAnalyzing(false);
        })
        .catch(() => {
            showError("Failed to load clips");
            resetUI();
        });
}

function renderClips() {
    const grid = document.getElementById("clips-grid");
    const section = document.getElementById("clips-section");
    const noClips = document.getElementById("no-clips");
    const count = document.getElementById("clip-count");

    section.classList.remove("hidden");
    count.textContent = currentClips.length + " clip" + (currentClips.length !== 1 ? "s" : "");

    if (currentClips.length === 0) {
        grid.classList.add("hidden");
        noClips.classList.remove("hidden");
        return;
    }

    grid.classList.remove("hidden");
    noClips.classList.add("hidden");

    grid.innerHTML = currentClips.map((clip, i) => `
        <div class="clip-card" data-index="${i}">
            <div class="clip-thumb" onclick="previewClip(${i})">
                ${clip.thumbnail
                    ? `<img src="/static/thumbnails/${clip.thumbnail}" alt="${clip.label}">`
                    : `<div style="width:100%;height:100%;background:#1a1a2e;display:flex;align-items:center;justify-content:center;color:#666">No Preview</div>`
                }
                <div class="play-overlay"><span>&#9654;</span></div>
            </div>
            <div class="clip-info">
                <div class="clip-label">${escapeHtml(clip.label)}</div>
                <div class="clip-meta">
                    <span>${clip.timestamp_display} &middot; ${clip.duration}s</span>
                    <div class="confidence-bar">
                        <div class="confidence-bar-fill" style="width: ${clip.confidence * 100}%"></div>
                    </div>
                </div>
            </div>
            <div class="clip-actions">
                <button class="btn-download" onclick="event.stopPropagation(); downloadClip('${clip.id}', '${clip.filename}')">Download</button>
                <button class="btn-delete" onclick="event.stopPropagation(); deleteClip('${clip.id}', ${i})">Remove</button>
            </div>
        </div>
    `).join("");
}

// Preview modal
function previewClip(index) {
    const clip = currentClips[index];
    if (!clip) return;

    previewClipData = clip;
    const modal = document.getElementById("preview-modal");
    const video = document.getElementById("preview-video");

    video.src = `/static/clips/${clip.filename}`;
    document.getElementById("modal-label").textContent = clip.label;
    document.getElementById("modal-time").textContent = `${clip.timestamp_display} - Duration: ${clip.duration}s`;

    modal.classList.remove("hidden");
    video.play().catch(() => {});
}

function closePreview() {
    const modal = document.getElementById("preview-modal");
    const video = document.getElementById("preview-video");
    video.pause();
    video.src = "";
    modal.classList.add("hidden");
    previewClipData = null;
}

function closeModal(event) {
    if (event.target === event.currentTarget) {
        closePreview();
    }
}

function downloadFromModal() {
    if (previewClipData) {
        downloadClip(previewClipData.id, previewClipData.filename);
    }
}

// Clip actions
function downloadClip(clipId, filename) {
    const a = document.createElement("a");
    a.href = `/api/clips/${currentJobId}/${clipId}/download`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function deleteClip(clipId, index) {
    if (!confirm("Remove this clip?")) return;

    fetch(`/api/clips/${currentJobId}/${clipId}/delete`, { method: "POST" })
        .then((res) => res.json())
        .then((data) => {
            if (data.success) {
                currentClips.splice(index, 1);
                renderClips();
            }
        });
}

// UI helpers
function setAnalyzing(analyzing) {
    const btn = document.getElementById("analyze-btn");
    const input = document.getElementById("vod-url");

    btn.disabled = analyzing;
    input.disabled = analyzing;

    if (analyzing) {
        btn.innerHTML = '<span class="spinner"></span> Analyzing';
    } else {
        btn.innerHTML = '<span class="btn-text">Analyze</span><span class="btn-icon">&#9654;</span>';
    }
}

function showError(msg) {
    const el = document.getElementById("error-msg");
    el.textContent = msg;
    el.classList.remove("hidden");
}

function hideError() {
    document.getElementById("error-msg").classList.add("hidden");
}

function resetUI() {
    setAnalyzing(false);
    document.getElementById("progress-section").classList.add("hidden");
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// Keyboard shortcut: Escape to close modal
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePreview();
});
