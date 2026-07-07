import streamlit as st
import os
import json
import requests
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = "http://127.0.0.1:8000/api"

# Set page config
st.set_page_config(
    page_title="HireAI - Structured Interview Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling (Dark Mode, Glassmorphism, Custom Typography)
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* Global Font Settings */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Base page background */
.stApp {
    background-color: #0B0F19;
    background-image: radial-gradient(circle at 10% 20%, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.8) 90%);
    color: #E2E8F0;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: rgba(17, 24, 39, 0.8) !important;
    backdrop-filter: blur(10px);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Glassmorphic Cards */
.glass-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}

.glass-card-header {
    font-family: 'Outfit', sans-serif;
    color: #38BDF8;
    font-weight: 700;
    font-size: 1.4rem;
    margin-bottom: 12px;
}

.interviewer-bubble {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 16px;
    padding: 20px;
    font-size: 1.15rem;
    line-height: 1.6;
    color: #F8FAFC;
    margin-bottom: 25px;
    box-shadow: 0 4px 20px rgba(56, 189, 248, 0.05);
}

/* Title and Hero Styling */
.hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(to right, #38BDF8, #818CF8, #EC4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
    text-align: center;
}

.hero-subtitle {
    font-size: 1.1rem;
    color: #94A3B8;
    text-align: center;
    margin-bottom: 40px;
}

/* Custom styled sub-sections */
.metric-box {
    text-align: center;
    padding: 15px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.metric-value {
    font-family: 'Outfit', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: #38BDF8;
}

.metric-label {
    font-size: 0.85rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Animation classes */
@keyframes pulse {
    0% { transform: scale(1); opacity: 0.9; }
    50% { transform: scale(1.05); opacity: 1; }
    100% { transform: scale(1); opacity: 0.9; }
}

.pulse-btn {
    animation: pulse 2s infinite;
}

/* Progress bar styling */
.stProgress > div > div > div > div {
    background-image: linear-gradient(to right, #38BDF8, #818CF8);
}

/* Vertical Timeline styling */
.timeline-container {
    position: relative;
    padding-left: 30px;
    margin-top: 20px;
    margin-bottom: 20px;
}
.timeline-container::before {
    content: '';
    position: absolute;
    left: 9px;
    top: 5px;
    width: 2px;
    height: calc(100% - 20px);
    background: rgba(255, 255, 255, 0.1);
}
.timeline-item {
    position: relative;
    margin-bottom: 25px;
}
.timeline-marker {
    position: absolute;
    left: -27px;
    top: 6px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #38BDF8;
    border: 2px solid #0B0F19;
    box-shadow: 0 0 8px #38BDF8;
}
.timeline-marker.follow-up {
    background: #EC4899;
    box-shadow: 0 0 8px #EC4899;
}
.timeline-content {
    background: rgba(30, 41, 59, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 16px;
}
.timeline-title {
    font-weight: 700;
    font-size: 1.0rem;
    color: #38BDF8;
    margin-bottom: 6px;
    font-family: 'Outfit', sans-serif;
}
.timeline-title.follow-up {
    color: #EC4899;
}

/* Force dark-mode style for inputs & textareas */
.stTextArea textarea, .stTextInput input, div[data-baseweb="textarea"], div[data-baseweb="input"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
}

/* Fix main Streamlit header white-bar leak */
header[data-testid="stHeader"] {
    background-color: rgba(15, 23, 42, 0.5) !important;
    backdrop-filter: blur(10px) !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def check_server_running() -> bool:
    """Checks if the FastAPI server is running locally."""
    try:
        requests.get("http://127.0.0.1:8000/", timeout=1.0)
        return True
    except Exception:
        return False

def check_or_start_server() -> bool:
    """Checks if the server is running. If not, auto-starts server.py in the background."""
    if check_server_running():
        return True
    try:
        import subprocess
        import time
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NO_WINDOW
            
        subprocess.Popen(
            ["python", "server.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            creationflags=creationflags,
            close_fds=True
        )
        # Wait up to 4 seconds for server to bind
        for _ in range(8):
            time.sleep(0.5)
            if check_server_running():
                return True
    except Exception:
        pass
    return False

# ----------------- SESSION STATE CONFIG -----------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.interview_started = False
    st.session_state.resume_text = ""
    st.session_state.target_role = ""
    st.session_state.skills = []
    st.session_state.summary = ""
    st.session_state.history = []
    st.session_state.fresh_asked = 0
    st.session_state.current_question_index = 0
    st.session_state.current_transcript_buffer = ""
    st.session_state.last_was_weak = False
    st.session_state.current_question = ""
    st.session_state.interview_completed = False
    st.session_state.review_stage = False
    st.session_state.evaluation = None
    st.session_state.saved_paths = None
    st.session_state.tts_active = True
    st.session_state.stt_active = True
    st.session_state.speech_trigger = ""
    st.session_state.backend_mode = "offline"
    st.session_state.start_time = None
    st.session_state.end_time = None
    st.session_state.experience_level = "Mid-Level"

# ----------------- SIDEBAR CONFIG -----------------
st.sidebar.markdown("<h2 style='font-family:Outfit; font-weight:700; color:#38BDF8;'>💼 HireAI Config</h2>", unsafe_allow_html=True)

# Connection Status Indicator
server_online = check_or_start_server()
if server_online:
    st.sidebar.markdown("<p style='color:#10B981; font-weight:600;'>● FastAPI Server: ONLINE</p>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<p style='color:#EF4444; font-weight:600;'>● FastAPI Server: OFFLINE</p>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='font-family:Outfit; font-weight:600;'>Voice Settings</h3>", unsafe_allow_html=True)
st.session_state.tts_active = st.sidebar.checkbox("Interviewer TTS (Read Aloud)", value=st.session_state.tts_active)
st.session_state.stt_active = st.sidebar.checkbox("Candidate STT (Voice Input Panel)", value=st.session_state.stt_active)

# Session Countdown Timer in Sidebar
if st.session_state.interview_started and not st.session_state.interview_completed:
    st.sidebar.markdown("---")
    st.sidebar.markdown("<h3 style='font-family:Outfit; font-weight:600;'>⌛ Session Timer</h3>", unsafe_allow_html=True)
    
    elapsed = (datetime.now() - st.session_state.start_time).total_seconds()
    remaining = max(600 - int(elapsed), 0)
    
    timer_html = f"""
    <div style="text-align: center; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 12px; padding: 12px; color: #FCA5A5; font-family: 'Outfit', sans-serif;">
        <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; color: #F87171; font-weight: bold;">TIME REMAINING</div>
        <div id="sidebar-countdown-val" style="font-size: 2.0rem; font-weight: bold; font-family: monospace;">00:00</div>
    </div>
    
    <script>
    let secsLeft = parseInt("{remaining}");
    const disp = document.getElementById("sidebar-countdown-val");
    
    function tick() {{
        const m = Math.floor(secsLeft / 60);
        const s = secsLeft % 60;
        disp.innerText = String(m).padStart(2, '0') + ":" + String(s).padStart(2, '0');
        
        if (secsLeft <= 0) {{
            clearInterval(tInterval);
            window.parent.location.reload();
        }} else {{
            secsLeft--;
        }}
    }}
    tick();
    const tInterval = setInterval(tick, 1000);
    </script>
    """
    with st.sidebar:
        import streamlit.components.v1 as components
        components.html(timer_html, height=95)

st.sidebar.markdown("---")
st.sidebar.markdown("### Upload Resume")
uploaded_file = st.sidebar.file_uploader("Upload PDF, DOCX, or TXT Resume", type=["pdf", "docx", "txt"])

# Handle Resume Upload and parsing via FastAPI
if uploaded_file is not None and not st.session_state.interview_started and server_online:
    temp_dir = os.path.join("data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    with st.spinner("Requesting parsing from FastAPI..."):
        try:
            abs_temp_path = os.path.abspath(temp_path)
            res = requests.post(f"{API_URL}/parse", json={"file_path": abs_temp_path})
            res.raise_for_status()
            data = res.json()
            
            st.session_state.resume_text = data["text"]
            st.session_state.target_role = data["inferred_role"]
            st.session_state.skills = data["skills"]
            st.session_state.summary = data["summary"]
            st.session_state.experience_level = data.get("experience_level", "Mid-Level")
            st.session_state.backend_mode = data.get("mode", "offline")
            
            st.sidebar.success(f"Resume parsed successfully! ({st.session_state.backend_mode.upper()} mode)")
        except Exception as e:
            st.sidebar.error(f"Error parsing resume via server: {e}")
            
    if os.path.exists(temp_path):
        os.remove(temp_path)

# Helper function to speak question aloud using Web Speech API (HTML/JS)
def trigger_speech(text):
    if not st.session_state.tts_active:
        return
    encoded_text = urllib.parse.quote(text)
    html_code = f"""
    <script>
    window.speechSynthesis.cancel();
    const textToSpeak = decodeURIComponent("{encoded_text}");
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 1.0;
    const voices = window.speechSynthesis.getVoices();
    const chosenVoice = voices.find(v => v.name.includes("Google US English") || v.name.includes("Zira") || v.lang === "en-US") || voices[0];
    if(chosenVoice) {{
        utterance.voice = chosenVoice;
    }}
    window.speechSynthesis.speak(utterance);
    </script>
    """
    import streamlit.components.v1 as components
    components.html(html_code, height=0, width=0)

# Save session utility
def save_session_streamlit():
    sessions_dir = os.path.join("data", "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    json_path = os.path.join(sessions_dir, f"session_{timestamp}.json")
    md_path = os.path.join(sessions_dir, f"session_{timestamp}.md")
    
    transcript_data = {
        "role": st.session_state.target_role,
        "timestamp": datetime.now().isoformat(),
        "history": st.session_state.history,
        "evaluation": st.session_state.evaluation
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2)
        
    md_content = f"# Interview Transcript - {st.session_state.target_role}\n"
    md_content += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
    
    for turn in st.session_state.history:
        if turn["role"] == "interviewer":
            md_content += f"### Interviewer\n> {turn['content']}\n\n"
        else:
            md_content += f"### Candidate\n> {turn['content']}\n\n"
            md_content += f"**Score:** `{turn.get('score', 0)}/10`\n\n"
            md_content += f"**Feedback:** {turn.get('justification', '')}\n\n"
            b = turn.get("breakdown", {})
            if b:
                md_content += "**Category Breakdown:**\n"
                md_content += f"- Relevance: {b.get('relevance')}\n"
                md_content += f"- Correctness & Depth: {b.get('correctness_depth')}\n"
                md_content += f"- Clarity: {b.get('clarity')}\n"
                md_content += f"- Specificity & Evidence: {b.get('specificity_evidence')}\n\n"
            md_content += "---\n\n"
            
    eval_block = st.session_state.evaluation
    md_content += "## Candidate Assessment Report\n\n"
    md_content += f"**Overall Rating:** `{eval_block.get('overall_score')}/100` | **Evaluation Mode:** `{eval_block.get('mode', 'N/A').upper()}`\n\n"
    
    md_content += "### 1. Executive Summary\n"
    md_content += f"- **Overall Verdict:** {eval_block.get('verdict', 'N/A')}\n"
    md_content += f"- **Key Strengths:** {eval_block.get('key_strengths', 'N/A')}\n"
    md_content += f"- **Primary Areas for Growth:** {eval_block.get('growth_areas', 'N/A')}\n\n"
    
    md_content += "### 2. Dimension Breakdown & Scoring\n"
    md_content += "Rate each dimension on a scale of 1 to 5 (1 = Critical Gaps, 3 = Meets Expectations, 5 = Exceptional). Provide specific, verbatim text or conceptual evidence from the transcript to back up the score.\n\n"
    
    comm = eval_block.get('communication_skills', {})
    tech = eval_block.get('technical_depth', {})
    prob = eval_block.get('problem_solving_adaptability', {})
    
    md_content += f"*   **Communication Skills:** {comm.get('score', 0)}/5\n"
    md_content += f"    - *Evidence:* {comm.get('evidence', 'N/A')}\n"
    md_content += f"*   **Technical Depth:** {tech.get('score', 0)}/5\n"
    md_content += f"    - *Evidence:* {tech.get('evidence', 'N/A')}\n"
    md_content += f"*   **Problem-Solving & Adaptability:** {prob.get('score', 0)}/5\n"
    md_content += f"    - *Evidence:* {prob.get('evidence', 'N/A')}\n\n"
    
    detailed = eval_block.get('detailed_technical', {})
    md_content += "### 3. Detailed Technical Assessment\n"
    md_content += f"- **Accuracy of Logic/Code:** {detailed.get('accuracy', 'N/A')}\n"
    md_content += f"- **Optimization & Trade-offs:** {detailed.get('optimization', 'N/A')}\n"
    md_content += f"- **Edge-Case Awareness:** {detailed.get('edge_cases', 'N/A')}\n\n"
    
    feedback = eval_block.get('feedback', {})
    md_content += "### 4. Tailored Feedback & Suggestions\n"
    md_content += f"- **For the Candidate:** {feedback.get('candidate', 'N/A')}\n"
    md_content += f"- **For the Hiring Team:** {feedback.get('hiring_team', 'N/A')}\n"
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    st.session_state.saved_paths = (json_path, md_path)

def reset_interview():
    st.session_state.interview_started = False
    st.session_state.history = []
    st.session_state.fresh_asked = 0
    st.session_state.current_question_index = 0
    st.session_state.current_transcript_buffer = ""
    st.session_state.last_was_weak = False
    st.session_state.current_question = ""
    st.session_state.interview_completed = False
    st.session_state.evaluation = None
    st.session_state.saved_paths = None
    st.session_state.start_time = None
    st.session_state.end_time = None
    st.rerun()

# ----------------- MAIN LAYOUT -----------------
st.markdown("<h1 class='hero-title'>HireAI</h1>", unsafe_allow_html=True)
st.markdown("<p class='hero-subtitle'>Autonomous Structured Mock Interview Agent powered by FastAPI</p>", unsafe_allow_html=True)

if not server_online:
    st.error("⚠️ Backend Server Offline: Please start the FastAPI backend server using standard Python in your console before launching the UI:\n\n`python server.py`")
else:
    if not st.session_state.interview_started:
        st.markdown(
            "<div class='glass-card'>"
            "<div class='glass-card-header'>Welcome to HireAI</div>"
            "To begin, upload a resume in the sidebar. The FastAPI server will parse your resume, infer your target role, "
            "and structure a targeted 5-question technical interview. If you do not have API keys configured, the server "
            "will automatically run in <b>Offline Mock Mode</b>, delivering realistic, tailored question paths without costs."
            "</div>", 
            unsafe_allow_html=True
        )
        
        if st.session_state.resume_text:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                roles_list = [
                    "Backend Developer",
                    "Frontend Developer",
                    "Data Analyst",
                    "Data Engineer",
                    "DevOps Engineer",
                    "Data Scientist",
                    "AI Engineer"
                ]
                inferred_lower = st.session_state.target_role.lower()
                default_role_idx = 0
                if "data scientist" in inferred_lower:
                    default_role_idx = roles_list.index("Data Scientist")
                elif "ai engineer" in inferred_lower or "machine learning" in inferred_lower or "artificial intelligence" in inferred_lower:
                    default_role_idx = roles_list.index("AI Engineer")
                elif "data analyst" in inferred_lower or "business analyst" in inferred_lower or "analytics" in inferred_lower:
                    default_role_idx = roles_list.index("Data Analyst")
                elif "frontend" in inferred_lower:
                    default_role_idx = roles_list.index("Frontend Developer")
                elif "data engineer" in inferred_lower:
                    default_role_idx = roles_list.index("Data Engineer")
                elif "devops" in inferred_lower or "sre" in inferred_lower:
                    default_role_idx = roles_list.index("DevOps Engineer")
                elif "backend" in inferred_lower or "software engineer" in inferred_lower:
                    default_role_idx = roles_list.index("Backend Developer")
                
                selected_role = st.selectbox("Target Role", options=roles_list, index=default_role_idx)
                
                # Dynamically update the tech stack when the role changes
                if selected_role != st.session_state.target_role or not st.session_state.skills:
                    st.session_state.target_role = selected_role
                    role_skills = {
                        "Backend Developer": ["Python", "FastAPI", "Go", "Java", "Docker", "Kubernetes", "AWS", "SQL", "PostgreSQL", "Redis", "MongoDB", "Elasticsearch", "gRPC", "Git", "CI/CD"],
                        "Frontend Developer": ["React", "HTML/CSS", "JavaScript", "TypeScript", "Redux", "Zustand", "Webpack", "Vite", "Node.js", "Git", "Jest", "SEO"],
                        "Data Analyst": ["SQL", "Excel", "Power BI", "Tableau", "Data Storytelling", "Python", "Pandas", "NumPy", "A/B Testing", "Statistics", "Data Reporting"],
                        "Data Engineer": ["SQL", "ETL", "Python", "Apache Spark", "Airflow", "Snowflake", "BigQuery", "Kafka", "Data Warehousing", "Hadoop", "Git"],
                        "DevOps Engineer": ["Linux", "Git", "Docker", "Kubernetes", "Terraform", "CI/CD", "GitHub Actions", "Jenkins", "AWS", "Prometheus", "Grafana", "Bash"],
                        "Data Scientist": ["Python", "Pandas", "NumPy", "scikit-learn", "TensorFlow", "PyTorch", "MLOps", "Statistics", "Machine Learning", "Linear Regression", "Git"],
                        "AI Engineer": ["Python", "LLM", "RAG", "Vector Databases", "Prompt Engineering", "Fine-Tuning", "Quantization", "PyTorch", "Docker", "HuggingFace", "Git"]
                    }
                    st.session_state.skills = role_skills.get(selected_role, ["Software Engineering", "Python", "Problem Solving"])
                
                # Manual override for Experience Level
                levels = ["Junior", "Mid-Level", "Senior"]
                default_idx = levels.index(st.session_state.experience_level) if st.session_state.experience_level in levels else 1
                st.session_state.experience_level = st.selectbox("Target Experience Level", options=levels, index=default_idx)
                
                st.markdown(f"**Brief Summary:** *{st.session_state.summary}*")
                st.markdown("**Top Technical Skills Inferred:**")
                st.write(", ".join([f"`{s}`" for s in st.session_state.skills[:12]]))
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col2:
                st.markdown("<div class='glass-card' style='height:100%; text-align:center;'>", unsafe_allow_html=True)
                st.markdown("<h3 style='font-family:Outfit; color:#818CF8;'>Start Session</h3>", unsafe_allow_html=True)
                st.write("Ready to test your skills? The session will conduct a structured dialogue, ask questions one-by-one, score them silently, and provide feedback at the end.")
                
                if st.button("🚀 Start Interview", use_container_width=True, type="primary"):
                    with st.spinner("Generating first question from FastAPI..."):
                        try:
                            res = requests.post(f"{API_URL}/question/first", json={
                                "resume_text": st.session_state.resume_text,
                                "target_role": st.session_state.target_role,
                                "experience_level": st.session_state.experience_level
                            })
                            res.raise_for_status()
                            first_q = res.json()["question"]
                            
                            st.session_state.start_time = datetime.now()
                            st.session_state.current_question = first_q
                            st.session_state.history.append({"role": "interviewer", "content": first_q, "is_follow_up": False})
                            st.session_state.fresh_asked = 1
                            st.session_state.interview_started = True
                            st.session_state.speech_trigger = first_q
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error starting interview: {e}")
                st.markdown("</div>", unsafe_allow_html=True)
                
    elif st.session_state.interview_started and st.session_state.review_stage and not st.session_state.interview_completed:
        st.markdown("<div class='glass-card' style='padding: 25px; border-radius: 12px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-family:Outfit; text-align:center; color: #38BDF8;'>📝 Review & Edit Your Answers</h2>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center; color: #94A3B8; margin-bottom: 25px; font-size: 0.95rem;'>"
            "Below are all the questions asked and your recorded answers. You can manually edit "
            "any answer to improve it before submitting them for the final evaluation report."
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)
        
        # We will loop through the candidate answers in history and display them
        candidate_turns = [i for i, turn in enumerate(st.session_state.history) if turn["role"] == "candidate"]
        
        updated_answers = {}
        
        for idx, turn_idx in enumerate(candidate_turns):
            # The question is the turn preceding it (role == interviewer)
            question_content = "Question"
            if turn_idx > 0 and st.session_state.history[turn_idx - 1]["role"] == "interviewer":
                question_content = st.session_state.history[turn_idx - 1]["content"]
            
            orig_answer = st.session_state.history[turn_idx]["content"]
            
            st.markdown(f"<div style='background: rgba(30, 41, 59, 0.4); border-left: 4px solid #38BDF8; padding: 12px; border-radius: 6px; margin-bottom: 8px;'><b>🗣️ Question {idx + 1}:</b><br/>{question_content}</div>", unsafe_allow_html=True)
            
            # Key must be unique for each review text area
            review_key = f"review_ans_{turn_idx}"
            updated_answer = st.text_area("Your Answer:", value=orig_answer, key=review_key, height=120)
            updated_answers[turn_idx] = updated_answer
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            if st.button("✅ Submit Interview & Generate Report", use_container_width=True, type="primary"):
                # We need to update history with the edited answers
                # And re-score any edited answer!
                with st.spinner("Processing final submissions and updating evaluation report..."):
                    try:
                        for turn_idx, new_ans in updated_answers.items():
                            orig_turn = st.session_state.history[turn_idx]
                            # Re-score only if the answer was actually modified
                            if new_ans.strip() != orig_turn["content"].strip():
                                q_text = st.session_state.history[turn_idx - 1]["content"] if turn_idx > 0 else ""
                                res = requests.post(f"{API_URL}/score", json={
                                    "question": q_text,
                                    "answer": new_ans,
                                    "target_role": st.session_state.target_role
                                })
                                res.raise_for_status()
                                score_res = res.json()
                                
                                st.session_state.history[turn_idx]["content"] = new_ans
                                st.session_state.history[turn_idx]["score"] = score_res["score"]
                                st.session_state.history[turn_idx]["justification"] = score_res["justification"]
                                st.session_state.history[turn_idx]["breakdown"] = score_res["breakdown"]
                            else:
                                st.session_state.history[turn_idx]["content"] = new_ans
                                
                        # Call API evaluate endpoint
                        res = requests.post(f"{API_URL}/evaluate", json={
                            "target_role": st.session_state.target_role,
                            "history": st.session_state.history
                        })
                        res.raise_for_status()
                        evaluation = res.json()
                        st.session_state.end_time = datetime.now()
                        st.session_state.evaluation = evaluation
                        st.session_state.interview_completed = True
                        st.session_state.review_stage = False
                        save_session_streamlit()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit edits and evaluate: {e}")

    elif st.session_state.interview_started and not st.session_state.interview_completed:
        # Check for 10-minute timeout (600 seconds)
        elapsed = (datetime.now() - st.session_state.start_time).total_seconds()
        if elapsed >= 600:
            st.session_state.end_time = datetime.now()
            st.session_state.interview_completed = True
            with st.spinner("⏳ Time limit reached! Compiling final report..."):
                try:
                    # Save current in-progress answer if any text exists
                    ans_box_key = f"candidate_ans_input_{st.session_state.fresh_asked}_{len(st.session_state.history)}"
                    unsubmitted_ans = st.session_state.get(ans_box_key, "").strip()
                    if unsubmitted_ans:
                        try:
                            score_res = requests.post(f"{API_URL}/score", json={
                                "question": st.session_state.current_question,
                                "answer": unsubmitted_ans,
                                "target_role": st.session_state.target_role
                            }).json()
                            st.session_state.history.append({
                                "role": "candidate",
                                "content": unsubmitted_ans,
                                "score": score_res.get("score", 5),
                                "justification": score_res.get("justification", "Answer saved at timeout."),
                                "breakdown": score_res.get("breakdown", {}),
                                "is_follow_up": st.session_state.last_was_weak
                            })
                        except Exception:
                            st.session_state.history.append({
                                "role": "candidate",
                                "content": unsubmitted_ans,
                                "score": 5,
                                "justification": "Answer saved at timeout.",
                                "breakdown": {},
                                "is_follow_up": st.session_state.last_was_weak
                            })
                            
                    res = requests.post(f"{API_URL}/evaluate", json={
                        "target_role": st.session_state.target_role,
                        "history": st.session_state.history
                    })
                    res.raise_for_status()
                    evaluation = res.json()
                except Exception as e:
                    # Dynamic fallback based on scores actually submitted
                    valid_scores = [turn["score"] for turn in st.session_state.history if "score" in turn]
                    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 5.0
                    overall_score = round(avg_score * 10)
                    rec = "Borderline"
                    if overall_score >= 80:
                        rec = "Strong fit"
                    elif overall_score < 50:
                        rec = "Not ready yet"
                        
                    evaluation = {
                        "overall_score": overall_score,
                        "scoring_formula": "Average of all question scores (fresh and follow-up) scaled out of 100: (Sum of scores / Number of questions) * 10",
                        "strengths": ["Completed initial responses during session."],
                        "gaps": ["Interview session reached the 10-minute time limit."],
                        "recommendation": rec,
                        "recommendation_reasoning": "Interview timed out after 10 minutes.",
                        "summary_paragraph": f"The candidate completed {len(valid_scores)} answers before the time limit expired."
                    }
                st.session_state.evaluation = evaluation
                save_session_streamlit()
                st.rerun()

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        progress_val = min(st.session_state.fresh_asked / 5.0, 1.0)
        st.progress(progress_val)
        
        col_l, col_r = st.columns([3, 1])
        with col_l:
            st.write(f"**Role:** `{st.session_state.target_role}` | **Mode:** `{st.session_state.backend_mode.upper()}`")
        with col_r:
            st.markdown(f"<div style='text-align:right; font-weight:600;'>Question {st.session_state.fresh_asked} of 5 (Fresh)</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div class='interviewer-bubble'><b>👤 AI Interviewer:</b><br/>{st.session_state.current_question}</div>", unsafe_allow_html=True)
        
        if st.session_state.speech_trigger == st.session_state.current_question:
            trigger_speech(st.session_state.current_question)
            st.session_state.speech_trigger = ""
            
        st.markdown("### Your Answer")
        
        if st.session_state.stt_active:
            stt_html = """
            <div style="background: rgba(30, 41, 59, 0.3); border: 1px dashed rgba(255,255,255,0.1); border-radius: 12px; padding: 15px; margin-bottom: 15px;">
                <p style="margin-top:0; font-size: 0.9rem; color: #94A3B8;">🎙️ <b>Speech-to-Text Dictate Assist:</b> Click 'Start Recording' and speak your answer. Your spoken response will automatically fill the text box below in real-time!</p>
                <button id="stt-btn" style="background-color: #38BDF8; color: #0F172A; border: none; border-radius: 8px; padding: 8px 16px; font-weight: bold; cursor: pointer; margin-right: 10px;">🎤 Start Recording</button>
                <button id="stt-stop" style="background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 8px; padding: 8px 16px; font-weight: bold; cursor: pointer; display: none;">⏹️ Stop</button>
                <span id="stt-status" style="font-size: 0.85rem; color: #38BDF8; font-style: italic;">Ready</span>
                <div id="stt-result" style="margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 6px; min-height: 40px; font-size: 0.95rem; color: #E2E8F0; border: 1px solid rgba(255,255,255,0.05); user-select: all;">(Transcribed text will appear here and sync to the main input field)</div>
            </div>
            
            <script>
            const btn = document.getElementById('stt-btn');
            const stopBtn = document.getElementById('stt-stop');
            const status = document.getElementById('stt-status');
            const result = document.getElementById('stt-result');
            const placeholder = "(Transcribed text will appear here and sync to the main input field)";
            
            function getCleanText() {
                const text = result.innerText.trim();
                if (text === placeholder) return "";
                return text;
            }
            
            const currentQuestionId = "QUESTION_ID_PLACEHOLDER";
            const savedQuestionId = sessionStorage.getItem('stt_question_id');
            
            let accumulatedTranscript = '';
            let isManuallyStopped = true;
            
            if (savedQuestionId !== currentQuestionId) {
                sessionStorage.setItem('stt_accumulated_transcript', '');
                sessionStorage.setItem('stt_is_manually_stopped', 'true');
                sessionStorage.setItem('stt_question_id', currentQuestionId);
                accumulatedTranscript = '';
                isManuallyStopped = true;
                result.innerText = placeholder;
            } else {
                accumulatedTranscript = sessionStorage.getItem('stt_accumulated_transcript') || '';
                isManuallyStopped = sessionStorage.getItem('stt_is_manually_stopped') === 'false' ? false : true;
                if (accumulatedTranscript) {
                    result.innerText = accumulatedTranscript;
                } else {
                    result.innerText = placeholder;
                }
            }
            
            let recognition;
            
            let mediaRecorder;
            let audioChunks = [];

            function safeStartRecognition() {
                if (isManuallyStopped) return;
                try {
                    recognition.start();
                    status.innerText = "Listening...";
                } catch(err) {
                    console.log("Recognition start deferred:", err.message);
                    if (err.name === 'InvalidStateError' || err.message.includes('already started')) {
                        setTimeout(safeStartRecognition, 100);
                    }
                }
            }

            function triggerParentSubmit() {
                try {
                    const parentDoc = window.parent.document;
                    const buttons = parentDoc.querySelectorAll("button");
                    for (let btn of buttons) {
                        if (btn.innerText && btn.innerText.includes("Submit Answer")) {
                            btn.click();
                            break;
                        }
                    }
                } catch(err) {
                    console.error("Failed to click parent submit button:", err);
                }
            }

            function syncToStreamlit(text, forceSync = false) {
                try {
                    const parentDoc = window.parent.document;
                    const textareas = parentDoc.querySelectorAll("textarea");
                    for (let ta of textareas) {
                        const nativeValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                        if (nativeValueSetter) {
                            nativeValueSetter.call(ta, text);
                        } else {
                            ta.value = text;
                        }
                        
                        // Dispatch input event to update React component state internally
                        ta.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        if (forceSync) {
                            // Dispatch change and blur to sync to Python backend
                            ta.dispatchEvent(new Event('change', { bubbles: true }));
                            ta.dispatchEvent(new Event('blur', { bubbles: true }));
                        }
                    }
                } catch(err) {
                    console.error("DOM sync error: ", err);
                }
            }

            function setupManualEditListener() {
                try {
                    const parentDoc = window.parent.document;
                    const textareas = parentDoc.querySelectorAll("textarea");
                    for (let ta of textareas) {
                        ta.addEventListener('input', (e) => {
                            if (e.isTrusted) { 
                                accumulatedTranscript = ta.value;
                                sessionStorage.setItem('stt_accumulated_transcript', ta.value);
                                result.innerText = ta.value;
                            }
                        });
                    }
                } catch(err) {
                    console.error("Setup edit listener error:", err);
                }
            }
            setTimeout(setupManualEditListener, 500);
            
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = 'en-US';
                
                recognition.onstart = () => {
                    status.innerText = "Listening...";
                    btn.style.display = 'none';
                    stopBtn.style.display = 'inline-block';
                };
                
                recognition.onresult = (event) => {
                    let interimTranscript = '';
                    let finalTranscript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        if (event.results[i].isFinal) {
                            finalTranscript += event.results[i][0].transcript;
                        } else {
                            interimTranscript += event.results[i][0].transcript;
                        }
                    }
                    const currentSessionText = finalTranscript + interimTranscript;
                    const text = (accumulatedTranscript + " " + currentSessionText).trim();
                    result.innerText = text;
                    sessionStorage.setItem('stt_accumulated_transcript', text);
                    syncToStreamlit(text, false);
                };
                
                recognition.onerror = (e) => {
                    console.error("Speech recognition error: ", e.error);
                    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                        isManuallyStopped = true;
                        sessionStorage.setItem('stt_is_manually_stopped', 'true');
                        status.innerText = "Permission/Service Error: " + e.error;
                        btn.style.display = 'inline-block';
                        stopBtn.style.display = 'none';
                        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                            mediaRecorder.stop();
                        }
                    } else {
                        // Recoverable errors (no-speech, network timeouts, aborted) are handled by self-healing onend
                        console.log("Recoverable speech error: " + e.error + ", auto-restarting...");
                    }
                };
                
                recognition.onend = () => {
                    accumulatedTranscript = getCleanText();
                    sessionStorage.setItem('stt_accumulated_transcript', accumulatedTranscript);
                    
                    if (!isManuallyStopped) {
                        status.innerText = "Listening (resuming)...";
                        syncToStreamlit(accumulatedTranscript, false);
                        safeStartRecognition();
                    } else {
                        status.innerText = "Listening completed & synchronized.";
                        btn.style.display = 'inline-block';
                        stopBtn.style.display = 'none';
                    }
                };
                
                btn.onclick = () => {
                    isManuallyStopped = false;
                    sessionStorage.setItem('stt_is_manually_stopped', 'false');
                    accumulatedTranscript = getCleanText();
                    if (result.innerText.trim() === placeholder) {
                        result.innerText = "";
                    }
                    safeStartRecognition();
                    
                    // Media Recording
                    audioChunks = [];
                    navigator.mediaDevices.getUserMedia({ audio: true })
                        .then(stream => {
                            mediaRecorder = new MediaRecorder(stream);
                            mediaRecorder.ondataavailable = e => {
                                if (e.data.size > 0) {
                                    audioChunks.push(e.data);
                                }
                            };
                            mediaRecorder.onstop = () => {
                                const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
                                const formData = new FormData();
                                formData.append("file", audioBlob, "recording.wav");
                                formData.append("question_index", "QUESTION_INDEX_PLACEHOLDER");
                                
                                status.innerText = "Saving recording & submitting answer...";
                                
                                fetch("http://127.0.0.1:8000/api/upload_audio", {
                                    method: "POST",
                                    body: formData,
                                    keepalive: true
                                })
                                .then(response => response.json())
                                .then(data => {
                                    console.log("Audio file uploaded:", data);
                                    triggerParentSubmit();
                                })
                                .catch(error => {
                                    console.error("Audio upload error:", error);
                                    triggerParentSubmit();
                                });
                                
                                stream.getTracks().forEach(track => track.stop());
                            };
                            mediaRecorder.start();
                        })
                        .catch(err => {
                            console.error("Microphone access denied:", err);
                        });
                };
                
                stopBtn.onclick = () => {
                    isManuallyStopped = true;
                    sessionStorage.setItem('stt_is_manually_stopped', 'true');
                    recognition.stop();
                    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                        mediaRecorder.stop();
                    }
                    syncToStreamlit(result.innerText, true);
                };
                
                // Startup resumption logic
                if (!isManuallyStopped) {
                    result.innerText = accumulatedTranscript;
                    status.innerText = "Listening (resuming)...";
                    btn.style.display = 'none';
                    stopBtn.style.display = 'inline-block';
                    safeStartRecognition();
                } else if (accumulatedTranscript) {
                    result.innerText = accumulatedTranscript;
                    status.innerText = "Speech loaded from session.";
                }
                
                window.addEventListener('beforeunload', () => {
                    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                        mediaRecorder.stop();
                    }
                    syncToStreamlit(result.innerText, true);
                });
            } else {
                status.innerText = "Speech Recognition API not supported in this browser.";
                btn.style.disabled = true;
            }
            </script>
            """.replace("QUESTION_ID_PLACEHOLDER", f"{st.session_state.fresh_asked}_{len(st.session_state.history)}").replace("QUESTION_INDEX_PLACEHOLDER", f"{st.session_state.fresh_asked}")
            st.components.v1.html(stt_html, height=180)

        # Bind text area to st.session_state.current_transcript_buffer
        candidate_answer = st.text_area(
            "Type or paste your answer here:", 
            key="current_transcript_buffer", 
            height=150
        )
        
        col_b1, col_b2 = st.columns([3, 2])
        with col_b2:
            if st.button("Submit Answer & Next Question ➔", use_container_width=True, type="primary"):
                if not candidate_answer.strip():
                    st.warning("Please type or record an answer before submitting.")
                else:
                    with st.spinner("Scoring answer via FastAPI..."):
                        try:
                            # Call API score endpoint
                            res = requests.post(f"{API_URL}/score", json={
                                "question": st.session_state.current_question,
                                "answer": candidate_answer,
                                "target_role": st.session_state.target_role
                            })
                            res.raise_for_status()
                            score_res = res.json()
                            
                            # Append candidate response
                            st.session_state.history.append({
                                "role": "candidate",
                                "content": candidate_answer,
                                "score": score_res["score"],
                                "justification": score_res["justification"],
                                "breakdown": score_res["breakdown"],
                                "is_follow_up": st.session_state.last_was_weak
                            })
                            
                            # Check next steps
                            if score_res["is_weak"] and not st.session_state.last_was_weak:
                                st.session_state.last_was_weak = True
                                with st.spinner("Generating follow-up question..."):
                                    res = requests.post(f"{API_URL}/question/follow-up", json={
                                        "resume_text": st.session_state.resume_text,
                                        "target_role": st.session_state.target_role,
                                        "question": st.session_state.current_question,
                                        "answer": candidate_answer,
                                        "experience_level": st.session_state.experience_level
                                    })
                                    res.raise_for_status()
                                    next_q = res.json()["question"]
                            else:
                                st.session_state.last_was_weak = False
                                
                                if st.session_state.fresh_asked < 5:
                                    with st.spinner("Generating next fresh question..."):
                                        res = requests.post(f"{API_URL}/question/next", json={
                                            "resume_text": st.session_state.resume_text,
                                            "target_role": st.session_state.target_role,
                                            "history": st.session_state.history,
                                            "experience_level": st.session_state.experience_level
                                        })
                                        res.raise_for_status()
                                        next_q = res.json()["question"]
                                        st.session_state.fresh_asked += 1
                                else:
                                    next_q = None
                            
                            # Advance the dynamic question counter pointer
                            st.session_state.current_question_index += 1
                            
                            # Clear the transcript buffer for the next question
                            st.session_state.current_transcript_buffer = ""
                            
                            if next_q:
                                st.session_state.current_question = next_q
                                st.session_state.history.append({"role": "interviewer", "content": next_q, "is_follow_up": st.session_state.last_was_weak})
                                st.session_state.speech_trigger = next_q
                                st.rerun()
                            else:
                                st.session_state.review_stage = True
                                save_session_streamlit()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Failed to submit response to backend: {e}")

    elif st.session_state.interview_completed:
        st.markdown("<h2 style='font-family:Outfit; text-align:center;'>Interview Evaluation Report</h2>", unsafe_allow_html=True)
        
        # Check if the session timed out
        if st.session_state.start_time and st.session_state.end_time:
            st_time = st.session_state.start_time
            ed_time = st.session_state.end_time
            if isinstance(st_time, str):
                st_time = datetime.fromisoformat(st_time)
            if isinstance(ed_time, str):
                ed_time = datetime.fromisoformat(ed_time)
            if (ed_time - st_time).total_seconds() >= 600:
                st.warning("⌛ Session Timeout: Your 10-minute interview session has expired. To maintain structure, your answers so far have been compiled into this final report and you have been logged out of the active session.")
        
        # Calculate interview duration
        duration_str = "N/A"
        if st.session_state.start_time and st.session_state.end_time:
            st_time = st.session_state.start_time
            ed_time = st.session_state.end_time
            if isinstance(st_time, str):
                st_time = datetime.fromisoformat(st_time)
            if isinstance(ed_time, str):
                ed_time = datetime.fromisoformat(ed_time)
            delta = ed_time - st_time
            total_secs = int(delta.total_seconds())
            duration_str = f"{total_secs // 60}m {total_secs % 60}s"

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.markdown(
                f"<div class='metric-box'>"
                f"<div class='metric-value'>{st.session_state.evaluation.get('overall_score')}%</div>"
                f"<div class='metric-label'>Overall Score</div>"
                f"</div>", 
                unsafe_allow_html=True
            )
        with col_m2:
            st.markdown(
                f"<div class='metric-box'>"
                f"<div class='metric-value'>{st.session_state.evaluation.get('verdict', 'N/A')}</div>"
                f"<div class='metric-label'>Fit Recommendation</div>"
                f"</div>", 
                unsafe_allow_html=True
            )
        with col_m3:
            tot_q = sum(1 for turn in st.session_state.history if turn["role"] == "candidate")
            st.markdown(
                f"<div class='metric-box'>"
                f"<div class='metric-value'>{tot_q}</div>"
                f"<div class='metric-label'>Total Questions</div>"
                f"</div>", 
                unsafe_allow_html=True
            )
        with col_m4:
            st.markdown(
                f"<div class='metric-box'>"
                f"<div class='metric-value'>{duration_str}</div>"
                f"<div class='metric-label'>Session Duration</div>"
                f"</div>", 
                unsafe_allow_html=True
            )
            
        st.write("")
        
        # 1. Executive Summary
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card-header'>📝 1. Executive Summary</div>", unsafe_allow_html=True)
        st.markdown(f"**Overall Verdict:** `{st.session_state.evaluation.get('verdict', 'N/A')}`")
        st.markdown(f"**Key Strengths:** {st.session_state.evaluation.get('key_strengths', 'N/A')}")
        st.markdown(f"**Primary Areas for Growth:** {st.session_state.evaluation.get('growth_areas', 'N/A')}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 2. Dimension Breakdown & Scoring
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card-header'>📊 2. Dimension Breakdown & Scoring</div>", unsafe_allow_html=True)
        st.write("Rate each dimension on a scale of 1 to 5 (1 = Critical Gaps, 3 = Meets Expectations, 5 = Exceptional):")
        
        comm = st.session_state.evaluation.get('communication_skills', {})
        tech = st.session_state.evaluation.get('technical_depth', {})
        prob = st.session_state.evaluation.get('problem_solving_adaptability', {})
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.markdown(
                f"<div style='padding:12px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:8px; height:100%;'>"
                f"<b>📢 Communication Skills:</b> {comm.get('score', 0)}/5<br/>"
                f"<span style='font-size:0.85rem; color:#CBD5E1;'><i>Evidence:</i> {comm.get('evidence', 'N/A')}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_c2:
            st.markdown(
                f"<div style='padding:12px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:8px; height:100%;'>"
                f"<b>⚙️ Technical Depth:</b> {tech.get('score', 0)}/5<br/>"
                f"<span style='font-size:0.85rem; color:#CBD5E1;'><i>Evidence:</i> {tech.get('evidence', 'N/A')}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_c3:
            st.markdown(
                f"<div style='padding:12px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); border-radius:8px; height:100%;'>"
                f"<b>🎯 Problem-Solving & Adaptability:</b> {prob.get('score', 0)}/5<br/>"
                f"<span style='font-size:0.85rem; color:#CBD5E1;'><i>Evidence:</i> {prob.get('evidence', 'N/A')}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 3. Detailed Technical Assessment & 4. Tailored Feedback
        col_left, col_right = st.columns([1, 1])
        with col_left:
            detailed = st.session_state.evaluation.get('detailed_technical', {})
            st.markdown("<div class='glass-card' style='height:100%;'>", unsafe_allow_html=True)
            st.markdown("<div class='glass-card-header'>🛠️ 3. Detailed Technical Assessment</div>", unsafe_allow_html=True)
            st.markdown(f"**Accuracy of Logic/Code:** {detailed.get('accuracy', 'N/A')}")
            st.markdown(f"**Optimization & Trade-offs:** {detailed.get('optimization', 'N/A')}")
            st.markdown(f"**Edge-Case Awareness:** {detailed.get('edge_cases', 'N/A')}")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_right:
            feedback = st.session_state.evaluation.get('feedback', {})
            st.markdown("<div class='glass-card' style='height:100%;'>", unsafe_allow_html=True)
            st.markdown("<div class='glass-card-header'>💡 4. Tailored Feedback & Suggestions</div>", unsafe_allow_html=True)
            st.markdown(f"**For the Candidate:** {feedback.get('candidate', 'N/A')}")
            st.markdown(f"**For the Hiring Team:** {feedback.get('hiring_team', 'N/A')}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card-header'>📊 Question-by-Question Breakdown</div>", unsafe_allow_html=True)
        
        chart_labels = []
        chart_scores = []
        q_counter = 1
        for turn in st.session_state.history:
            if turn["role"] == "candidate":
                label = f"Q{q_counter} " + ("(Follow-up)" if turn.get("is_follow_up") else "(Fresh)")
                chart_labels.append(label)
                chart_scores.append(turn.get("score", 0))
                q_counter += 1
                
        import pandas as pd
        df = pd.DataFrame({
            "Question": chart_labels,
            "Score (0-10)": chart_scores
        }).set_index("Question")
        st.bar_chart(df)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Chronological Timeline & Critique Tabs
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card-header'>📋 Chronological Interview Timeline & Details</div>", unsafe_allow_html=True)
        
        tab_timeline, tab_critiques = st.tabs(["🕒 Visual Interview Timeline", "📜 Critique Details"])
        
        with tab_timeline:
            def format_critique_html(justification, breakdown):
                import re
                suggestion_marker = re.search(r'\b(suggestions?|suggest):\s*', justification, re.IGNORECASE)
                critique_part = justification
                suggestion_part = ""
                if suggestion_marker:
                    start_idx = suggestion_marker.start()
                    end_idx = suggestion_marker.end()
                    critique_part = justification[:start_idx].strip()
                    suggestion_part = justification[end_idx:].strip()
                    if critique_part.endswith(":") or critique_part.endswith(".") or critique_part.endswith(","):
                        critique_part = critique_part.rstrip(":,.")
                
                critique_html = f"""<div style='margin-top: 12px; padding: 12px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;'>
<div style='font-size: 0.85rem; margin-bottom: 6px;'>
<span style='color: #F87171; font-weight: bold;'>🔍 Critique:</span>
<span style='color: #E2E8F0;'>{critique_part}</span>
</div>"""
                if suggestion_part:
                    critique_html += f"""<div style='font-size: 0.85rem; margin-bottom: 6px;'>
<span style='color: #34D399; font-weight: bold;'>💡 Suggestion:</span>
<span style='color: #E2E8F0;'>{suggestion_part}</span>
</div>"""
                if breakdown:
                    critique_html += f"""<div style='margin-top: 8px; padding-top: 6px; border-top: 1px dashed rgba(255, 255, 255, 0.1);'>
<div style='font-size: 0.75rem; font-weight: bold; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>Criteria Breakdown:</div>
<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; font-size: 0.8rem; color: #CBD5E1;'>"""
                    if breakdown.get("relevance"):
                        critique_html += f"<div>🎯 <b>Relevance:</b> {breakdown['relevance']}</div>"
                    if breakdown.get("correctness_depth"):
                        critique_html += f"<div>⚙️ <b>Correctness:</b> {breakdown['correctness_depth']}</div>"
                    if breakdown.get("clarity"):
                        critique_html += f"<div>📢 <b>Clarity:</b> {breakdown['clarity']}</div>"
                    if breakdown.get("specificity_evidence"):
                        critique_html += f"<div>📊 <b>Specificity:</b> {breakdown['specificity_evidence']}</div>"
                    critique_html += "</div></div>"
                critique_html += "</div>"
                return critique_html

            timeline_html = "<div class='timeline-container'>"
            q_idx = 1
            for turn in st.session_state.history:
                if turn["role"] == "interviewer":
                    type_label = "Follow-up Question" if turn.get("is_follow_up") else f"Question {q_idx}"
                    class_suffix = " follow-up" if turn.get("is_follow_up") else ""
                    timeline_html += f"""<div class='timeline-item'>
<div class='timeline-marker{class_suffix}'></div>
<div class='timeline-content'>
<div class='timeline-title{class_suffix}'>🗣️ {type_label}</div>
<p style='margin:0; font-size:0.95rem; font-style:italic;'>"{turn['content']}"</p>
</div>
</div>"""
                else:
                    score = turn.get("score", 0)
                    justification = turn.get("justification", "")
                    breakdown = turn.get("breakdown", {})
                    critique_html = format_critique_html(justification, breakdown)
                    timeline_html += f"""<div class='timeline-item'>
<div class='timeline-marker' style='background: #10B981; box-shadow: 0 0 8px #10B981;'></div>
<div class='timeline-content' style='border-left: 3px solid #10B981;'>
<div class='timeline-title' style='color: #10B981;'>✍️ Candidate Answer (Score: {score}/10)</div>
<p style='margin:0 0 8px 0; font-size:0.95rem;'>"{turn['content']}"</p>
{critique_html}
</div>
</div>"""
                    q_idx += 1
            timeline_html += "</div>"
            st.markdown(timeline_html, unsafe_allow_html=True)
            
        with tab_critiques:
            q_idx = 1
            for turn_idx, turn in enumerate(st.session_state.history):
                if turn["role"] == "interviewer":
                    continue
                
                # Find the preceding interviewer question
                question_content = "N/A"
                is_follow_up = False
                if turn_idx > 0 and st.session_state.history[turn_idx - 1]["role"] == "interviewer":
                    question_content = st.session_state.history[turn_idx - 1]["content"]
                    is_follow_up = st.session_state.history[turn_idx - 1].get("is_follow_up", False)
                
                q_type = "Follow-up Question" if is_follow_up else "Fresh Question"
                score = turn.get("score", 0)
                justification = turn.get("justification", "")
                
                # Split critique and suggestion
                import re
                suggestion_marker = re.search(r'\b(suggestions?|suggest):\s*', justification, re.IGNORECASE)
                critique_part = justification
                suggestion_part = ""
                if suggestion_marker:
                    start_idx = suggestion_marker.start()
                    end_idx = suggestion_marker.end()
                    critique_part = justification[:start_idx].strip()
                    suggestion_part = justification[end_idx:].strip()
                    if critique_part.endswith(":") or critique_part.endswith(".") or critique_part.endswith(","):
                        critique_part = critique_part.rstrip(":,.")
                else:
                    q_lower = question_content.lower()
                    if "regression" in q_lower:
                        suggestion_part = "Discuss how collinearity affects coefficient interpretation and standard error."
                    elif "bottleneck" in q_lower:
                        suggestion_part = "Detail standard backpressure patterns, queue sizes, or cache configurations."
                    elif "etl" in q_lower or "docker" in q_lower:
                        suggestion_part = "Describe Docker build optimizations like multi-stage caching or parquet partition sizes."
                    elif "statistics" in q_lower:
                        suggestion_part = "Provide a specific dataset example, like how salary distributions skew the mean vs. median."
                    else:
                        suggestion_part = "Mention specific frameworks, tools, or libraries to ground your architectural design."
                
                st.markdown(f"**Interviewer ({q_type}):** *\"{question_content}\"*")
                st.markdown(f"**Candidate:** *\"{turn['content']}\"*")
                st.markdown(f"**Score:** {score}/10 — *{critique_part}*")
                st.markdown(f"**Suggestion:** {suggestion_part}")
                
                b = turn.get("breakdown", {})
                if b:
                    with st.expander(f"View criteria breakdown for Q{q_idx}"):
                        st.markdown(f"- **Relevance:** {b.get('relevance', 'N/A')}")
                        st.markdown(f"- **Correctness & Depth:** {b.get('correctness_depth', 'N/A')}")
                        st.markdown(f"- **Clarity:** {b.get('clarity', 'N/A')}")
                        st.markdown(f"- **Specificity & Evidence:** {b.get('specificity_evidence', 'N/A')}")
                st.markdown("---")
                q_idx += 1
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.session_state.saved_paths:
            json_p, md_p = st.session_state.saved_paths
            st.success(f"Transcript and assessment report saved successfully!\n- **JSON:** `{json_p}`\n- **Markdown:** `{md_p}`")
            
        if st.button("🔄 Start New Interview", type="primary"):
            reset_interview()
