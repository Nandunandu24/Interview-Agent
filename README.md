# HireAI: Intelligent Structured Interview Agent

An autonomous AI Interview Agent that conducts structured mock technical interviews end-to-end. It runs entirely locally or on free tiers using **FastAPI**, and is designed to work **completely without API keys** in a robust, offline mock mode. When API keys are provided for **Groq** or **Google Gemini**, the FastAPI server acts as a gateway to these models for dynamic technical evaluations.

The app supports voice synthesis (Text-to-Speech) for the interviewer and browser-native voice transcription (Speech-to-Text) for the candidate.

---

## 📌 Project Overview
- **Challenge Name:** The 24-Hour AI Agent Challenge (Rooman Technologies)
- **Role Track:** Junior AI Research Associate
- **Agent Chosen:** Interview Agent (Intermediate Category)
- **One-Sentence Core:** My agent takes a candidate's resume/profile along with interactive answers and produces an objective, question-by-question technical evaluation report.

## 🚀 Expected Capabilities Implemented
* **Dynamic Role-Specific Question Generation:** Generates contextual questions from candidate profiles without repeating historical nodes.
* **Turn-by-Turn Response Scoring:** Provides a granular score out of 10 for each response based on relevance, clarity, depth, and evidence.
* **Comprehensive Session Evaluation:** Outputs a clean Markdown and structured JSON session summary of candidate highlights and growth areas.
* **Multi-Turn State Engine:** Successfully supports a full multi-turn evaluation stream (up to 5+ questions).

---

## 🛠️ Tech Stack & Architecture
- **Backend Framework:** FastAPI (Python 3.10+)
- **Frontend Dashboard UI:** Streamlit (with custom dark-themed glassmorphism elements)
- **Client Fallback:** Command Line Interface (CLI)
- **AI Orchestration:** System-prompt engineered LLM pipeline with memory tracking
- **Storage Layer:** Local filesystem storage (`data/sessions/` directory utilizing timestamps)

### System Architecture
The application is structured as a client-server architecture:
- **Backend:** A local FastAPI REST API server (`server.py`) that handles all core logic (resume parsing, question generation, scoring, and evaluations).
- **Clients:** A Streamlit web dashboard (`app.py`) and a terminal CLI fallback (`cli.py`). Both interfaces communicate with the backend via HTTP REST endpoints.

```mermaid
graph TD
    subgraph Client Layer
        A["Streamlit Web UI (app.py)"]
        B["Terminal CLI (cli.py)"]
    end

    subgraph Backend Layer (FastAPI - server.py)
        C["API Router (Endpoints)"]
        D["Resume Parser"]
        E["Question Engine"]
        F["Scoring Engine"]
        G["Evaluator Engine"]
    end

    A -- HTTP Requests --> C
    B -- HTTP Requests --> C

    D -. "No API Key" .-> H["Offline / Mock Mode<br>(Keyword-aware templates)"]
    E -. "No API Key" .-> H
    F -. "No API Key" .-> H
    G -. "No API Key" .-> H
```

### Detailed Interview Loop Logic
```mermaid
graph TD
    A["Ask Question"] --> B["Candidate Answers<br>(Typed or Voice Input)"]
    B --> C["Score the Answer<br>(LLM rates 0-10 + breakdown)"]
    C --> D{"Weak answer (score < 5) OR<br>fewer than 5 fresh questions?"}
    D -- "Yes (Weak or < 5 fresh asked)" --> E["Ask follow-up (if weak) OR<br>Ask next fresh question"]
    E --> A
    D -- "No (5+ fresh asked, not weak)" --> F["Exit Loop"]
    F --> G["Final Evaluation"]
```

---

## 📦 Installation & Setup Instructions
```bash
# 1. Clone the repository
git clone https://github.com/Nandunandu24/Interview-Agent.git
cd Interview-Agent

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows use:
venv\Scripts\activate
# On macOS/Linux use:
source venv/bin/activate

# 3. Install pinned dependencies
pip install -r requirements.txt
```

### Environment Configuration
To use actual LLMs (online mode), copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open the `.env` file and configure your API keys (e.g. Groq or Google Gemini):
```ini
# Groq API Key (Llama-3.3-70b-versatile / Llama-3.1-8b-instant)
GROQ_API_KEY="your_groq_api_key_here"

# Gemini API Key (Gemini 2.0 Flash / Gemini 1.5 Flash)
GEMINI_API_KEY="your_gemini_api_key_here"
```
*Note: If no API keys are configured, the server automatically boots in **Offline Mock Mode**, allowing you to test and run the entire interview simulation offline.*

---

## 🏃 How to Run the Agent End-to-End
To run the agent, you need to start the FastAPI backend server first and then launch one of the client interfaces.

### Step 1: Start the Backend (FastAPI Server)
Run the following command in your terminal to boot the server:
```bash
python server.py
```
The backend server will start locally at `http://127.0.0.1:8000`.

### Step 2: Run the Client Interface
Open a second terminal window, activate your virtual environment, and run either the Web UI or the CLI:

#### Option A: Launch the Web UI Dashboard (Streamlit - Recommended)
```bash
streamlit run app.py
```
This launches a browser-based dashboard. Upload your resume, click **🚀 Start Interview**, and conduct your interactive technical interview.

#### Option B: Launch the Terminal UI (CLI Fallback)
```bash
python cli.py
```
This runs a fully guided, keyboard-interactive technical mock interview directly in your console.

### Running Automated Integration Tests
To verify all FastAPI endpoints, offline mock fallbacks, and parsing components:
```bash
python -m unittest test_agent.py
```

---

## 📄 Sample Inputs and Outputs (The Deliverables)
Every mock interview session conducts an interactive dialogue (at least 5 questions) and auto-saves the raw session transcript and candidate evaluation summaries.

### In-Repo Deliverable Locations
- **Saved Session Transcripts:** Transcripts are automatically saved locally inside the `data/sessions/` directory utilizing timestamps.
- **Reference Deliverables:**
  - **Structured JSON Transcript:** [sample_transcript.json](data/sessions/sample_transcript.json) - Contains the complete raw transcript payload, including turn-by-turn scores (0-10) and relevance/correctness/clarity criteria breakdowns.
  - **Comprehensive Markdown Assessment Report:** [sample_transcript.md](data/sessions/sample_transcript.md) - Contains the complete formatted Candidate Assessment Report, including:
    1. Executive Summary (Overall Verdict, Key Strengths, Growth Areas)
    2. Dimension Breakdown & Scoring (Communication, Technical Depth, Problem Solving)
    3. Detailed Technical Assessment (Logic, Optimization, Edge cases)
    4. Tailored Actionable Suggestions (For Candidate, For Hiring Team)

---

## ⚖️ Tradeoff Notes & Technical Reasoning

### 1. Model & API Selections
- **Groq & Google Gemini APIs:** Groq was selected as the primary online inference engine due to its sub-second token latency, allowing for fluid real-time speech-to-text response feedback loops. Google Gemini was included as an alternative provider because of its large context window and strong performance on structural coding tasks.

### 2. Local Filesystem vs. Database Storage
- **Decision:** Session logs are persisted locally as JSON and Markdown files (`data/sessions/`) rather than using an external relational database (like PostgreSQL) or cloud database (like MongoDB).
- **Reasoning:** In a 24-hour hackathon window, local files eliminate the overhead of database provisioning, connection pools, and migration scripts. Plain files are highly portable, require zero configuration to run, and allow direct inspectability for reviewers.

### 3. Client-Side Speech APIs
- **Decision:** Built-in web Text-to-Speech (TTS) and Speech-to-Text (STT) APIs were implemented.
- **Reasoning:** Running audio client-side reduces server latency, eliminates expensive server-side audio transcription API costs, and runs out-of-the-box in Chrome without extra Python audio dependencies.

### 4. Honest Limitations & Future Improvements
If given more time beyond the 24-hour limit, the following enhancements would be prioritised:
- **Evaluation Consistency:** Implement a consensus/multi-agent judging framework where multiple prompts evaluate the candidate's answers in parallel to minimize scoring variance.
- **Complex Layout Resume Parsing:** Incorporate visual document layout analysis (e.g. PyMuPDF or layout-parser) to handle multi-column PDFs without scrambling reading orders.
- **Whisper/API Transcription Integration:** Add server-side audio transcription via OpenAI's Whisper API as a configurable fallback for non-Chrome browsers, ensuring consistent voice input quality.
- **Persistent DB Storage:** Transition the local file storage to a lightweight embedded database like SQLite or a scalable document store (MongoDB) to support enterprise-grade search and candidate history filters.
