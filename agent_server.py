# ==============================================================================
# 1. IMPORTS & CONFIGURATION (Final Deployment Script)
# ==============================================================================
import os
import json
import requests
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from typing import List
from flask import Flask, request, jsonify # Essential for the web server

# --- Load Environment Variables (.env file) ---
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- Client Setup (CRITICAL: Client is capitalized) ---
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

client = genai.Client(api_key=GEMINI_API_KEY) 
MODEL_NAME = "gemini-2.5-flash" 

# URL structure for sending messages back to the Telegram API
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ==============================================================================
# 2. PYDANTIC SCHEMAS (Complete structures for Agents 1, 2, and 3)
# ==============================================================================

class ConceptExtraction(BaseModel):
    title: str = Field(description="The concise, main title of the material.")
    summary: str = Field(description="A friendly, peer-tutor style summary.")
    core_concepts: List[str] = Field(description="List of 5 most critical technical terms.")

class Flashcard(BaseModel):
    concept: str = Field(description="The academic term/concept name.")
    definition: str = Field(description="A concise, simple explanation.")

class QuizQuestion(BaseModel):
    question: str = Field(description="The question based on the concept.")
    options: List[str] = Field(description="List of 4 plausible answer options.")
    correct_answer: str = Field(description="The single correct answer text.")

class StudyMaterial(BaseModel):
    flashcards: List[Flashcard] = Field(description="Exactly 5 flashcards.")
    quiz_questions: List[QuizQuestion] = Field(description="Exactly 3 multiple-choice questions.")

class CriticalReview(BaseModel):
    critique_persona: str = Field(description="The persona Agent 3 adopted.")
    feedback: str = Field(description="A short (3-4 sentence) constructive critique.")


# ==============================================================================
# 3. AGENT EXECUTION FUNCTION (The Core Logic)
# ==============================================================================

def run_sensei_audit(input_text: str):
    """Runs the full 3-step agentic workflow using the user's input."""

    # --- AGENT 1: Core Concept Extractor ---
    AGENT_1_PROMPT = f"""
You are **SenSei AI's Core Concept Extractor**, acting as a friendly, expert peer tutor. Your sole purpose is to analyze the text provided below, make it immediately understandable, and extract the absolute fundamentals into the required JSON format.
RULES:
1. Your summary must be simple, encouraging, and focused on "what matters for the exam."
2. You must identify exactly 5 critical terms/concepts.
TEXT TO ANALYZE:
---
{input_text}
---
"""
    
    response_1 = client.models.generate_content(
        model=MODEL_NAME, contents=AGENT_1_PROMPT, 
        config={"response_mime_type": "application/json", "response_schema": ConceptExtraction},
    )
    agent_1_result = json.loads(response_1.text)
    
    # --- AGENT 2: Study Material Generator ---
    concepts_list_str = ', '.join(agent_1_result['core_concepts'])
    AGENT_2_PROMPT = f"""
You are **SenSei AI's Study Material Generator**. Your task is to create focused study materials based **ONLY** on the following list of concepts. You must adhere strictly to the JSON schema.
Concepts to Base Materials On:
---
{concepts_list_str}
---
Your Output Requirements:
1.  Generate exactly 5 flashcards, one for each concept provided.
2.  Generate exactly 3 multiple-choice questions that test knowledge of these concepts.
"""

    response_2 = client.models.generate_content(
        model=MODEL_NAME, contents=AGENT_2_PROMPT,
        config={"response_mime_type": "application/json", "response_schema": StudyMaterial},
    )
    agent_2_material = json.loads(response_2.text)
    
    # --- AGENT 3: Critical Reviewer ---
    AGENT_3_PROMPT = f"""
You are **SenSei AI's Critical Reviewer**, acting as a highly experienced, slightly stern but fair University Professor. Your task is to perform a final audit on the original source material and its suitability for study.
RULES:
1.  Adopt the persona of a Professor.
2.  Your output must be a constructive critique, 3-4 sentences long.
3.  Critique the **original text** (provided below), assessing its clarity, use of jargon, and difficulty level for a new student. Do NOT critique the flashcards or quizzes.
ORIGINAL TEXT TO CRITIQUE:
---
{input_text}
---
"""
    response_3 = client.models.generate_content(
        model=MODEL_NAME, contents=AGENT_3_PROMPT,
        config={"response_mime_type": "application/json", "response_schema": CriticalReview},
    )
    agent_3_critique = json.loads(response_3.text)

    # --- FINAL MERGE ---
    final_result = {
        'academicAudit': {
            'title': agent_1_result['title'],
            'summary': agent_1_result['summary'],
            'core_concepts': agent_1_result['core_concepts'],
            'studyMaterials': agent_2_material,
            'criticalReview': agent_3_critique,
        }
    }
    return final_result


# ==============================================================================
# 4. WEB SERVER HOOK (Receives Telegram input and replies)
# ==============================================================================
app = Flask(__name__)

def send_telegram_message(chat_id, text):
    """Sends a simple text message reply back to the user."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    # Send the request back to Telegram
    requests.post(url, json=payload)


@app.route('/', methods=['POST'])
def webhook():
    # Extracts data from the Telegram JSON Webhook
    update = request.get_json()

    if update and 'message' in update and 'text' in update['message']:
        chat_id = update['message']['chat']['id']
        user_text = update['message']['text']
        
        # 1. RUN THE AGENT CHAIN on the live user input
        final_audit = run_sensei_audit(user_text)

        # 2. Format the output
        title = final_audit['academicAudit']['title']
        summary = final_audit['academicAudit']['summary']
        critique = final_audit['academicAudit']['criticalReview']['feedback']
        
        response_text = (
            f"🧠 *SenSei AI Audit Complete: {title}*\n\n"
            f"⭐ *Peer Tutor Summary:*\n{summary}\n\n"
            f"📝 *Professor's Critique:*\n{critique}\n\n"
            f"_{len(final_audit['academicAudit']['studyMaterials']['flashcards'])} Flashcards and 3 Quizzes created!_"
        )

        # 3. Send the reply
        send_telegram_message(chat_id, response_text)

    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    print("Starting Flask Webhook Server on port 5000...")
    app.run(host='0.0.0.0', port=5000)