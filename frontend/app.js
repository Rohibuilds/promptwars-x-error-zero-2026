const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const messages = document.getElementById("messages");

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

    messages.scrollTop = messages.scrollHeight;
}


async function sendMessage() {

    const message = messageInput.value.trim();

    if (!message) {
        return;
    }

    addMessage(message, "user");

    messageInput.value = "";

    addMessage("NEXUS is thinking...", "nexus");

    try {

        const response = await fetch(API_URL, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })
        });


        const data = await response.json();


        const nexusMessages =
            document.querySelectorAll(".nexus-message");

        const thinkingMessage =
            nexusMessages[nexusMessages.length - 1];

        if (thinkingMessage) {
            thinkingMessage.remove();
        }


        addMessage(
            data.response,
            "nexus"
        );

    } catch (error) {

        const nexusMessages =
            document.querySelectorAll(".nexus-message");

        const thinkingMessage =
            nexusMessages[nexusMessages.length - 1];

        if (thinkingMessage) {
            thinkingMessage.remove();
        }

        addMessage(
            "Unable to connect to NEXUS backend.",
            "nexus"
        );

        console.error(error);
    }
}


sendButton.addEventListener(
    "click",
    sendMessage
);


messageInput.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {
            sendMessage();
        }

    }
);