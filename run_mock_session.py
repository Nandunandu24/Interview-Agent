import os
import json
from datetime import datetime
from unittest.mock import patch

# We import the actual functions from our codebase
from core.resume_parser import parse_resume
from core.scorer import score_answer
from core.evaluator import generate_evaluation
from cli import save_transcript

# Define mock outputs for the LLM
MOCK_ROLE_INFERENCE = {
    "inferred_role": "Lead Backend Developer",
    "skills": ["Python", "FastAPI", "Redis", "Docker", "Kubernetes", "PostgreSQL", "Apache Spark", "gRPC"],
    "summary": "Highly experienced Backend Developer specializing in scalable distributed systems and robust data pipelines."
}

MOCK_QUESTIONS = [
    # Q1: Fresh
    "I see on your resume that you designed and implemented a high-throughput microservices architecture using Python, FastAPI, and gRPC at TechCorp. Can you walk me through a major bottleneck you encountered and how you solved it?",
    # Q2: Fresh
    "You also mentioned building ETL pipelines in Apache Spark that process over 10TB of data daily at DataInc. How did you handle data skew and partition tuning to prevent performance degradation?",
    # Q3: Fresh (Will trigger weak score)
    "Let's touch on containerization. How do you manage secrets and configuration variables in your Kubernetes deployments?",
    # Q4: Follow-up to Q3
    "You mentioned using standard secrets. Can you elaborate on how you secure those secrets at rest, and how your applications consume them (e.g. environment variables vs file mounts)?",
    # Q5: Fresh
    "How do you approach testing asynchronous tasks and API endpoints in a FastAPI application?",
    # Q6: Fresh
    "Lastly, you've mentored junior developers. Can you describe your code review philosophy and how you handle conflicts when an engineer disagrees with your feedback?"
]

MOCK_ANSWERS = [
    # A1
    "At TechCorp, our major bottleneck was database connection pooling and I/O congestion during peak traffic. We had multiple microservices querying the same PostgreSQL DB. To resolve this, I implemented connection pooling with SQLAlchemy, tuned the pool size and overflow settings, and added a Redis cache layer to store frequently accessed static configurations. This reduced read database load by 40% and improved latency by 35%.",
    # A2
    "Handling data skew was critical. We had a partition key that was heavily skewed towards a few customer IDs. To solve this, we used salting, appending a random integer to the key to distribute the data evenly across partitions. We also tuned spark.sql.shuffle.partitions to match our cluster core count, which improved our job completion times significantly.",
    # A3
    "We use standard Secrets.", # Weak/vague answer
    # A4 (Follow-up)
    "We encrypt Kubernetes secrets at rest using AWS KMS keys. In the pods, we mount secrets as files rather than injecting them directly as environment variables, which prevents them from leaking in process dumps or logs. We also use HashiCorp Vault for dynamic secret rotation.",
    # A5
    "For async tests, we use pytest-asyncio. We mock network calls using aioresponses. For integration tests, we run Docker containers using Testcontainers to spin up actual Redis and PostgreSQL instances, ensuring our tests run in clean, isolated environments.",
    # A6
    "My philosophy is to focus on the code, not the person. I use linters and formatters to automate styling arguments. When there's a disagreement, I ask them to explain their design choice and we discuss the trade-offs of both options. If needed, we reference our team guidelines or do a quick prototype."
]

MOCK_SCORINGS = [
    # S1
    {
        "score": 9,
        "is_weak": False,
        "justification": "The candidate gave a highly technical response, identifying specific database bottlenecks and implementing an effective caching and pooling solution.",
        "breakdown": {
            "relevance": "Excellent - directly addressed the bottleneck query.",
            "correctness_depth": "High depth - discussed SQLAlchemy pool tuning and Redis caching.",
            "clarity": "Very clear and structured explanation.",
            "specificity_evidence": "Specific metrics provided (40% DB load reduction, 35% latency improvement)."
        }
    },
    # S2
    {
        "score": 8,
        "is_weak": False,
        "justification": "Good answer. Explained partition skew mitigation using salting and Spark configuration tuning.",
        "breakdown": {
            "relevance": "Strong - answered about partition tuning.",
            "correctness_depth": "Correct - salting is a standard solution for Spark skew.",
            "clarity": "Clear explanation of the problem and solution.",
            "specificity_evidence": "Mentioned salting, shuffle partition config, and 10TB scale."
        }
    },
    # S3 (Weak)
    {
        "score": 3,
        "is_weak": True,
        "justification": "Extremely brief and vague. Did not explain key management, security, or injection patterns.",
        "breakdown": {
            "relevance": "Minimal - only named one concept.",
            "correctness_depth": "Low depth - no explanation of mechanics.",
            "clarity": "Too brief to evaluate clarity.",
            "specificity_evidence": "No details or tools mentioned."
        }
    },
    # S4 (Follow-up recovery)
    {
        "score": 9,
        "is_weak": False,
        "justification": "Excellent follow-up response. Correctly identified secret-at-rest encryption with KMS, file mounts to prevent environment leak, and Vault integration.",
        "breakdown": {
            "relevance": "Direct response to the follow-up prompt.",
            "correctness_depth": "High - understood security risks of environment variable injection.",
            "clarity": "Well-structured and professional.",
            "specificity_evidence": "AWS KMS, file mounts, HashiCorp Vault, dynamic rotation."
        }
    },
    # S5
    {
        "score": 9,
        "is_weak": False,
        "justification": "Very strong testing answer. Explained async pytest fixtures, network mocking, and Testcontainers integration.",
        "breakdown": {
            "relevance": "Directly answered FastAPI testing.",
            "correctness_depth": "Excellent - mentioned pytest-asyncio and Testcontainers.",
            "clarity": "Highly articulate.",
            "specificity_evidence": "pytest-asyncio, aioresponses, Testcontainers, Redis, Postgres."
        }
    },
    # S6
    {
        "score": 8,
        "is_weak": False,
        "justification": "Solid behavioral answer. Focused on code standard automation and objective debate of trade-offs.",
        "breakdown": {
            "relevance": "Directly addressed conflict and mentoring.",
            "correctness_depth": "Appropriate - standard engineering management practice.",
            "clarity": "Clear and thoughtful.",
            "specificity_evidence": "Mentioned linters, formatters, guidelines, prototyping."
        }
    }
]

MOCK_EVALUATION = {
    "overall_score": 77,
    "scoring_formula": "Average of all question scores (fresh and follow-up) scaled out of 100: (Sum of scores / Number of questions) * 10",
    "strengths": [
        "Strong experience in database optimization, connection pooling (SQLAlchemy), and caching strategies (Redis).",
        "Expertise in big data processing on Spark, including handling data skew using salting.",
        "Solid security practices regarding Kubernetes secret management, leveraging file mounts, KMS, and HashiCorp Vault.",
        "Mature testing workflow employing modern tools like pytest-asyncio and containerized dependencies (Testcontainers)."
    ],
    "gaps": [
        "Initial answer on Kubernetes secret management was extremely brief and lacked detail, requiring interviewer prompt.",
        "Could expand on caching patterns (e.g. write-through vs cache-aside) and their trade-offs."
    ],
    "recommendation": "Strong fit",
    "recommendation_reasoning": "The candidate has demonstrated exceptional backend system design and data engineering depth across all questions, quickly correcting a brief answer during the follow-up.",
    "summary_paragraph": "Jane Doe performed exceptionally well in this interview for Lead Backend Developer. She demonstrated high technical competency in database scaling, distributed data processing, containerized infrastructure security, and async testing patterns. Her communication is structured and professional. Aside from one initially brief answer, her technical depth is solid."
}

def main():
    print("Running simulated mock session...")
    resume_path = os.path.join("data", "sample_resume.txt")
    
    # 1. Parse Resume (uses real text extraction)
    resume_text = parse_resume(resume_path)
    
    # 2. Re-create the dialogue loop using mock values
    history = []
    
    # Simulating Q1
    q1 = MOCK_QUESTIONS[0]
    ans1 = MOCK_ANSWERS[0]
    score1 = MOCK_SCORINGS[0]
    history.append({"role": "interviewer", "content": q1, "is_follow_up": False})
    history.append({
        "role": "candidate",
        "content": ans1,
        "score": score1["score"],
        "justification": score1["justification"],
        "breakdown": score1["breakdown"],
        "is_follow_up": False
    })
    
    # Simulating Q2
    q2 = MOCK_QUESTIONS[1]
    ans2 = MOCK_ANSWERS[1]
    score2 = MOCK_SCORINGS[1]
    history.append({"role": "interviewer", "content": q2, "is_follow_up": False})
    history.append({
        "role": "candidate",
        "content": ans2,
        "score": score2["score"],
        "justification": score2["justification"],
        "breakdown": score2["breakdown"],
        "is_follow_up": False
    })
    
    # Simulating Q3 (Weak Answer)
    q3 = MOCK_QUESTIONS[2]
    ans3 = MOCK_ANSWERS[2]
    score3 = MOCK_SCORINGS[2]
    history.append({"role": "interviewer", "content": q3, "is_follow_up": False})
    history.append({
        "role": "candidate",
        "content": ans3,
        "score": score3["score"],
        "justification": score3["justification"],
        "breakdown": score3["breakdown"],
        "is_follow_up": False
    })
    
    # Simulating Q4 (Follow-up)
    q4 = MOCK_QUESTIONS[3]
    ans4 = MOCK_ANSWERS[3]
    score4 = MOCK_SCORINGS[3]
    history.append({"role": "interviewer", "content": q4, "is_follow_up": True})
    history.append({
        "role": "candidate",
        "content": ans4,
        "score": score4["score"],
        "justification": score4["justification"],
        "breakdown": score4["breakdown"],
        "is_follow_up": True
    })
    
    # Simulating Q5
    q5 = MOCK_QUESTIONS[4]
    ans5 = MOCK_ANSWERS[4]
    score5 = MOCK_SCORINGS[4]
    history.append({"role": "interviewer", "content": q5, "is_follow_up": False})
    history.append({
        "role": "candidate",
        "content": ans5,
        "score": score5["score"],
        "justification": score5["justification"],
        "breakdown": score5["breakdown"],
        "is_follow_up": False
    })
    
    # Simulating Q6
    q6 = MOCK_QUESTIONS[5]
    ans6 = MOCK_ANSWERS[5]
    score6 = MOCK_SCORINGS[5]
    history.append({"role": "interviewer", "content": q6, "is_follow_up": False})
    history.append({
        "role": "candidate",
        "content": ans6,
        "score": score6["score"],
        "justification": score6["justification"],
        "breakdown": score6["breakdown"],
        "is_follow_up": False
    })
    
    # 3. Save transcript using actual cli.py logic
    role = "Lead Backend Developer"
    json_path, md_path = save_transcript(role, history, MOCK_EVALUATION)
    
    print("\nSimulated Session Created successfully!")
    print(f"JSON saved: {json_path}")
    print(f"MD saved: {md_path}")
    
    # Copy file to standard deliverables for the assignment
    deliverables_dir = os.path.join("data", "sessions")
    sample_json = os.path.join(deliverables_dir, "sample_transcript.json")
    sample_md = os.path.join(deliverables_dir, "sample_transcript.md")
    
    import shutil
    shutil.copy(json_path, sample_json)
    shutil.copy(md_path, sample_md)
    print(f"Copied to standard deliverables:\n - {sample_json}\n - {sample_md}")

if __name__ == "__main__":
    main()
