# ==============================================================================
# ##############################################################################
# ####################### TELEGRAM HANDLER CODE ################################
# ##############################################################################
# This file manages the Telegram interaction, imports the core logic, and handles 
# interactive state and button presses.

import os
import logging
import json
import io
import random
import re 
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler)
from typing import List

# --- IMPORT THE CORE AI FUNCTION ---
from agent_logic import run_sensei_audit, client, MODEL_NAME 

# --- CONFIGURATION & SETUP ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Global storage for quiz data: {chat_id: {audit: {}, full_quiz_bank: [...], current_index: 0}}
USER_DATA_STORE = {} 

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def safe_markdown_format(text: str) -> str:
    """
    Cleans up potentially dangerous AI formatting characters (like # or *)
    and converts them to simple, safe Telegram Markdown, ensuring stability.
    """
    # 1. Escape characters that MUST be escaped in Telegram Markdown V2 (or V1)
    text = re.sub(r'([_\*\[\]\(\)~`>#\+\-=\|\{\}\.!])', r'\\\1', text)
    # 2. Convert newlines to double newlines for paragraph breaks
    text = text.replace('\n', '\n\n')
    
    # Final cleanup: reduce multiple newlines to max two.
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def get_main_menu_keyboard():
    """Generates the main menu keyboard shown after the audit."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Download Full Quiz PDF (20 Qs)", callback_data="download_pdf")],
        [InlineKeyboardButton("🧠 Start Practice Quiz (All 20 Qs)", callback_data="start_quiz")] 
    ])

def get_random_practice_questions(quiz_bank: list, count: int = 5):
    """Selects a small number of random questions for the interactive practice quiz."""
    if not isinstance(quiz_bank, list) or not quiz_bank:
        return []
    quiz_dicts = [q for q in quiz_bank if isinstance(q, dict)]
    
    # We will use ALL questions now, not just a sample of 5
    return quiz_dicts 

def get_question_keyboard(question_data: dict):
    """Generates the keyboard for a single multiple-choice question, including the stop button."""
    options = question_data['options']
    
    keyboard = []
    random.shuffle(options) 
    
    for option in options:
        # Callback data format: check_answer|{correct_answer}|{user_choice}
        callback_data = f"check_answer|{question_data['correct_answer']}|{option}"
        keyboard.append([InlineKeyboardButton(option, callback_data=callback_data)])
    
    # NEW: Add the stop button below the options
    keyboard.append([InlineKeyboardButton("🛑 Stop Practice Quiz", callback_data="stop_quiz")])
        
    return InlineKeyboardMarkup(keyboard)

# ==============================================================================
# ASYNCHRONOUS HANDLERS (Telegram Interaction)
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the welcome message when the /start command is issued."""
    welcome_text = (
        '🎉 *Welcome to SenSei AI!* 🎉\n\n'
        'I am your multi-agent study buddy. To start, please send me any text '
        'from your lecture notes, book, or article. I will instantly perform '
        'a full audit and generate study materials!'
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text, runs the AI agent, and provides options."""
    
    user_text = update.message.text.strip()
    chat_id = update.message.chat_id
    
    # --- Intent Detection & Greeting ---
    
    # Intent 1: Polite Greeting
    if len(user_text.split()) < 3 and user_text.lower() in ["hi", "hello", "hey", "hlo"]:
        await update.message.reply_text("Hello! I'm SenSei AI. Send me notes or ask a specific question to get started.")
        return

    # Intent 2: Ask for Practice/More Questions (Check if data exists first)
    if re.search(r"(practice|more questions|next question|quiz)", user_text, re.IGNORECASE):
        user_state = USER_DATA_STORE.get(chat_id)
        if user_state and user_state.get('full_quiz_bank'):
            await handle_quiz_start(update, context)
            return
        else:
            await update.message.reply_text("I don't have study materials yet! Please send me the notes or article you want to analyze first.")
            return

    # Intent 3: Catch-all for short, non-recognized input (Fallback to help message)
    if len(user_text.split()) < 4:
        await update.message.reply_text(
            "*I'm sorry, I need more text.* To use SenSei AI, please send your full *notes or article* or ask a detailed question (e.g., 'What is paging and segmentation?')."
        )
        return


    # --- Standard Audit Flow (This runs for all other inputs, including questions) ---
    
    # 1. Send the typing action while the agent works
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    try:
        # 2. RUN THE AGENT CHAIN on the live user input (The Brain Runs!)
        final_output = run_sensei_audit(user_text)
        
        # Safely retrieve audit data using .get() to prevent KeyError crashes
        audit = final_output.get('audit', {}) 
        
        # Safely load the full quiz bank
        quiz_json_str = final_output.get('quiz_questions_json', '[]')
        
        # CRITICAL: Ensure full_quiz_bank_list is populated correctly.
        try:
            full_quiz_bank_list = json.loads(quiz_json_str)
        except json.JSONDecodeError:
            logger.error(f"JSON Decode Error on quiz bank: {quiz_json_str[:100]}...")
            full_quiz_bank_list = []
            
        # Store state for interactive quiz and PDF sending (now storing ALL 20 Qs)
        USER_DATA_STORE[chat_id] = {
            'audit': audit,
            'full_quiz_bank': full_quiz_bank_list, # Store all 20 for iteration
            'current_index': 0,
            'pdf_data': final_output.get('pdf_data', '')
        }

        # Determine the primary text to show (Q&A or Summary)
        educational_answer = audit.get('educational_answer')
        summary = audit.get('summary')
        title = audit.get('title', 'Academic Topic')
        core_concepts = audit.get('core_concepts', [])
        
        # Robustly prioritize Educational Answer for short inputs (questions)
        if educational_answer and len(user_text.split()) < 15:
            # Display the direct answer 
            primary_text = f"💡 *Educational Answer:*\n{safe_markdown_format(educational_answer)}" # FIX: Now uses the educational_answer
            
        elif summary:
            primary_text = f"⭐ *Document Summary:*\n{safe_markdown_format(summary)}"
        else:
             primary_text = "*The AI could not generate a specific summary or answer for this input, but core concepts were extracted.*"


        # 3. Construct the final reply text
        response_text = (
            f"✅ *AUDIT COMPLETE: {title}*\n\n"
            f"{primary_text}\n\n"
            f"🎯 *Core Concepts Extracted:*\n— {', '.join(core_concepts)}\n\n"
            f"Your study materials are ready! ({len(full_quiz_bank_list)} Questions Generated)"
        )

        # 4. Send the final reply with the interactive keyboard
        await update.message.reply_text(response_text, 
                                        parse_mode='Markdown', 
                                        reply_markup=get_main_menu_keyboard())

    except Exception as e:
        logger.error(f"Agent Execution Error: {e}") 
        error_message = f"🛑 *Error:* SenSei AI failed to generate content. Please check the text or try again. (Internal Error: {type(e).__name__})"
        await update.message.reply_text(error_message, parse_mode='Markdown')


# ==============================================================================
# CALLBACK HANDLERS (Interactive Quizzing and PDF)
# ==============================================================================

async def send_next_practice_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the next question in the practice quiz sequence (Iterates through all 20)."""
    
    chat_id = update.effective_chat.id
    user_state = USER_DATA_STORE.get(chat_id)
    
    if not user_state:
        await context.bot.send_message(chat_id, "Quiz data expired. Please send new notes to start a practice quiz.")
        return

    current_index = user_state['current_index']
    # NEW: Use the full quiz bank (20 questions)
    practice_qs = user_state['full_quiz_bank']
    
    if current_index >= len(practice_qs):
        # Quiz is finished after all 20 questions
        await context.bot.send_message(chat_id, "🎉 *Practice Quiz Finished!* You completed all 20 questions. Excellent work.", parse_mode='Markdown')
        # Clear state after completion
        del USER_DATA_STORE[chat_id]
        return

    question_data = practice_qs[current_index]
    total_qs = len(practice_qs)
    
    question_text = f"❓ *Practice Q{current_index + 1}/{total_qs}:*\n{question_data['question_text']}"
    
    await context.bot.send_message(chat_id, 
                                   question_text, 
                                   parse_mode='Markdown', 
                                   reply_markup=get_question_keyboard(question_data))


async def handle_quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for starting the interactive practice quiz."""
    query = update.callback_query
    # Check if this handler was called by a button press or an inline command
    if query:
        await query.answer()
        chat_id = query.message.chat_id
    else:
        # Called by text input (e.g., "practice")
        chat_id = update.message.chat_id
    
    user_state = USER_DATA_STORE.get(chat_id)
    
    if not user_state or not user_state.get('full_quiz_bank'):
        await context.bot.send_message(chat_id, "Quiz data is unavailable. Please send new notes to perform an audit and generate a quiz bank first.")
        return

    # Reset index and get the first practice question
    USER_DATA_STORE[chat_id]['current_index'] = 0
    
    # Send a confirmation message for the start of the full quiz
    await context.bot.send_message(chat_id, 
                                   "🚀 Starting the full 20-question practice session. Click 'Stop Quiz' anytime to exit.",
                                   parse_mode='Markdown')
    
    await send_next_practice_question(update, context)


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks the user's answer and progresses the quiz."""
    query = update.callback_query
    
    # Parse the data from the button callback: check_answer|{correct_answer}|{user_choice}
    parts = query.data.split('|')
    correct_answer = parts[1]
    user_choice = parts[2]
    
    is_correct = (user_choice == correct_answer)
    
    # Determine the response emoji and feedback message
    feedback_text = "🎯 *Correct!*" if is_correct else f"❌ *Incorrect.* The answer was: *{correct_answer}*"
    
    # Show the user the result by answering the query
    await query.answer(feedback_text, show_alert=True)
    
    # Edit the question message to show the final result and remove buttons
    await query.edit_message_text(f"{query.message.text}\n\n{feedback_text}", 
                                  parse_mode='Markdown', 
                                  reply_markup=None) 
    
    # Update state and send next question if available
    chat_id = query.message.chat_id
    user_state = USER_DATA_STORE.get(chat_id)
    
    if user_state:
        current_index = user_state['current_index']
        USER_DATA_STORE[chat_id]['current_index'] = current_index + 1
        await send_next_practice_question(update, context)


async def handle_pdf_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the request to download the PDF."""
    query = update.callback_query
    await query.answer("Generating your full PDF Quiz...")
    
    chat_id = query.message.chat_id
    user_state = USER_DATA_STORE.get(chat_id)
    
    if not user_state or not user_state.get('pdf_data'):
        await context.bot.send_message(chat_id, "Error: Quiz data expired. Please analyze new text first.")
        return

    # Decode the pdf_data string back into bytes
    pdf_bytes = user_state['pdf_data'].encode('latin1')
    
    # Send the PDF file directly to the user
    await context.bot.send_document(
        chat_id=chat_id,
        document=io.BytesIO(pdf_bytes),
        filename=f"SenSei_AI_Quiz_{user_state['audit']['title'].replace(' ', '_')}.pdf",
        caption="Here is your full 20-question practice PDF!"
    )

async def handle_quiz_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the stop quiz button press and gracefully exits the practice mode."""
    query = update.callback_query
    await query.answer("Practice quiz stopped.")
    
    chat_id = query.message.chat_id
    
    # Remove the buttons from the current question message
    await query.edit_message_text(f"{query.message.text}\n\n*🛑 Practice Quiz Stopped.*", 
                                  parse_mode='Markdown', 
                                  reply_markup=None)
    
    # Send a final friendly message
    await context.bot.send_message(chat_id, "You have exited the practice quiz. Send new notes anytime to start another audit!")
    
    # Clear the user's state to prevent errors on next run
    if chat_id in USER_DATA_STORE:
        del USER_DATA_STORE[chat_id]
    
# ==============================================================================
# MAIN FUNCTION (Entry point)
# ==============================================================================

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
         raise ValueError("TELEGRAM_BOT_TOKEN not found. Please check your .env file.")

    # We must ensure the client is initialized, which happens when agent_logic is imported.
    try:
        from agent_logic import client # Check for client existence
    except Exception as e:
        # If the client cannot be imported, crash with a helpful error
        raise RuntimeError(f"Failed to initialize AI Client from agent_logic.py: {e}")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_handler(CallbackQueryHandler(handle_pdf_download, pattern='^download_pdf$'))
    application.add_handler(CallbackQueryHandler(handle_quiz_start, pattern='^start_quiz$'))
    application.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern='^check_answer'))
    application.add_handler(CallbackQueryHandler(handle_quiz_stop, pattern='^stop_quiz$'))
    

    print("🤖 SenSei AI Bot is starting... (Press Ctrl+C to stop)")
    application.run_polling(poll_interval=1.0) 

if __name__ == '__main__':
    main()