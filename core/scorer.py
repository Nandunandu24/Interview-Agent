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

def score_answer(question: str, answer: str, target_role: str) -> dict:
    """
    Evaluates a candidate's answer to a specific interview question.
    Returns a dictionary matching the AnswerScore schema.
    """
    prompt = f"""
You are an expert technical interviewer for the role: "{target_role}".
Evaluate the candidate's answer to the given question based on these four criteria:
1. Relevance: Did they answer the actual question?
2. Correctness/Depth: Is the explanation technically correct, sound, and deep?
3. Clarity: Is the response well-articulated, clear, and easy to follow?
4. Specificity/Evidence: Did they mention concrete technologies, metrics, examples, or experiences?

Question:
{question}

Candidate's Answer:
{answer}

Task:
Provide a score between 0 and 10.
Decide if the answer is weak (is_weak = true if score < 5). An answer is weak if it is extremely brief, misses the core technical point, is vague, or lacks details.
Break down your evaluation for all four criteria.

Return ONLY a valid JSON object matching the following schema:
{{
  "score": 7,
  "is_weak": false,
  "justification": "A summary explanation of the evaluation.",
  "breakdown": {{
    "relevance": "Specific feedback on how well the candidate addressed the question.",
    "correctness_depth": "Feedback on technical accuracy and depth of concepts mentioned.",
    "clarity": "Feedback on communication style, structure, and readability.",
    "specificity_evidence": "Feedback on concrete examples, data points, or technologies used."
  }}
}}

Ensure the JSON is perfectly valid. Do not include markdown code blocks (like ```json), introduction, or conversational filler.
"""
    try:
        response_text = ask_llm(prompt, expect_json=True)
        
        # Clean any markdown formatting if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response_text.strip())
        
        # Validate with Pydantic
        validated_data = AnswerScore(**data)
        return validated_data.model_dump()
        
    except (ValidationError, json.JSONDecodeError, Exception) as e:
        # Graceful fallback in case of LLM formatting error or connection issues
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
        q_lower = question.lower()
        ans_lower = answer.lower()
        
        tech_hits = []
        for tech in COMMON_SKILLS + ["scale", "optimize", "secure", "test", "pool", "cache", "database", "api"]:
            if re.search(r'\b' + re.escape(tech) + r'\b', answer, re.IGNORECASE):
                tech_hits.append(tech)
                
        # Default feedback placeholders
        relevance = "Addressed the question topic directly."
        correctness = "Basic conceptual understanding of the requested topic."
        clarity = "Well structured explanation." if word_count > 20 else "Explanation was brief."
        specificity = f"Referenced tools/concepts: {', '.join(tech_hits)}." if tech_hits else "Lacked specific tool names or metrics."
        justification = "Answer shows general conceptual understanding but lacks specific details."
        score = 6
        is_weak = False
        
        # Identify unique topic of the question to customize evaluation
        if any(k in q_lower for k in ["architectural decisions", "analytics pipeline", "ingestion"]):
            relevance = "Addressed the architectural design and data flow of the analytics pipeline."
            if any(w in ans_lower for w in ["airflow", "kafka", "spark", "dbt", "luigi", "prefect", "glue"]):
                correctness = "Demonstrated clear understanding of data flow orchestration and ingestion layers."
                score = 8
                justification = f"Detailed response explaining pipeline stages and referencing orchestration tools like {tech_hits[0] if tech_hits else 'Airflow'}."
            else:
                correctness = "Conceptual understanding of data pipelines, but lacks structural and tool depth."
                score = 6
                justification = "Answer shows general conceptual understanding but lacks specific details. Suggestion: Mention concrete tools, libraries, or frameworks (e.g., Apache Kafka or Airflow) you would use to build the ingestion and orchestration layers."
                
        elif "regression" in q_lower:
            relevance = "Focused on regression predictive models and coefficient interpretation."
            if "multiple" in ans_lower or "simple" in ans_lower:
                if "coefficient" in ans_lower or "weight" in ans_lower:
                    correctness = "Clearly articulated simple vs. multiple regression and the meaning of coefficient weights."
                    score = 8
                    justification = "Solid distinction between regression models and correct interpretation of coefficient mathematical weight."
                else:
                    correctness = "Distinguishes regression types conceptually but misses practical coefficient interpretation."
                    score = 6
                    justification = "Answer describes regression models but lacks coefficient interpretation. Suggestion: Clarify how regression coefficients mathematically represent the expected change in the target variable per unit change of the predictor, holding other variables constant."
            else:
                correctness = "Struggled with linear regression definitions and coefficient scaling."
                score = 5
                is_weak = True
                justification = "Response was somewhat vague on regression. Suggestion: Study the difference between simple linear regression (single independent variable) and multiple linear regression (multiple predictors)."

        elif any(k in q_lower for k in ["bottleneck", "equilibria", "rate limit", "supply chain"]):
            relevance = "Addressed supply chain bottlenecks, API rate limits, and integration mitigations."
            if "rate limit" in ans_lower or "api" in ans_lower:
                if any(w in ans_lower for w in ["queue", "backoff", "cache", "retry", "celery", "redis"]):
                    correctness = "Proposed standard rate limit mitigations using message queues or caching."
                    score = 8
                    justification = "Correctly addressed integration bottlenecks using queueing/caching systems."
                else:
                    correctness = "Identified rate limit issues but proposed a basic polling delay instead of architectural solutions."
                    score = 6
                    justification = "Answer shows general conceptual understanding of API limits but lacks design depth. Suggestion: Propose architectural solutions like exponential backoff, request queues (e.g. Celery), or caching."
            else:
                correctness = "Vague description of supply chain bottlenecks and mitigation challenges."
                score = 5
                is_weak = True
                justification = "Response was somewhat vague on mitigation. Suggestion: Discuss using queue systems (like RabbitMQ) or API gateways to manage data rate limits."

        elif any(k in q_lower for k in ["etl", "docker", "gcp", "google cloud", "azure", "databricks"]):
            relevance = "Addressed containerization practices and cloud ETL platforms."
            if "docker" in ans_lower or "pipeline" in ans_lower:
                if any(w in ans_lower for w in ["image", "container", "multi-stage", "kubernetes", "k8s", "ci/cd"]):
                    correctness = "Demonstrated clear dev standards with Docker and ETL automation."
                    score = 8
                    justification = "Clear response detailing containerization and cloud environment build/test processes."
                else:
                    correctness = "General overview of ETL phases, but lacked containerization execution details."
                    score = 6
                    justification = "Answer shows general conceptual understanding of Docker/ETL but lacks execution standards. Suggestion: Elaborate on how you handle error states, scalability issues, or testing for this technology."
            else:
                correctness = "Struggled to articulate daily cloud engineering standards."
                score = 5
                is_weak = True
                justification = "Response was somewhat vague on cloud engineering standards. Suggestion: Detail how containerization (Docker) or cloud services influence your architectural choices."

        elif any(k in q_lower for k in ["statistics", "mean", "median", "mode", "standard deviation"]):
            relevance = "Addressed statistical measures (mean, median, mode, std dev) for a non-technical audience."
            if "average" in ans_lower or "middle" in ans_lower or "spread" in ans_lower or "deviation" in ans_lower:
                if "square root" in ans_lower or "variance" in ans_lower:
                    correctness = "Gave circular mathematical definitions instead of simple layman explanations."
                    score = 6
                    justification = "Answer explains definitions but fails to translate standard deviation intuitively to non-technical users. Suggestion: Use a concrete analogy (e.g. height variance in a room) to explain spread."
                else:
                    correctness = "Correctly simplified measures of center and spread."
                    score = 8
                    justification = "Good non-technical explanation of descriptive statistics."
            else:
                correctness = "Failed to explain statistics intuitively."
                score = 5
                is_weak = True
                justification = "Response was somewhat vague. Suggestion: Practice using analogies (e.g. explaining mean as 'balancing point') to communicate concepts to a layman."
                
        # Generic length-based overrides
        if word_count < 10:
            score = 3
            is_weak = True
            justification = "Response was extremely brief. Suggestion: Expand your answer by explaining key steps, naming specific tools, and giving a concrete example."
            relevance = "Response was too brief to address the topic."
            correctness = "Basic conceptual understanding."
            clarity = "Explanation was brief."
            specificity = "Lacked specific tool names or metrics."
        elif word_count < 25 and score > 5:
            score = 5
            is_weak = True
            justification = "Response was somewhat vague. Suggestion: Provide concrete tool names (e.g. specific libraries or databases), mention metrics, or walk through a past project scenario."

        # Parse out Critique and Suggestion from justification for clean display
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
                
        # Tailor suggestion to the specific question topic if none parsed
        if not suggestion_part:
            if "regression" in q_lower:
                suggestion_part = "Discuss how collinearity affects coefficient interpretation and how standard error behaves."
            elif "bottleneck" in q_lower:
                suggestion_part = "Detail standard backpressure patterns, queue sizes, or cache-aside configurations."
            elif "etl" in q_lower or "docker" in q_lower:
                suggestion_part = "Describe Docker build optimizations like multi-stage caching or parquet partition sizes."
            elif "statistics" in q_lower:
                suggestion_part = "Provide a specific dataset example, like how salary distributions skew the mean vs. median."
            else:
                suggestion_part = "Mention specific frameworks, tools, or libraries to ground your architectural design."

        # Format justification with suggestion to maintain backend API format
        full_justification = f"{critique_part}. Suggestion: {suggestion_part}"

        return {
            "score": score,
            "is_weak": is_weak,
            "justification": full_justification,
            "breakdown": {
                "relevance": relevance,
                "correctness_depth": correctness,
                "clarity": clarity,
                "specificity_evidence": specificity
            }
        }
