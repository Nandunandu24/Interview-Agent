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
    Generates the initial interview question.
    Must reference something specific from the candidate's resume (e.g., a project, tool, or skill).
    Calibrates difficulty based on candidate experience level. Uses RAG vector retrieval.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    rag_context = _get_rag_context_block(resume_text, f"{target_role} projects experience skills", rag_instance=rag_instance, top_k=3)
    
    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and structured interview by dynamically generating the first question.

Candidate's Experience Level: {level}
{rag_context}
Task:
Generate the FIRST question of the interview.

QUESTION GENERATION RULES:
1. Resume Grounding: This first question MUST explicitly reference a specific detail from the candidate's resume or retrieved RAG context (e.g., a specific project, tool, database, framework, or company they worked at, or a skill they claimed).
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

def generate_next_question(resume_text: str, target_role: str, history: list, experience_level: str = None, rag_instance: ResumeRAG = None) -> str:
    """
    Generates a new, fresh question for the interview based on the role, resume, and history.
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

Candidate's Experience Level: {level}
{rag_context}
Candidate's Resume:
{resume_text}

Interview History (Transcript):
{history_str}

---

QUESTION GENERATION RULES:
1. Zero Repetition Guardrail: Check the Interview History. You are strictly forbidden from asking a question on the exact same topic, metric, or project unless you are explicitly digging deeper into a loophole in their previous answer.
2. Keyword Hooking: Analyze the candidate's last response in the transcript. Identify specific technical keywords, libraries, or architectural terms they just used.
3. Pillar Rotation: Alternate your focus across the interview. Do not cluster all questions around one area. Switch intelligently between:
   - Work Experience Detail: Deep-diving into scaling, trade-offs, or real-world constraints from a previous company.
   - Project Architecture: Breaking down specific tool selections, bottlenecks, or deployment strategies from their listed projects.
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

def generate_follow_up(resume_text: str, target_role: str, question: str, answer: str, experience_level: str = None, rag_instance: ResumeRAG = None) -> str:
    """
    Generates a targeted follow-up question digging deeper on the candidate's weak or vague answer.
    """
    level = experience_level if experience_level else determine_experience_level(resume_text)
    rag_context = _get_rag_context_block(resume_text, f"{question} {answer}", rag_instance=rag_instance, top_k=3)

    prompt = f"""You are an expert, highly adaptive Technical Interviewer Agent for the role: "{target_role}". Your goal is to conduct a fluid, deep, and targeted interview follow-up.

The candidate gave a weak or vague answer to a question. You need to ask ONE targeted follow-up question to dig deeper and challenge them to provide more specificity, technical depth, or concrete evidence.

Candidate's Experience Level: {level}
{rag_context}
Original Question:
{question}

Candidate's Answer:
{answer}

---

QUESTION GENERATION RULES:
1. Keyword Hooking: Analyze the candidate's answer. Identify specific technical keywords, libraries, or architectural terms they just used.
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

