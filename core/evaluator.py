import os
import json
from pydantic import BaseModel, Field, ValidationError
from .llm_client import ask_llm

class DimensionEvaluation(BaseModel):
    score: int = Field(description="Score from 1 to 5 (1 = Critical Gaps, 3 = Meets Expectations, 5 = Exceptional).")
    evidence: str = Field(description="Specific, verbatim text or conceptual evidence from the transcript to back up the score.")

class DetailedTechnical(BaseModel):
    accuracy: str = Field(description="Did they solve the core problem correctly? Note any bugs or logical fallacies.")
    optimization: str = Field(description="Did they discuss time/space complexity or system design trade-offs? Quote their reasoning.")
    edge_cases: str = Field(description="Did they proactively consider constraints or fail to see blind spots?")

class FeedbackBlock(BaseModel):
    candidate: str = Field(description="Concrete advice on what they should study, how they can structure their answers better, or technical gaps to close.")
    hiring_team: str = Field(description="Specific suggestions on what to double-check or dive deeper into during a subsequent live round, based on weak spots spotted by the agent.")

class FinalEvaluation(BaseModel):
    overall_score: int = Field(description="Overall interview score on a scale of 0 to 100.")
    scoring_formula: str = Field(description="The formula used to calculate overall_score.")
    verdict: str = Field(description="Overall verdict: 'Strong Hire', 'Hire', 'Borderline', or 'No Hire'.")
    key_strengths: str = Field(description="1-2 sentences summarizing major highlights.")
    growth_areas: str = Field(description="1-2 sentences summarizing biggest gaps.")
    communication_skills: DimensionEvaluation
    technical_depth: DimensionEvaluation
    topic_knowledge: DimensionEvaluation
    problem_solving_adaptability: DimensionEvaluation
    detailed_technical: DetailedTechnical
    feedback: FeedbackBlock

def generate_evaluation(target_role: str, history: list, experience_level: str = "Mid-Level") -> dict:
    """
    Analyzes the interview history and generates a comprehensive final evaluation calibrated to the target role and experience level.
    """
    # Calculate simple math for average of scores
    valid_scores = [turn["score"] for turn in history if "score" in turn]
    avg_score_10 = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    computed_overall_score = round(avg_score_10 * 10) # convert to 0-100
    
    # Format history and calculated score for prompt
    history_str = ""
    for idx, turn in enumerate(history):
        if turn["role"] == "interviewer":
            history_str += f"Interviewer: {turn['content']}\n"
        else:
            score = turn.get("score", "N/A")
            justification = turn.get("justification", "N/A")
            history_str += f"Candidate: {turn['content']}\n(Score: {score}/10 | Feedback: {justification})\n\n"

    prompt = f"""
You are an expert AI Technical Interview Evaluator. Your task is to analyze the provided interview transcript for the role "{target_role}" at the "{experience_level}" level and generate a highly structured, objective, and actionable Candidate Assessment Report.

Target Role: {target_role}
Candidate Experience Level: {experience_level}

Interview Transcript with Scores:
{history_str}

Computed Overall Score: {computed_overall_score} out of 100
Formula: (Average of all question scores) * 10

VERDICT CALIBRATION RULES BASED ON OVERALL SCORE ({computed_overall_score}/100):
- Score >= 80: "Strong Hire" (Demonstrates exceptional technical depth, communication fluency, and topic mastery).
- Score 68 - 79: "Hire" (Meets expectations with solid technical accuracy and clear communication).
- Score 50 - 67: "Borderline" (Requires further live evaluation; candidate demonstrated partial topic knowledge or clarity gaps).
- Score < 50: "No Hire" (Significant technical, communication, or topic mastery gaps).

EVALUATION CALIBRATION RULES FOR {experience_level.upper()} LEVEL:
- If JUNIOR: Assess whether candidate demonstrated solid core understanding, correct basic logic, and clean explanation of foundational concepts. Do not dock points for lacking enterprise architecture or complex scale/failover trade-offs.
- If MID-LEVEL: Assess production readiness, concrete library/tool usage, error handling, performance optimization, and testing practices.
- If SENIOR: Assess architectural design choices, system scalability under peak load, failover resilience, security compliance, and leadership/trade-off context.

Task:
Generate a final assessment matching the following exact JSON structure:
{{
  "verdict": "Strong Hire | Hire | Borderline | No Hire",
  "key_strengths": "1-2 sentences summarizing major highlights relative to {experience_level} expectations.",
  "growth_areas": "1-2 sentences summarizing biggest technical or communication gaps for a {experience_level} engineer.",
  
  "communication_skills": {{
    "score": 4,
    "evidence": "Evaluation of articulation, clarity, fluency, and communication style based on transcript."
  }},
  "technical_depth": {{
    "score": 3,
    "evidence": "Evaluation of technical accuracy, depth, and design reasoning demonstrated for a {experience_level} candidate in {target_role}."
  }},
  "topic_knowledge": {{
    "score": 3,
    "evidence": "Evaluation of specific domain knowledge, technology concepts, and framework mastery demonstrated."
  }},
  "problem_solving_adaptability": {{
    "score": 3,
    "evidence": "How they handled follow-ups, constraints, or initially approached the technical problem."
  }},
  
  "detailed_technical": {{
    "accuracy": "Did they solve the core technical problems correctly? Note any bugs, misconceptions, or strong answers.",
    "optimization": "Did they discuss complexity, performance, or system design trade-offs appropriate for a {experience_level} candidate?",
    "edge_cases": "Did they consider constraints or fail to see blind spots relative to {experience_level} standards?"
  }},
  
  "feedback": {{
    "candidate": "Concrete advice on what they should study, how they can structure their answers better, or technical gaps to close for a {experience_level} candidate.",
    "hiring_team": "Specific suggestions on what to double-check or dive deeper into during a subsequent live round, based on weak spots spotted by the agent."
  }}
}}

Ensure scores for communication_skills, technical_depth, topic_knowledge, and problem_solving_adaptability are from 1 to 5 (1 = Critical Gaps, 3 = Meets Expectations, 5 = Exceptional).
Return ONLY a valid JSON object matching the schema. Do not include markdown code blocks, introductory text, or conversational lines.
"""
    try:
        response_text = ask_llm(prompt, expect_json=True)
        
        # Clean any markdown formatting if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response_text.strip())
        
        # Override score to maintain strict mathematical consistency
        data["overall_score"] = computed_overall_score
        data["scoring_formula"] = "Average of all question scores (fresh and follow-up) scaled out of 100: (Sum of scores / Number of questions) * 10"
        
        if computed_overall_score >= 78:
            data["verdict"] = "Strong Hire"
        elif computed_overall_score >= 64:
            data["verdict"] = "Hire"
        elif computed_overall_score >= 48:
            data["verdict"] = "Borderline"
        else:
            data["verdict"] = "No Hire"
            
        validated_data = FinalEvaluation(**data)
        return validated_data.model_dump()
        
    except (ValidationError, json.JSONDecodeError, Exception) as e:
        # Fallback evaluation
        rec = "Borderline"
        if computed_overall_score >= 78:
            rec = "Strong Hire"
        elif computed_overall_score >= 64:
            rec = "Hire"
        elif computed_overall_score < 48:
            rec = "No Hire"
            
        return {
            "overall_score": computed_overall_score,
            "scoring_formula": "Average of all question scores (fresh and follow-up) scaled out of 100: (Sum of scores / Number of questions) * 10",
            "verdict": rec,
            "key_strengths": "Completed responses for all questions during the interview.",
            "growth_areas": "Evaluation compiled under fallback mode; detailed gaps should be verified.",
            "communication_skills": {
                "score": 3,
                "evidence": "Maintained basic response flow and responded to all questions."
            },
            "technical_depth": {
                "score": 3,
                "evidence": "Concepts were described but depth should be verified in code challenges."
            },
            "topic_knowledge": {
                "score": 3,
                "evidence": "Demonstrated foundational topic knowledge across the resume skills."
            },
            "problem_solving_adaptability": {
                "score": 3,
                "evidence": "Answered questions based on the resume topics without deviation."
            },
            "detailed_technical": {
                "accuracy": "No major compilation or syntax issues identified in verbal responses.",
                "optimization": "Not discussed in depth; should be verified via hands-on exercises.",
                "edge_cases": "Not proactively addressed in the short verbal responses."
            },
            "feedback": {
                "candidate": "Study specific libraries and frameworks related to your target role.",
                "hiring_team": "Verify practical coding, optimization, and edge-case handling in a live interview."
            }
        }
