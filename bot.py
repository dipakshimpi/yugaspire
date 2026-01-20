import logging
import asyncio
import os
import json
import random
import re
from collections import Counter
from telegram import Update, Poll
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    CommandHandler,
    filters,
)

# ---------------------------------------------------------------------------
# CONFIGURATION & LOGGING
# ---------------------------------------------------------------------------

# Enable logging to see debug information in the console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# Replace None with your Group ID (integer) to forward files there.
# Example: TARGET_GROUP_ID = -100123456789
TARGET_GROUP_ID = -5206036224

# This dictionary is now only used for the fallback "Review/Approve/Reject" poll
poll_file_map = {}

# ---------------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------------

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when a user sends a file.
    1. Detects file type and metadata.
    2. Sends a non-anonymous poll.
    3. Stores the mapping between the new poll and the file.
    """
    message = update.message
    logging.info(f"Current Chat ID: {message.chat_id} (Type: {message.chat.type})")
    
    # 1. Detect File Type and Metadata
    file_id = None
    file_name = "Unknown Filename"
    file_type = "Unknown Type"
    
    if message.document:
        file_type = "Document"
        file_id = message.document.file_id
        file_name = message.document.file_name
    elif message.photo:
        file_type = "Photo"
        file_id = message.photo[-1].file_id # -1 is the highest resolution
        file_name = "Photo_Image.jpg" # Photos often don't have filenames
    elif message.video:
        file_type = "Video"
        file_id = message.video.file_id
        file_name = message.video.file_name or "Video.mp4"
    elif message.audio:
        file_type = "Audio"
        file_id = message.audio.file_id
        file_name = message.audio.file_name
    elif message.voice:
        file_type = "Voice Note"
        file_id = message.voice.file_id
        file_name = "Voice_Note.ogg"

    user = message.from_user
    logging.info(f"Received {file_type}: {file_name} from {user.first_name}")

    # 2. Determine where to send the poll (Private vs Group Forwarding)
    chat_id_to_send = message.chat_id
    reply_to_id = message.message_id

    # If sent in Private Chat AND we have a Target Group configured
    if message.chat.type == 'private' and TARGET_GROUP_ID:
        # Forward the file to the group so the poll makes sense there
        try:
            forwarded = await context.bot.forward_message(
                chat_id=TARGET_GROUP_ID,
                from_chat_id=message.chat_id,
                message_id=message.message_id
            )
            chat_id_to_send = TARGET_GROUP_ID
            reply_to_id = forwarded.message_id
        except Exception as e:
            logging.error(f"Failed to forward: {e}")
            return

    # 3. Send Non-Anonymous Poll
    questions = ["Review", "Approve", "Reject"]
    poll_message = await context.bot.send_poll(
        chat_id=chat_id_to_send,
        question="What do you want to do with this file?",
        options=questions,
        is_anonymous=False, # REQUIRED: Must be false to track who voted
        type=Poll.REGULAR,
        reply_to_message_id=reply_to_id
    )

    # 4. Store Metadata
    poll_id = poll_message.poll.id
    poll_file_map[poll_id] = {
        "file_name": file_name,
        "file_type": file_type,
        "uploader_id": user.id,
        "uploader_name": user.username or user.first_name,
        "chat_id": chat_id_to_send
    }

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when a user answers a poll.
    """
    answer = update.poll_answer
    poll_id = answer.poll_id
    user = answer.user
    selected_ids = answer.option_ids
    
    # Check if this poll is tracked by us
    if poll_id in poll_file_map:
        file_info = poll_file_map[poll_id]
        options_text = ["Review", "Approve", "Reject"]
        
        # Convert option IDs (0, 1, 2) to text
        selected_choices = [options_text[i] for i in selected_ids]
        action_string = ", ".join(selected_choices) if selected_choices else "Retracted Vote"

        # Log the response
        print(f"\n[POLL RESPONSE]")
        print(f"User:   {user.username or user.first_name} (ID: {user.id})")
        print(f"File:   {file_info['file_name']} ({file_info['file_type']})")
        print(f"Action: {action_string}")
        print("-" * 30)

async def get_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper command to get the Group ID easily."""
    await update.message.reply_text(f"The Group ID is: {update.effective_chat.id}")

async def handle_json_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Parses JSON text messages to generate polls.
    Expected format: [{"question": "...", "answer": "..."}, ...]
    """
    if update.message.chat.type != 'private':
        return

    text = update.message.text.strip()

    # Heuristic check: if it doesn't look like JSON, provide instructions and exit.
    if not text.startswith(('[', '{')):
        await update.message.reply_text(
            "Hi! To create a quiz, please paste your questions in a valid JSON format. "
            "I will ignore regular text messages."
        )
        return

    try:
        # Try parsing as JSON
        data = json.loads(text)
        
        questions = []
        if isinstance(data, list):
            questions = data
        elif isinstance(data, dict):
            if "questions" in data:
                questions = data["questions"]
            else:
                # Fallback: Look for any list in the dictionary values (e.g. "python_questions": [...])
                for value in data.values():
                    if isinstance(value, list):
                        questions = value
                        break
        
        if not questions:
            await update.message.reply_text("⚠️ The JSON appears valid, but I couldn't find a list of questions.")
            return

        if not TARGET_GROUP_ID:
            await update.message.reply_text("⚠️ Please configure TARGET_GROUP_ID in the code.")
            return

        await update.message.reply_text(f"⚙️ Processing {len(questions)} questions from JSON...")
        
        # Collect all answers for distractors
        all_answers = [q.get("answer") for q in questions if q.get("answer")]

        for q in questions:
            question_text = q.get("question")
            correct_answer = q.get("answer")
            
            if not question_text or not correct_answer:
                continue

            # Generate distractors
            distractors = list(set(all_answers) - {correct_answer})
            random.shuffle(distractors)
            options = [correct_answer] + distractors[:3]
            
            # Ensure at least 2 options
            while len(options) < 2:
                options.append("False" if correct_answer == "True" else "True")
                if len(options) < 2: options.append("Other")
            
            random.shuffle(options)
            correct_option_id = options.index(correct_answer)

            await context.bot.send_poll(
                chat_id=TARGET_GROUP_ID,
                question=question_text,
                options=options,
                type=Poll.QUIZ,
                correct_option_id=correct_option_id,
                is_anonymous=False
            )
        
        await update.message.reply_text("✅ All polls sent to the group!")

    except json.JSONDecodeError as e:
        # It looked like JSON but failed to parse. Give the user feedback.
        await update.message.reply_text(
            f"❌ **JSON Error**\n\nI could not parse the text. Please check your format for issues like trailing commas or incorrect quotes.\n\n*Details: `{e}`*"
        )

if __name__ == '__main__':
    TOKEN = "8565347213:AAEbUsyfPrcWBExTSDjE9pnCLsLdHO1Ibdo"

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("id", get_group_id))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_json_message))

    # Filter to accept almost any file type
    file_filter = filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE
    
    application.add_handler(MessageHandler(file_filter, handle_file_upload))
    application.add_handler(PollAnswerHandler(handle_poll_answer))

    print("Bot is running...")
    application.run_polling()