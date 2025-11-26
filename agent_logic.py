# ==============================================================================
# ##############################################################################
# ######################### SEN SEI AI CORE LOGIC ############################
# ##############################################################################
# This file contains all AI logic, structured schemas, and PDF generation.

import os
import json
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional
import io
import logging

# --- PDF Generation Libraries ---
# NOTE: pip install reportlab
from reportlab.pdfgen import canvas 
from reportlab.lib.pagesizes import letter 

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================

# Load environment variables (must be run first to get keys)
load_dotenv() 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash" 

if not GEMINI_API_KEY:
    raise ValueError("FATAL ERROR: GEMINI_API_KEY is missing or invalid in .env")

# Initialize the Gemini Client once (CRITICAL: Client is capitalized)
client = genai.Client(api_key=GEMINI_API_KEY) 
logger = logging.getLogger(__name__)


# ==============================================================================
# 2. PYDANTIC SCHEMAS (Define structured output)
# ==============================================================================

class QuizQuestion(BaseModel):
    """A single multiple-choice question for the quiz bank or practice."""
    question_text: str = Field(description="The full text of the multiple-choice question.")
    options: List[str] = Field(description="List of 4 plausible answer options.")
    correct_answer: str = Field(description="The single correct answer text (must match one option).")
    
class CoreAudit(BaseModel):
    """Schema for the combined audit, quiz bank, and educational answer."""
    educational_answer: Optional[str] = Field(description="If the input was a direct question, provide a concise, high-quality educational answer here (max 5 sentences). If the input was notes, summarize the whole document.")
    title: str = Field(description="The concise, main title of the material.")
    core_concepts: List[str] = Field(description="A list of 5 critical technical or academic terms.")
    quiz_bank: List[QuizQuestion] = Field(description="A bank of 20 multiple-choice questions based on the input text and core concepts.")


# ==============================================================================
# 3. HELPER FUNCTION: PDF Generation
# ==============================================================================

def create_quiz_pdf(title: str, quiz_bank: List[dict]) -> bytes:
    """Generates a PDF document from the quiz bank in memory."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    line_height = 16
    margin = 72
    y = height - margin
    
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin, y, f"SenSei AI Quiz: {title}")
    y -= line_height * 2
    
    for i, quiz in enumerate(quiz_bank[:20]):
        if y < margin: 
            p.showPage()
            p.setFont("Helvetica-Bold", 18)
            p.drawString(margin, height - margin, f"{title} (Cont.)")
            y = height - margin - line_height * 2
            
        p.setFont("Helvetica-Bold", 10)
        # FIX: Access using dictionary notation []
        p.drawString(margin, y, f"{i+1}. {quiz['question_text']}") 
        y -= line_height
        
        # Draw options
        p.setFont("Helvetica", 9)
        # FIX: Access using dictionary notation []
        for option_index, option in enumerate(quiz['options']): 
            label = chr(65 + option_index) # A, B, C, D
            p.drawString(margin + 10, y, f"{label}. {option}")
            y -= line_height
            
        y -= line_height / 2 # Space between questions
            
    p.save()
    return buffer.getvalue()


# ==============================================================================
# 4. AGENT EXECUTION FUNCTION (The Core Logic - To be imported)
# ==============================================================================

def run_sensei_audit(input_text: str):
    """Runs the specialized AI agent to generate all required materials."""

    # --- AGENT PROMPT: Combined extraction, Q&A, and quiz generation ---
    AGENT_PROMPT = f"""
You are **SenSei AI**, a world-class educational agent. Your single task is to perform an immediate, thorough academic audit on the text provided below.

INSTRUCTIONS:
1.  Analyze the input. If it is a direct question (e.g., "What is ATP?"), use the `educational_answer` field to provide a concise, factual answer (max 5 sentences). If the input is a large document/notes, use the `summary` field.
2.  Identify exactly 5 core concepts.
3.  Generate a bank of exactly 20 diverse multiple-choice questions (`quiz_bank`) covering the entire input material. Each question must have 4 options and a single correct answer.

TEXT TO ANALYZE:
---
{input_text}
---
"""
    
    # 1. Run the unified agent
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=AGENT_PROMPT,
        config={"response_mime_type": "application/json", "response_schema": CoreAudit},
    )
    audit_result = json.loads(response.text)
    
    # 2. Generate the PDF
    # FIX: We ensure we pass a list of dictionaries to the PDF creator
    quiz_bank_as_dicts = [q for q in audit_result['quiz_bank']]
    pdf_bytes = create_quiz_pdf(audit_result['title'], quiz_bank_as_dicts)

    # 3. Format the final output structure
    final_output = {
        'audit': audit_result,
        # Store PDF data as bytes (encoded to latin1 for safe transfer)
        'pdf_data': pdf_bytes.decode('latin1'), 
        # Store full quiz bank JSON string for interactive use in the handler
        'quiz_questions_json': json.dumps(audit_result['quiz_bank'])
    }
    
    return final_output