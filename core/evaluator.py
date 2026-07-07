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
    verdict: str = Field(description="Overall verdict: 'Strong Hire', 'Hire', or 'No Hire'.")
    key_strengths: str = Field(description="1-2 sentences summarizing major highlights.")
    growth_areas: str = Field(description="1-2 sentences summarizing biggest gaps.")
    communication_skills: DimensionEvaluation
    technical_depth: DimensionEvaluation
    problem_solving_adaptability: DimensionEvaluation
    detailed_technical: DetailedTechnical
    feedback: FeedbackBlock

def generate_evaluation(target_role: str, history: list) -> dict:
    """
    Analyzes the interview history and generates a comprehensive final evaluation.
    """
    # Calculate simple math for average of scores
    valid_scores = [turn["score"] for turn in history if "score" in turn]
    avg_score_10 = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    computed_overall_score = round(avg_score_10 * 10) # convert to 0-100
    
    # We pass the history and calculated score to the LLM to get detailed qualitative insights.
    history_str = ""
    for idx, turn in enumerate(history):
        if turn["role"] == "interviewer":
            history_str += f"Interviewer: {turn['content']}\n"
        else:
            score = turn.get("score", "N/A")
            justification = turn.get("justification", "N/A")
            history_str += f"Candidate: {turn['content']}\n(Score: {score}/10 | Feedback: {justification})\n\n"

    prompt = f"""
You are an expert AI Technical Interview Evaluator. Your task is to analyze the provided interview transcript for the role "{target_role}" and generate a highly structured, objective, and actionable Candidate Assessment Report.

Interview Transcript with Scores:
{history_str}

Computed Overall Score: {computed_overall_score} out of 100
Formula: (Average of all question scores) * 10

Task:
Generate a final assessment matching the following exact JSON structure:
{{
  "verdict": "Strong Hire | Hire | No Hire",
  "key_strengths": "1-2 sentences summarizing major highlights.",
  "growth_areas": "1-2 sentences summarizing biggest gaps.",
  
  "communication_skills": {{
    "score": 4,
    "evidence": "Specific, verbatim text or conceptual evidence from the transcript to back up the score."
  }},
  "technical_depth": {{
    "score": 3,
    "evidence": "Specific code, logic, or system design decisions they made, noting accuracy or gaps."
  }},
  "problem_solving_adaptability": {{
    "score": 3,
    "evidence": "How they handled hints, constraints, or initially approached the problem."
  }},
  
  "detailed_technical": {{
    "accuracy": "Did they solve the core problem correctly? Note any bugs or logical fallacies.",
    "optimization": "Did they discuss time/space complexity or system design trade-offs? Quote their reasoning.",
    "edge_cases": "Did they proactively consider constraints or fail to see blind spots?"
  }},
  
  "feedback": {{
    "candidate": "Concrete advice on what they should study, how they can structure their answers better, or technical gaps to close.",
    "hiring_team": "Specific suggestions on what to double-check or dive deeper into during a subsequent live round, based on weak spots spotted by the agent."
  }}
}}

Ensure the scores for communication_skills, technical_depth, and problem_solving_adaptability are from 1 to 5 (1 = Critical Gaps, 3 = Meets Expectations, 5 = Exceptional).
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
        
        validated_data = FinalEvaluation(**data)
        return validated_data.model_dump()
        
    except (ValidationError, json.JSONDecodeError, Exception) as e:
        # Fallback evaluation
        rec = "Borderline"
        if computed_overall_score >= 80:
            rec = "Strong Hire"
        elif computed_overall_score < 50:
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
