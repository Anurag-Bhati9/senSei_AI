🧠 SenSei AI: The Instant Study Assistant Telegram Bot



🚀 Project Overview



SenSei AI is an innovative Telegram bot designed to instantly transform any piece of text—lecture notes, document summaries, or direct questions—into comprehensive, actionable study materials. Our core mission is to automate the creation of high-quality quizzes and educational summaries, making learning faster and more efficient.



Tagline



Transform text into knowledge, instantly. Your notes, your personalized quiz master.



✨ Key Features



Instant Educational Answers: Provides a direct, concise, and structured answer for specific user queries (e.g., "What is Paging?").



Core Concept Extraction: Automatically identifies and extracts the 5 most critical terms or concepts from any provided text.



20-Question Practice Quizzes: Generates a full bank of multiple-choice questions (MCQ) for interactive practice directly within the Telegram chat interface.



PDF Study Guide Generation: Offers the option to download a complete, formatted PDF containing the entire 20-question quiz bank for offline studying or printing.



Stateful Sessions: Uses user-specific data persistence to ensure continuous and uninterrupted quiz sessions.



🛠️ Technology Stack (Assumed)



Core AI/LLM: Google Gemini API (for Academic Audit and content generation)



Platform: Python (Backend Logic)



Interface: Telegram Bot API



Database: Firestore (for state management and user data persistence)



🔄 Workflow: How SenSei AI Works



The project relies on a sophisticated Multi-Agent AI Framework to conduct a thorough "Academic Audit" on the user's input. The process is visualized below:



graph TD

&nbsp;   %% Define distinct styles for visual appeal

&nbsp;   classDef input fill:#4CAF50, color:#fff, stroke:#388E3C, stroke-width:2px;

&nbsp;   classDef processing fill:#FF9800, color:#000, stroke:#F57C00, stroke-width:2px;

&nbsp;   classDef output fill:#00BCD4, color:#000, stroke:#0097A7, stroke-width:2px;

&nbsp;   classDef decision fill:#8BC34A, stroke:#689F38, stroke-width:2px;

&nbsp;   classDef final fill:#607D8B, color:#fff, stroke:#455A64, stroke-width:2px;



&nbsp;   A\[User Sends Text or Question]:::input

&nbsp;   B(Telegram Bot Receives Input \& User ID):::input

&nbsp;   C{Academic Audit Initiated - Multi-Agent AI Framework}:::processing



&nbsp;   A -->|via Telegram| B

&nbsp;   B --> C



&nbsp;   %% Parallel Processing (The Core Audit)

&nbsp;   C --> D\[Generate Concise Educational Answer]:::processing

&nbsp;   C --> E\[Extract 5 Core Concepts (Keywords)]:::processing

&nbsp;   C --> F\[Generate 20-Question Quiz Bank (MCQ)]:::processing



&nbsp;   D \& E \& F --> G\[Aggregate Results \& Present Output Menu]:::output



&nbsp;   %% User Choice / Output Actions

&nbsp;   G --> H{Option 1: Start Interactive Quiz}:::decision

&nbsp;   G --> I{Option 2: Download PDF Study Guide}:::decision



&nbsp;   H --> J(Begin Quiz Session - Uses Data Persistence)

&nbsp;   I --> K(Deliver Complete PDF File to User)



&nbsp;   J --> L\[Study Complete / Session End]:::final

&nbsp;   K --> L



&nbsp;   subgraph User Experience Flow

&nbsp;       A

&nbsp;       B

&nbsp;       G

&nbsp;       H

&nbsp;       I

&nbsp;       L

&nbsp;   end



&nbsp;   subgraph AI Processing Engine

&nbsp;       C

&nbsp;       D

&nbsp;       E

&nbsp;       F

&nbsp;       J

&nbsp;       K

&nbsp;   end





⚙️ Setup and Installation



Prerequisites



Python 3.8+



A Telegram Bot Token (from BotFather)



A Google AI API Key



A Firestore Database configured for persistence



Installation Steps



Clone the Repository:



git clone \[https://github.com/Anurag-Bhati9/SenSei-AI.git](https://github.com/Anurag-Bhaati9/SenSei-AI.git)

cd SenSei-AI





Install Dependencies:



pip install -r requirements.txt





Configure Environment Variables:

Create a .env file in the root directory and add your credentials:



TELEGRAM\_BOT\_TOKEN="8595321662:AAHex5lZLQRSQDKm15rtEaHY7kdl9XncYWI"

GEMINI\_API\_KEY="AIzaSyByRHbJ0ap3x6tJ6iJafXmj9AQ9otU2NRI"







Run the Bot:



python main.py





📖 Usage



Open the Telegram application and find your bot.



Start a conversation using the /start command.



Paste any text (notes, articles, definitions) into the chat.



SenSei AI will process the text and immediately provide an educational summary and a menu offering two options:



Start Quiz: Begin the 20-question interactive MCQ session.



Get PDF: Receive the full quiz bank as a downloadable file.



Contact: GitHub : Anurag-Bhati9



