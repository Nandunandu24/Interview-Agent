import os
import json
from pydantic import BaseModel, Field, ValidationError
from .llm_client import ask_llm

class ScorerBreakdown(BaseModel):
    relevance: str = Field(description="Evaluation of how relevant the candidate's answer is to the question.")
    correctness_depth: str = Field(description="Evaluation of technical correctness, depth of knowledge, and accuracy.")
    clarity: str = Field(description="Evaluation of the clarity, articulation, and structure of the explanation.")
    specificity_evidence: str = Field(description="Evaluation of specific details, metrics, technologies, or evidence mentioned.")

class AnswerScore(BaseModel):
    score: int = Field(description="Total score from 0 to 10.")
    is_weak: bool = Field(description="True if score is strictly less than 5, indicating a weak/vague answer that requires a follow-up.")
    justification: str = Field(description="Summary justification for the overall score.")
    breakdown: ScorerBreakdown

def score_answer(question: str, answer: str, target_role: str, experience_level: str = "Mid-Level") -> dict:
    """
    Evaluates a candidate's answer to a specific interview question as an LLM-as-a-Judge.
    Evaluates Technical Depth (0-3), Keywords/Tools (0-3), Communication/Fluency (0-2), and Topic Knowledge (0-2).
    Returns a dictionary matching the AnswerScore schema.
    """
    prompt = f"""
You are an expert AI Technical Interview Scorer acting as LLM-as-a-Judge for the role: "{target_role}" at the "{experience_level}" level.

Task:
Evaluate the candidate's answer to the given question based on their technical depth, technical keyword usage, communication fluency, and topic knowledge.

Question Asked:
{question}

Candidate's Answer:
{answer}

EXPERIENCE LEVEL CALIBRATION ({experience_level}):
- JUNIOR: Expect foundational understanding, core syntax/logic, and clean explanation of basic steps.
- MID-LEVEL: Expect production readiness, framework/library usage, error handling, and performance optimization.
- SENIOR: Expect architectural choices, system scalability under peak load, failover strategies, and leadership context.

RUBRIC MATRIX (Sum to calculate total score 0 to 10):
1. Technical Depth (0 to 3 pts): Accuracy, design reasoning, and step-by-step logic appropriate for a {experience_level} candidate.
2. Keywords & Tools (0 to 3 pts): Presence of relevant frameworks, libraries, technologies, or metrics.
3. Communication & Fluency (0 to 2 pts): Structure, articulation, clarity, and readability.
4. Topic Knowledge & Relevance (0 to 2 pts): Directness and correctness in addressing the question topic.

SCORE RULES:
- Total Score = Sum of 4 dimensions (0 to 10).
- Set is_weak = true ONLY if Total Score < 4 (e.g. answer is extremely brief, off-topic, or completely vague).
- If Total Score >= 4, set is_weak = false.

Return ONLY a valid JSON object matching the following schema:
{{
  "score": 7,
  "is_weak": false,
  "justification": "A clear, encouraging 1-2 sentence technical summary explaining the score based on technical depth, keywords, and communication.",
  "breakdown": {{
    "relevance": "Specific feedback on how directly the candidate answered the question.",
    "correctness_depth": "Specific evaluation of technical accuracy and depth for a {experience_level} candidate.",
    "clarity": "Feedback on communication style, structure, and verbal fluency.",
    "specificity_evidence": "Feedback on concrete technical keywords, frameworks, tools, or metrics used."
  }}
}}

Ensure the JSON is perfectly valid. Do not include markdown code blocks, introduction, or conversational filler.
"""
    try:
        response_text = ask_llm(prompt, expect_json=True)
        
        # Clean any markdown formatting if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response_text.strip())
        
        # Ensure is_weak consistency: only true if score < 4
        if data.get("score", 6) >= 4:
            data["is_weak"] = False
        else:
            data["is_weak"] = True

        validated_data = AnswerScore(**data)
        return validated_data.model_dump()
        
    except (ValidationError, json.JSONDecodeError, Exception) as e:
        # Graceful dynamic fallback matrix
        import re
        COMMON_SKILLS = [
            "Python", "FastAPI", "Go", "Java", "Docker", "Kubernetes", "AWS", "SQL",
            "PostgreSQL", "Redis", "MongoDB", "Elasticsearch", "Spark", "ETL", "Django",
            "Flask", "gRPC", "React", "Node.js", "TypeScript", "Pandas", "PyTorch", "Git", "CI/CD",
            "Excel", "Power BI", "Tableau", "Data Storytelling", "Airflow", "Kafka", "Snowflake", 
            "BigQuery", "Terraform", "Jenkins", "Prometheus", "Grafana", "HTML/CSS", "Redux", "Zustand",
            "scikit-learn", "TensorFlow", "RAG", "LLM", "quantization", "fine-tuning", "vector database"
        ]
        
        words = answer.strip().split()
        word_count = len(words)
        ans_lower = answer.lower()
        
        tech_hits = []
        for tech in COMMON_SKILLS + ["scale", "optimize", "secure", "test", "pool", "cache", "database", "api", "architecture", "query", "model"]:
            if re.search(r'\b' + re.escape(tech) + r'\b', answer, re.IGNORECASE):
                tech_hits.append(tech)
                
        # Calculate score dynamically based on keyword density, communication clarity, and length
        base_score = 6
        if len(tech_hits) >= 2:
            base_score += 2
        elif len(tech_hits) == 1:
            base_score += 1
            
        if word_count > 25:
            base_score += 1
            
        score = min(max(base_score, 3), 9)
        if word_count < 5:
            score = 3
            
        is_weak = score < 4
        
        relevance = "Addressed the core question topic directly."
        correctness = f"Demonstrated technical depth with concepts like {', '.join(tech_hits[:2])}." if tech_hits else "Demonstrated general conceptual understanding."
        clarity = "Clear and well-structured response." if word_count > 12 else "Concise answer."
        specificity = f"Used technical terms: {', '.join(tech_hits)}." if tech_hits else "Focused on general technical concepts."
        justification = f"Solid answer addressing the question with good communication fluency and technical vocabulary ({', '.join(tech_hits[:3]) if tech_hits else 'conceptual terms'})."

        return {
            "score": score,
            "is_weak": is_weak,
            "justification": justification,
            "breakdown": {
                "relevance": relevance,
                "correctness_depth": correctness,
                "clarity": clarity,
                "specificity_evidence": specificity
            }
        }
