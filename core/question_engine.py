import os
import json
import re
from .llm_client import ask_llm

from .rag_engine import ResumeRAG

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

def _get_rag_context_block(resume_text: str, query_str: str, rag_instance: ResumeRAG = None, top_k: int = 3) -> str:
    """Helper to query RAG vector store and build a formatted context block."""
    if not rag_instance:
        rag_instance = ResumeRAG(resume_text)
    retrieved_chunks = rag_instance.query(query_str, top_k=top_k)
    if retrieved_chunks:
        chunks_text = "\n---\n".join(f"[Chunk {idx+1}]: {c}" for idx, c in enumerate(retrieved_chunks))
        return f"\n=== RETRIEVED RESUME CONTEXT (RAG VECTOR SEARCH) ===\n{chunks_text}\n"
    return ""

def generate_first_question(resume_text: str, target_role: str, experience_level: str = None, rag_instance: ResumeRAG = None) -> str:
    """
    Generates the initial interview question grounded strictly in candidate skills, projects, experience, and target role.
    Calibrates difficulty based on candidate experience level. Uses RAG vector retrieval.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    rag_context = _get_rag_context_block(resume_text, f"{target_role} projects experience skills", rag_instance=rag_instance, top_k=3)
    
    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and structured interview by dynamically generating the first question.

Target Role Chosen: "{target_role}"
Candidate's Experience Level: {level}

{rag_context}

Candidate's Resume:
{resume_text}

Task:
Generate the FIRST question of the interview.

QUESTION GENERATION RULES:
1. Resume & Role Grounding: This question MUST explicitly reference specific skills, projects, or work experience listed on the candidate's resume (e.g., a specific project architecture, framework, database, tool, or work experience detail) and tie it directly to the chosen role: "{target_role}".
2. Pillar Focus: Start with either a specific Work Experience Detail or a Project Architecture breakdown listed on their resume.
3. Calibrate question difficulty and technical depth to match their experience level ({level}):
   - If Junior: Ask about core principles, basic usage, implementation steps, and problem-solving logic.
   - If Mid-Level: Ask about performance optimizations, integration patterns, edge cases, and concrete engineering challenges.
   - If Senior: Ask about architectural design decisions, scalability trade-offs, system failures, and leadership context.

OUTPUT FORMAT:
Output your response in clear, conversational text as the Interviewer. Do not include any meta-commentary, headers, or explanations of your logic. Just ask the question.
"""
    response = ask_llm(prompt)
    return response.strip()

def generate_next_question(resume_text: str, target_role: str, history: list, experience_level: str = None, rag_instance: ResumeRAG = None) -> str:
    """
    Generates a new, fresh question for the interview based on the role, resume skills/projects/experience, and candidate answer.
    Calibrates difficulty based on candidate experience level. Uses RAG vector retrieval.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    
    # Format history for the prompt
    history_str = ""
    last_candidate_ans = ""
    for idx, turn in enumerate(history):
        role = "Interviewer" if turn["role"] == "interviewer" else "Candidate"
        content = turn["content"]
        history_str += f"{role}: {content}\n"
        if turn["role"] == "candidate":
            last_candidate_ans = content
        
    rag_query = f"{target_role} {last_candidate_ans}" if last_candidate_ans else target_role
    rag_context = _get_rag_context_block(resume_text, rag_query, rag_instance=rag_instance, top_k=3)

    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and completely non-repetitive interview by dynamically generating the next question.

Target Role Chosen: "{target_role}"
Candidate's Experience Level: {level}

{rag_context}

Candidate's Resume (Skills, Projects, Experience):
{resume_text}

Interview History (Transcript & Candidate Answers):
{history_str}

---

QUESTION GENERATION RULES:
1. Candidate Answer & Resume Synthesis: Analyze the candidate's LAST answer. Identify specific technical tools, concepts, or solutions they mentioned. Bridge their answer directly into another skill, project, or work experience bullet from their resume.
2. Zero Repetition Guardrail: Check the Interview History. You are strictly forbidden from asking a question on the exact same topic, metric, or project unless you are explicitly digging deeper into a loophole in their previous answer.
3. Pillar Rotation: Alternate your focus across the interview. Do not cluster all questions around one area. Switch intelligently between:
   - Work Experience Detail: Deep-diving into scaling, trade-offs, or real-world constraints from a previous role.
   - Project Architecture: Breaking down specific tool selections, bottlenecks, or deployment strategies from their listed projects.
   - Skills & Core Engineering: Testing core algorithms, frameworks, tools, or domain concepts essential for {target_role}.

4. Calibrate question difficulty and technical depth to match their experience level ({level}):
  - If Junior: Ask about core principles, basic usage, implementation steps, and logic.
  - If Mid-Level: Ask about performance optimizations, integration patterns, and concrete challenges.
  - If Senior: Ask about architectural design decisions, scalability trade-offs, system failures, and leadership context.

OUTPUT FORMAT:
Output your response in clear, conversational text as the Interviewer. Do not include any meta-commentary, headers, or explanations of your logic. Just ask the question.
"""
    response = ask_llm(prompt)
    return response.strip()

def generate_follow_up(resume_text: str, target_role: str, question: str, answer: str, experience_level: str = None, rag_instance: ResumeRAG = None) -> str:
    """
    Generates a targeted follow-up question digging deeper on the candidate's weak or vague answer.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    rag_context = _get_rag_context_block(resume_text, f"{question} {answer}", rag_instance=rag_instance, top_k=3)

    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and targeted interview follow-up.

The candidate gave a weak or vague answer to a question. You need to ask ONE targeted follow-up question to dig deeper and challenge them to provide more specificity, technical depth, or concrete evidence based on their resume skills, projects, candidate answer, and chosen role ({target_role}).

Target Role Chosen: "{target_role}"
Candidate's Experience Level: {level}

{rag_context}

Original Question:
{question}

Candidate's Answer:
{answer}

Candidate's Resume:
{resume_text}

---

QUESTION GENERATION RULES:
1. Candidate Answer Hooking: Analyze the candidate's answer. Identify specific technical keywords, tools, or concepts they mentioned or omitted.
2. Cross-Reference Resume Skills & Projects: Bridge their weak answer to specific projects, skills, or experience listed on their resume.
3. Deep-Dive behavior: Challenge them to defend their technical choices, explain implementation steps, or provide concrete metrics relevant to a {level} candidate in the {target_role} role.

OUTPUT FORMAT:
Output your response in clear, conversational text as the Interviewer. Do not include any meta-commentary, headers, or explanations of your logic. Just ask the follow-up question.
"""
    response = ask_llm(prompt)
    return response.strip()

