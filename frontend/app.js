/**
 * RA NEXUS — Sapthagiri NPS University Digital Assistant
 * Professional Client Application Logic
 */

(function () {
    "use strict";

    // Application State
    const state = {
        profile: {
            branch: "ECE",
            academic_year: 1,
            semester: 2,
            section: "1ECE02",
            batch: "All"
        },
        activeView: "dashboard",
        facilities: [],
        sections: [],
        isSending: false
    };

    // DOM Elements
    const elements = {
        // Layout
        sidebar: document.getElementById("appSidebar"),
        mobileToggle: document.getElementById("mobileMenuToggle"),
        navTabs: document.querySelectorAll(".nav-tab"),
        viewPanels: document.querySelectorAll(".view-panel"),

        // Header
        headerProfileBadge: document.getElementById("headerProfileBadge"),
        headerProfileText: document.getElementById("headerProfileText"),
        headerProfileTag: document.getElementById("headerProfileTag"),
        systemHealthBadge: document.getElementById("systemHealthBadge"),
        systemHealthText: document.getElementById("systemHealthText"),

        // Dashboard
        dashSearchInput: document.getElementById("dashboardSearchInput"),
        dashSearchBtn: document.getElementById("dashboardSearchBtn"),
        dashProfileTitle: document.getElementById("dashProfileTitle"),
        dashProfileStatus: document.getElementById("dashProfileStatus"),
        dashProfileDesc: document.getElementById("dashProfileDesc"),
        dashChangeProfileBtn: document.getElementById("dashChangeProfileBtn"),
        quickChips: document.querySelectorAll(".chip-card"),
        portalSwitches: document.querySelectorAll("[data-switch]"),

        // Timetable
        ttBranchSelect: document.getElementById("ttBranchSelect"),
        ttSectionSelect: document.getElementById("ttSectionSelect"),
        ttWeekdaySelect: document.getElementById("ttWeekdaySelect"),
        ttBatchSelect: document.getElementById("ttBatchSelect"),
        ttNextClassBtn: document.getElementById("timetableNextClassBtn"),
        nextClassResultBox: document.getElementById("nextClassResultBox"),
        nextClassResultTitle: document.getElementById("nextClassResultTitle"),
        nextClassResultBody: document.getElementById("nextClassResultBody"),
        closeNextClassResultBtn: document.getElementById("closeNextClassResultBtn"),
        timetableLoading: document.getElementById("timetableLoading"),
        timetableProvisionalNotice: document.getElementById("timetableProvisionalNotice"),
        ttNoticeSection: document.getElementById("ttNoticeSection"),
        timetableTableWrapper: document.getElementById("timetableTableWrapper"),
        timetableTableBody: document.getElementById("timetableTableBody"),
        timetableUnregisteredState: document.getElementById("timetableUnregisteredState"),
        timetableUnregisteredMsg: document.getElementById("timetableUnregisteredMsg"),

        // Directory
        directorySearchInput: document.getElementById("directorySearchInput"),
        directoryGrid: document.getElementById("directoryGrid"),
        categoryPills: document.querySelectorAll(".pill-btn"),

        // Chat
        chatContextSection: document.getElementById("chatContextSection"),
        chatContextEditBtn: document.getElementById("chatContextEditBtn"),
        messagesContainer: document.getElementById("messages"),
        messageInput: document.getElementById("messageInput"),
        sendButton: document.getElementById("sendButton"),
        clearChatBtn: document.getElementById("clearChatBtn"),
        liveAnnouncer: document.getElementById("liveAnnouncer"),

        // Profile Form
        profileForm: document.getElementById("profileForm"),
        profBranch: document.getElementById("profBranch"),
        profYear: document.getElementById("profYear"),
        profSemester: document.getElementById("profSemester"),
        profSection: document.getElementById("profSection"),
        profBatch: document.getElementById("profBatch"),
        profileValidationBox: document.getElementById("profileValidationBox"),
        profileValidationText: document.getElementById("profileValidationText"),
        resetProfileBtn: document.getElementById("resetProfileBtn"),

        // Diagnostics & Staging Telemetry
        diagHealthVal: document.getElementById("diagHealthVal"),
        diagHealthSub: document.getElementById("diagHealthSub"),
        refreshDiagnosticsBtn: document.getElementById("refreshDiagnosticsBtn"),
        diagStagingStatus: document.getElementById("diagStagingStatus"),
        diagStagingSections: document.getElementById("diagStagingSections"),
        diagStagingEntries: document.getElementById("diagStagingEntries"),
        diagProductionStatus: document.getElementById("diagProductionStatus"),
        timetableStagingBanner: document.getElementById("timetableStagingBanner"),
        timetableStagingStatusBadge: document.getElementById("timetableStagingStatusBadge"),
        ttStagedSectionsCount: document.getElementById("ttStagedSectionsCount"),
        ttStagedEntriesCount: document.getElementById("ttStagedEntriesCount")
    };

    /* ==========================================================================
       STORAGE & PROFILE INITIALIZATION
       ========================================================================== */

    function loadProfile() {
        try {
            const saved = localStorage.getItem("ra_nexus_profile");
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.section) state.profile.section = parsed.section.trim().toUpperCase();
                if (parsed.branch) state.profile.branch = parsed.branch.trim().toUpperCase();
                if (parsed.academic_year) state.profile.academic_year = parseInt(parsed.academic_year) || 1;
                if (parsed.semester) state.profile.semester = parseInt(parsed.semester) || 2;
                if (parsed.batch) state.profile.batch = parsed.batch.trim();
            }
        } catch (e) {
            console.warn("Could not load stored student profile:", e);
        }
        applyProfileToUI();
    }

    function saveProfile() {
        try {
            localStorage.setItem("ra_nexus_profile", JSON.stringify(state.profile));
        } catch (e) {
            console.warn("Could not persist student profile:", e);
        }
        applyProfileToUI();
    }

    function applyProfileToUI() {
        const { branch, section, batch } = state.profile;
        const isRegistered = (section === "1ECE02");

        // Header chip
        if (elements.headerProfileText) {
            elements.headerProfileText.textContent = `${branch} • ${section}`;
        }
        if (elements.headerProfileTag) {
            elements.headerProfileTag.textContent = isRegistered ? "Provisional" : "Unverified";
            elements.headerProfileTag.className = isRegistered ? "chip-status-tag" : "chip-status-tag unverified";
        }

        // Dashboard banner
        if (elements.dashProfileTitle) {
            elements.dashProfileTitle.textContent = `${branch} — Section ${section}`;
        }
        if (elements.dashProfileStatus) {
            elements.dashProfileStatus.textContent = isRegistered ? "Provisional Registration" : "Unregistered Section";
            elements.dashProfileStatus.className = isRegistered ? "status-badge amber" : "status-badge amber";
        }
        if (elements.dashProfileDesc) {
            if (isRegistered) {
                elements.dashProfileDesc.textContent = "Currently configured for ECE Section 1ECE02. Timetable records for this section are registered; detailed period timings and weekday day-by-day schedules are pending official publication.";
            } else {
                elements.dashProfileDesc.textContent = `Section ${section} is not registered in the verified university database. Timetable lookups will request clarification.`;
            }
        }

        // Chat Context Bar
        if (elements.chatContextSection) {
            elements.chatContextSection.textContent = `${branch} • ${section} (Batch ${batch})`;
        }

        // Profile Form sync
        if (elements.profBranch) elements.profBranch.value = branch;
        if (elements.profYear) elements.profYear.value = String(state.profile.academic_year);
        if (elements.profSemester) elements.profSemester.value = String(state.profile.semester);
        if (elements.profSection) elements.profSection.value = section;
        if (elements.profBatch) elements.profBatch.value = batch;

        // Timetable selects sync
        if (elements.ttBranchSelect) elements.ttBranchSelect.value = branch;
        if (elements.ttBatchSelect) elements.ttBatchSelect.value = (batch === "All" ? "" : batch);

        validateProfileInput();
    }

    function validateProfileInput() {
        if (!elements.profileValidationBox || !elements.profSection) return;
        const enteredSec = elements.profSection.value.trim().toUpperCase();
        const enteredBranch = elements.profBranch ? elements.profBranch.value.trim().toUpperCase() : "ECE";

        if (enteredSec === "1ECE02") {
            if (enteredBranch === "ECE") {
                elements.profileValidationBox.className = "validation-feedback success";
                elements.profileValidationText.textContent = "Verified registered section for ECE (provisional schedule pending official period timings).";
            } else {
                elements.profileValidationBox.className = "validation-feedback warning";
                elements.profileValidationText.textContent = `Branch mismatch: Section 1ECE02 belongs to ECE, not ${enteredBranch}.`;
            }
        } else if (enteredSec) {
            elements.profileValidationBox.className = "validation-feedback warning";
            elements.profileValidationText.textContent = `Section ${enteredSec} is not yet cataloged in verified university records.`;
        } else {
            elements.profileValidationBox.className = "validation-feedback neutral";
            elements.profileValidationText.textContent = "Enter a section ID to validate against institutional records.";
        }
    }

    /* ==========================================================================
       VIEW NAVIGATION
       ========================================================================== */

    function showView(targetView) {
        state.activeView = targetView;

        elements.navTabs.forEach(tab => {
            const isTarget = tab.dataset.view === targetView;
            tab.classList.toggle("active", isTarget);
            if (isTarget) {
                tab.setAttribute("aria-current", "page");
            } else {
                tab.removeAttribute("aria-current");
            }
        });

        elements.viewPanels.forEach(panel => {
            panel.hidden = (panel.id !== `${targetView}View`);
        });

        // Close mobile sidebar if open
        if (elements.sidebar) {
            elements.sidebar.classList.remove("open");
            if (elements.mobileToggle) {
                elements.mobileToggle.setAttribute("aria-expanded", "false");
            }
        }

        // View specific activations
        if (targetView === "timetable") {
            loadTimetableData();
            fetchSystemHealth();
        } else if (targetView === "directory") {
            if (state.facilities.length === 0) {
                loadCampusFacilities();
            }
        } else if (targetView === "system") {
            fetchSystemHealth();
        } else if (targetView === "chat") {
            if (elements.messageInput) {
                setTimeout(() => elements.messageInput.focus(), 100);
            }
        }
    }

    /* ==========================================================================
       TIMETABLE LOGIC
       ========================================================================== */

    async function loadSectionsCatalog() {
        try {
            const res = await fetch("/api/timetable/sections");
            if (!res.ok) return;
            const data = await res.json();
            if (data && Array.isArray(data.sections)) {
                state.sections = data.sections;
                filterSectionsByBranch();
            }
        } catch (e) {
            console.warn("Failed to load sections catalog:", e);
        }
    }

    function filterSectionsByBranch() {
        if (!elements.ttSectionSelect) return;
        const currentBranch = elements.ttBranchSelect ? elements.ttBranchSelect.value : state.profile.branch;
        const branchSections = state.sections.filter(s => s.branch === currentBranch);

        elements.ttSectionSelect.innerHTML = "";
        if (branchSections.length > 0) {
            branchSections.forEach(sec => {
                const opt = document.createElement("option");
                opt.value = sec.section_id;
                opt.textContent = `${sec.section_id} (${sec.branch_name || sec.branch} • Provisional)`;
                elements.ttSectionSelect.appendChild(opt);
            });
            elements.ttSectionSelect.disabled = false;
        } else {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = `No published sections for ${currentBranch}`;
            elements.ttSectionSelect.appendChild(opt);
            elements.ttSectionSelect.disabled = true;
        }
    }

    async function loadTimetableData() {
        const branch = elements.ttBranchSelect ? elements.ttBranchSelect.value : state.profile.branch;
        const sec = (elements.ttSectionSelect && !elements.ttSectionSelect.disabled) ? elements.ttSectionSelect.value : "";
        const weekday = elements.ttWeekdaySelect ? elements.ttWeekdaySelect.value : "";
        const batch = elements.ttBatchSelect ? elements.ttBatchSelect.value : "";

        if (elements.timetableLoading) elements.timetableLoading.hidden = false;
        if (elements.timetableProvisionalNotice) elements.timetableProvisionalNotice.hidden = true;
        if (elements.timetableTableWrapper) elements.timetableTableWrapper.hidden = true;
        if (elements.timetableUnregisteredState) elements.timetableUnregisteredState.hidden = true;

        if (!sec) {
            if (elements.timetableLoading) elements.timetableLoading.hidden = true;
            if (elements.timetableUnregisteredState) {
                elements.timetableUnregisteredState.hidden = false;
                if (elements.timetableUnregisteredMsg) {
                    elements.timetableUnregisteredMsg.textContent = `No timetable records have been published yet for the ${branch} department. Official schedules will appear here once authenticated.`;
                }
            }
            return;
        }

        if (elements.ttNoticeSection) elements.ttNoticeSection.textContent = sec;

        if (elements.timetableLoading) elements.timetableLoading.hidden = false;
        if (elements.timetableProvisionalNotice) elements.timetableProvisionalNotice.hidden = true;
        if (elements.timetableTableWrapper) elements.timetableTableWrapper.hidden = true;
        if (elements.timetableUnregisteredState) elements.timetableUnregisteredState.hidden = true;

        try {
            let url = `/api/timetable/schedule?section=${encodeURIComponent(sec)}`;
            if (branch) url += `&branch=${encodeURIComponent(branch)}`;
            if (weekday) url += `&weekday=${encodeURIComponent(weekday)}`;
            if (batch) url += `&batch=${encodeURIComponent(batch)}`;

            const res = await fetch(url);
            if (elements.timetableLoading) elements.timetableLoading.hidden = true;

            if (res.status === 404) {
                if (elements.timetableUnregisteredState) {
                    elements.timetableUnregisteredState.hidden = false;
                    if (elements.timetableUnregisteredMsg) {
                        elements.timetableUnregisteredMsg.textContent = `Section ${sec} is not registered in the verified university timetable repository.`;
                    }
                }
                return;
            }

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                if (elements.timetableUnregisteredState) {
                    elements.timetableUnregisteredState.hidden = false;
                    if (elements.timetableUnregisteredMsg) {
                        elements.timetableUnregisteredMsg.textContent = err.detail || `Unable to retrieve timetable for section ${sec}.`;
                    }
                }
                return;
            }

            const data = await res.json();
            const entries = data.entries || [];

            // Check if section has entries with periods or is pending
            if (entries.length === 0 || data.status === "schedule_pending" || sec === "1ECE02") {
                if (elements.timetableProvisionalNotice) elements.timetableProvisionalNotice.hidden = false;
            } else {
                renderTimetableEntries(entries);
            }
        } catch (e) {
            console.error("Timetable load error:", e);
            if (elements.timetableLoading) elements.timetableLoading.hidden = true;
            if (elements.timetableProvisionalNotice) elements.timetableProvisionalNotice.hidden = false;
        }
    }

    function renderTimetableEntries(entries) {
        if (!elements.timetableTableBody || !elements.timetableTableWrapper) return;
        elements.timetableTableBody.innerHTML = "";

        if (entries.length === 0) {
            if (elements.timetableProvisionalNotice) elements.timetableProvisionalNotice.hidden = false;
            elements.timetableTableWrapper.hidden = true;
            return;
        }

        entries.forEach(item => {
            const tr = document.createElement("tr");
            const isBreak = Boolean(
                item.is_break ||
                (item.subject_name && /break|lunch|interval|recess|tea/i.test(item.subject_name)) ||
                (item.subject_code && /break|lunch/i.test(item.subject_code))
            );

            if (isBreak) {
                tr.className = "schedule-break-row";
            }

            const periodTd = document.createElement("td");
            periodTd.textContent = item.period ? `Period ${item.period}` : "—";

            const timeTd = document.createElement("td");
            timeTd.textContent = (item.start_time && item.end_time) ? `${item.start_time} - ${item.end_time}` : "Pending";

            const dayTd = document.createElement("td");
            dayTd.textContent = item.weekday ? item.weekday.charAt(0).toUpperCase() + item.weekday.slice(1) : "—";

            const subjectTd = document.createElement("td");
            if (isBreak) {
                subjectTd.innerHTML = `<span class="badge-break">☕ ${escapeHtml(item.subject_name || "Break / Recess")}</span>`;
            } else {
                subjectTd.innerHTML = `<strong>${escapeHtml(item.subject_name || "—")}</strong><br><small class="text-muted">${escapeHtml(item.subject_code || "")}</small>`;
            }

            const facultyTd = document.createElement("td");
            facultyTd.textContent = isBreak ? "—" : (item.faculty_name || "Assigned Faculty");

            const roomTd = document.createElement("td");
            roomTd.textContent = isBreak ? "—" : (item.classroom || "Main Block");

            const batchTd = document.createElement("td");
            const batchVal = item.batch || "All";
            if (batchVal === "All") {
                batchTd.textContent = "All";
            } else {
                batchTd.innerHTML = `<span class="batch-badge">${escapeHtml(batchVal)}</span>`;
            }

            tr.appendChild(periodTd);
            tr.appendChild(timeTd);
            tr.appendChild(dayTd);
            tr.appendChild(subjectTd);
            tr.appendChild(facultyTd);
            tr.appendChild(roomTd);
            tr.appendChild(batchTd);

            elements.timetableTableBody.appendChild(tr);
        });

        elements.timetableTableWrapper.hidden = false;
    }

    async function checkNextClass() {
        const sec = (elements.ttSectionSelect ? elements.ttSectionSelect.value : state.profile.section) || "1ECE02";
        const nowIso = new Date().toISOString();

        if (!elements.nextClassResultBox || !elements.nextClassResultBody) return;

        elements.nextClassResultBox.hidden = false;
        elements.nextClassResultTitle.textContent = `Current / Next Class Lookup — Section ${sec}`;
        elements.nextClassResultBody.textContent = "Querying deterministic schedule engine...";

        try {
            const res = await fetch(`/api/timetable/next-class?section=${encodeURIComponent(sec)}&client_time=${encodeURIComponent(nowIso)}`);
            const data = await res.json();

            if (!res.ok) {
                elements.nextClassResultBody.textContent = data.detail || `Error retrieving class status for ${sec}.`;
                return;
            }

            if (data.can_determine && data.next_class) {
                const nc = data.next_class;
                elements.nextClassResultBody.innerHTML = `
                    <div style="color:var(--accent-green);font-weight:600;margin-bottom:4px;">Next Class Verified:</div>
                    <strong>${escapeHtml(nc.subject_name || "Subject")} (${escapeHtml(nc.subject_code || "")})</strong><br>
                    <span>Room: ${escapeHtml(nc.classroom || "Classroom")} • Faculty: ${escapeHtml(nc.faculty_name || "Assigned Faculty")}</span><br>
                    <small style="color:var(--text-muted)">Time: ${escapeHtml(nc.start_time || "")} - ${escapeHtml(nc.end_time || "")}</small>
                `;
            } else {
                elements.nextClassResultBody.textContent = data.response || "Timetable data for this section does not currently contain active weekday period timings.";
            }
        } catch (e) {
            elements.nextClassResultBody.textContent = "Unable to connect to timetable service. Please ensure local server is running.";
        }
    }

    /* ==========================================================================
       CAMPUS DIRECTORY LOGIC
       ========================================================================== */

    async function loadCampusFacilities() {
        if (!elements.directoryGrid) return;
        elements.directoryGrid.innerHTML = `
            <div class="state-container">
                <div class="spinner" aria-hidden="true"></div>
                <p>Loading verified campus facilities...</p>
            </div>
        `;

        try {
            const res = await fetch("/api/campus/facilities");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            state.facilities = data.facilities || [];
            renderFacilities(state.facilities);
        } catch (e) {
            elements.directoryGrid.innerHTML = `
                <div class="state-container">
                    <span class="state-icon">⚠️</span>
                    <h3>Unable to load facilities</h3>
                    <p>Could not retrieve verified campus records from the local server.</p>
                </div>
            `;
        }
    }

    function renderFacilities(list) {
        if (!elements.directoryGrid) return;
        elements.directoryGrid.innerHTML = "";

        if (list.length === 0) {
            elements.directoryGrid.innerHTML = `
                <div class="state-container">
                    <span class="state-icon">🔍</span>
                    <h3>No matching facilities found</h3>
                    <p>Try searching for a different keyword or select "All Facilities".</p>
                </div>
            `;
            return;
        }

        list.forEach(item => {
            const card = document.createElement("article");
            card.className = "facility-card";

            const header = document.createElement("div");
            header.className = "facility-card-header";
            header.innerHTML = `
                <h3 class="facility-title">${escapeHtml(item.title)}</h3>
                <span class="facility-badge">${escapeHtml(item.category || "Facility")}</span>
            `;

            const loc = document.createElement("div");
            loc.className = "facility-location";
            loc.innerHTML = `📍 <span>${escapeHtml(item.location)}</span>`;

            const desc = document.createElement("p");
            desc.className = "facility-desc";
            desc.textContent = item.description || "";

            card.appendChild(header);
            card.appendChild(loc);
            card.appendChild(desc);

            if (item.timings) {
                const timings = document.createElement("div");
                timings.className = "timings-badge";
                timings.innerHTML = `⏰ <span>Hours: ${escapeHtml(item.timings)}</span>`;
                card.appendChild(timings);
            }

            if (Array.isArray(item.equipment) && item.equipment.length > 0) {
                const eqList = document.createElement("div");
                eqList.className = "equipment-list";
                item.equipment.forEach(eq => {
                    const eqTag = document.createElement("span");
                    eqTag.className = "equipment-tag";
                    eqTag.textContent = eq;
                    eqList.appendChild(eqTag);
                });
                card.appendChild(eqList);
            }

            const footer = document.createElement("div");
            footer.className = "facility-card-footer";
            footer.innerHTML = `
                <span class="verification-tag">✔ Verified Record</span>
                <button class="text-link-button ask-about-btn">Ask Assistant →</button>
            `;

            const askBtn = footer.querySelector(".ask-about-btn");
            if (askBtn) {
                askBtn.addEventListener("click", () => {
                    showView("chat");
                    sendMessage(`Tell me about the ${item.title} and its facilities`);
                });
            }

            card.appendChild(footer);
            elements.directoryGrid.appendChild(card);
        });
    }

    function filterFacilities() {
        const query = elements.directorySearchInput ? elements.directorySearchInput.value.trim().toLowerCase() : "";
        let activeCat = "all";
        const activePill = document.querySelector(".pill-btn.active");
        if (activePill) activeCat = activePill.dataset.category || "all";

        const filtered = state.facilities.filter(item => {
            const matchesCat = (activeCat === "all") || (item.category && item.category.toLowerCase() === activeCat);
            if (!matchesCat) return false;

            if (!query) return true;
            const fullText = (
                `${item.title} ${item.location} ${item.description || ""} ${(item.equipment || []).join(" ")} ${item.timings || ""}`
            ).toLowerCase();
            return fullText.includes(query);
        });

        renderFacilities(filtered);
    }

    /* ==========================================================================
       AI ASSISTANT CHAT LOGIC
       ========================================================================== */

    function addChatMessage(text, sender, toolName = null, isVerified = true) {
        if (!elements.messagesContainer) return null;

        const wrapper = document.createElement("div");
        wrapper.className = `message-wrapper ${sender === "user" ? "user-message" : "nexus-message"}`;

        if (sender !== "user") {
            const badge = document.createElement("div");
            badge.className = "message-sender-badge";
            badge.innerHTML = `
                <span class="badge-dot" aria-hidden="true"></span>
                <strong>RA NEXUS Core</strong>
                <span class="badge-tag">${isVerified ? "Verified" : "Notice"}</span>
            `;
            wrapper.appendChild(badge);
        }

        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        bubble.textContent = text;
        wrapper.appendChild(bubble);

        if (toolName) {
            const toolBadge = document.createElement("div");
            toolBadge.className = "tool-indicator-badge";
            const displayNames = {
                timetable: "Timetable Engine",
                timetable_engine: "Timetable Engine",
                knowledge_search: "Campus Knowledge Base",
                calculator: "Safe AST Calculator",
                system_status: "System Diagnostics"
            };
            toolBadge.innerHTML = `<span class="tool-badge-icon" aria-hidden="true">⚙</span> Executed via <strong>${escapeHtml(displayNames[toolName] || toolName)}</strong>`;
            wrapper.appendChild(toolBadge);
        }

        elements.messagesContainer.appendChild(wrapper);

        // Screen reader announcement
        if (sender !== "user" && elements.liveAnnouncer) {
            elements.liveAnnouncer.textContent = text;
        }

        // Scroll into view
        requestAnimationFrame(() => {
            elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
        });

        return wrapper;
    }

    async function sendMessage(customText = null) {
        if (state.isSending) return;

        const inputVal = elements.messageInput ? elements.messageInput.value.trim() : "";
        const queryText = (customText || inputVal).trim();

        if (!queryText) return;

        if (elements.messageInput) {
            elements.messageInput.value = "";
            elements.messageInput.style.height = "auto";
        }

        // Add user message
        addChatMessage(queryText, "user");

        // Add thinking placeholder with animated indicator
        const thinkingWrapper = document.createElement("div");
        thinkingWrapper.className = "message-wrapper nexus-message thinking-message";
        thinkingWrapper.innerHTML = `
            <div class="message-sender-badge">
                <span class="badge-dot thinking" aria-hidden="true"></span>
                <strong>RA NEXUS Core</strong>
                <span class="badge-tag">Processing</span>
            </div>
            <div class="message-bubble thinking-bubble">
                <span class="typing-indicator" aria-hidden="true">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </span>
                <span>Consulting Sapthagiri NPS University records...</span>
            </div>
        `;
        elements.messagesContainer.appendChild(thinkingWrapper);
        elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;

        state.isSending = true;
        if (elements.sendButton) elements.sendButton.disabled = true;

        const payload = {
            message: queryText,
            student_context: {
                branch: state.profile.branch,
                academic_year: parseInt(state.profile.academic_year) || 1,
                semester: parseInt(state.profile.semester) || 2,
                section: state.profile.section,
                batch: state.profile.batch !== "All" ? state.profile.batch : undefined
            },
            client_time: new Date().toISOString()
        };

        try {
            const res = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (thinkingWrapper && thinkingWrapper.parentNode) {
                thinkingWrapper.parentNode.removeChild(thinkingWrapper);
            }

            if (!res.ok) {
                throw new Error(`Server returned status ${res.status}`);
            }

            const data = await res.json();
            const responseText = data.response || "Task processed.";
            addChatMessage(responseText, "nexus", data.tool, true);

        } catch (err) {
            console.error("Chat error:", err);
            if (thinkingWrapper && thinkingWrapper.parentNode) {
                thinkingWrapper.parentNode.removeChild(thinkingWrapper);
            }
            addChatMessage("Unable to reach the RA NEXUS assistant. Please ensure the local backend server is running.", "nexus", null, false);
        } finally {
            state.isSending = false;
            if (elements.sendButton) elements.sendButton.disabled = false;
            if (elements.messageInput) {
                elements.messageInput.disabled = false;
                elements.messageInput.focus();
            }
        }
    }

    function clearChatHistory() {
        if (!elements.messagesContainer) return;
        elements.messagesContainer.innerHTML = `
            <div class="message-wrapper nexus-message">
                <div class="message-sender-badge">
                    <span class="badge-dot" aria-hidden="true"></span>
                    <strong>RA NEXUS Core</strong>
                    <span class="badge-tag">Local Engine</span>
                </div>
                <div class="message-bubble">
                    Conversation history cleared. Ask a new academic question or select a suggested prompt from the Dashboard.
                </div>
            </div>
        `;
    }

    /* ==========================================================================
       SYSTEM DIAGNOSTICS LOGIC
       ========================================================================== */

    async function fetchSystemHealth() {
        try {
            const [healthRes, stagingRes] = await Promise.all([
                fetch("/health").catch(() => null),
                fetch("/api/timetable/staging-status").catch(() => null)
            ]);

            if (healthRes && healthRes.ok) {
                const data = await healthRes.json();
                if (elements.systemHealthBadge) {
                    elements.systemHealthBadge.style.display = "flex";
                }
                if (elements.systemHealthText) {
                    elements.systemHealthText.textContent = data.status === "online" ? "Systems Online" : "Service Degraded";
                }
                if (elements.diagHealthVal) {
                    elements.diagHealthVal.textContent = data.status === "online" ? "Online" : data.status;
                    elements.diagHealthVal.className = data.status === "online" ? "diag-val text-green" : "diag-val text-amber";
                }
                if (elements.diagHealthSub) {
                    elements.diagHealthSub.textContent = `FastAPI • ${data.institution || "Sapthagiri NPS University"}`;
                }
            } else {
                if (elements.systemHealthText) {
                    elements.systemHealthText.textContent = "Offline (Local)";
                }
                if (elements.diagHealthVal) {
                    elements.diagHealthVal.textContent = "Disconnected";
                    elements.diagHealthVal.className = "diag-val text-red";
                }
                if (elements.diagHealthSub) {
                    elements.diagHealthSub.textContent = "Backend Unreachable";
                }
            }

            if (stagingRes && stagingRes.ok) {
                const sData = await stagingRes.json();
                if (elements.diagStagingStatus) {
                    elements.diagStagingStatus.textContent = sData.status ? sData.status.replace("_", " ").toUpperCase() : "Pending Review";
                }
                if (elements.diagStagingSections) {
                    elements.diagStagingSections.textContent = `${sData.section_count || 75} Sections`;
                }
                if (elements.diagStagingEntries) {
                    elements.diagStagingEntries.textContent = `${(sData.record_count || 2682).toLocaleString()} Entries`;
                }
                if (elements.diagProductionStatus) {
                    elements.diagProductionStatus.textContent = sData.production_unaffected ? "100% Isolated" : "Check Needed";
                    elements.diagProductionStatus.className = sData.production_unaffected ? "diag-val text-green" : "diag-val text-amber";
                }
                if (elements.ttStagedSectionsCount) {
                    elements.ttStagedSectionsCount.textContent = String(sData.section_count || 75);
                }
                if (elements.ttStagedEntriesCount) {
                    elements.ttStagedEntriesCount.textContent = (sData.record_count || 2682).toLocaleString();
                }
                if (elements.timetableStagingStatusBadge) {
                    elements.timetableStagingStatusBadge.textContent = sData.status ? sData.status.replace("_", " ").toUpperCase() : "Pending Review";
                }
            }
        } catch (e) {
            console.warn("System diagnostics fetch issue:", e);
        }
    }

    /* ==========================================================================
       UTILITIES
       ========================================================================== */

    function escapeHtml(val) {
        return String(val || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    /* ==========================================================================
       EVENT LISTENERS & BINDINGS
       ========================================================================== */

    function bindEvents() {
        // Navigation Tabs
        elements.navTabs.forEach(tab => {
            tab.addEventListener("click", () => {
                const view = tab.dataset.view;
                if (view) showView(view);
            });
        });

        // Mobile Menu Toggle
        if (elements.mobileToggle && elements.sidebar) {
            elements.mobileToggle.addEventListener("click", () => {
                const isOpen = elements.sidebar.classList.toggle("open");
                elements.mobileToggle.setAttribute("aria-expanded", String(isOpen));
            });
        }

        // Header Profile Badge
        if (elements.headerProfileBadge) {
            elements.headerProfileBadge.addEventListener("click", () => showView("profile"));
        }

        // Dashboard Switchers
        elements.portalSwitches.forEach(btn => {
            btn.addEventListener("click", () => {
                const view = btn.dataset.switch;
                if (view) showView(view);
            });
        });

        if (elements.dashChangeProfileBtn) {
            elements.dashChangeProfileBtn.addEventListener("click", () => showView("profile"));
        }

        // Dashboard Search Bar
        if (elements.dashSearchBtn && elements.dashSearchInput) {
            const handleDashSearch = () => {
                const q = elements.dashSearchInput.value.trim();
                if (q) {
                    showView("chat");
                    sendMessage(q);
                    elements.dashSearchInput.value = "";
                }
            };
            elements.dashSearchBtn.addEventListener("click", handleDashSearch);
            elements.dashSearchInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    handleDashSearch();
                }
            });
        }

        // Suggested Question Chips
        elements.quickChips.forEach(chip => {
            chip.addEventListener("click", () => {
                const q = chip.dataset.query;
                if (q) {
                    showView("chat");
                    sendMessage(q);
                }
            });
        });

        // Timetable Dropdowns
        if (elements.ttBranchSelect) {
            elements.ttBranchSelect.addEventListener("change", () => {
                filterSectionsByBranch();
                loadTimetableData();
            });
        }
        if (elements.ttSectionSelect) {
            elements.ttSectionSelect.addEventListener("change", () => loadTimetableData());
        }
        if (elements.ttWeekdaySelect) {
            elements.ttWeekdaySelect.addEventListener("change", () => loadTimetableData());
        }
        if (elements.ttBatchSelect) {
            elements.ttBatchSelect.addEventListener("change", () => loadTimetableData());
        }
        if (elements.ttNextClassBtn) {
            elements.ttNextClassBtn.addEventListener("click", checkNextClass);
        }
        if (elements.closeNextClassResultBtn && elements.nextClassResultBox) {
            elements.closeNextClassResultBtn.addEventListener("click", () => {
                elements.nextClassResultBox.hidden = true;
            });
        }

        // Directory Search & Filters
        if (elements.directorySearchInput) {
            elements.directorySearchInput.addEventListener("input", filterFacilities);
        }
        elements.categoryPills.forEach(pill => {
            pill.addEventListener("click", () => {
                elements.categoryPills.forEach(p => {
                    p.classList.remove("active");
                    p.setAttribute("aria-checked", "false");
                });
                pill.classList.add("active");
                pill.setAttribute("aria-checked", "true");
                filterFacilities();
            });
        });

        // Chat Input & Enter key
        if (elements.sendButton) {
            elements.sendButton.addEventListener("click", () => sendMessage());
        }
        if (elements.messageInput) {
            elements.messageInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            elements.messageInput.addEventListener("input", () => {
                elements.messageInput.style.height = "auto";
                elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 120) + "px";
            });
        }
        if (elements.clearChatBtn) {
            elements.clearChatBtn.addEventListener("click", clearChatHistory);
        }
        if (elements.chatContextEditBtn) {
            elements.chatContextEditBtn.addEventListener("click", () => showView("profile"));
        }

        // Profile Form
        if (elements.profSection) {
            elements.profSection.addEventListener("input", validateProfileInput);
        }
        if (elements.profBranch) {
            elements.profBranch.addEventListener("change", validateProfileInput);
        }
        if (elements.profileForm) {
            elements.profileForm.addEventListener("submit", (e) => {
                e.preventDefault();
                state.profile.branch = elements.profBranch.value.trim().toUpperCase();
                state.profile.academic_year = parseInt(elements.profYear.value) || 1;
                state.profile.semester = parseInt(elements.profSemester.value) || 2;
                state.profile.section = elements.profSection.value.trim().toUpperCase();
                state.profile.batch = elements.profBatch.value.trim();
                saveProfile();

                if (elements.profileValidationBox) {
                    elements.profileValidationBox.className = "validation-feedback success";
                    elements.profileValidationText.textContent = "Academic profile updated and saved for this session.";
                }
            });
        }
        if (elements.resetProfileBtn) {
            elements.resetProfileBtn.addEventListener("click", () => {
                state.profile = {
                    branch: "ECE",
                    academic_year: 1,
                    semester: 2,
                    section: "1ECE02",
                    batch: "All"
                };
                saveProfile();
            });
        }

        // Diagnostics Refresh
        if (elements.refreshDiagnosticsBtn) {
            elements.refreshDiagnosticsBtn.addEventListener("click", fetchSystemHealth);
        }
    }

    /* ==========================================================================
       INITIALIZATION
       ========================================================================== */

    function init() {
        loadProfile();
        bindEvents();
        loadSectionsCatalog();
        fetchSystemHealth();
        showView("dashboard");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
