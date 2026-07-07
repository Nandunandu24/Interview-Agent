import os
import json
import re
from .llm_client import ask_llm

def determine_experience_level(resume_text: str) -> str:
    """Estimates the experience level of the candidate based on resume content."""
    level = "Mid-Level"
    senior_keywords = ["senior", "lead", "principal", "architect", "staff", "manager", "head", "director", "sr."]
    junior_keywords = ["junior", "intern", "associate", "graduate", "fresher", "entry", "jr."]
    
    text = resume_text.lower()
    senior_count = sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text)) for kw in senior_keywords)
    junior_count = sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text)) for kw in junior_keywords)
    
    # Try finding year span
    years = [int(y) for y in re.findall(r'\b(20\d{2})\b', text)]
    if years:
        try:
            min_year = min(years)
            from datetime import datetime
            span = datetime.now().year - min_year
            if span >= 6:
                level = "Senior"
            elif span <= 2:
                level = "Junior"
        except Exception:
            pass
            
    if senior_count > junior_count and senior_count >= 1:
        level = "Senior"
    elif junior_count > senior_count and junior_count >= 1:
        level = "Junior"
        
    return level

def generate_first_question(resume_text: str, target_role: str, experience_level: str = None) -> str:
    """
    Generates the initial interview question.
    Must reference something specific from the candidate's resume (e.g., a project, tool, or skill).
    Calibrates difficulty based on candidate experience level.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    
    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and structured interview by dynamically generating the first question.

Candidate's Experience Level: {level}

Task:
Generate the FIRST question of the interview.

QUESTION GENERATION RULES:
1. Resume Grounding: This first question MUST explicitly reference a specific detail from the candidate's resume (e.g., a specific project, tool, database, framework, or company they worked at, or a skill they claimed, like: "I see on your resume that you implemented a Redis caching strategy at TechCorp. Can you walk me through...").
2. Pillar Focus: Start with either a specific Work Experience Detail or a Project Architecture breakdown listed on their resume.
3. Calibrate the question difficulty and technical depth to match their experience level ({level}):
   - If Junior: Ask about basic usage, implementation steps, and understanding of core principles.
   - If Mid-Level: Ask about performance optimizations, integration patterns, and concrete challenges.
   - If Senior: Ask about architectural design decisions, scalability trade-offs, system failures, and leadership context.

OUTPUT FORMAT:
Output your response in clear, conversational text as the Interviewer. Do not include any meta-commentary, headers, or explanations of your logic. Just ask the question.

Candidate's Resume:
{resume_text}
"""
    response = ask_llm(prompt)
    return response.strip()

def generate_next_question(resume_text: str, target_role: str, history: list, experience_level: str = None) -> str:
    """
    Generates a new, fresh question for the interview based on the role, resume, and history.
    Calibrates difficulty based on candidate experience level.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    
    # Format history for the prompt
    history_str = ""
    for idx, turn in enumerate(history):
        role = "Interviewer" if turn["role"] == "interviewer" else "Candidate"
        content = turn["content"]
        history_str += f"{role}: {content}\n"
        
    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and completely non-repetitive interview by dynamically generating the next question.

Candidate's Experience Level: {level}

Candidate's Resume:
{resume_text}

Interview History (Transcript):
{history_str}

---

QUESTION GENERATION RULES:
1. Zero Repetition Guardrail: Check the Interview History. You are strictly forbidden from asking a question on the exact same topic, metric, or project unless you are explicitly digging deeper into a loophole in their previous answer.
2. Keyword Hooking: Analyze the candidate's last response in the transcript. Identify specific technical keywords, libraries, or architectural terms they just used (e.g. if they mentioned 'caching with Redis', hook onto 'cache eviction policies' or 'data persistence options in Redis').
3. Pillar Rotation: Alternate your focus across the interview. Do not cluster all questions around one area. Switch intelligently between:
   - Work Experience Detail: Deep-diving into scaling, trade-offs, or real-world constraints from a previous company.
   - Project Architecture: Breaking down specific tool selections, bottlenecks, or deployment strategies from their listed projects (e.g., analyzing agent frameworks, database schemas, or cloud pipelines).
   - Foundational / Core Engineering: Testing core algorithmic logic, optimization (Big O), database joins, or data pipelines.

EXECUTABLE BEHAVIOR:
- Pivot to a completely different node of their resume (e.g., shift from an engineering project to a specific tool or work experience metric) to test their breadth, ensuring you alternate pillars.
- Calibrate the question difficulty and technical depth to match their experience level ({level}):
  - If Junior: Ask about basic usage, implementation steps, and understanding of core principles.
  - If Mid-Level: Ask about performance optimizations, integration patterns, and concrete challenges.
  - If Senior: Ask about architectural design decisions, scalability trade-offs, system failures, and leadership context.

OUTPUT FORMAT:
Output your response in clear, conversational text as the Interviewer. Do not include any meta-commentary, headers, or explanations of your logic. Just ask the question.
"""
    response = ask_llm(prompt)
    return response.strip()

def generate_follow_up(resume_text: str, target_role: str, question: str, answer: str, experience_level: str = None) -> str:
    """
    Generates a targeted follow-up question digging deeper on the candidate's weak or vague answer.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    
    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and targeted interview follow-up.

The candidate gave a weak or vague answer to a question. You need to ask ONE targeted follow-up question to dig deeper and challenge them to provide more specificity, technical depth, or concrete evidence.

Candidate's Experience Level: {level}

Original Question:
{question}

Candidate's Answer:
{answer}

---

QUESTION GENERATION RULES:
1. Keyword Hooking: Analyze the candidate's answer. Identify specific technical keywords, libraries, or architectural terms they just used (e.g. if they mentioned 'data cleaning', hook onto 'imputation methods' or 'handling data skew').
2. Deep-Dive targeted behavior: Do not change the subject. Generate a targeted follow-up question that explicitly forces them to defend their design choices or name concrete tools/metrics/libraries they would use.
3. Calibrate the question difficulty and technical depth to match their experience level ({level}):
   - If Junior: Focus on explaining basic steps, mechanics, or simple code choices.
   - If Mid-Level: Focus on production configuration, security, and metrics.
   - If Senior: Focus on failovers, scalability under load, enterprise compliance, and system failure modes.

OUTPUT FORMAT:
Output your response in clear, conversational text as the Interviewer. Do not include any meta-commentary, headers, or explanations of your logic. Just ask the follow-up question.
"""
    response = ask_llm(prompt)
    return response.strip()
