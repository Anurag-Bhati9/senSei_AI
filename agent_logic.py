# ==============================================================================
# 1. IMPORTS & CONFIGURATION
# This code is designed to run in a serverless environment (like Cloudflare/Flask)
# where keys are provided securely via environment variables.
# ==============================================================================
import os
import json
from venv import logger
from google import genai
from pydantic import BaseModel, Field
from typing import List

# NOTE: In a real server (like Cloudflare), the API key is automatically available 
#       in the environment variables. We assume it is set here.
# NOTE: The client initialization should be outside the main function for efficiency.
# The fixed capitalization is CRITICAL here: genai.Client()
# The fixed capitalization is CRITICAL here: genai.Client()

# --- EXPLICITLY DEFINE THE KEY FIRST ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
if not GEMINI_API_KEY:
    raise ValueError("FATAL ERROR: Gemini API Key is missing or invalid in .env")



# The fixed capitalization is CRITICAL here: genai.Client()
client = genai.Client(api_key="GEMINI_API_KEY") 
MODEL_NAME = "gemini-2.5-flash" 

# --- DEBUGGING CODE: CHECK API KEY VALIDITY ---
try:
    # Attempt a very fast, basic request to ensure the key is accepted
    response = client.models.generate_content(
        model=MODEL_NAME, 
        contents="Say 'OK'",
        config={"max_output_tokens": 1}
    )
    # If the response is successful, the key is good.
    if response.text.strip():
        logger.info("--- DIAGNOSTIC: Gemini API Key is valid and accessible. ---")
    else:
        # Should not happen with this prompt, but checks for empty response
        logger.warning("--- DIAGNOSTIC: Key connected but received empty response. ---")

except Exception as e:
    # If a major error occurs (like 403 Permission Denied), the connection fails here.
    logger.error(f"--- DIAGNOSTIC: FATAL API CONNECTION ERROR --- Error: {e}")
    # We re-raise the exception to crash the bot and stop it from running expensive tasks.
    raise RuntimeError("Critical Gemini API connection failure. Please check your API key status.")

# --- END DEBUGGING CODE ---

# --- Sample Input Text (For local testing only) ---
SAMPLE_TEXT = """
The human body uses two primary energy systems during exercise: the aerobic and anaerobic systems.
The anaerobic (without oxygen) system is split into the ATP-PC system, used for short, explosive movements lasting 1-10 seconds (like sprinting or lifting heavy weights), and the glycolytic system, which produces energy from glucose for efforts lasting between 10 seconds and 2 minutes. This system produces lactic acid as a byproduct.
The aerobic (with oxygen) system, also known as oxidative phosphorylation, is used for long-duration activities like marathon running. It relies on a steady supply of oxygen to break down carbohydrates and fats, providing a continuous, but slower, energy supply. The body will always use the aerobic system for rest and low-intensity exercise.
"""


# ==============================================================================
# 2. PYDANTIC SCHEMAS (Agent 1, 2, and 3 Output Structures)
# ==============================================================================

# Agent 1 Schema
class ConceptExtraction(BaseModel):
    title: str = Field(description="The concise, main title of the material.")
    summary: str = Field(description="A friendly, peer-tutor style summary.")
    core_concepts: List[str] = Field(description="List of 5 most critical technical terms.")

# Agent 2 Schemas
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

# Agent 3 Schema
class CriticalReview(BaseModel):
    critique_persona: str = Field(description="The persona Agent 3 adopted.")
    feedback: str = Field(description="A short (3-4 sentence) constructive critique.")


# ==============================================================================
# 3. AGENT EXECUTION FUNCTION (Takes user input and returns final JSON)
# ==============================================================================

def run_sensei_audit(input_text: str):
    """Runs the full 3-step agentic workflow and returns the final merged JSON."""

    # --- AGENT 1: Core Concept Extractor ---
    AGENT_1_PROMPT = f"""... [AGENT 1 PROMPT TEXT GOES HERE, reference the 'input_text'] ..."""
    
    # NOTE: To keep the code clean for transfer, we are using the generic prompt placeholder.
    # You must paste the full AGENT_1_PROMPT content (including the f-string) from Colab here.
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
        model=MODEL_NAME,
        contents=AGENT_1_PROMPT,
        config={"response_mime_type": "application/json", "response_schema": ConceptExtraction},
    )
    agent_1_result = json.loads(response_1.text)
    
    # --- AGENT 2: Study Material Generator ---
    concepts_for_agent_2 = agent_1_result['core_concepts']
    concepts_list_str = ', '.join(concepts_for_agent_2)

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
        model=MODEL_NAME,
        contents=AGENT_2_PROMPT,
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
        model=MODEL_NAME,
        contents=AGENT_3_PROMPT,
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
