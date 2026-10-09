const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const messages = document.getElementById("messages");
const activity = document.getElementById("activity");

const quickCards = document.querySelectorAll(".quick-card");

const API_URL = "/chat";


function addMessage(text, type) {

    const message = document.createElement("div");

    message.classList.add(
        "message",
        type === "user"
            ? "user-message"
            : "nexus-message"
    );

    message.textContent = text;

    messages.appendChild(message);

    if (type !== "user") {
        const announcer = document.getElementById("liveAnnouncer");
        if (announcer) {
            announcer.textContent = text;
        }
    }

    requestAnimationFrame(function() {
        const workspace = messages.closest(".workspace");

        if (workspace) {
            workspace.scrollTo({
                top: workspace.scrollHeight,
                behavior: "smooth"
            });
        }
    });

    return message;
}


function setActivity(text) {

    activity.innerHTML = `
        <div class="activity-empty">
            <span aria-hidden="true">◉</span>
            ${escapeHtml(text)}
        </div>
    `;
}


function showAgentActivity(tool) {

    const toolNames = {
        knowledge_search: "KNOWLEDGE SEARCH",
        calculator: "CALCULATOR",
        system_status: "SYSTEM STATUS"
    };

    const toolName =
        toolNames[tool] || "GENERAL AGENT";


    activity.innerHTML = `
        <div class="activity-empty">
            <span>◉</span>
            Task received
        </div>

        <div class="activity-empty">
            <span>◉</span>
            Understanding request
        </div>

        <div class="activity-empty">
            <span>◉</span>
            Tool selected:
            <strong>${toolName}</strong>
        </div>

        <div class="activity-empty">
            <span>◉</span>
            Executing ${toolName.toLowerCase()}
        </div>

        <div class="activity-empty">
            <span>◉</span>
            Task completed
        </div>
    `;
}


function addActivityHistory(message, tool, response) {

    const history =
        document.getElementById("activityHistory");

    if (!history) {
        return;
    }

    const empty =
        history.querySelector(".activity-empty-history");

    if (empty) {
        empty.remove();
    }

    const item =
        document.createElement("div");

    item.className = "workspace-card activity-history-item";

    const toolName =
        tool || "GENERAL AGENT";

    item.innerHTML = `
        <div class="activity-history-icon">●</div>

        <div class="activity-history-content">
            <strong>TASK COMPLETED</strong>

            <p>${escapeHtml(message)}</p>

            <span>
                Tool: ${escapeHtml(toolName)}
            </span>

            <small>
                ${escapeHtml(response || "Task completed successfully")}
            </small>
        </div>
    `;

    history.prepend(item);
}


function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


async function sendMessage(customMessage = null) {

    const message =
        customMessage ||
        messageInput.value.trim();

    if (!message) {
        return;
    }


    addMessage(message, "user");

    messageInput.value = "";


    setActivity(
        "NEXUS is understanding the task..."
    );


    const thinkingMessage =
        addMessage(
            "NEXUS is thinking...",
            "nexus"
        );


    try {

        setActivity(
            "Selecting the best tool..."
        );


        const response = await fetch(
            API_URL,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    message: message
                })
            }
        );


        if (!response.ok) {

            throw new Error(
                `Server returned ${response.status}`
            );

        }


        const data =
            await response.json();


        thinkingMessage.remove();


        showAgentActivity(
            data.tool
        );


        addMessage(
            data.response ||
            "NEXUS completed the task.",
            "nexus"
        );

        addActivityHistory(
            message,
            data.tool,
            data.response
        );


    } catch (error) {

        console.error(error);


        thinkingMessage.remove();


        setActivity(
            "Unable to complete the task"
        );


        addMessage(
            "I couldn't connect to the NEXUS agent. Please make sure the backend server is running.",
            "nexus"
        );

    }

}


/* SEND BUTTON */

sendButton.addEventListener(
    "click",
    () => sendMessage()
);


/* ENTER KEY */

messageInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {

            event.preventDefault();

            sendMessage();

        }

    }
);


/* QUICK ACTIONS */

quickCards.forEach(
    function(card) {

        card.addEventListener(
            "click",
            function() {

                const message =
                    card.dataset.message;

                sendMessage(message);

            }
        );

    }
);


/* INITIAL STATE */

setActivity(
    "Ready for a task"
);


/* WORKSPACE NAVIGATION */

const navItems = document.querySelectorAll(".nav-item");

const assistantView = document.getElementById("assistantView");
const toolsView = document.getElementById("toolsView");
const knowledgeView = document.getElementById("knowledgeView");
const activityView = document.getElementById("activityView");


function showWorkspaceView(view) {

    if (assistantView) {
        assistantView.hidden = view !== "assistant";
    }

    if (toolsView) {
        toolsView.hidden = view !== "tools";
    }

    if (knowledgeView) {
        knowledgeView.hidden = view !== "knowledge";
    }

    if (activityView) {
        activityView.hidden = view !== "activity";
    }

}


navItems.forEach(function(item) {

    item.addEventListener("click", function() {

        navItems.forEach(function(nav) {
            nav.classList.remove("active");
            nav.removeAttribute("aria-current");
        });

        item.classList.add("active");
        item.setAttribute("aria-current", "page");

        const view = item.dataset.view;

        showWorkspaceView(view);

        if (view === "assistant") {
            setActivity("Ready for a task");
        }

        if (view === "tools") {
            setActivity("Tools available: Knowledge Search, Calculator, System Status");
        }

        if (view === "knowledge") {
            setActivity("Knowledge base connected and ready");
        }

        if (view === "activity") {
            setActivity("Agent activity monitoring enabled");
        }

    });

});


showWorkspaceView("assistant");
