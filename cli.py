import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load env variables
load_dotenv()

API_URL = "http://127.0.0.1:8000/api"

def check_server_running() -> bool:
    """Checks if the FastAPI server is running locally."""
    try:
        # Simple check by requesting a non-existent path but checking if host responds
        requests.get("http://127.0.0.1:8000/", timeout=1.5)
        return True
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return True # Any response or timeout means the server port is bound/responding

def init_voice():
    """Initializes the pyttsx3 Text-to-Speech engine safely."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        voices = engine.getProperty('voices')
        if voices:
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
        return engine
    except Exception as e:
        print(f"\n[Warning] Could not initialize voice engine offline: {e}")
        print("Continuing in text-only mode.")
        return None

def speak(engine, text):
    """Speaks text aloud using pyttsx3 safely if engine is configured."""
    if engine:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"\n[Voice error: {e}]")

def save_transcript(role: str, history: list, evaluation: dict) -> tuple[str, str]:
    """
    Saves the session transcript in structured JSON and readable Markdown formats.
    """
    sessions_dir = os.path.join("data", "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"session_{timestamp}.json"
    md_filename = f"session_{timestamp}.md"
    
    json_path = os.path.join(sessions_dir, json_filename)
    md_path = os.path.join(sessions_dir, md_filename)
    
    transcript_data = {
        "role": role,
        "timestamp": datetime.now().isoformat(),
        "history": history,
        "evaluation": evaluation
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, indent=2)
        
    md_content = f"""# Interview Transcript - {role}
**Date & Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Interview Dialogue

"""
    for turn in history:
        if turn["role"] == "interviewer":
            md_content += f"### Interviewer\n> {turn['content']}\n\n"
        else:
            score = turn.get("score", 0)
            justification = turn.get("justification", "")
            breakdown = turn.get("breakdown", {})
            
            md_content += f"### Candidate\n> {turn['content']}\n\n"
            md_content += f"**Score:** `{score}/10`\n\n"
            md_content += f"**Feedback:** {justification}\n\n"
            if breakdown:
                md_content += "**Category Breakdown:**\n"
                md_content += f"- *Relevance:* {breakdown.get('relevance', 'N/A')}\n"
                md_content += f"- *Correctness & Depth:* {breakdown.get('correctness_depth', 'N/A')}\n"
                md_content += f"- *Clarity:* {breakdown.get('clarity', 'N/A')}\n"
                md_content += f"- *Specificity & Evidence:* {breakdown.get('specificity_evidence', 'N/A')}\n\n"
            md_content += "---\n\n"
            
    md_content += f"""## Final Evaluation Summary

**Overall Score:** `{evaluation.get('overall_score', 0)}/100`

**Scoring Formula:** {evaluation.get('scoring_formula', '')}

### Recommendation
> **{evaluation.get('recommendation', 'N/A')}** - {evaluation.get('recommendation_reasoning', '')}

### Strengths
"""
    for strength in evaluation.get("strengths", []):
        md_content += f"- {strength}\n"
        
    md_content += "\n### Gaps & Areas to Improve\n"
    for gap in evaluation.get("gaps", []):
        md_content += f"- {gap}\n"
        
    md_content += f"\n### Detailed Performance Review\n{evaluation.get('summary_paragraph', '')}\n"
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    return json_path, md_path

def main():
    print("=" * 60)
    print("      STRUCTURED AI INTERVIEW AGENT (REST CLIENT)       ")
    print("=" * 60)
    
    # Check if backend server is online
    if not check_server_running():
        print("[Error] The FastAPI backend server is not running on http://127.0.0.1:8000.")
        print("Please start the backend server first in another window:")
        print("    python server.py")
        sys.exit(1)
        
    # Setup Voice TTS engine
    voice_pref = input("Enable audio read-aloud for interviewer questions? (y/n): ").strip().lower()
    engine = None
    if voice_pref == 'y':
        engine = init_voice()
        if engine:
            print("Voice read-aloud active.")
            
    # Resume File Selection
    default_resume_txt = os.path.join("data", "sample_resume.txt")
    default_resume_pdf = os.path.join("data", "sample_resume.pdf")
    
    default_resume = default_resume_pdf if os.path.exists(default_resume_pdf) else default_resume_txt
    if not os.path.exists(default_resume):
        default_resume = ""
        
    resume_prompt = f"Enter path to candidate's resume file (PDF, DOCX, TXT) [Default: {default_resume}]: " if default_resume else "Enter path to candidate's resume file (PDF, DOCX, TXT): "
    resume_path = input(resume_prompt).strip()
    
    if not resume_path:
        if default_resume:
            resume_path = default_resume
        else:
            print("[Error] Resume file path is required to start.")
            sys.exit(1)
            
    # Resolve absolute path to make sure the backend finds it
    abs_resume_path = os.path.abspath(resume_path)
            
    # Parse Resume via FastAPI
    print(f"\nParsing resume via FastAPI: {abs_resume_path}...")
    try:
        res = requests.post(f"{API_URL}/parse", json={"file_path": abs_resume_path})
        res.raise_for_status()
        parse_data = res.json()
        resume_text = parse_data["text"]
        inferred_role = parse_data["inferred_role"]
        skills = parse_data["skills"]
        summary = parse_data["summary"]
        backend_mode = parse_data.get("mode", "offline")
        print(f"Resume parsed successfully! (Server Mode: {backend_mode.upper()})")
    except Exception as e:
        print(f"[Error] Failed to parse resume via server: {e}")
        sys.exit(1)
        
    print("\nInferred Candidate Profile:")
    print(f"  Target Role: {inferred_role}")
    print(f"  Top Skills : {', '.join(skills[:8])}")
    print(f"  Profile Summary: {summary}")
    
    confirm_role = input(f"\nConfirm target role [Default: {inferred_role}]: ").strip()
    target_role = confirm_role if confirm_role else inferred_role
    
    print(f"\nStarting mock interview for: {target_role}...")
    print("Rules: Min 5 fresh questions. Weak answers (score < 5) trigger 1 targeted follow-up.")
    print("=" * 60)
    
    history = []
    fresh_asked = 0
    last_was_weak = False
    last_question = ""
    
    while fresh_asked < 5 or last_was_weak:
        if last_was_weak:
            print("\n[AI Scorer detected a vague/weak answer. Requesting targeted follow-up...]")
            last_candidate_answer = history[-1]["content"]
            res = requests.post(f"{API_URL}/question/follow-up", json={
                "resume_text": resume_text,
                "target_role": target_role,
                "question": last_question,
                "answer": last_candidate_answer
            })
            res.raise_for_status()
            question = res.json()["question"]
            last_was_weak = False
            is_follow_up = True
        else:
            if fresh_asked == 0:
                print("\n[Generating resume-aware opening question...]")
                res = requests.post(f"{API_URL}/question/first", json={
                    "resume_text": resume_text,
                    "target_role": target_role
                })
            else:
                print("\n[Generating next fresh question...]")
                res = requests.post(f"{API_URL}/question/next", json={
                    "resume_text": resume_text,
                    "target_role": target_role,
                    "history": history
                })
            res.raise_for_status()
            question = res.json()["question"]
            fresh_asked += 1
            is_follow_up = False
            
        print(f"\nInterviewer: {question}")
        speak(engine, question)
        
        last_question = question
        history.append({"role": "interviewer", "content": question, "is_follow_up": is_follow_up})
        
        answer = input("\nYour Answer (type here): ").strip()
        while not answer:
            answer = input("Answer cannot be empty. Your Answer: ").strip()
            
        print("\nEvaluating answer silently...")
        res = requests.post(f"{API_URL}/score", json={
            "question": question,
            "answer": answer,
            "target_role": target_role
        })
        res.raise_for_status()
        score_res = res.json()
        
        history.append({
            "role": "candidate",
            "content": answer,
            "score": score_res["score"],
            "justification": score_res["justification"],
            "breakdown": score_res["breakdown"],
            "is_follow_up": is_follow_up
        })
        
        if score_res["is_weak"] and not is_follow_up:
            last_was_weak = True
            
        print("Score evaluated (hidden until session completion).")
        print(f"Progress: {fresh_asked}/5 Fresh Questions Asked.")
        
    print("\n" + "=" * 60)
    print("Interview Completed! Generating Final Evaluation Report...")
    print("=" * 60)
    
    res = requests.post(f"{API_URL}/evaluate", json={
        "target_role": target_role,
        "history": history
    })
    res.raise_for_status()
    evaluation = res.json()
    
    # Save files
    json_p, md_p = save_transcript(target_role, history, evaluation)
    
    print("\n--- Final Performance Summary ---")
    print(f"Overall Rating : {evaluation.get('overall_score')}/100")
    print(f"Recommendation : {evaluation.get('recommendation')} - {evaluation.get('recommendation_reasoning')}")
    print(f"Evaluation Mode: {evaluation.get('mode', 'N/A').upper()}")
    print("\nStrengths:")
    for strength in evaluation.get("strengths", []):
        print(f"  * {strength}")
    print("\nAreas to Improve:")
    for gap in evaluation.get("gaps", []):
        print(f"  * {gap}")
        
    print("\n" + "=" * 60)
    print(f"Full transcript saved as JSON: {json_p}")
    print(f"Readable summary saved as Markdown: {md_p}")
    print("=" * 60)

if __name__ == "__main__":
    main()
