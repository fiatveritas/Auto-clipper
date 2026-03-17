// ===== Persistent State =====
// Everything saves to localStorage so closing the tab doesn't lose your settings.

const STORAGE_KEY = "autoclipper_state";

function loadState() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch { return {}; }
}

function saveState() {
    const triggerWordsEl = document.getElementById("trigger-words-input");
    const state = {
        selectedGame: selectedGame,
        apiKey: document.getElementById("api-key").value.trim(),
        vodUrl: document.getElementById("vod-url").value.trim(),
        timeStart: document.getElementById("time-start").value.trim(),
        timeEnd: document.getElementById("time-end").value.trim(),
        timeRangeOpen: !document.getElementById("time-range-wrapper").classList.contains("hidden"),
        detectionMethod: document.getElementById("detection-method").value,
        sensitivity: document.getElementById("sensitivity").value,
        source: currentSource,
        currentJobId: currentJobId,
        detectionSettings: saveDetectionSettings(),
        triggerWords: triggerWordsEl ? triggerWordsEl.value : "",
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

// Save whenever the user changes anything
function hookAutoSave() {
    ["vod-url", "api-key", "time-start", "time-end"].forEach(id => {
        document.getElementById(id).addEventListener("input", saveState);
    });
    // Save on tab close / navigate away
    window.addEventListener("beforeunload", saveState);
    // Save periodically as backup
    setInterval(saveState, 5000);
}

function restoreState() {
    const state = loadState();
    if (!state || !Object.keys(state).length) return;

    if (state.selectedGame) {
        selectedGame = state.selectedGame;
    }
    if (state.apiKey) {
        document.getElementById("api-key").value = state.apiKey;
    }
    if (state.vodUrl) {
        document.getElementById("vod-url").value = state.vodUrl;
    }
    if (state.timeStart) {
        document.getElementById("time-start").value = state.timeStart;
    }
    if (state.timeEnd) {
        document.getElementById("time-end").value = state.timeEnd;
    }
    if (state.timeRangeOpen) {
        document.getElementById("time-range-wrapper").classList.remove("hidden");
        document.getElementById("time-toggle-icon").textContent = "-";
    }
    if (state.detectionMethod) {
        document.getElementById("detection-method").value = state.detectionMethod;
        onDetectionMethodChange(state.detectionMethod);
    }
    if (state.sensitivity) {
        document.getElementById("sensitivity").value = state.sensitivity;
        onSensitivityChange(state.sensitivity);
    }
    if (state.source) {
        setSource(state.source);
    }
    if (state.detectionSettings) {
        restoreDetectionSettings(state.detectionSettings);
    }
    if (state.triggerWords) {
        const el = document.getElementById("trigger-words-input");
        if (el) el.value = state.triggerWords;
    }
    if (state.currentJobId) {
        currentJobId = state.currentJobId;
        fetchClips(currentJobId);
    }
}

// ===== Main Tab Navigation =====
function switchMainTab(tabName) {
    // Support both old .nav-tab and new .nav-item sidebar buttons
    document.querySelectorAll(".nav-tab, .nav-item").forEach(t => t.classList.toggle("active", t.dataset.tab === tabName));
    document.querySelectorAll(".main-tab-content").forEach(t => t.classList.remove("active"));
    const target = document.getElementById(`tab-${tabName}-main`);
    if (target) target.classList.add("active");
    // Close sidebar on mobile after selection
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("visible");
}

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.toggle("open");
    if (overlay) overlay.classList.toggle("visible");
}

function filterGameCards(query) {
    const q = (query || "").toLowerCase().trim();
    document.querySelectorAll(".game-card").forEach(card => {
        const name = (card.querySelector(".game-card-name")?.textContent || "").toLowerCase();
        const desc = (card.querySelector(".game-card-desc")?.textContent || "").toLowerCase();
        card.style.display = (!q || name.includes(q) || desc.includes(q)) ? "" : "none";
    });
}

// ===== Game Selection =====
let selectedGame = "arc_raiders";
let availableGames = [];

function loadGames() {
    fetch("/api/games")
        .then(res => res.json())
        .then(data => {
            availableGames = data.games || [];
            renderGameOptions();
            renderGameCards();
            updateGameActiveDisplay();
        })
        .catch(() => {
            availableGames = [
                { id: "arc_raiders", name: "Arc Raiders", description: "Sci-fi co-op shooter" },
                { id: "war_thunder", name: "War Thunder", description: "Military vehicles" },
            ];
            renderGameOptions();
            renderGameCards();
            updateGameActiveDisplay();
        });
}

function renderGameOptions() {
    const select = document.getElementById("game-select");
    select.innerHTML = availableGames.map(game => `
        <option value="${game.id}" ${game.id === selectedGame ? 'selected' : ''}>
            ${escapeHtml(game.name)} — ${escapeHtml(game.description)}
        </option>
    `).join("");
}

function getGameTag(game) {
    const id = game.id.toLowerCase();
    const desc = (game.description || "").toLowerCase();
    if (desc.includes("recommended") || id === "arc_raiders") return { label: "Recommended", cls: "recommended" };
    if (desc.includes("aggressive") || desc.includes("wide-net")) return { label: "Aggressive", cls: "aggressive" };
    if (desc.includes("audio")) return { label: "Audio-Heavy", cls: "audio" };
    if (desc.includes("motion")) return { label: "Motion-Based", cls: "motion" };
    if (desc.includes("precision") || desc.includes("conservative")) return { label: "Precision", cls: "precision" };
    if (desc.includes("pvpve") || id.includes("v7")) return { label: "PvPvE", cls: "pvpve" };
    return null;
}

function renderGameCards() {
    const container = document.getElementById("game-cards-container");
    if (!container) return;
    container.innerHTML = availableGames.map(game => {
        const tag = getGameTag(game);
        const tagHtml = tag ? `<span class="game-card-tag ${tag.cls}">${tag.label}</span>` : '';
        return `
            <div class="game-card ${game.id === selectedGame ? 'selected' : ''}"
                 data-game-id="${game.id}"
                 onclick="selectGameCard('${game.id}')">
                <div class="game-card-name">${escapeHtml(game.name)}</div>
                <div class="game-card-desc">${escapeHtml(game.description)}</div>
                ${tagHtml}
            </div>
        `;
    }).join("");
}

function updateGameActiveDisplay() {
    const game = availableGames.find(g => g.id === selectedGame) || { name: selectedGame, description: "" };
    const nameEl = document.getElementById("game-active-name");
    const descEl = document.getElementById("game-active-desc");
    if (nameEl) nameEl.textContent = game.name;
    if (descEl) descEl.textContent = game.description;
}

function selectGameCard(gameId) {
    selectedGame = gameId;
    const select = document.getElementById("game-select");
    if (select.value !== gameId) select.value = gameId;
    renderGameCards();
    updateGameActiveDisplay();
    // Auto-collapse after selection
    document.getElementById("game-cards-container").classList.add("hidden");
    document.getElementById("game-cards-toggle").textContent = "Show all";
    saveState();
}

function toggleGameCards() {
    const container = document.getElementById("game-cards-container");
    const btn = document.getElementById("game-cards-toggle");
    const isHidden = container.classList.toggle("hidden");
    btn.textContent = isHidden ? "Show all" : "Hide";
}

function selectGame(gameId) {
    selectedGame = gameId;
    const select = document.getElementById("game-select");
    if (select.value !== gameId) select.value = gameId;
    renderGameCards();
    updateGameActiveDisplay();
    saveState();
}

// ===== Source Toggle (URL vs Upload) =====
let currentSource = "url";
let selectedFile = null;

function setSource(source) {
    currentSource = source;
    document.querySelectorAll(".source-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.source === source);
    });
    document.getElementById("url-mode").classList.toggle("hidden", source !== "url");
    document.getElementById("upload-mode").classList.toggle("hidden", source !== "upload");
    hideError();
    saveState();
}

// ===== File Upload =====
function initUpload() {
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
    dropZone.addEventListener("dragleave", () => { dropZone.classList.remove("drag-over"); });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        if (e.dataTransfer.files.length > 0) handleFileSelect(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) handleFileSelect(fileInput.files[0]);
    });
}

function handleFileSelect(file) {
    const allowedExt = [".mp4", ".mkv", ".mov", ".avi", ".flv", ".ts", ".webm"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowedExt.includes(ext)) {
        showError("Unsupported file type. Use: " + allowedExt.join(", "));
        return;
    }
    selectedFile = file;
    document.getElementById("file-name").textContent = file.name;
    document.getElementById("file-size").textContent = formatFileSize(file.size);
    document.getElementById("file-info").classList.remove("hidden");
    document.getElementById("upload-btn").classList.remove("hidden");
    document.getElementById("drop-zone").classList.add("hidden");
    hideError();
}

function clearFile() {
    selectedFile = null;
    document.getElementById("file-input").value = "";
    document.getElementById("file-info").classList.add("hidden");
    document.getElementById("upload-btn").classList.add("hidden");
    document.getElementById("drop-zone").classList.remove("hidden");
}

function startUploadAnalysis() {
    if (!selectedFile) { showError("Please select a file first"); return; }
    hideError();
    setUploading(true);
    showProgress();
    saveState();

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("api_key", document.getElementById("api-key").value.trim());
    formData.append("time_start", document.getElementById("time-start").value.trim());
    formData.append("time_end", document.getElementById("time-end").value.trim());
    formData.append("game", selectedGame);
    formData.append("detection_method", document.getElementById("detection-method").value);
    formData.append("sensitivity", document.getElementById("sensitivity").value);
    formData.append("detection_overrides", JSON.stringify(getDetectionOverrides()));

    const xhr = new XMLHttpRequest();
    xhr.timeout = 0;  // No timeout for large file uploads
    xhr.open("POST", "/api/upload");
    xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 40);
            updateProgress("uploading", pct, `Uploading... ${Math.round(e.loaded / e.total * 100)}%`);
        }
    });
    xhr.addEventListener("load", () => {
        if (xhr.status === 200) {
            const data = JSON.parse(xhr.responseText);
            if (data.error) { showError(data.error); resetUI(); return; }
            currentJobId = data.job_id;
            startPolling();
        } else {
            try { showError(JSON.parse(xhr.responseText).error || "Upload failed (status " + xhr.status + ")"); }
            catch { showError("Upload failed (status " + xhr.status + "). Check that the server is running and the file is a valid video."); }
            resetUI();
        }
    });
    xhr.addEventListener("error", () => { showError("Upload failed."); resetUI(); });
    xhr.send(formData);
}

function setUploading(uploading) {
    const btn = document.getElementById("upload-btn");
    btn.disabled = uploading;
    btn.innerHTML = uploading
        ? '<span class="spinner"></span> Uploading'
        : '<span class="btn-text">Upload &amp; Analyze</span><span class="btn-icon">&#9654;</span>';
}

// ===== App State =====
let currentJobId = null;
let currentClips = [];
let previewClipData = null;
let previewClipIndex = -1;
let pollTimer = null;
let pollFailures = 0;
let vodDuration = 0;

// ===== Init =====
window.addEventListener("DOMContentLoaded", () => {
    waitForBackend();
});

function waitForBackend() {
    fetch("/api/games")
        .then(res => {
            if (!res.ok) throw new Error("not ready");
            return res.json();
        })
        .then(() => {
            // Backend is ready — show the app
            const overlay = document.getElementById("loading-overlay");
            const app = document.getElementById("app-container");
            overlay.classList.add("fade-out");
            app.classList.remove("hidden");
            setTimeout(() => overlay.remove(), 500);

            // Now initialize everything
            restoreState();
            loadGames();
            hookAutoSave();
            loadLibrary();
            loadSessions();
            initUpload();
        })
        .catch(() => {
            // Not ready yet, retry in 1 second
            setTimeout(waitForBackend, 1000);
        });
}

// ===== VOD Library =====
function loadLibrary() {
    fetch("/api/library")
        .then(res => res.json())
        .then(data => {
            const vods = data.vods || [];
            const list = document.getElementById("library-list");
            const count = document.getElementById("library-count");
            const empty = document.getElementById("library-empty");

            count.textContent = vods.length;

            if (vods.length === 0) {
                list.innerHTML = "";
                if (empty) empty.classList.remove("hidden");
                return;
            }

            if (empty) empty.classList.add("hidden");

            list.innerHTML = vods.map(vod => `
                <div class="library-item">
                    <div class="library-item-info" onclick="analyzeFromLibrary('${escapeHtml(vod.filename)}')">
                        <span class="library-item-name">${escapeHtml(vod.filename)}</span>
                        <span class="library-item-meta">
                            ${formatFileSize(vod.size)}
                            ${vod.duration ? ' &middot; ' + formatTime(vod.duration) : ''}
                        </span>
                    </div>
                    <button class="library-item-clip" onclick="event.stopPropagation(); showManualClip('${escapeHtml(vod.filename)}')" title="Manual Clip">Clip</button>
                    <button class="library-item-delete" onclick="deleteLibraryVod('${escapeHtml(vod.filename)}')" title="Delete">&times;</button>
                </div>
            `).join("");
        })
        .catch(() => {});
}

function analyzeFromLibrary(filename) {
    hideError();
    setAnalyzing(true);
    showProgress();

    const apiKey = document.getElementById("api-key").value.trim();
    const timeStart = document.getElementById("time-start").value.trim();
    const timeEnd = document.getElementById("time-end").value.trim();

    fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            library_file: filename,
            api_key: apiKey,
            time_start: timeStart,
            time_end: timeEnd,
            game: selectedGame,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
            resetUI();
            return;
        }
        currentJobId = data.job_id;
        startPolling();
    })
    .catch(() => {
        showError("Failed to start analysis.");
        resetUI();
    });
}

function deleteLibraryVod(filename) {
    if (!confirm("Delete this saved VOD? This frees up storage.")) return;

    fetch(`/api/library/${encodeURIComponent(filename)}/delete`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            if (data.success) loadLibrary();
        });
}

// ===== Saved Sessions =====
function loadSessions() {
    fetch("/api/sessions")
        .then(res => res.json())
        .then(data => {
            const sessions = data.sessions || [];
            const list = document.getElementById("sessions-list");
            const count = document.getElementById("sessions-count");
            const empty = document.getElementById("sessions-empty");

            count.textContent = sessions.length;

            if (sessions.length === 0) {
                list.innerHTML = "";
                if (empty) empty.classList.remove("hidden");
                return;
            }

            if (empty) empty.classList.add("hidden");

            list.innerHTML = sessions.map(s => `
                <div class="library-item">
                    <div class="library-item-info" onclick="loadSession('${escapeHtml(s.job_id)}')">
                        <span class="library-item-name">${s.clip_count} clip${s.clip_count !== 1 ? 's' : ''}</span>
                        <span class="library-item-meta">
                            ${escapeHtml(s.url || 'Unknown source')}
                            ${s.created_at ? ' &middot; ' + new Date(s.created_at).toLocaleDateString() : ''}
                            ${s.vod_available ? '' : ' &middot; <em>VOD removed</em>'}
                        </span>
                    </div>
                    <button class="library-item-delete" onclick="deleteSession('${escapeHtml(s.job_id)}')" title="Delete">&times;</button>
                </div>
            `).join("");
        })
        .catch(() => {});
}

function loadSession(jobId) {
    currentJobId = jobId;
    saveState();
    fetchClips(jobId);
}

function deleteSession(jobId) {
    if (!confirm("Delete this saved session?")) return;
    fetch(`/api/sessions/${encodeURIComponent(jobId)}/delete`, { method: "POST" })
        .then(res => res.json())
        .then(data => {
            if (data.success) loadSessions();
        });
}

function formatFileSize(bytes) {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}

// Start analysis
function startAnalysis() {
    const url = document.getElementById("vod-url").value.trim();
    const apiKey = document.getElementById("api-key").value.trim();

    if (!url) {
        showError("Please paste a Twitch or YouTube VOD link");
        return;
    }

    if (!url.includes("twitch.tv") && !url.includes("youtube.com") && !url.includes("youtu.be")) {
        showError("That doesn't look like a Twitch or YouTube URL");
        return;
    }

    hideError();
    setAnalyzing(true);
    showProgress();
    saveState();

    const timeStart = document.getElementById("time-start").value.trim();
    const timeEnd = document.getElementById("time-end").value.trim();

    const detectionMethod = document.getElementById("detection-method").value;
    const sensitivity = parseInt(document.getElementById("sensitivity").value);

    fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            url,
            api_key: apiKey,
            time_start: timeStart,
            time_end: timeEnd,
            game: selectedGame,
            detection_method: detectionMethod,
            sensitivity: sensitivity,
            detection_overrides: getDetectionOverrides(),
        }),
    })
    .then((res) => res.json())
    .then((data) => {
        if (data.error) {
            showError(data.error);
            resetUI();
            return;
        }
        currentJobId = data.job_id;
        startPolling();
    })
    .catch(() => {
        showError("Failed to start analysis. Please try again.");
        resetUI();
    });
}

document.getElementById("vod-url").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        if (e.shiftKey) {
            // Shift+Enter adds to batch queue
            addToBatchQueue();
        } else {
            startAnalysis();
        }
    }
});

// Polling
function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollFailures = 0;
    pollTimer = setInterval(pollJob, 1500);
}

function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

function pollJob() {
    if (!currentJobId) return;

    fetch(`/api/jobs/${currentJobId}`)
        .then((res) => {
            if (!res.ok) {
                throw new Error(`Job not found (${res.status})`);
            }
            return res.json();
        })
        .then((data) => {
            pollFailures = 0;

            if (data.error && !data.status) {
                showError(data.error);
                resetUI();
                stopPolling();
                return;
            }

            updateProgress(data.status, data.progress, data.message);

            if (data.status === "complete") {
                stopPolling();
                showNotification("Analysis complete! Your clips are ready.");
                fetchClips(currentJobId);
            } else if (data.status === "error") {
                stopPolling();
                showError(data.message || data.error || "An error occurred");
                resetUI();
            }
        })
        .catch((err) => {
            pollFailures = (pollFailures || 0) + 1;
            if (pollFailures >= 5) {
                stopPolling();
                showError("Lost connection to the analysis job. Please try again.");
                resetUI();
            }
        });
}

// Progress
function showProgress() {
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("clips-section").classList.add("hidden");
}

function updateProgress(status, progress, message) {
    document.getElementById("progress-bar").style.width = progress + "%";
    document.getElementById("progress-pct").textContent = progress + "%";
    document.getElementById("progress-message").textContent = message || "";

    const titles = {
        queued: "Queued...",
        uploading: "Uploading VOD",
        downloading: "Downloading VOD",
        analyzing: "Analyzing Gameplay",
        clipping: "Extracting Clips",
        complete: "Complete!",
        error: "Error",
    };
    document.getElementById("progress-title").textContent = titles[status] || "Processing...";
}

// Clips
function fetchClips(jobId) {
    fetch(`/api/clips/${jobId}`)
        .then((res) => res.json())
        .then((data) => {
            currentClips = data.clips || [];
            vodDuration = data.vod_duration || 0;
            renderClips();
            setAnalyzing(false);
            loadLibrary(); // Refresh — new VOD may have been saved
            loadSessions(); // Refresh — new session saved
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
                    ? `<img src="/static/thumbnails/${clip.thumbnail}?t=${Date.now()}" alt="${escapeHtml(clip.label)}">`
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
            ${renderStars(clip.id, clip.rating)}
            <div class="clip-actions">
                <button class="btn-download" onclick="event.stopPropagation(); downloadClip('${clip.id}', '${clip.filename}')">Download</button>
                <button class="btn-trim" onclick="event.stopPropagation(); previewClip(${i})">Trim</button>
                <button class="btn-delete" onclick="event.stopPropagation(); deleteClip('${clip.id}', ${i})">Remove</button>
            </div>
        </div>
    `).join("");
}

// ===== Editor Tabs =====
function switchEditorTab(tabName) {
    document.querySelectorAll(".editor-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".editor-tab-content").forEach(t => t.classList.remove("active"));
    document.querySelector(`.editor-tab[data-tab="${tabName}"]`).classList.add("active");
    document.getElementById(`tab-${tabName}`).classList.add("active");

    // Initialize crop canvas when switching to crop tab
    if (tabName === "crop") initCropCanvas();
}

// ===== Preview + Trim =====
function previewClip(index) {
    const clip = currentClips[index];
    if (!clip) return;

    previewClipData = clip;
    previewClipIndex = index;
    const modal = document.getElementById("preview-modal");
    const video = document.getElementById("preview-video");

    video.src = `/static/clips/${clip.filename}?t=${Date.now()}`;
    document.getElementById("modal-label").textContent = clip.label;
    document.getElementById("modal-time").textContent = `${clip.timestamp_display} - Duration: ${clip.duration}s`;

    // Set up trim controls
    const startInput = document.getElementById("trim-start");
    const endInput = document.getElementById("trim-end");
    const maxTime = vodDuration || clip.end_time + 120;

    startInput.value = clip.start_time;
    endInput.value = clip.end_time;
    startInput.max = maxTime;
    endInput.max = maxTime;

    document.getElementById("trim-duration-display").textContent = clip.duration + "s";

    document.getElementById("trim-status").textContent = "";
    document.getElementById("trim-status").className = "trim-status";

    // Reset to trim tab
    switchEditorTab("trim");

    // Reset effects
    resetEffects();

    // Reset crop
    cropRegion = null;
    cropPreset = "original";

    // Initialize timeline
    initTimeline();

    modal.classList.remove("hidden");
    video.play().catch(() => {});
}

// ===== Timeline Scrubber =====
let timelineDragging = null; // "start", "end", or null

function initTimeline() {
    if (!previewClipData) return;
    const maxTime = vodDuration || previewClipData.end_time + 60;

    document.getElementById("timeline-start-label").textContent = formatTime(0);
    document.getElementById("timeline-end-label").textContent = formatTime(maxTime);

    updateTimelineUI();
    initTimelineClickToClip();
}

function updateTimelineUI() {
    if (!previewClipData) return;
    const maxTime = vodDuration || previewClipData.end_time + 60;
    const start = parseFloat(document.getElementById("trim-start").value) || 0;
    const end = parseFloat(document.getElementById("trim-end").value) || 0;

    const track = document.getElementById("timeline-track");
    const range = document.getElementById("timeline-range");
    const handleStart = document.getElementById("timeline-handle-start");
    const handleEnd = document.getElementById("timeline-handle-end");

    const startPct = (start / maxTime) * 100;
    const endPct = (end / maxTime) * 100;

    range.style.left = startPct + "%";
    range.style.width = (endPct - startPct) + "%";
    handleStart.style.left = `calc(${startPct}% - 6px)`;
    handleEnd.style.left = `calc(${endPct}% - 6px)`;

    document.getElementById("timeline-range-display").textContent =
        `${formatTime(start)} - ${formatTime(end)}`;
    document.getElementById("timeline-duration-display").textContent =
        Math.max(0, end - start).toFixed(1) + "s";
    document.getElementById("trim-duration-display").textContent =
        Math.max(0, end - start).toFixed(1) + "s";
}

function onTrimInputChange() {
    updateTimelineUI();
}

function adjustTrim(field, delta) {
    const input = document.getElementById(`trim-${field}`);
    let val = parseFloat(input.value) + delta;
    val = Math.max(0, val);
    if (vodDuration > 0) val = Math.min(vodDuration, val);
    input.value = val.toFixed(1);
    onTrimInputChange();
}

// Timeline drag handlers
(function() {
    function getTimeFromX(e, track) {
        const rect = track.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const pct = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        const maxTime = vodDuration || (previewClipData ? previewClipData.end_time + 60 : 300);
        return pct * maxTime;
    }

    function onDown(e) {
        const target = e.target;
        if (target.id === "timeline-handle-start") {
            timelineDragging = "start";
            target.classList.add("dragging");
        } else if (target.id === "timeline-handle-end") {
            timelineDragging = "end";
            target.classList.add("dragging");
        }
        if (timelineDragging) e.preventDefault();
    }

    function onMove(e) {
        if (!timelineDragging) return;
        e.preventDefault();
        const track = document.getElementById("timeline-track");
        const t = getTimeFromX(e, track);
        const input = document.getElementById(`trim-${timelineDragging}`);
        input.value = t.toFixed(1);
        onTrimInputChange();
    }

    function onUp() {
        if (timelineDragging) {
            document.querySelectorAll(".timeline-handle").forEach(h => h.classList.remove("dragging"));
            timelineDragging = null;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const track = document.getElementById("timeline-track");
        track.addEventListener("mousedown", onDown);
        track.addEventListener("touchstart", onDown, { passive: false });
        document.addEventListener("mousemove", onMove);
        document.addEventListener("touchmove", onMove, { passive: false });
        document.addEventListener("mouseup", onUp);
        document.addEventListener("touchend", onUp);

        // Click on track to jump
        track.addEventListener("click", (e) => {
            if (e.target.classList.contains("timeline-handle")) return;
            const t = getTimeFromX(e, track);
            // Move whichever handle is closer
            const start = parseFloat(document.getElementById("trim-start").value);
            const end = parseFloat(document.getElementById("trim-end").value);
            if (Math.abs(t - start) < Math.abs(t - end)) {
                document.getElementById("trim-start").value = t.toFixed(1);
            } else {
                document.getElementById("trim-end").value = t.toFixed(1);
            }
            onTrimInputChange();
        });
    });
})();

function applyTrim() {
    if (!previewClipData || !currentJobId) return;

    const start = parseFloat(document.getElementById("trim-start").value);
    const end = parseFloat(document.getElementById("trim-end").value);

    if (end <= start) {
        document.getElementById("trim-status").textContent = "End must be after start";
        document.getElementById("trim-status").className = "trim-status error";
        return;
    }

    if (end - start > 300) {
        document.getElementById("trim-status").textContent = "Max clip length is 5 minutes";
        document.getElementById("trim-status").className = "trim-status error";
        return;
    }

    const statusEl = document.getElementById("trim-status");
    statusEl.textContent = "Re-cutting clip...";
    statusEl.className = "trim-status working";

    const trimBtn = document.getElementById("trim-apply-btn");
    trimBtn.disabled = true;

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/trim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start, end }),
    })
    .then((res) => res.json())
    .then((data) => {
        trimBtn.disabled = false;

        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }

        if (data.success && data.clip) {
            currentClips[previewClipIndex] = data.clip;
            previewClipData = data.clip;

            const video = document.getElementById("preview-video");
            video.src = `/static/clips/${data.clip.filename}?t=${Date.now()}`;
            video.play().catch(() => {});

            document.getElementById("modal-time").textContent =
                `${data.clip.timestamp_display} - Duration: ${data.clip.duration}s`;

            statusEl.textContent = "Clip updated!";
            statusEl.className = "trim-status success";

            renderClips();
        }
    })
    .catch(() => {
        trimBtn.disabled = false;
        statusEl.textContent = "Failed to trim clip";
        statusEl.className = "trim-status error";
    });
}

// ===== Crop Tool =====
let cropRegion = null; // {x, y, w, h} as 0-1 ratios
let cropPreset = "original";
let cropFrame = null;
let cropDragging = false;
let cropDragStart = null;

function initCropCanvas() {
    const video = document.getElementById("preview-video");
    const canvas = document.getElementById("crop-canvas");
    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 360;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    cropFrame = ctx.getImageData(0, 0, canvas.width, canvas.height);

    if (!cropRegion) {
        cropRegion = { x: 0, y: 0, w: 1, h: 1 };
    }

    drawCropOverlay();
    updateCropSizeDisplay();
}

function setCropPreset(preset) {
    cropPreset = preset;
    document.querySelectorAll("#tab-crop .preset-btn").forEach(b => b.classList.remove("active"));
    if (event && event.target) event.target.classList.add("active");

    const canvas = document.getElementById("crop-canvas");
    const aspect = canvas.width / canvas.height;

    if (preset === "original") {
        cropRegion = { x: 0, y: 0, w: 1, h: 1 };
    } else if (preset === "custom") {
        cropRegion = { x: 0.05, y: 0.05, w: 0.9, h: 0.9 };
    } else {
        // Parse target ratio
        const [rw, rh] = preset.split(":").map(Number);
        const targetAspect = rw / rh;

        if (targetAspect > aspect) {
            // Wider than source - fit width, crop height
            const cropH = aspect / targetAspect;
            cropRegion = { x: 0, y: (1 - cropH) / 2, w: 1, h: cropH };
        } else {
            // Taller than source - fit height, crop width
            const cropW = targetAspect / aspect;
            cropRegion = { x: (1 - cropW) / 2, y: 0, w: cropW, h: 1 };
        }
    }

    drawCropOverlay();
    updateCropSizeDisplay();
}

function drawCropOverlay() {
    const canvas = document.getElementById("crop-canvas");
    const ctx = canvas.getContext("2d");

    if (cropFrame) ctx.putImageData(cropFrame, 0, 0);

    if (!cropRegion) return;

    const w = canvas.width, h = canvas.height;
    const rx = cropRegion.x * w, ry = cropRegion.y * h;
    const rw = cropRegion.w * w, rh = cropRegion.h * h;

    // Darken outside crop
    ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
    // Top
    ctx.fillRect(0, 0, w, ry);
    // Bottom
    ctx.fillRect(0, ry + rh, w, h - (ry + rh));
    // Left
    ctx.fillRect(0, ry, rx, rh);
    // Right
    ctx.fillRect(rx + rw, ry, w - (rx + rw), rh);

    // Crop border
    ctx.strokeStyle = var_accent;
    ctx.lineWidth = 2;
    ctx.strokeRect(rx, ry, rw, rh);

    // Rule of thirds grid
    ctx.strokeStyle = "rgba(255, 255, 255, 0.2)";
    ctx.lineWidth = 1;
    for (let i = 1; i <= 2; i++) {
        ctx.beginPath();
        ctx.moveTo(rx + (rw * i / 3), ry);
        ctx.lineTo(rx + (rw * i / 3), ry + rh);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(rx, ry + (rh * i / 3));
        ctx.lineTo(rx + rw, ry + (rh * i / 3));
        ctx.stroke();
    }

    // Corner handles
    ctx.fillStyle = var_accent;
    const hs = 8;
    [[rx, ry], [rx + rw, ry], [rx, ry + rh], [rx + rw, ry + rh]].forEach(([cx, cy]) => {
        ctx.fillRect(cx - hs/2, cy - hs/2, hs, hs);
    });
}

const var_accent = "#9147ff";

function updateCropSizeDisplay() {
    if (!cropRegion) return;
    const canvas = document.getElementById("crop-canvas");
    const pw = Math.round(cropRegion.w * canvas.width);
    const ph = Math.round(cropRegion.h * canvas.height);
    document.getElementById("crop-size-display").textContent = `${pw} x ${ph}px`;
}

// Crop canvas drag to reposition
(function() {
    let dragging = false;
    let dragOffsetX, dragOffsetY;

    function getPos(e, canvas) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
            x: (clientX - rect.left) * scaleX / canvas.width,
            y: (clientY - rect.top) * scaleY / canvas.height
        };
    }

    function onStart(e) {
        if (!cropRegion || cropPreset === "original") return;
        const canvas = document.getElementById("crop-canvas");
        const pos = getPos(e, canvas);

        // Check if click is inside crop region
        if (pos.x >= cropRegion.x && pos.x <= cropRegion.x + cropRegion.w &&
            pos.y >= cropRegion.y && pos.y <= cropRegion.y + cropRegion.h) {
            dragging = true;
            dragOffsetX = pos.x - cropRegion.x;
            dragOffsetY = pos.y - cropRegion.y;
            e.preventDefault();
        }
    }

    function onMove(e) {
        if (!dragging || !cropRegion) return;
        e.preventDefault();
        const canvas = document.getElementById("crop-canvas");
        const pos = getPos(e, canvas);

        let nx = pos.x - dragOffsetX;
        let ny = pos.y - dragOffsetY;
        nx = Math.max(0, Math.min(1 - cropRegion.w, nx));
        ny = Math.max(0, Math.min(1 - cropRegion.h, ny));

        cropRegion.x = nx;
        cropRegion.y = ny;

        drawCropOverlay();
    }

    function onEnd() { dragging = false; }

    document.addEventListener("DOMContentLoaded", () => {
        const canvas = document.getElementById("crop-canvas");
        canvas.addEventListener("mousedown", onStart);
        canvas.addEventListener("touchstart", onStart, { passive: false });
        document.addEventListener("mousemove", onMove);
        document.addEventListener("touchmove", onMove, { passive: false });
        document.addEventListener("mouseup", onEnd);
        document.addEventListener("touchend", onEnd);
    });
})();

function exportCrop() {
    if (!previewClipData || !currentJobId || !cropRegion) return;
    if (cropPreset === "original") {
        document.getElementById("crop-status").textContent = "No crop applied";
        document.getElementById("crop-status").className = "trim-status error";
        return;
    }

    const statusEl = document.getElementById("crop-status");
    const btn = document.getElementById("crop-export-btn");
    statusEl.textContent = "Exporting cropped clip...";
    statusEl.className = "trim-status working";
    btn.disabled = true;

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ crop: cropRegion }),
    })
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }
        statusEl.textContent = "Done! Downloading...";
        statusEl.className = "trim-status success";
        const a = document.createElement("a");
        a.href = `/static/clips/${data.filename}`;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    })
    .catch(() => {
        btn.disabled = false;
        statusEl.textContent = "Export failed";
        statusEl.className = "trim-status error";
    });
}

// ===== Effects =====
function onEffectChange() {
    const speed = parseFloat(document.getElementById("fx-speed").value);
    const brightness = parseFloat(document.getElementById("fx-brightness").value);
    const contrast = parseFloat(document.getElementById("fx-contrast").value);
    const volume = parseFloat(document.getElementById("fx-volume").value);

    document.getElementById("fx-speed-val").textContent = speed + "x";
    document.getElementById("fx-brightness-val").textContent = brightness.toFixed(2);
    document.getElementById("fx-contrast-val").textContent = contrast.toFixed(2);
    document.getElementById("fx-volume-val").textContent = Math.round(volume * 100) + "%";

    // Live CSS preview for brightness/contrast on video
    const video = document.getElementById("preview-video");
    video.style.filter = `brightness(${1 + brightness}) contrast(${contrast})`;
    video.playbackRate = Math.max(0.25, Math.min(4, speed));
}

function resetEffects() {
    document.getElementById("fx-speed").value = 1;
    document.getElementById("fx-brightness").value = 0;
    document.getElementById("fx-contrast").value = 1;
    document.getElementById("fx-volume").value = 1;
    onEffectChange();

    // Reset CSS preview
    const video = document.getElementById("preview-video");
    video.style.filter = "";
    video.playbackRate = 1;
}

function exportWithEffects() {
    if (!previewClipData || !currentJobId) return;

    const speed = parseFloat(document.getElementById("fx-speed").value);
    const brightness = parseFloat(document.getElementById("fx-brightness").value);
    const contrast = parseFloat(document.getElementById("fx-contrast").value);
    const volume = parseFloat(document.getElementById("fx-volume").value);

    if (speed === 1 && brightness === 0 && contrast === 1 && volume === 1) {
        document.getElementById("fx-status").textContent = "No effects applied";
        document.getElementById("fx-status").className = "trim-status error";
        return;
    }

    const statusEl = document.getElementById("fx-status");
    const btn = document.getElementById("fx-export-btn");
    statusEl.textContent = "Exporting with effects...";
    statusEl.className = "trim-status working";
    btn.disabled = true;

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ speed, brightness, contrast, volume }),
    })
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }
        statusEl.textContent = "Done! Downloading...";
        statusEl.className = "trim-status success";
        const a = document.createElement("a");
        a.href = `/static/clips/${data.filename}`;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    })
    .catch(() => {
        btn.disabled = false;
        statusEl.textContent = "Export failed";
        statusEl.className = "trim-status error";
    });
}

function closePreview() {
    const modal = document.getElementById("preview-modal");
    const video = document.getElementById("preview-video");
    video.pause();
    video.src = "";
    video.style.filter = "";
    video.playbackRate = 1;
    modal.classList.add("hidden");
    previewClipData = null;
    previewClipIndex = -1;
}

function closeModal(event) {
    if (event.target === event.currentTarget) closePreview();
}

function downloadFromModal() {
    if (previewClipData) downloadClip(previewClipData.id, previewClipData.filename);
}

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

// Toggles
function toggleTimeRange() {
    const wrapper = document.getElementById("time-range-wrapper");
    const icon = document.getElementById("time-toggle-icon");
    wrapper.classList.toggle("hidden");
    icon.textContent = wrapper.classList.contains("hidden") ? "+" : "-";
    saveState();
}

function onDetectionMethodChange(method) {
    const hints = {
        audio_cv: "Uses audio spikes (gunshots/explosions) combined with visual detection. Best for most games.",
        audio_only: "Detects loud moments only (gunfire, explosions). Fastest method, no video scanning needed.",
        cv_only: "Frame-by-frame color/motion analysis. Works without audio but less accurate for some games.",
        motion: "Detects high-movement periods (combat, camera shakes, explosions). Pure pixel motion analysis.",
        scene_change: "Finds visual disruptions — explosions, flashes, damage effects. Measures how fast the scene shifts.",
        hybrid: "Runs audio + motion + scene change together. Slowest but catches everything — if any signal fires, it counts.",
        clip_triggers: "Transcribes audio with Whisper to find when someone says 'clip that!', 'clip this!', or 'clip!' — auto-clips the preceding 30 seconds. Requires openai-whisper (pip install openai-whisper).",
        chat_spikes: "Uses Twitch chat activity spikes to find hype moments. Only works with Twitch VOD URLs.",
        ai_vision: "AI analyzes screenshots of your gameplay. Most accurate but requires xAI API key and costs per use.",
        roboflow_workflow: "Roboflow AI workflow for Arc Raiders — streams video through a detect-and-classify pipeline. Requires Roboflow API key.",
        roboflow_model: "Sends frames directly to your Roboflow model for object detection. Simpler setup — just needs a Roboflow API key.",
        yolo_local: "Runs a trained YOLO model (best.pt) on each frame. You MUST have a trained model file in the models/ folder. Without it, this will fail. Train your own model on Roboflow or use CV Pipeline instead.",
        arc_cv_pipeline: "Reads HUD elements (health bar, ammo, XP), detects VFX (muzzle flash, fire, explosions, damage vignette), and tracks frame-to-frame changes. No model file or API key needed — works offline out of the box. Best for Arc Raiders, decent for other shooters.",
    };
    document.getElementById("detection-hint").textContent = hints[method] || "";
    const apiSection = document.getElementById("api-key-section");
    if (method === "ai_vision" || method === "roboflow_workflow" || method === "roboflow_model") {
        apiSection.classList.remove("hidden");
    } else {
        apiSection.classList.add("hidden");
    }
    // Refresh sensitivity hint to show CV version names when applicable
    onSensitivityChange(document.getElementById("sensitivity").value);
    saveState();
}

// Helpers
function setAnalyzing(analyzing) {
    const btn = document.getElementById("analyze-btn");
    const input = document.getElementById("vod-url");
    btn.disabled = analyzing;
    input.disabled = analyzing;
    btn.innerHTML = analyzing
        ? '<span class="spinner"></span> Analyzing'
        : '<span class="btn-text">Analyze</span><span class="btn-icon">&#9654;</span>';
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
    setUploading(false);
    stopPolling();
    document.getElementById("progress-section").classList.add("hidden");
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function formatTime(seconds) {
    seconds = Math.round(seconds);
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${m}:${String(s).padStart(2, "0")}`;
}

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        if (!document.getElementById("tiktok-modal").classList.contains("hidden")) {
            closeTikTok();
        } else {
            closePreview();
        }
    }
});

// ===== TikTok Editor =====
let tiktokFrame = null; // captured video frame as ImageData
let tiktokDrawing = null; // "gameplay" or "webcam"
let tiktokDragStart = null;
let tiktokRegions = { gameplay: null, webcam: null };
let tiktokCurrentPreset = "cam-top-right";

function openTikTokEditor() {
    if (!previewClipData) return;

    const video = document.getElementById("preview-video");
    const canvas = document.getElementById("tiktok-canvas");
    const ctx = canvas.getContext("2d");

    // Capture current frame from video
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 360;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    tiktokFrame = ctx.getImageData(0, 0, canvas.width, canvas.height);

    // Default drawing mode
    tiktokDrawing = "gameplay";

    // Apply default preset
    setPreset("cam-top-right");

    document.getElementById("tiktok-modal").classList.remove("hidden");
    document.getElementById("tiktok-status").textContent = "";
    document.getElementById("tiktok-status").className = "trim-status";

    drawTikTokOverlay();
}

function closeTikTok() {
    document.getElementById("tiktok-modal").classList.add("hidden");
}

function setPreset(name) {
    tiktokCurrentPreset = name;

    // Update active button
    document.querySelectorAll(".preset-btn").forEach(b => {
        b.classList.remove("active");
        if (b.textContent.toLowerCase().includes(name.replace("cam-", "").replace("-", " ")) ||
            (name === "no-cam" && b.textContent.includes("No Webcam")) ||
            (name === "custom" && b.textContent === "Custom")) {
            b.classList.add("active");
        }
    });

    if (name === "cam-top-right") {
        tiktokRegions.gameplay = { x: 0, y: 0, w: 1, h: 1 };
        tiktokRegions.webcam = { x: 0.72, y: 0.02, w: 0.26, h: 0.30 };
    } else if (name === "cam-top-left") {
        tiktokRegions.gameplay = { x: 0, y: 0, w: 1, h: 1 };
        tiktokRegions.webcam = { x: 0.02, y: 0.02, w: 0.26, h: 0.30 };
    } else if (name === "cam-bottom-right") {
        tiktokRegions.gameplay = { x: 0, y: 0, w: 1, h: 1 };
        tiktokRegions.webcam = { x: 0.72, y: 0.68, w: 0.26, h: 0.30 };
    } else if (name === "cam-bottom-left") {
        tiktokRegions.gameplay = { x: 0, y: 0, w: 1, h: 1 };
        tiktokRegions.webcam = { x: 0.02, y: 0.68, w: 0.26, h: 0.30 };
    } else if (name === "no-cam") {
        tiktokRegions.gameplay = { x: 0, y: 0, w: 1, h: 1 };
        tiktokRegions.webcam = null;
    } else if (name === "custom") {
        tiktokRegions.gameplay = { x: 0.05, y: 0.05, w: 0.9, h: 0.9 };
        tiktokRegions.webcam = { x: 0.7, y: 0.02, w: 0.28, h: 0.30 };
    }

    drawTikTokOverlay();
    drawTikTokPreview();
}

function drawTikTokOverlay() {
    const canvas = document.getElementById("tiktok-canvas");
    const ctx = canvas.getContext("2d");

    // Restore original frame
    if (tiktokFrame) ctx.putImageData(tiktokFrame, 0, 0);

    const w = canvas.width, h = canvas.height;

    // Draw gameplay region (green)
    if (tiktokRegions.gameplay) {
        const r = tiktokRegions.gameplay;
        ctx.strokeStyle = "#00ff00";
        ctx.lineWidth = 3;
        ctx.setLineDash([8, 4]);
        ctx.strokeRect(r.x * w, r.y * h, r.w * w, r.h * h);
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(0, 255, 0, 0.1)";
        ctx.fillRect(r.x * w, r.y * h, r.w * w, r.h * h);
        ctx.fillStyle = "#00ff00";
        ctx.font = "bold 14px sans-serif";
        ctx.fillText("GAMEPLAY", r.x * w + 6, r.y * h + 18);
    }

    // Draw webcam region (blue)
    if (tiktokRegions.webcam) {
        const r = tiktokRegions.webcam;
        ctx.strokeStyle = "#00aaff";
        ctx.lineWidth = 3;
        ctx.setLineDash([8, 4]);
        ctx.strokeRect(r.x * w, r.y * h, r.w * w, r.h * h);
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(0, 170, 255, 0.15)";
        ctx.fillRect(r.x * w, r.y * h, r.w * w, r.h * h);
        ctx.fillStyle = "#00aaff";
        ctx.font = "bold 14px sans-serif";
        ctx.fillText("WEBCAM", r.x * w + 6, r.y * h + 18);
    }
}

function drawTikTokPreview() {
    const srcCanvas = document.getElementById("tiktok-canvas");
    const preview = document.getElementById("tiktok-preview");
    const ctx = preview.getContext("2d");
    const sw = srcCanvas.width, sh = srcCanvas.height;

    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, 180, 320);

    if (tiktokRegions.webcam) {
        // Stacked: gameplay 70%, webcam 30%
        const gpH = 224; // 70% of 320
        const wcH = 96;  // 30% of 320

        if (tiktokFrame) {
            // Draw gameplay crop
            const g = tiktokRegions.gameplay;
            const tempCanvas = document.createElement("canvas");
            tempCanvas.width = sw; tempCanvas.height = sh;
            tempCanvas.getContext("2d").putImageData(tiktokFrame, 0, 0);

            ctx.drawImage(tempCanvas,
                g.x * sw, g.y * sh, g.w * sw, g.h * sh,
                0, 0, 180, gpH);

            // Draw webcam crop
            const w = tiktokRegions.webcam;
            ctx.drawImage(tempCanvas,
                w.x * sw, w.y * sh, w.w * sw, w.h * sh,
                0, gpH, 180, wcH);

            // Divider line
            ctx.strokeStyle = "#333";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, gpH);
            ctx.lineTo(180, gpH);
            ctx.stroke();
        }
    } else {
        // Gameplay only
        if (tiktokFrame) {
            const g = tiktokRegions.gameplay;
            const tempCanvas = document.createElement("canvas");
            tempCanvas.width = sw; tempCanvas.height = sh;
            tempCanvas.getContext("2d").putImageData(tiktokFrame, 0, 0);

            ctx.drawImage(tempCanvas,
                g.x * sw, g.y * sh, g.w * sw, g.h * sh,
                0, 0, 180, 320);
        }
    }
}

// Canvas mouse + touch interaction for custom drawing
(function() {
    let drawing = false;
    let startX, startY;

    function getPos(e, canvas) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        let clientX, clientY;
        if (e.touches && e.touches.length > 0) {
            clientX = e.touches[0].clientX;
            clientY = e.touches[0].clientY;
        } else if (e.changedTouches && e.changedTouches.length > 0) {
            clientX = e.changedTouches[0].clientX;
            clientY = e.changedTouches[0].clientY;
        } else {
            clientX = e.clientX;
            clientY = e.clientY;
        }
        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY,
        };
    }

    function onStart(e) {
        e.preventDefault();
        drawing = true;
        const canvas = document.getElementById("tiktok-canvas");
        const pos = getPos(e, canvas);
        startX = pos.x;
        startY = pos.y;
    }

    function onMove(e) {
        if (!drawing) return;
        e.preventDefault();
        const canvas = document.getElementById("tiktok-canvas");
        const pos = getPos(e, canvas);

        const x = Math.min(startX, pos.x) / canvas.width;
        const y = Math.min(startY, pos.y) / canvas.height;
        const w = Math.abs(pos.x - startX) / canvas.width;
        const h = Math.abs(pos.y - startY) / canvas.height;

        tiktokRegions[tiktokDrawing] = { x, y, w, h };
        drawTikTokOverlay();
        drawTikTokPreview();
    }

    function onEnd() { drawing = false; }

    document.addEventListener("DOMContentLoaded", () => {
        const canvas = document.getElementById("tiktok-canvas");

        // Mouse events
        canvas.addEventListener("mousedown", onStart);
        canvas.addEventListener("mousemove", onMove);
        canvas.addEventListener("mouseup", onEnd);

        // Touch events
        canvas.addEventListener("touchstart", onStart, { passive: false });
        canvas.addEventListener("touchmove", onMove, { passive: false });
        canvas.addEventListener("touchend", onEnd);

        // Right-click / long-press to switch region
        canvas.addEventListener("contextmenu", (e) => {
            e.preventDefault();
            tiktokDrawing = tiktokDrawing === "gameplay" ? "webcam" : "gameplay";
            const status = document.getElementById("tiktok-status");
            status.textContent = `Now drawing: ${tiktokDrawing}`;
            status.className = "trim-status";
        });

        // Long press for touch (switch region)
        let longPressTimer = null;
        canvas.addEventListener("touchstart", (e) => {
            longPressTimer = setTimeout(() => {
                tiktokDrawing = tiktokDrawing === "gameplay" ? "webcam" : "gameplay";
                const status = document.getElementById("tiktok-status");
                status.textContent = `Now drawing: ${tiktokDrawing}`;
                status.className = "trim-status";
                drawing = false; // cancel the draw
            }, 600);
        });
        canvas.addEventListener("touchend", () => { clearTimeout(longPressTimer); });
        canvas.addEventListener("touchmove", () => { clearTimeout(longPressTimer); });
    });
})();

function switchDrawingRegion() {
    tiktokDrawing = tiktokDrawing === "gameplay" ? "webcam" : "gameplay";
    document.getElementById("tiktok-drawing-label").textContent =
        tiktokDrawing.charAt(0).toUpperCase() + tiktokDrawing.slice(1);
    const status = document.getElementById("tiktok-status");
    status.textContent = `Now drawing: ${tiktokDrawing}`;
    status.className = "trim-status";
}

function exportTikTok() {
    if (!previewClipData || !currentJobId) return;

    const statusEl = document.getElementById("tiktok-status");
    const btn = document.getElementById("tiktok-export-btn");
    statusEl.textContent = "Creating TikTok version...";
    statusEl.className = "trim-status working";
    btn.disabled = true;

    const layout = tiktokRegions.webcam ? "stacked" : "gameplay_only";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/tiktok`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            gameplay: tiktokRegions.gameplay,
            webcam: tiktokRegions.webcam,
            layout: layout,
        }),
    })
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }
        if (data.success) {
            statusEl.textContent = "Done! Downloading...";
            statusEl.className = "trim-status success";

            // Trigger download
            const a = document.createElement("a");
            a.href = `/static/clips/${data.filename}`;
            a.download = data.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    })
    .catch(() => {
        btn.disabled = false;
        statusEl.textContent = "Failed to create TikTok version";
        statusEl.className = "trim-status error";
    });
}

// ===== THEME TOGGLE =====
function toggleTheme() {
    document.body.classList.toggle("light-theme");
    const isLight = document.body.classList.contains("light-theme");
    localStorage.setItem("autoclipper_theme", isLight ? "light" : "dark");
    document.getElementById("theme-toggle").textContent = isLight ? "\u263E" : "\u2606";
}

(function initTheme() {
    const saved = localStorage.getItem("autoclipper_theme");
    if (saved === "light") {
        document.body.classList.add("light-theme");
    }
})();

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener("keydown", (e) => {
    // Don't trigger shortcuts when typing in inputs
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;

    const modal = document.getElementById("preview-modal");
    const isModalOpen = !modal.classList.contains("hidden");

    if (isModalOpen) {
        const video = document.getElementById("preview-video");
        if (e.key === " " || e.key === "k") {
            e.preventDefault();
            video.paused ? video.play() : video.pause();
        } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            video.currentTime = Math.max(0, video.currentTime - 5);
        } else if (e.key === "ArrowRight") {
            e.preventDefault();
            video.currentTime = Math.min(video.duration, video.currentTime + 5);
        } else if (e.key === "Escape") {
            closePreview();
        } else if (e.key === "j") {
            video.currentTime = Math.max(0, video.currentTime - 10);
        } else if (e.key === "l") {
            video.currentTime = Math.min(video.duration, video.currentTime + 10);
        } else if (e.key === "m") {
            video.muted = !video.muted;
        } else if (e.key === "f") {
            video.requestFullscreen && video.requestFullscreen();
        }
    }

    // Global shortcuts
    if (e.key === "1" && e.altKey) switchEditorTab("trim");
    if (e.key === "2" && e.altKey) switchEditorTab("crop");
    if (e.key === "3" && e.altKey) switchEditorTab("effects");
    if (e.key === "4" && e.altKey) switchEditorTab("captions");
    if (e.key === "5" && e.altKey) switchEditorTab("more");

    // Navigate clips with arrow keys when modal closed
    if (!isModalOpen && currentClips.length > 0) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            const dir = e.key === "ArrowDown" ? 1 : -1;
            const idx = (previewClipIndex + dir + currentClips.length) % currentClips.length;
            previewClip(idx);
        }
    }
});

// ===== CAPTIONS EXPORT =====
function exportCaptions() {
    if (!previewClipData || !currentJobId) return;

    const text = document.getElementById("caption-text").value.trim();
    if (!text) {
        document.getElementById("caption-status").textContent = "Enter caption text";
        document.getElementById("caption-status").className = "trim-status error";
        return;
    }

    const position = document.getElementById("caption-position").value;
    const fontSize = parseInt(document.getElementById("caption-size").value);
    const color = document.getElementById("caption-color").value;

    const statusEl = document.getElementById("caption-status");
    const btn = document.getElementById("caption-export-btn");
    statusEl.textContent = "Adding captions...";
    statusEl.className = "trim-status working";
    btn.disabled = true;

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/captions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, position, font_size: fontSize, color }),
    })
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }
        statusEl.textContent = "Done! Downloading...";
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
        trackAnalytics("caption_export");
    })
    .catch(() => {
        btn.disabled = false;
        statusEl.textContent = "Export failed";
        statusEl.className = "trim-status error";
    });
}

// ===== MORE TOOLS PANEL TOGGLES =====
function hideAllSubPanels() {
    document.querySelectorAll(".more-sub-panel").forEach(p => p.classList.add("hidden"));
}

function showWatermarkPanel() {
    hideAllSubPanels();
    document.getElementById("watermark-panel").classList.remove("hidden");
    loadWatermarks();
}

function showZoomPanPanel() {
    hideAllSubPanels();
    document.getElementById("zoompan-panel").classList.remove("hidden");
}

function showSfxPanel() {
    hideAllSubPanels();
    document.getElementById("sfx-panel").classList.remove("hidden");
    loadSfx();
}

function showGifPanel() {
    hideAllSubPanels();
    document.getElementById("gif-panel").classList.remove("hidden");
}

function splitClipUI() {
    hideAllSubPanels();
    document.getElementById("split-panel").classList.remove("hidden");
    if (previewClipData) {
        document.getElementById("split-time").max = previewClipData.duration;
        document.getElementById("split-time").value = Math.round(previewClipData.duration / 2);
    }
}

function showMergePanel() {
    hideAllSubPanels();
    document.getElementById("merge-panel").classList.remove("hidden");
    renderMergeList();
}

// ===== WATERMARK =====
function loadWatermarks() {
    fetch("/api/watermarks")
        .then(res => res.json())
        .then(data => {
            const sel = document.getElementById("watermark-select");
            sel.innerHTML = '<option value="">Select watermark...</option>';
            (data.watermarks || []).forEach(f => {
                sel.innerHTML += `<option value="${f}">${f}</option>`;
            });
        });
}

// Upload watermark file
document.addEventListener("DOMContentLoaded", () => {
    const wmInput = document.getElementById("watermark-file");
    if (wmInput) {
        wmInput.addEventListener("change", () => {
            if (!wmInput.files.length) return;
            const fd = new FormData();
            fd.append("file", wmInput.files[0]);
            fetch("/api/watermarks/upload", { method: "POST", body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadWatermarks();
                        document.getElementById("watermark-select").value = data.filename;
                    }
                });
        });
    }
});

function exportWatermark() {
    if (!previewClipData || !currentJobId) return;
    const wmFile = document.getElementById("watermark-select").value;
    if (!wmFile) {
        document.getElementById("watermark-status").textContent = "Select a watermark";
        document.getElementById("watermark-status").className = "trim-status error";
        return;
    }

    const statusEl = document.getElementById("watermark-status");
    statusEl.textContent = "Applying watermark...";
    statusEl.className = "trim-status working";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/watermark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            watermark_filename: wmFile,
            position: document.getElementById("watermark-position").value,
            opacity: parseFloat(document.getElementById("watermark-opacity").value),
            scale: parseFloat(document.getElementById("watermark-scale").value),
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }
        statusEl.textContent = "Done!";
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
        trackAnalytics("watermark_export");
    })
    .catch(() => { statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== ZOOM/PAN =====
function exportZoomPan() {
    if (!previewClipData || !currentJobId) return;
    const statusEl = document.getElementById("zoompan-status");
    statusEl.textContent = "Applying zoom effect...";
    statusEl.className = "trim-status working";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/zoompan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            zoom_start: parseFloat(document.getElementById("zoom-start").value),
            zoom_end: parseFloat(document.getElementById("zoom-end").value),
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { statusEl.textContent = data.error; statusEl.className = "trim-status error"; return; }
        statusEl.textContent = "Done!";
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
    })
    .catch(() => { statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== SOUND EFFECTS =====
function loadSfx() {
    fetch("/api/sfx")
        .then(res => res.json())
        .then(data => {
            const sel = document.getElementById("sfx-select");
            sel.innerHTML = '<option value="">Select sound...</option>';
            (data.sfx || []).forEach(f => {
                sel.innerHTML += `<option value="${f}">${f}</option>`;
            });
        });
}

document.addEventListener("DOMContentLoaded", () => {
    const sfxInput = document.getElementById("sfx-file");
    if (sfxInput) {
        sfxInput.addEventListener("change", () => {
            if (!sfxInput.files.length) return;
            const fd = new FormData();
            fd.append("file", sfxInput.files[0]);
            fetch("/api/sfx/upload", { method: "POST", body: fd })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        loadSfx();
                        document.getElementById("sfx-select").value = data.filename;
                    }
                });
        });
    }
});

function exportSfx() {
    if (!previewClipData || !currentJobId) return;
    const sfxFile = document.getElementById("sfx-select").value;
    if (!sfxFile) {
        document.getElementById("sfx-status").textContent = "Select a sound effect";
        document.getElementById("sfx-status").className = "trim-status error";
        return;
    }
    const statusEl = document.getElementById("sfx-status");
    statusEl.textContent = "Adding sound effect...";
    statusEl.className = "trim-status working";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/sfx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            sfx_filename: sfxFile,
            timestamp: parseFloat(document.getElementById("sfx-timestamp").value),
            volume: parseFloat(document.getElementById("sfx-volume").value),
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { statusEl.textContent = data.error; statusEl.className = "trim-status error"; return; }
        statusEl.textContent = "Done!";
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
    })
    .catch(() => { statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== GIF EXPORT =====
function exportGif() {
    if (!previewClipData || !currentJobId) return;
    const statusEl = document.getElementById("gif-status");
    statusEl.textContent = "Creating GIF...";
    statusEl.className = "trim-status working";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/gif`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            start_offset: parseFloat(document.getElementById("gif-start").value),
            duration: parseFloat(document.getElementById("gif-duration").value),
            fps: parseInt(document.getElementById("gif-fps").value),
            width: parseInt(document.getElementById("gif-width").value),
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { statusEl.textContent = data.error; statusEl.className = "trim-status error"; return; }
        const sizeMB = (data.size / 1024 / 1024).toFixed(1);
        statusEl.textContent = `Done! ${sizeMB}MB`;
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
        trackAnalytics("gif_export");
    })
    .catch(() => { statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== SPLIT CLIP =====
function splitClip() {
    if (!previewClipData || !currentJobId) return;
    const statusEl = document.getElementById("split-status");
    statusEl.textContent = "Splitting...";
    statusEl.className = "trim-status working";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/split`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ split_time: parseFloat(document.getElementById("split-time").value) }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { statusEl.textContent = data.error; statusEl.className = "trim-status error"; return; }
        statusEl.textContent = "Split complete!";
        statusEl.className = "trim-status success";
        // Refresh clips
        fetchClips(currentJobId);
        setTimeout(closePreview, 1000);
    })
    .catch(() => { statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== MERGE CLIPS =====
function renderMergeList() {
    const list = document.getElementById("merge-clip-list");
    if (!list) return;
    list.innerHTML = "";
    currentClips.forEach((clip, i) => {
        list.innerHTML += `
            <label class="merge-clip-item">
                <input type="checkbox" data-index="${i}" value="${clip.id}">
                <span>${clip.label} (${clip.duration}s) - ${clip.timestamp_display}</span>
            </label>`;
    });
}

function mergeClips() {
    if (!currentJobId) return;
    const checked = document.querySelectorAll("#merge-clip-list input:checked");
    const clipIds = Array.from(checked).map(cb => cb.value);
    if (clipIds.length < 2) {
        document.getElementById("merge-status").textContent = "Select at least 2 clips";
        document.getElementById("merge-status").className = "trim-status error";
        return;
    }

    const statusEl = document.getElementById("merge-status");
    statusEl.textContent = "Merging clips...";
    statusEl.className = "trim-status working";

    fetch(`/api/clips/${currentJobId}/merge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            clip_ids: clipIds,
            transition: document.getElementById("merge-transition").value,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { statusEl.textContent = data.error; statusEl.className = "trim-status error"; return; }
        statusEl.textContent = "Merged! Downloading...";
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
    })
    .catch(() => { statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== YOUTUBE SHORTS =====
function openYouTubeShortEditor() {
    // Reuse TikTok editor but change export
    openTikTokEditor();
    // Swap export button to YT
    const btn = document.getElementById("tiktok-export-btn");
    btn.textContent = "Export YouTube Short";
    btn.onclick = exportYouTubeShort;
    document.querySelector(".tiktok-title").textContent = "YouTube Shorts Editor";
}

function exportYouTubeShort() {
    if (!previewClipData || !currentJobId) return;
    const statusEl = document.getElementById("tiktok-status");
    statusEl.textContent = "Creating YouTube Short...";
    statusEl.className = "trim-status working";
    const btn = document.getElementById("tiktok-export-btn");
    btn.disabled = true;

    const layout = tiktokRegions.webcam ? "stacked" : "gameplay_only";

    fetch(`/api/clips/${currentJobId}/${previewClipData.id}/youtube-short`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            gameplay: tiktokRegions.gameplay,
            webcam: tiktokRegions.webcam,
            layout: layout,
        }),
    })
    .then(res => res.json())
    .then(data => {
        btn.disabled = false;
        if (data.error) { statusEl.textContent = data.error; statusEl.className = "trim-status error"; return; }
        statusEl.textContent = "Done! Downloading...";
        statusEl.className = "trim-status success";
        triggerDownload(data.filename);
        trackAnalytics("youtube_short_export");
    })
    .catch(() => { btn.disabled = false; statusEl.textContent = "Failed"; statusEl.className = "trim-status error"; });
}

// ===== BATCH TIKTOK =====
function batchTikTok() {
    if (!currentJobId || currentClips.length === 0) return;
    const preset = prompt("Which preset? (cam-top-right, cam-bottom-right, no-cam)", "cam-top-right");
    if (!preset) return;

    // Set regions based on preset
    let gameplay = { x: 0, y: 0, w: 1, h: 1 };
    let webcam = null;
    let layout = "gameplay_only";

    if (preset === "cam-top-right") { webcam = { x: 0.72, y: 0.02, w: 0.26, h: 0.30 }; layout = "stacked"; }
    else if (preset === "cam-top-left") { webcam = { x: 0.02, y: 0.02, w: 0.26, h: 0.30 }; layout = "stacked"; }
    else if (preset === "cam-bottom-right") { webcam = { x: 0.72, y: 0.68, w: 0.26, h: 0.30 }; layout = "stacked"; }
    else if (preset === "cam-bottom-left") { webcam = { x: 0.02, y: 0.68, w: 0.26, h: 0.30 }; layout = "stacked"; }

    const clipIds = currentClips.map(c => c.id);

    showNotification(`Creating ${clipIds.length} TikTok videos...`);

    fetch(`/api/clips/${currentJobId}/batch-tiktok`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clip_ids: clipIds, gameplay, webcam, layout }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { showNotification(data.error); return; }
        const count = (data.results || []).filter(r => r && r.filename).length;
        showNotification(`Done! ${count} TikTok videos created.`);
        // Download each
        (data.results || []).forEach(r => {
            if (r && r.filename) triggerDownload(r.filename);
        });
        trackAnalytics("batch_tiktok", { count });
    })
    .catch(() => showNotification("Batch TikTok failed"));
}

// ===== CLIP SORTING / FILTERING =====
function sortClips(sortBy) {
    const order = "desc";
    fetch(`/api/clips/${currentJobId}/sorted?sort_by=${sortBy}&order=${order}`)
        .then(res => res.json())
        .then(data => {
            if (data.clips) {
                currentClips = data.clips;
                renderClips();
            }
        });
}

function filterClips(filterVal) {
    if (filterVal === "all") {
        fetchClips(currentJobId);
        return;
    }
    fetch(`/api/clips/${currentJobId}/sorted?review_status=${filterVal}`)
        .then(res => res.json())
        .then(data => {
            if (data.clips) {
                currentClips = data.clips;
                renderClips();
            }
        });
}

// ===== DUPLICATE DETECTION =====
function findDuplicates() {
    if (!currentJobId) return;
    fetch(`/api/clips/${currentJobId}/duplicates`)
        .then(res => res.json())
        .then(data => {
            if (!data.groups || data.groups.length === 0) {
                showNotification("No duplicate clips found!");
                return;
            }
            let msg = `Found ${data.groups.length} group(s) of overlapping clips:\n`;
            data.groups.forEach((g, i) => {
                msg += `\nGroup ${i + 1}: ${g.clip_ids.length} clips (${Math.round(g.overlap_pct * 100)}% overlap)`;
            });
            alert(msg);
        });
}

// ===== CLIP METADATA (REVIEW, TAGS, NOTES) =====
function setClipReview(clipId, status) {
    if (!currentJobId) return;
    fetch(`/api/clips/${currentJobId}/${clipId}/metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ review_status: status }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // Update local clip data
            const clip = currentClips.find(c => c.id === clipId);
            if (clip) clip.review_status = status;
            renderClips();
        }
    });
}

function addClipTag(clipId) {
    const tag = prompt("Enter tag:");
    if (!tag) return;
    const clip = currentClips.find(c => c.id === clipId);
    const tags = (clip && clip.tags) || [];
    tags.push(tag.trim());

    fetch(`/api/clips/${currentJobId}/${clipId}/metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && clip) {
            clip.tags = tags;
            renderClips();
        }
    });
}

function addClipNote(clipId) {
    const clip = currentClips.find(c => c.id === clipId);
    const existing = (clip && clip.notes) || "";
    const note = prompt("Notes:", existing);
    if (note === null) return;

    fetch(`/api/clips/${currentJobId}/${clipId}/metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: note }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && clip) {
            clip.notes = note;
        }
    });
}

// ===== ANALYTICS =====
function trackAnalytics(event, details) {
    fetch("/api/analytics/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event, details: details || {} }),
    }).catch(() => {}); // fire and forget
}

function loadAnalytics() {
    fetch("/api/analytics")
        .then(res => res.json())
        .then(data => {
            const events = data.events || [];
            document.getElementById("stat-total-clips").textContent = currentClips.length;
            document.getElementById("stat-total-exports").textContent =
                events.filter(e => e.event && e.event.includes("export")).length;
            document.getElementById("stat-total-tiktoks").textContent =
                events.filter(e => e.event === "tiktok_export" || e.event === "batch_tiktok").length;
            document.getElementById("stat-total-gifs").textContent =
                events.filter(e => e.event === "gif_export").length;
        })
        .catch(() => {});
}

function toggleAnalytics() {
    // Analytics is now always visible in the Library tab
    loadAnalytics();
}

// ===== EXPORT PRESETS =====
function loadExportPresets() {
    fetch("/api/presets")
        .then(res => res.json())
        .then(data => {
            const sel = document.getElementById("export-preset-select");
            if (!sel) return;
            sel.innerHTML = '<option value="">None</option>';
            (data.presets || []).forEach(p => {
                sel.innerHTML += `<option value="${p.id}">${p.name}</option>`;
            });
        })
        .catch(() => {});
}

function saveExportPreset() {
    const name = prompt("Preset name:");
    if (!name) return;

    const settings = {
        gameplay: tiktokRegions.gameplay,
        webcam: tiktokRegions.webcam,
        preset: tiktokCurrentPreset,
    };

    fetch("/api/presets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, type: "tiktok", settings }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadExportPresets();
            showNotification("Preset saved!");
        }
    });
}

function loadExportPreset(presetId) {
    if (!presetId) return;
    fetch("/api/presets")
        .then(res => res.json())
        .then(data => {
            const preset = (data.presets || []).find(p => p.id === presetId);
            if (preset && preset.settings) {
                if (preset.settings.gameplay) tiktokRegions.gameplay = preset.settings.gameplay;
                if (preset.settings.webcam) tiktokRegions.webcam = preset.settings.webcam;
                if (preset.settings.preset) setPreset(preset.settings.preset);
                drawTikTokOverlay();
                drawTikTokPreview();
            }
        });
}

// ===== WATCH FOLDER =====
function toggleWatchFolder() {
    const btn = document.getElementById("watch-folder-btn");
    const isActive = btn.classList.contains("watch-folder-active");

    if (isActive) {
        fetch("/api/watch-folder/stop", { method: "POST" })
            .then(res => res.json())
            .then(() => {
                btn.classList.remove("watch-folder-active");
                btn.textContent = "Watch Folder: Off";
            });
    } else {
        const apiKey = document.getElementById("api-key").value.trim();
        const gameId = selectedGame;
        fetch("/api/watch-folder/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: apiKey, game: gameId }),
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                btn.classList.add("watch-folder-active");
                btn.textContent = "Watch Folder: ON";
            }
        });
    }
}

// ===== NOTIFICATIONS =====
function showNotification(message) {
    // Browser notification
    if (Notification.permission === "granted") {
        new Notification("Auto-Clipper", { body: message });
    } else if (Notification.permission !== "denied") {
        Notification.requestPermission();
    }

    // Toast notification
    let toast = document.getElementById("notification-toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "notification-toast";
        toast.className = "notification-toast";
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
}

// ===== HELPER: TRIGGER DOWNLOAD =====
function triggerDownload(filename) {
    const a = document.createElement("a");
    a.href = `/static/clips/${filename}`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// ===== SENSITIVITY SLIDER =====
function onSensitivityChange(val) {
    val = parseInt(val);
    const method = document.getElementById("detection-method").value;
    const isCv = method === "arc_cv_pipeline";
    let hint;
    if (isCv) {
        // Show CV scoring version names
        if (val < 20) hint = `${val}% — v1_strict: Fewest clips, highest quality. Requires strong combat evidence + temporal change.`;
        else if (val < 40) hint = `${val}% — v5_combat_only: Only clips confirmed fighting (needs 2+ combat signals at once).`;
        else if (val < 60) hint = `${val}% — v3_temporal (DEFAULT): Detects frame-to-frame changes. Stable brightness = boring, sudden spike = combat.`;
        else if (val < 80) hint = `${val}% — v2_balanced: Good balance. Static signals discounted without temporal support.`;
        else hint = `${val}% — v4_aggressive: Most clips. Better to clip something boring than miss real action.`;
    } else {
        if (val <= 20) hint = `${val}% — Very selective: only the most intense moments.`;
        else if (val <= 40) hint = `${val}% — Conservative: fewer clips, higher quality.`;
        else if (val <= 60) hint = `${val}% — Balanced: catches most action without too many false positives.`;
        else if (val <= 80) hint = `${val}% — Sensitive: catches more subtle moments.`;
        else hint = `${val}% — Maximum: captures everything, may include quiet moments.`;
    }
    document.getElementById("sensitivity-hint").textContent = hint;
    saveState();
}

// ===== BATCH QUEUE =====
let batchQueue = [];

function addToBatchQueue() {
    const url = document.getElementById("vod-url").value.trim();
    if (!url) return;
    if (batchQueue.includes(url)) return;
    batchQueue.push(url);
    document.getElementById("vod-url").value = "";
    renderBatchQueue();
}

function removeBatchItem(index) {
    batchQueue.splice(index, 1);
    renderBatchQueue();
}

function clearBatchQueue() {
    batchQueue = [];
    renderBatchQueue();
}

function renderBatchQueue() {
    const section = document.getElementById("batch-queue-section");
    const list = document.getElementById("batch-queue-list");
    const count = document.getElementById("batch-count");
    const startBtn = document.getElementById("batch-start-btn");

    if (batchQueue.length === 0) {
        section.classList.add("hidden");
        return;
    }

    section.classList.remove("hidden");
    count.textContent = batchQueue.length + " queued";
    startBtn.classList.remove("hidden");

    list.innerHTML = batchQueue.map((url, i) => `
        <div class="batch-queue-item">
            <span class="batch-queue-url">${escapeHtml(url)}</span>
            <button class="file-remove" onclick="removeBatchItem(${i})">&times;</button>
        </div>
    `).join("");
}

function startBatchAnalysis() {
    if (batchQueue.length === 0) return;
    const apiKey = document.getElementById("api-key").value.trim();
    const detectionMethod = document.getElementById("detection-method").value;
    const sensitivity = parseInt(document.getElementById("sensitivity").value);

    showProgress();

    fetch("/api/batch-analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            urls: batchQueue,
            api_key: apiKey,
            game: selectedGame,
            detection_method: detectionMethod,
            sensitivity: sensitivity,
            detection_overrides: getDetectionOverrides(),
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { showError(data.error); resetUI(); return; }
        currentJobId = data.job_id;
        batchQueue = [];
        renderBatchQueue();
        startPolling();
    })
    .catch(() => { showError("Batch analysis failed"); resetUI(); });
}

// ===== HIGHLIGHT REEL =====
function exportHighlightReel() {
    if (!currentJobId || currentClips.length === 0) return;

    const transition = prompt("Transition type? (none, fade, wipe)", "fade");
    if (transition === null) return;

    showNotification("Creating highlight reel...");

    const clipIds = currentClips.map(c => c.id);

    fetch(`/api/clips/${currentJobId}/highlight-reel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            clip_ids: clipIds,
            transition: transition || "none",
            resolution: document.getElementById("export-resolution").value,
            quality: document.getElementById("export-quality").value,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) { showNotification(data.error); return; }
        showNotification("Highlight reel ready!");
        triggerDownload(data.filename);
        trackAnalytics("highlight_reel");
    })
    .catch(() => showNotification("Failed to create highlight reel"));
}

// ===== STAR RATING =====
function setClipRating(clipId, rating) {
    if (!currentJobId) return;
    fetch(`/api/clips/${currentJobId}/${clipId}/metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating: rating }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const clip = currentClips.find(c => c.id === clipId);
            if (clip) clip.rating = rating;
            renderClips();
        }
    });
}

function renderStars(clipId, currentRating) {
    let html = '<div class="clip-stars">';
    for (let i = 1; i <= 5; i++) {
        const filled = i <= (currentRating || 0);
        html += `<span class="star ${filled ? 'star-filled' : 'star-empty'}" onclick="event.stopPropagation(); setClipRating('${clipId}', ${i})">&#9733;</span>`;
    }
    html += '</div>';
    return html;
}

// ===== EXPORT SETTINGS =====
function toggleExportSettings() {
    document.getElementById("export-settings-content").classList.toggle("hidden");
}

// ===== CUSTOM GAME PROFILE =====
function toggleCustomProfile() {
    document.getElementById("custom-profile-content").classList.toggle("hidden");
}

function saveCustomProfile() {
    const name = document.getElementById("cp-name").value.trim();
    const id = document.getElementById("cp-id").value.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");

    if (!name || !id) {
        document.getElementById("cp-status").textContent = "Name and ID are required";
        document.getElementById("cp-status").className = "trim-status error";
        return;
    }

    const profile = {
        id: id,
        name: name,
        audio_threshold_db: parseFloat(document.getElementById("cp-audio-threshold").value),
        audio_weight: parseFloat(document.getElementById("cp-audio-weight").value),
        intensity_threshold: parseFloat(document.getElementById("cp-intensity").value),
        min_clip_duration: parseInt(document.getElementById("cp-min-clip").value),
        max_clip_duration: parseInt(document.getElementById("cp-max-clip").value),
        merge_gap: parseInt(document.getElementById("cp-merge-gap").value),
        ai_system_prompt: document.getElementById("cp-ai-prompt").value.trim(),
    };

    const statusEl = document.getElementById("cp-status");
    statusEl.textContent = "Saving...";
    statusEl.className = "trim-status working";

    fetch("/api/custom-profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            statusEl.textContent = data.error;
            statusEl.className = "trim-status error";
            return;
        }
        statusEl.textContent = "Profile saved! Refresh to see it in game list.";
        statusEl.className = "trim-status success";
        loadGames(); // Refresh game list
    })
    .catch(() => {
        statusEl.textContent = "Failed to save";
        statusEl.className = "trim-status error";
    });
}

// ===== PLATFORM UPLOAD HELPERS =====
function uploadToYouTube() {
    if (!previewClipData) return;
    // Can't do real OAuth in a local app, so open YouTube Studio upload page
    window.open("https://studio.youtube.com/channel/UC/videos/upload", "_blank");
    showNotification("YouTube Studio opened — upload your clip from the Downloads folder.");
    downloadFromModal();
}

function uploadToTikTok() {
    if (!previewClipData) return;
    window.open("https://www.tiktok.com/upload", "_blank");
    showNotification("TikTok upload opened — upload your clip from the Downloads folder.");
    downloadFromModal();
}

// ===== INIT NEW FEATURES ON LOAD =====
document.addEventListener("DOMContentLoaded", () => {
    // Show analytics section
    const analyticsSection = document.getElementById("analytics-section");
    if (analyticsSection) analyticsSection.classList.remove("hidden");

    // Show export settings and custom profile sections
    const exportSection = document.getElementById("export-settings-section");
    if (exportSection) exportSection.classList.remove("hidden");
    const cpSection = document.getElementById("custom-profile-section");
    if (cpSection) cpSection.classList.remove("hidden");

    // Load export presets
    loadExportPresets();

    // Request notification permission
    if ("Notification" in window && Notification.permission === "default") {
        // Will ask on first notification
    }

    // Check watch folder status
    fetch("/api/watch-folder/status")
        .then(res => res.json())
        .then(data => {
            const btn = document.getElementById("watch-folder-btn");
            if (btn && data.running) {
                btn.classList.add("watch-folder-active");
                btn.textContent = "Watch Folder: ON";
            }
        })
        .catch(() => {});
});

// ===== ADVANCED DETECTION SETTINGS =====
const DET_DEFAULTS = {
    "det-intensity": 0.35,
    "det-audio-weight": 0.30,
    "det-audio-thresh": -15,
    "det-merge-gap": 8,
    "det-min-clip": 20,
    "det-max-clip": 60,
    "det-sample-fps": 2,
    "det-fallback-ratio": 0.30,
    "det-window-sec": 3,
    "det-peak-weight": 0.60,
    "det-menu-suppress": "on",
    "det-brightness-thresh": 0.60,
};

function toggleDetectionSettings() {
    const panel = document.getElementById("detection-settings");
    const arrow = document.getElementById("detection-settings-arrow");
    panel.classList.toggle("hidden");
    arrow.classList.toggle("open");
}

function getDetectionOverrides() {
    const overrides = {};
    for (const [id, defaultVal] of Object.entries(DET_DEFAULTS)) {
        const el = document.getElementById(id);
        if (!el) continue;
        const val = (typeof defaultVal === "string") ? el.value : parseFloat(el.value);
        if (val !== defaultVal) {
            // Convert element id to backend key: "det-intensity" -> "intensity_threshold" etc.
            overrides[id] = val;
        }
    }
    // Always send all values so backend knows what to apply
    return {
        intensity_threshold: parseFloat(document.getElementById("det-intensity").value),
        audio_weight: parseFloat(document.getElementById("det-audio-weight").value),
        audio_threshold_db: parseFloat(document.getElementById("det-audio-thresh").value),
        merge_gap: parseInt(document.getElementById("det-merge-gap").value),
        min_clip_duration: parseInt(document.getElementById("det-min-clip").value),
        max_clip_duration: parseInt(document.getElementById("det-max-clip").value),
        sample_fps: parseInt(document.getElementById("det-sample-fps").value),
        fallback_threshold_ratio: parseFloat(document.getElementById("det-fallback-ratio").value),
        window_seconds: parseInt(document.getElementById("det-window-sec").value),
        peak_weight: parseFloat(document.getElementById("det-peak-weight").value),
        menu_suppress: document.getElementById("det-menu-suppress").value,
        brightness_threshold: parseFloat(document.getElementById("det-brightness-thresh").value),
    };
}

function resetDetectionSettings() {
    for (const [id, val] of Object.entries(DET_DEFAULTS)) {
        const el = document.getElementById(id);
        if (el) el.value = val;
    }
    saveState();
}

function saveDetectionSettings() {
    const settings = {};
    for (const id of Object.keys(DET_DEFAULTS)) {
        const el = document.getElementById(id);
        if (el) settings[id] = el.value;
    }
    return settings;
}

function restoreDetectionSettings(settings) {
    if (!settings) return;
    for (const [id, val] of Object.entries(settings)) {
        const el = document.getElementById(id);
        if (el) el.value = val;
    }
}

// ===== Toast Notifications =====

function showToast(message, type = "info", duration = 3000) {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-msg">${message}</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>`;
    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => toast.classList.add("toast-visible"));

    setTimeout(() => {
        toast.classList.remove("toast-visible");
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ===== Manual Clip & Clip Trigger Features =====

let manualClipVod = null; // currently selected library VOD for manual clipping

function showManualClip(filename) {
    manualClipVod = filename;
    const section = document.getElementById("manual-clip-section");
    document.getElementById("manual-clip-vod").textContent = filename;
    document.getElementById("manual-clip-timestamp").value = "";
    document.getElementById("manual-clip-status").textContent = "";
    section.classList.remove("hidden");

    // Check whisper availability
    fetch("/api/clip-trigger-status")
        .then(r => r.json())
        .then(data => {
            const scanBtn = document.getElementById("btn-scan-triggers");
            if (scanBtn) {
                if (data.available) {
                    scanBtn.title = `Using ${data.backend}`;
                    scanBtn.disabled = false;
                } else {
                    scanBtn.title = "Whisper not installed - pip install faster-whisper";
                    scanBtn.disabled = false; // Still allow click to show error
                }
            }
        })
        .catch(() => {});
}

function hideManualClip() {
    document.getElementById("manual-clip-section").classList.add("hidden");
    manualClipVod = null;
}

function parseTimestamp(str) {
    // Parse "1:23:45", "23:45", "45", "end", or raw seconds
    str = str.trim().toLowerCase();
    if (!str) return null;
    if (str === "end" && vodDuration > 0) return vodDuration;
    const parts = str.split(":").map(Number);
    if (parts.some(isNaN)) return null;
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 1) return parts[0];
    return null;
}

function createManualClip() {
    if (!manualClipVod) return;

    const tsInput = document.getElementById("manual-clip-timestamp").value;
    const duration = parseInt(document.getElementById("manual-clip-duration").value) || 30;
    const status = document.getElementById("manual-clip-status");

    const timestamp = parseTimestamp(tsInput);
    if (timestamp === null || timestamp < 0) {
        status.textContent = "Enter a valid timestamp (e.g. 1:23:45 or 'end')";
        status.className = "trim-status error";
        return;
    }

    status.textContent = "Clipping...";
    status.className = "trim-status";

    fetch("/api/manual-clip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            library_file: manualClipVod,
            timestamp: timestamp,
            duration: duration,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            status.textContent = data.error;
            status.className = "trim-status error";
            return;
        }
        status.textContent = "";
        showToast(`Clip created at ${formatTime(timestamp)}!`, "success");

        // Switch to the new session to show the clip
        currentJobId = data.job_id;
        currentClips = [data.clip];
        vodDuration = 0; // Will be set when we fetch clips
        renderClips();
        switchMainTab("analyze");
        loadSessions();
    })
    .catch(() => {
        status.textContent = "Failed to create clip";
        status.className = "trim-status error";
    });
}

function scanClipTriggers() {
    if (!manualClipVod) return;

    const status = document.getElementById("manual-clip-status");
    const duration = parseInt(document.getElementById("manual-clip-duration").value) || 30;

    // Get custom trigger words if configured
    const triggerInput = document.getElementById("trigger-words-input");
    let customTriggers = null;
    if (triggerInput && triggerInput.value.trim()) {
        customTriggers = triggerInput.value.split(",").map(s => s.trim()).filter(Boolean);
    }

    status.textContent = "Starting clip trigger scan...";
    status.className = "trim-status";

    fetch("/api/clip-trigger-scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            library_file: manualClipVod,
            clip_duration: duration,
            custom_triggers: customTriggers,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            status.textContent = data.error;
            status.className = "trim-status error";
            showToast(data.error, "error", 5000);
            return;
        }
        // Switch to analyze tab and start polling
        currentJobId = data.job_id;
        switchMainTab("analyze");
        setAnalyzing(true);
        showProgress();
        startPolling();
        showToast("Scanning VOD for clip triggers...", "info");
        status.textContent = "";
    })
    .catch(() => {
        status.textContent = "Failed to start scan";
        status.className = "trim-status error";
    });
}

// In-session manual clip (from clips toolbar)
function showSessionManualClip() {
    const panel = document.getElementById("session-manual-clip");
    document.getElementById("session-clip-timestamp").value = "";
    document.getElementById("session-clip-status").textContent = "";
    panel.classList.remove("hidden");
    document.getElementById("session-clip-timestamp").focus();
}

function createSessionManualClip() {
    if (!currentJobId) return;

    const tsInput = document.getElementById("session-clip-timestamp").value;
    const duration = parseInt(document.getElementById("session-clip-duration").value) || 30;
    const status = document.getElementById("session-clip-status");

    const timestamp = parseTimestamp(tsInput);
    if (timestamp === null || timestamp < 0) {
        status.textContent = "Enter a valid timestamp (e.g. 1:23:45)";
        status.className = "trim-status error";
        return;
    }

    status.textContent = "Clipping...";
    status.className = "trim-status";

    fetch(`/api/clips/${currentJobId}/manual-clip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            timestamp: timestamp,
            duration: duration,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            status.textContent = data.error;
            status.className = "trim-status error";
            return;
        }
        status.textContent = "";
        showToast(`Clip added at ${formatTime(timestamp)}!`, "success");
        // Add to current clips and re-render
        currentClips.push(data.clip);
        renderClips();
        // Scroll to the new clip
        setTimeout(() => {
            const cards = document.querySelectorAll(".clip-card");
            if (cards.length) cards[cards.length - 1].scrollIntoView({ behavior: "smooth", block: "center" });
        }, 100);
    })
    .catch(() => {
        status.textContent = "Failed to create clip";
        status.className = "trim-status error";
    });
}

// ===== Keyboard Shortcuts =====

document.addEventListener("keydown", function(e) {
    // Don't fire shortcuts when typing in inputs
    const tag = e.target.tagName.toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;

    // Ctrl/Cmd + Shift + C = Manual clip at current preview video time
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "c") {
        e.preventDefault();
        clipFromPreviewVideo();
        return;
    }

    // Escape = close modals/panels
    if (e.key === "Escape") {
        const modal = document.getElementById("preview-modal");
        if (modal && !modal.classList.contains("hidden")) {
            modal.classList.add("hidden");
            return;
        }
        const panel = document.getElementById("session-manual-clip");
        if (panel && !panel.classList.contains("hidden")) {
            panel.classList.add("hidden");
            return;
        }
    }
});

function clipFromPreviewVideo() {
    // If the preview modal is open, clip at the current playback position
    const video = document.getElementById("preview-video");
    const modal = document.getElementById("preview-modal");
    if (!video || !modal || modal.classList.contains("hidden")) {
        showToast("Open a clip preview first, then press Ctrl+Shift+C", "info");
        return;
    }

    if (!currentJobId) {
        showToast("No active session for clipping", "error");
        return;
    }

    // The preview shows a clip, but we want to clip from the original VOD
    // Use the clip's start_time + current playback position as the VOD timestamp
    if (!previewClipData) return;

    const vodTimestamp = previewClipData.start_time + video.currentTime;
    showToast(`Clipping at ${formatTime(vodTimestamp)}...`, "info");

    fetch(`/api/clips/${currentJobId}/manual-clip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            timestamp: vodTimestamp,
            duration: 30,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showToast(data.error, "error");
            return;
        }
        showToast("Clip created from preview position!", "success");
        currentClips.push(data.clip);
        renderClips();
    })
    .catch(() => showToast("Failed to create clip", "error"));
}

// ===== Timeline Click-to-Clip =====
// Double-click on the timeline track to create a manual clip at that point

function initTimelineClickToClip() {
    const track = document.getElementById("timeline-track");
    if (!track || track._clipClickBound) return;
    track._clipClickBound = true;

    track.addEventListener("dblclick", function(e) {
        if (!currentJobId || !previewClipData) return;

        const rect = track.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const maxTime = vodDuration || (previewClipData ? previewClipData.end_time + 60 : 300);
        const timestamp = pct * maxTime;

        showToast(`Creating clip at ${formatTime(timestamp)}...`, "info");

        fetch(`/api/clips/${currentJobId}/manual-clip`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                timestamp: timestamp,
                duration: 30,
            }),
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, "error");
                return;
            }
            showToast(`Clip added at ${formatTime(timestamp)}!`, "success");
            currentClips.push(data.clip);
            renderClips();
        })
        .catch(() => showToast("Failed to create clip", "error"));
    });
}
