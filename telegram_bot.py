import os
from venv import logger
from telegram import ( Update)
from telegram.ext import (Application,CallbackQueryHandler,CommandHandler,ContextTypes,ConversationHandler,MessageHandler,filters)

TELEGRAM_BOT_TOKEN="8595321662:AAGH5a-4aHFZ5yd0lupGN6pFlbJYiPMEZC8"
SAMPLE_TEXT = ""
INPUT = range(1)

# ==============================================================================
# ASYNCHRONOUS HANDLERS (Telegram Interaction) - MUST BE PRESENT
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the welcome message when the /start command is issued."""
    welcome_text = (
        '🎉 *Welcome to SenSei AI!* 🎉\n\n'
        'I am your multi-agent study buddy. To start, please send me any text '
        'from your lecture notes, book, or article. I will instantly perform '
        'a 3-step audit and send you study materials!'
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages, runs the AI agent, and replies."""
    
    user_text = update.message.text
    
    # 1. Send a confirmation/typing indicator while the agent works
    await update.message.reply_text("🧠 Analyzing your note response with SenSei AI... please wait.")
    
    try:
        # 2. RUN THE AGENT CHAIN on the live user input
        from agent_logic import run_sensei_audit # Local import is OK here
        final_audit = run_sensei_audit(user_text)

        # 3. Format the output from the final JSON result
        title = final_audit['academicAudit']['title']
        summary = final_audit['academicAudit']['summary']
        critique = final_audit['academicAudit']['criticalReview']['feedback']
        
        # 4. Construct the final reply text using Markdown for formatting
        response_text = (
            f"✅ *AUDIT COMPLETE: {title}*\n\n"
            f"⭐ *Peer Tutor Summary:*\n{summary}\n\n"
            f"📝 *Professor's Critique:*\n{critique}\n\n"
            f"_You have {len(final_audit['academicAudit']['studyMaterials']['flashcards'])} Flashcards and 3 Quizzes created!_"
        )

        # 5. Send the final reply
        await update.message.reply_text(response_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Agent Execution Error: {e}") 
        error_message = f"🛑 *Error Processing Request:* I ran into a problem while analyzing the text. Please check your text length and try again. Ensure your Gemini API Key is valid."
        await update.message.reply_text(error_message, parse_mode='Markdown')

# ==============================================================================
# MAIN FUNCTION (The entry point) - REMAINS THE SAME AS YOU HAD IT
# ==============================================================================
# def main() -> None: ...

# ==============================================================================
# 4. TELEGRAM HANDLERS (Finalized Main Function)
# ==============================================================================



# --- Final Main Function ---
def main() -> None:
    """Initializes and starts the bot using long polling."""
    # We load the token outside of main, but check it here:
    if not TELEGRAM_BOT_TOKEN:
         raise ValueError("TELEGRAM_BOT_TOKEN not found. Please check your .env file.")

    # 1. Create the Application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 2. Register handlers for commands and messages (SIMPLE HANDLERS ONLY)
    # The /start command is handled by start_command
    application.add_handler(CommandHandler("start", start_command))
    
    # All non-command text messages are handled by handle_message (which runs the AI)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. Start the bot (runs continuously)
    print("🤖 SenSei AI Bot is starting...")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    # This block starts the bot and keeps the script running continuously
    main()