const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const messages = document.getElementById("messages");
const activity = document.getElementById("activity");

const quickCards = document.querySelectorAll(".quick-card");

const API_URL = "http://127.0.0.1:8000/chat";


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

    message.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });

    return message;
}


function setActivity(text) {

    activity.innerHTML = `
        <div class="activity-empty">
            <span>◉</span>
            ${text}
        </div>
    `;
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


    setActivity("NEXUS is understanding the task...");


    const thinkingMessage =
        addMessage(
            "NEXUS is thinking...",
            "nexus"
        );


    try {

        setActivity("Selecting the best tool...");


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


        setActivity("Task completed successfully");


        addMessage(
            data.response ||
            "NEXUS completed the task.",
            "nexus"
        );


    } catch (error) {

        console.error(error);


        thinkingMessage.remove();


        setActivity("Unable to complete the task");


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