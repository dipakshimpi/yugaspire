# Yugaspire Telegram Bot

A versatile Telegram bot built with `python-telegram-bot` designed to streamline file reviews and automate quiz generation for groups.

## Features

*   **File Review System**: Upload any file (Document, Photo, Video, Audio) to the bot. It forwards the file to a designated group and attaches a "Review/Approve/Reject" poll for team collaboration.
*   **Automated Quiz Generator**: Send a JSON-formatted list of questions to the bot in a private chat, and it will automatically generate and send quiz polls to your group.
*   **Group Management**: Includes a helper command `/id` to easily retrieve Group IDs for configuration.
*   **Poll Tracking**: Logs poll responses (User, File/Question, Action) to the console.

## Prerequisites

*   Python 3.10+
*   A Telegram Bot Token (from @BotFather)

## Installation

1.  **Clone the repository** (or download the files):
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Install dependencies**:
    ```bash
    pip install python-telegram-bot
    ```

## Configuration

1.  Open `bot.py`.
2.  **Set Bot Token**:
    Replace the token in the `__main__` block with your actual token:
    ```python
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    ```
3.  **Set Target Group**:
    To enable forwarding files and quizzes to a specific group, replace `TARGET_GROUP_ID` with your group's ID (integer):
    ```python
    TARGET_GROUP_ID = -100123456789
    ```
    *Tip: Add the bot to your group and send `/id` inside the group to find this number.*

## Usage

### Running the Bot
```bash
python bot.py
```

### 1. File Review
*   Send a file (PDF, Image, etc.) to the bot in a private chat.
*   The bot forwards it to the configured `TARGET_GROUP_ID` with a poll: "What do you want to do with this file?" (Review, Approve, Reject).

### 2. Quiz Generation
*   Send a JSON message to the bot in a private chat with the following structure:
    ```json
    {
      "questions": [
        {
          "question": "What is Python?",
          "answer": "A programming language."
        },
        {
          "question": "What is 2+2?",
          "answer": "4"
        }
      ]
    }
    ```
*   The bot will generate quiz polls for each question, creating distractors (wrong answers) automatically from the other answers in the list.

## Contributing

Contributions are welcome! Please fork the repository and submit a Pull Request.
