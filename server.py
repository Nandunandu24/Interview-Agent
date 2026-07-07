import os
import re
import json
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Import core modules
from core.resume_parser import parse_resume, infer_role_and_skills
from core.question_engine import generate_first_question, generate_next_question, generate_follow_up
from core.scorer import score_answer
from core.evaluator import generate_evaluation

app = FastAPI(title="Structured AI Interview Agent Backend", version="1.0.0")

# --- OFFLINE MOCK MODE LOGIC ---
COMMON_SKILLS = [
    "Python", "FastAPI", "Go", "Java", "Docker", "Kubernetes", "AWS", "SQL",
    "PostgreSQL", "Redis", "MongoDB", "Elasticsearch", "Spark", "ETL", "Django",
    "Flask", "gRPC", "React", "Node.js", "TypeScript", "Pandas", "PyTorch", "Git", "CI/CD",
    "Excel", "Power BI", "Tableau", "Data Storytelling", "Airflow", "Kafka", "Snowflake", 
    "BigQuery", "Terraform", "Jenkins", "Prometheus", "Grafana", "HTML/CSS", "Redux", "Zustand",
    "scikit-learn", "TensorFlow", "RAG", "LLM", "quantization", "fine-tuning", "vector database"
]

OFFLINE_QUESTIONS = {
    "data analyst": {
        "Junior": [
            "Excel remains a staple for quick data analysis. Can you walk me through how you use Pivot Tables, XLOOKUP, or conditional formatting to summarize a dataset?",
            "SQL joins are fundamental to querying databases. Can you explain the difference between an INNER JOIN, LEFT JOIN, and OUTER JOIN, and when you would use each?",
            "Power BI is great for creating reports. Can you describe how you connect to a data source, model the relationships, and create a simple interactive dashboard?",
            "Data Storytelling helps stakeholders understand insights. How do you approach designing a chart or slide to communicate a complex data finding to a non-technical manager?",
            "Imagine you are faced with a dataset containing missing values and duplicates. Walk me through your step-by-step problem solving approach to clean and validate this data."
        ],
        "Mid-Level": [
            "SQL optimization is key for large databases. How do you analyze and optimize a slow-running query containing multiple subqueries or groupings?",
            "Tableau is widely used for enterprise reporting. Can you share how you build calculated fields, level of detail (LOD) expressions, or parameters to enhance dashboard interactivity?",
            "Python (specifically Pandas/NumPy) is powerful for data manipulation. Walk me through a challenging data aggregation or cleaning task you solved using Python.",
            "Designing clean data reporting is critical. What best practices do you follow to ensure your dashboard UI is intuitive, readable, and directly answers business questions?",
            "Statistical analysis is essential for identifying trends. Can you explain how you use descriptive statistics, correlation, or hypothesis testing to uncover patterns in user behavior?"
        ],
        "Senior": [
            "A/B testing is used to evaluate changes. How do you design an A/B test, determine the sample size needed, and evaluate statistical significance to make product recommendations?",
            "Data strategy is about aligning data with business goals. Walk me through how you establish data quality standards and KPIs for an organization.",
            "Advanced dashboard design requires scaling. How do you design dashboards that pull from high-volume data sources without causing high latency or rendering delays?",
            "Stakeholder communication is critical at a senior level. Describe a scenario where your data insights contradicted a senior leader's intuition. How did you present your findings and influence the decision?",
            "Analytics architecture is key to business intelligence. How do you design an analytics stack that scales from raw data ingestion to user-facing reports?"
        ]
    },
    "backend": {
        "Junior": [
            "Python is widely used for backend systems. Walk me through a simple script or helper function you wrote recently and how you ensured it was clean and readable.",
            "FastAPI is a modern web framework. Can you explain how you define route paths, query parameters, and request bodies using Pydantic models?",
            "SQL databases store relational data. Can you write a query to retrieve records from a table, filtered by a condition and ordered by a field?",
            "Git is essential for collaboration. Can you describe your workflow for creating a feature branch, making commits, and opening a pull request?",
            "How do you test your code to verify it works correctly (e.g., writing simple unit tests with pytest)?"
        ],
        "Mid-Level": [
            "I see you have experience with databases. In the context of a production environment, what are the primary indexing or pooling strategies you use to scale queries?",
            "Let's discuss API performance. How do you design endpoints for high throughput, optimize payload sizes, and minimize database queries (e.g. solving N+1 query problem)?",
            "Redis is commonly used for caching. Walk me through your cache invalidation strategies and how you prevent cache stampedes or thundering herd problems.",
            "Docker containerizes applications. How do you write a multi-stage Dockerfile to minimize image sizes and secure your containers?",
            "Asynchronous task queues help offload work. Can you explain how you handle background workers, retry mechanisms, and task failures using tools like Celery?"
        ],
        "Senior": [
            "As a senior engineer, can you detail a high-impact architectural initiative you led, focusing on scalability, service decoupling, and team coordination?",
            "Let's deep dive into distributed systems. How do you design services for high availability and loose coupling, and what concurrency or locking strategies do you employ at scale?",
            "When designing a large backend system, how do you manage distributed state, consistency vs. availability trade-offs (CAP theorem), and latency optimization?",
            "Describe a scenario where you had to make a critical, high-stakes technology choice (e.g., SQL vs. NoSQL). What trade-offs and business constraints did you weigh?",
            "How do you establish enterprise-grade CI/CD pipelines, security compliance controls, threat modeling, and load/stress testing environments?"
        ]
    },
    "frontend": {
        "Junior": [
            "HTML and CSS lay the foundation of the web. How do you use Flexbox or Grid to build a responsive navigation bar that works on both mobile and desktop?",
            "JavaScript handles interactivity. Can you explain how you register event listeners, modify the DOM, and make basic API fetch calls?",
            "React components are the building blocks. How do you manage component state with the useState hook and pass data via props?",
            "Git helps track changes. Describe a scenario where you encountered a merge conflict on a CSS file and how you resolved it.",
            "DOM manipulation can be tricky. Can you describe the differences between using React's virtual DOM and direct document queries?"
        ],
        "Mid-Level": [
            "TypeScript adds static typing. How do you define interfaces, union types, and generics to make your React components more type-safe and reusable?",
            "State management is crucial for large apps. What are the pros and cons of using React Context vs external libraries like Redux or Zustand in a mid-sized application?",
            "React component lifecycle is key to efficiency. Can you explain how the useEffect hook works, how to prevent infinite render loops, and when to clean up side effects?",
            "API optimization on the frontend improves user experience. How do you implement data fetching optimizations like debouncing, caching, or optimistic UI updates?",
            "Testing is critical. What strategies and frameworks (e.g., Jest, React Testing Library) do you use to test component rendering and user interactions?"
        ],
        "Senior": [
            "As applications scale, monoliths get heavy. What are the key architectural trade-offs, routing challenges, and deployment strategies when implementing Micro-Frontends?",
            "Web performance directly impacts conversion. Walk me through how you optimize core web vitals, including code splitting, lazy loading, image optimization, and CDN caching.",
            "SEO and accessibility (a11y) are essential for public apps. How do you implement Server-Side Rendering (SSR) or Static Site Generation (SSG) in frameworks like Next.js?",
            "Design systems keep the UI consistent. How do you coordinate with design teams to establish design tokens, component libraries, and themeable styles across multiple repositories?",
            "Security is critical. How do you protect frontend applications from vulnerabilities like Cross-Site Scripting (XSS), Cross-Site Request Forgery (CSRF), and open redirect attacks?"
        ]
    },
    "data engineer": {
        "Junior": [
            "SQL is the foundation of data querying. Can you write a query using aggregate functions (e.g., SUM, AVG) combined with GROUP BY and HAVING filters?",
            "ETL stands for Extract, Transform, Load. Can you describe a simple data pipeline you built, where the data came from, and how you loaded it into a target table?",
            "Python is widely used in data pipelines. How do you write a script to read a CSV file, parse the columns, and write the cleaned records to a file?",
            "Git keeps track of your scripts. Walk me through your team's code review process and how you ensure your pipeline scripts are reviewed and tested.",
            "Data schemas define how data is structured. What is the difference between structured data (like SQL tables) and semi-structured data (like JSON or XML)?"
        ],
        "Mid-Level": [
            "Apache Spark is used for large scale processing. How do you handle data skew, partition tuning, and broadcast joins to optimize slow-running Spark jobs?",
            "Airflow orchestrates pipelines. Walk me through how you write a DAG, configure task dependencies, handle retries, and set up SLA alerts for critical pipelines.",
            "Snowflake is a popular cloud data warehouse. How do you approach designing schemas (e.g., Star Schema vs. Snowflake Schema) for efficient analytical querying?",
            "Kafka handles streaming data. Can you explain the concepts of topics, partitions, consumer groups, and how you ensure message ordering in a distributed topic?",
            "Data warehousing requires scaling. What trade-offs do you consider when choosing between a columnar database (e.g., BigQuery) and a traditional transactional database?"
        ],
        "Senior": [
            "As a senior leader, how do you design a scalable Lakehouse architecture (e.g., using Delta Lake or Apache Iceberg) to unify batch and streaming analytics?",
            "Real-time streaming pipelines require high availability. How do you build fault-tolerant pipelines with exactly-once processing guarantees using Flink or Spark Streaming?",
            "Data Mesh is an emerging decentralized architecture. What are the operational, organizational, and technical challenges of treating data as a product across business units?",
            "Orchestrating complex enterprise workflows is challenging. How do you design pipelines that manage cross-DAG dependencies, dynamic task generation, and backfill scheduling?",
            "Compliance (GDPR/CCPA) is a major constraint. How do you design data anonymization, column-level access controls, and data lineage tracking in an enterprise data platform?"
        ]
    },
    "devops": {
        "Junior": [
            "Linux commands are fundamental. How do you use the command line to check disk usage, list active processes, or view log file updates in real-time?",
            "Git is crucial for version control. Walk me through how you use branches, tags, and commits to manage infrastructure code changes.",
            "Docker containers package applications. Can you explain what a container image is, how it differs from a virtual machine, and how you start a container locally?",
            "CI/CD automates deployments. Walk me through a simple GitHub Actions workflow or Jenkins pipeline you set up to build and test code on every commit.",
            "Scripting automates tasks. What languages (e.g., Bash, Python) do you use to write scripts that perform system administration or file cleanup?"
        ],
        "Mid-Level": [
            "Kubernetes orchestrates container deployments. How do you manage pod scaling, service discovery, ingress routing, and persistent storage volumes in a cluster?",
            "Terraform manages Infrastructure as Code. Can you describe how you manage state files, modules, variable inputs, and resource dependencies in a multi-environment setup?",
            "CI/CD workflows grow complex. How do you design a build/deploy pipeline that supports canary deployments, blue-green deployments, or manual approval gates?",
            "AWS provides core cloud resources. Walk me through how you configure VPCs, security groups, IAM roles, and load balancers to secure a public web application.",
            "Monitoring and alerting ensure uptime. How do you set up Prometheus and Grafana to collect application metrics, create dashboards, and alert on error rate spikes?"
        ],
        "Senior": [
            "As a senior leader, how do you design a multi-region cloud infrastructure for high availability, active-active replication, and automatic failover during outages?",
            "Disaster Recovery (DR) is critical. How do you design, implement, and routinely test backup/recovery strategies for high-volume stateful databases in the cloud?",
            "GitOps aligns deployments with git repositories. What are the architectural differences, security pros/cons, and tool selections (e.g., ArgoCD vs. Flux) for GitOps?",
            "Security compliance at scale is complex. How do you enforce security controls (e.g., SOC2, ISO27001) in Kubernetes environments, including network policies and image signing?",
            "Cloud costs can escalate quickly. How do you establish automated cost monitoring, spot instance strategies, resource rightsizing, and budget alerts across an enterprise?"
        ]
    },
    "data scientist": {
        "Junior": [
            "Python (specifically Pandas and NumPy) is a core tool for data scientists. Can you walk me through how you clean missing data, handle outliers, and perform basic aggregations on a dataset?",
            "Linear regression is one of the most fundamental predictive models. Can you explain the difference between simple and multiple linear regression, and how you interpret the coefficients?",
            "Data preprocessing is critical. Can you explain the difference between normalization (scaling data between 0 and 1) and standardization (z-score), and when you would use each?",
            "Git helps data scientists version control code and notebooks. Describe your workflow for committing changes and collaborating on research scripts.",
            "Basic statistics are the backbone of data science. Can you describe how you explain the mean, median, mode, and standard deviation of a dataset to a non-technical audience?"
        ],
        "Mid-Level": [
            "Machine learning models require proper evaluation. How do you choose between using Precision, Recall, F1-Score, and ROC-AUC when evaluating a binary classifier?",
            "Feature engineering can make or break a model. Walk me through a challenging scenario where you created new features or encoded categorical variables to improve model performance.",
            "SQL is vital for data extraction. How do you use window functions (like ROW_NUMBER or DENSE_RANK) or CTEs to extract complex datasets for model training?",
            "Overfitting is a common issue in machine learning. How do you use cross-validation, regularization (L1/L2), or hyperparameter tuning to ensure your model generalizes well?",
            "scikit-learn is widely used. Can you explain how you build a Pipeline to chain preprocessing, feature scaling, and model training in a clean, reproducible way?"
        ],
        "Senior": [
            "Deep learning models require massive computation. How do you design, optimize, and train deep neural networks (using PyTorch or TensorFlow) while avoiding exploding or vanishing gradients?",
            "MLOps is about bridging the gap between development and production. Walk me through your design for deploying, monitoring, and retraining a machine learning model at scale.",
            "Causal inference helps measure actual impact. How do you distinguish between correlation and causation in user data, and what techniques (like propensity score matching) do you use?",
            "High-dimensional data can be difficult to model. Can you explain how you use Principal Component Analysis (PCA) or t-SNE for dimensionality reduction, and how you evaluate the components?",
            "Describe a scenario where a model's offline evaluation was excellent, but its online business metrics (e.g., conversion) failed. How did you diagnose and resolve the discrepancy?"
        ]
    },
    "ai engineer": {
        "Junior": [
            "Python is the standard language for AI development. Walk me through a simple script you wrote to call a machine learning API or clean a text dataset.",
            "API integration is crucial for using foundation models. How do you make API requests to LLM providers (like OpenAI or Gemini) and handle error responses?",
            "Prompt engineering directly affects model outputs. Can you explain the difference between zero-shot, few-shot, and chain-of-thought prompting, with examples?",
            "Git is used to manage code. Can you describe how you version your prompts, configurations, or model weights alongside your application code?",
            "Neural networks are modeled after biological brains. Can you explain the concept of feedforward, weights, biases, and activation functions in a basic network?"
        ],
        "Mid-Level": [
            "Retrieval-Augmented Generation (RAG) is used to ground LLM responses. Walk me through how you build a RAG pipeline, including document chunking, embedding generation, and prompt assembly.",
            "Vector databases store high-dimensional embeddings. How do you choose between distance metrics (Cosine similarity vs. Euclidean distance) and query vectors in Chroma, Pinecone, or pgvector?",
            "Docker helps run AI models consistently. How do you containerize a PyTorch or HuggingFace application, and how do you ensure it can utilize GPU resources in containerized environments?",
            "Fine-tuning tailors LLMs to specific tasks. Can you explain the difference between full fine-tuning and Parameter-Efficient Fine-Tuning (PEFT/LoRA), and when you would use each?",
            "Model quantization reduces the size and latency of models. Can you explain the trade-offs in accuracy and memory consumption when quantizing an LLM to 4-bit or 8-bit precision?"
        ],
        "Senior": [
            "AI agent architectures allow models to take actions. How do you design a reliable agent loop (e.g. using ReAct pattern), handle tool usage, and prevent infinite planning loops?",
            "Training custom foundation models is resource-intensive. Walk me through your strategy for distributed training (e.g. using Deepspeed or PyTorch DDP) across multi-node GPU clusters.",
            "Model optimization is key to scaling inference. How do you optimize inference pipelines for low latency (e.g., using vLLM, TensorRT-LLM, or speculative decoding)?",
            "Deploying AI agents at scale introduces reliability challenges. How do you monitor agent performance, trace execution steps, log cost/tokens, and handle API rate limits?",
            "Describe a scenario where you designed a custom hybrid RAG and agentic system to solve a complex, multi-step user task. What architecture, fallback paths, and evaluation metrics did you use?"
        ]
    }
}

ROLE_FOLLOW_UP_TEMPLATES = {
    "data analyst": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain the basic steps of how you prepared that data, and how you verified your insights were accurate?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you validate and present that in a production dashboard, and what business metrics you track to ensure value?",
        "Senior": "As a senior analyst or leader, how do you handle data governance, stakeholder pushback, scalability under large datasets, and advanced predictive analysis for the '{focus}' setup you described?"
    },
    "backend": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain the basic steps of how you configured that, and what tools you used to verify it worked?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you configure and secure that in production, and what metrics you monitor to ensure correctness?",
        "Senior": "As a senior engineer or architect, how do you handle security auditing, failover scenarios, data durability, and performance optimization under peak loads for the '{focus}' setup you described?"
    },
    "frontend": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain the basic steps of how you built that component, and how you verified it rendered correctly?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you optimize, style, and test that component in production, and what performance metrics you monitor?",
        "Senior": "As a senior frontend architect, how do you handle state scalability, code bundle optimization, accessibility compliance, and security audits for the '{focus}' architecture you described?"
    },
    "data engineer": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain the basic steps of how you constructed that pipeline, and what schemas or tests you used to verify the output data?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you secure, monitor, and scale that pipeline in production, and what pipeline SLA metrics you track?",
        "Senior": "As a senior data architect, how do you handle data governance, schema evolution, failover recovery, and latency optimization under petabyte-scale loads for the '{focus}' pipeline you described?"
    },
    "devops": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain the basic steps of how you configured that script/container, and what logs or tests you checked to verify it worked?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you secure and deploy that in production, and what infrastructure metrics you monitor?",
        "Senior": "As a senior DevOps or site reliability architect, how do you handle automated failovers, security auditing, configuration drift, and cost efficiency at scale for the '{focus}' setup you described?"
    },
    "data scientist": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain how you prepared that data, and what statistical metrics you used to check for outliers or bias?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you evaluate that model feature/parameter, and how you guard against model drift?",
        "Senior": "As a senior data scientist, how do you communicate model uncertainty, validate business impact in production, and handle covariate shift for the '{focus}' setup you described?"
    },
    "ai engineer": {
        "Junior": "You mentioned '{focus}' in your response. Can you explain the basic steps of how you wrote that prompt/API call, and what fallback logic you used when it failed?",
        "Mid-Level": "You mentioned '{focus}' in your response. Can you go deeper and explain how you evaluate retrieval quality, optimize token usage, and secure the system against prompt injections?",
        "Senior": "As a senior AI architect, how do you handle model latency, explainability/bias controls, context window limitations, and cost optimization at scale for the '{focus}' architecture you described?"
    }
}

def check_api_keys() -> bool:
    """Returns True if at least one valid LLM API key is present."""
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    # Verify they aren't default placeholder strings
    has_groq = groq_key and "your_groq_api_key" not in groq_key
    has_gemini = gemini_key and "your_gemini_api_key" not in gemini_key
    return bool(has_groq or has_gemini)

def extract_resume_info_offline(text: str) -> dict:
    """Locally parses resume text using regex and matching templates, extracting experience level."""
    found_skills = []
    for skill in COMMON_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
            found_skills.append(skill)
            
    # Default fallback skills if none detected
    if not found_skills:
        found_skills = ["Software Engineering", "Python", "Problem Solving"]
        
    # Attempt to extract companies (proper nouns ending in Corp, Inc, Tech, etc.)
    companies = re.findall(r'\b[A-Z][a-zA-Z0-9]+(?:Corp|Inc|Ltd|Tech|Data)\b', text)
    company = companies[0] if companies else "your previous company"
    
    # Infer role based on title keywords
    role = "Software Engineer"
    if re.search(r'backend', text, re.IGNORECASE):
        role = "Backend Developer"
    elif re.search(r'data analyst', text, re.IGNORECASE):
        role = "Data Analyst"
    elif re.search(r'frontend', text, re.IGNORECASE):
        role = "Frontend Developer"
    elif re.search(r'full\s*stack', text, re.IGNORECASE):
        role = "Full Stack Engineer"
    elif re.search(r'data engineer', text, re.IGNORECASE):
        role = "Data Engineer"
    elif re.search(r'devops', text, re.IGNORECASE):
        role = "DevOps Engineer"
    elif re.search(r'data scientist', text, re.IGNORECASE):
        role = "Data Scientist"
    elif re.search(r'ai engineer|machine learning|artificial intelligence', text, re.IGNORECASE):
        role = "AI Engineer"
        
    # Determine experience level
    level = "Mid-Level"
    senior_keywords = ["senior", "lead", "principal", "architect", "staff", "manager", "head", "director", "sr."]
    junior_keywords = ["junior", "intern", "associate", "graduate", "fresher", "entry", "jr."]
    
    senior_count = sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)) for kw in senior_keywords)
    junior_count = sum(len(re.findall(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE)) for kw in junior_keywords)
    
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
        
    summary = f"Experienced candidate specializing in {', '.join(found_skills[:3])} with past tenure at {company}."
    
    return {
        "inferred_role": role,
        "skills": found_skills,
        "summary": summary,
        "company": company,
        "experience_level": level
    }

def extract_experience_projects_certifications(text: str) -> dict:
    """Parses resume text locally to extract chunks of work experience, projects, and certifications."""
    lines = text.split("\n")
    experience_bullets = []
    project_bullets = []
    certifications = []
    
    current_section = None
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # Section detection
        line_lower = line_clean.lower()
        if any(h in line_lower for h in ["experience", "employment", "history", "work history", "tenure"]):
            current_section = "experience"
            continue
        elif any(h in line_lower for h in ["project", "key initiatives", "portfolio"]):
            current_section = "projects"
            continue
        elif any(h in line_lower for h in ["certification", "credentials", "licenses", "courses", "education"]):
            current_section = "certifications"
            
        # Extract based on current section
        if current_section == "experience" and (line_clean.startswith("*") or line_clean.startswith("-") or len(line_clean) > 40):
            bullet = re.sub(r'^[\*\-\•\s]+', '', line_clean)
            if len(bullet) > 20:
                experience_bullets.append(bullet)
        elif current_section == "projects" and (line_clean.startswith("*") or line_clean.startswith("-") or len(line_clean) > 40):
            bullet = re.sub(r'^[\*\-\•\s]+', '', line_clean)
            if len(bullet) > 20:
                project_bullets.append(bullet)
                
        # Certification check anywhere in the text
        if any(c in line_lower for c in ["certified", "certification", "license", "certificate", "aws ", "gcp ", "azure", "coursera", "udemy"]):
            if not any(h == line_lower for h in ["certifications", "licenses", "courses"]):
                clean_cert = re.sub(r'^[\*\-\•\s]+', '', line_clean)
                if len(clean_cert) > 10 and len(clean_cert) < 100:
                    certifications.append(clean_cert)
                    
    # Fallbacks if none found
    if not experience_bullets:
        experience_bullets = ["Developed key features and resolved software defects to support business requirements."]
    if not project_bullets:
        project_bullets = ["Designed and implemented a modular application to solve specific domain challenges."]
    if not certifications:
        certifications = ["Professional Technical Training Certification"]
        
    return {
        "experience": experience_bullets,
        "projects": project_bullets,
        "certifications": certifications
    }

def get_offline_question(resume_text: str, role: str, q_index: int, history: list = None, experience_level: str = None) -> str:
    """Generates realistic technical questions locally based on resume keywords and experience level."""
    info = extract_resume_info_offline(resume_text)
    company = info["company"]
    level = experience_level if experience_level else info["experience_level"]
    
    if level not in ["Junior", "Senior", "Mid-Level"]:
        level = "Mid-Level"
        
    # Extract structured items from resume
    extracted = extract_experience_projects_certifications(resume_text)
    exp_bullets = extracted["experience"]
    proj_bullets = extracted["projects"]
    certs = extracted["certifications"]
    
    # Custom Question Routing:
    if q_index == 1:
        bullet = exp_bullets[0]
        if len(bullet) > 150:
            bullet = bullet[:147] + "..."
        return f"I see in your previous experience at {company} that you worked to '{bullet}'. Can you walk me through the specific architectural decisions and execution steps for this task?"
        
    elif q_index == 3:
        proj = proj_bullets[0]
        if len(proj) > 150:
            proj = proj[:147] + "..."
        return f"Your resume highlights the project: '{proj}'. What were the primary design bottlenecks or implementation challenges you encountered, and how did you mitigate them?"
        
    elif q_index == 4:
        cert = certs[0]
        if len(cert) > 100:
            cert = cert[:97] + "..."
        return f"I see you listed '{cert}' on your profile. How have the skills or standards learned from this credential directly influenced your technical decisions and daily practices?"
        
    else:
        role_lower = role.lower()
        matched_role = "backend" # default fallback
        
        if "data scientist" in role_lower:
            matched_role = "data scientist"
        elif "ai engineer" in role_lower or "machine learning" in role_lower or "artificial intelligence" in role_lower:
            matched_role = "ai engineer"
        elif "data analyst" in role_lower or "business analyst" in role_lower or "analytics" in role_lower:
            matched_role = "data analyst"
        elif "frontend" in role_lower or "react" in role_lower or "web developer" in role_lower:
            matched_role = "frontend"
        elif "data engineer" in role_lower or "spark" in role_lower or "etl" in role_lower:
            matched_role = "data engineer"
        elif "devops" in role_lower or "sre" in role_lower or "cloud engineer" in role_lower or "infrastructure" in role_lower:
            matched_role = "devops"
        elif "backend" in role_lower or "software engineer" in role_lower or "developer" in role_lower:
            matched_role = "backend"
            
        questions_list = OFFLINE_QUESTIONS[matched_role][level]
        question_template = questions_list[(q_index - 1) % len(questions_list)]
        return question_template.replace("{company}", company)

def get_offline_follow_up(resume_text: str, question: str, answer: str, experience_level: str = None) -> str:
    """Generates a targeted follow-up question offline based on the experience level and answer content."""
    info = extract_resume_info_offline(resume_text)
    level = experience_level if experience_level else info["experience_level"]
    
    if level not in ["Junior", "Senior", "Mid-Level"]:
        level = "Mid-Level"
        
    # Find any technical words mentioned in the answer
    found_tech = []
    for word in COMMON_SKILLS + ["database", "monolith", "latency", "secrets", "caching"]:
        if re.search(r'\b' + re.escape(word) + r'\b', answer, re.IGNORECASE):
            found_tech.append(word)
            
    focus = found_tech[0] if found_tech else "architecture details"
    
    # Extract role context from question or resume
    question_lower = question.lower()
    matched_role = "backend" # default fallback
    
    if "data scientist" in question_lower or "model" in question_lower or "statistics" in question_lower or "regression" in question_lower:
        matched_role = "data scientist"
    elif "ai engineer" in question_lower or "prompt" in question_lower or "rag" in question_lower or "llm" in question_lower:
        matched_role = "ai engineer"
    elif "data analyst" in question_lower or "excel" in question_lower or "dashboard" in question_lower or "power bi" in question_lower or "tableau" in question_lower or "storytelling" in question_lower:
        matched_role = "data analyst"
    elif "frontend" in question_lower or "css" in question_lower or "react" in question_lower or "component" in question_lower or "typescript" in question_lower:
        matched_role = "frontend"
    elif "data engineer" in question_lower or "spark" in question_lower or "airflow" in question_lower or "pipeline" in question_lower or "warehouse" in question_lower:
        matched_role = "data engineer"
    elif "devops" in question_lower or "kubernetes" in question_lower or "terraform" in question_lower or "ci/cd" in question_lower:
        matched_role = "devops"
        
    template = ROLE_FOLLOW_UP_TEMPLATES[matched_role][level]
    return template.replace("{focus}", focus)

def score_answer_offline(question: str, answer: str) -> dict:
    """Evaluates an answer offline based on word count, question keywords, and technical keywords, giving suggestions."""
    words = answer.strip().split()
    word_count = len(words)
    q_lower = question.lower()
    ans_lower = answer.lower()
    
    # Check for technical terms
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
        relevance = "Addressed the architectural design and flow of the analytics pipeline."
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

def generate_evaluation_offline(history: list) -> dict:
    """Aggregates scores and compiles final summary evaluation offline dynamically based on performance."""
    candidate_turns = [turn for turn in history if turn.get("role") == "candidate"]
    valid_scores = [turn["score"] for turn in candidate_turns if "score" in turn]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 5.0
    overall = round(avg_score * 10)
    
    weak_turns = [t for t in candidate_turns if t.get("score", 0) < 5]
    medium_turns = [t for t in candidate_turns if 5 <= t.get("score", 0) < 8]
    strong_turns = [t for t in candidate_turns if t.get("score", 0) >= 8]
    
    weak_count = len(weak_turns)
    total_count = len(candidate_turns)
    
    if overall >= 80:
        verdict = "Strong Hire"
    elif overall >= 65:
        verdict = "Hire"
    else:
        verdict = "No Hire"

    # Communication skills scoring
    comm_score = 3
    if weak_count == 0:
        comm_score = 4
    elif weak_count > 2:
        comm_score = 2
    comm_evidence = f"Candidate maintained verbal flow, delivering {total_count - weak_count} acceptable responses."

    # Technical depth
    tech_score = 3
    if len(strong_turns) >= 2:
        tech_score = 4
    elif weak_count > 2:
        tech_score = 2
    tech_evidence = f"Aligned conceptually on {len(strong_turns)} topics. Met baseline requirements, but {weak_count} items required follow-up queries."

    # Problem solving
    prob_score = 3
    prob_evidence = "Walked through technical questions systematically according to mock session guidelines."

    # Detailed technical
    accuracy_str = "Logic was conceptually correct, though syntax and deep execution details were not fully explored verbally."
    opt_str = "Focused primarily on basic workarounds; did not proactively detail time/space complexity or system trade-offs."
    edge_str = "Answered standard cases; did not raise or detail edge cases or failure modes."

    # Feedback
    cand_feed = "Practice speaking in concrete bullet points. Highlight specific libraries, database optimization, caching, and state management trade-offs."
    team_feed = "Conduct a live coding challenge to verify practical problem solving, algorithmic correctness, and real-time execution depth."

    # Highlight major highlights/gaps for executive summary
    if verdict == "Strong Hire":
        strengths_summary = "Excellent baseline knowledge with high conceptual accuracy across all questions."
        gaps_summary = "Minor growth opportunities in explaining high-throughput optimization trade-offs."
    elif verdict == "Hire":
        strengths_summary = "Solid general understanding of engineering practices and Docker/ETL pipelines."
        gaps_summary = "Needs to focus on explaining architectural decisions, rate limits, and caching strategies."
    else:
        strengths_summary = "Demonstrated basic familiarity with software terms and ETL workflows."
        gaps_summary = "Exhibited significant gaps in technical depth, regression modeling, and system scaling details."

    return {
        "overall_score": overall,
        "scoring_formula": "Average of all question scores (fresh and follow-up) scaled out of 100: (Sum of scores / Number of questions) * 10",
        "verdict": verdict,
        "key_strengths": strengths_summary,
        "growth_areas": gaps_summary,
        "communication_skills": {
            "score": comm_score,
            "evidence": comm_evidence
        },
        "technical_depth": {
            "score": tech_score,
            "evidence": tech_evidence
        },
        "problem_solving_adaptability": {
            "score": prob_score,
            "evidence": prob_evidence
        },
        "detailed_technical": {
            "accuracy": accuracy_str,
            "optimization": opt_str,
            "edge_cases": edge_str
        },
        "feedback": {
            "candidate": cand_feed,
            "hiring_team": team_feed
        }
    }


# --- API REQUEST/RESPONSE SCHEMAS ---

class ParseRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path to the candidate's resume file")

class ParseResponse(BaseModel):
    text: str
    inferred_role: str
    skills: list[str]
    summary: str
    experience_level: str = "Mid-Level"
    mode: str = Field(description="Recruiter backend execution mode: 'online' or 'offline'")

class FirstQuestionRequest(BaseModel):
    resume_text: str
    target_role: str
    experience_level: Optional[str] = Field(default=None, description="Manual override for experience level")

class QuestionResponse(BaseModel):
    question: str
    mode: str

class NextQuestionRequest(BaseModel):
    resume_text: str
    target_role: str
    history: list[dict]
    experience_level: Optional[str] = Field(default=None, description="Manual override for experience level")

class FollowUpRequest(BaseModel):
    resume_text: str
    target_role: str
    question: str
    answer: str
    experience_level: Optional[str] = Field(default=None, description="Manual override for experience level")

class ScoreRequest(BaseModel):
    question: str
    answer: str
    target_role: str

class ScoreBreakdown(BaseModel):
    relevance: str
    correctness_depth: str
    clarity: str
    specificity_evidence: str

class ScoreResponse(BaseModel):
    score: int
    is_weak: bool
    justification: str
    breakdown: ScoreBreakdown
    mode: str

class EvaluateRequest(BaseModel):
    target_role: str
    history: list[dict]

class DimensionEvaluation(BaseModel):
    score: int
    evidence: str

class DetailedTechnical(BaseModel):
    accuracy: str
    optimization: str
    edge_cases: str

class FeedbackBlock(BaseModel):
    candidate: str
    hiring_team: str

class EvaluateResponse(BaseModel):
    overall_score: int
    scoring_formula: str
    verdict: str
    key_strengths: str
    growth_areas: str
    communication_skills: DimensionEvaluation
    technical_depth: DimensionEvaluation
    problem_solving_adaptability: DimensionEvaluation
    detailed_technical: DetailedTechnical
    feedback: FeedbackBlock
    mode: str


# --- API ENDPOINTS ---

@app.post("/api/parse", response_model=ParseResponse)
def api_parse(req: ParseRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail=f"File not found at: {req.file_path}")
        
    try:
        text = parse_resume(req.file_path)
        offline_info = extract_resume_info_offline(text)
        
        if check_api_keys():
            try:
                inferred = infer_role_and_skills(text)
                return {
                    "text": text,
                    "inferred_role": inferred.get("inferred_role", "Software Engineer"),
                    "skills": inferred.get("skills", []),
                    "summary": inferred.get("summary", ""),
                    "experience_level": offline_info["experience_level"],
                    "mode": "online"
                }
            except Exception:
                pass
                
        return {
            "text": text,
            "inferred_role": offline_info["inferred_role"],
            "skills": offline_info["skills"],
            "summary": offline_info["summary"],
            "experience_level": offline_info["experience_level"],
            "mode": "offline"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")

@app.post("/api/question/first", response_model=QuestionResponse)
def api_first_question(req: FirstQuestionRequest):
    if check_api_keys():
        try:
            q = generate_first_question(req.resume_text, req.target_role, req.experience_level)
            return {"question": q, "mode": "online"}
        except Exception as e:
            # Fallback to offline on failure
            pass
            
    q = get_offline_question(req.resume_text, req.target_role, 1, experience_level=req.experience_level)
    return {"question": q, "mode": "offline"}

@app.post("/api/question/next", response_model=QuestionResponse)
def api_next_question(req: NextQuestionRequest):
    # Calculate index of fresh questions asked
    fresh_count = 1
    for turn in req.history:
        if turn.get("role") == "interviewer" and not turn.get("is_follow_up"):
            fresh_count += 1
            
    if check_api_keys():
        try:
            q = generate_next_question(req.resume_text, req.target_role, req.history, req.experience_level)
            return {"question": q, "mode": "online"}
        except Exception as e:
            pass
            
    q = get_offline_question(req.resume_text, req.target_role, fresh_count, req.history, experience_level=req.experience_level)
    return {"question": q, "mode": "offline"}

@app.post("/api/question/follow-up", response_model=QuestionResponse)
def api_follow_up(req: FollowUpRequest):
    if check_api_keys():
        try:
            q = generate_follow_up(req.resume_text, req.target_role, req.question, req.answer, req.experience_level)
            return {"question": q, "mode": "online"}
        except Exception as e:
            pass
            
    q = get_offline_follow_up(req.resume_text, req.question, req.answer, experience_level=req.experience_level)
    return {"question": q, "mode": "offline"}

@app.post("/api/score", response_model=ScoreResponse)
def api_score(req: ScoreRequest):
    if check_api_keys():
        try:
            res = score_answer(req.question, req.answer, req.target_role)
            return {
                "score": res["score"],
                "is_weak": res["is_weak"],
                "justification": res["justification"],
                "breakdown": res["breakdown"],
                "mode": "online"
            }
        except Exception as e:
            pass
            
    res = score_answer_offline(req.question, req.answer)
    return {
        "score": res["score"],
        "is_weak": res["is_weak"],
        "justification": res["justification"],
        "breakdown": res["breakdown"],
        "mode": "offline"
    }

@app.post("/api/evaluate", response_model=EvaluateResponse)
def api_evaluate(req: EvaluateRequest):
    if check_api_keys():
        try:
            res = generate_evaluation(req.target_role, req.history)
            return {
                "overall_score": res["overall_score"],
                "scoring_formula": res["scoring_formula"],
                "verdict": res["verdict"],
                "key_strengths": res["key_strengths"],
                "growth_areas": res["growth_areas"],
                "communication_skills": res["communication_skills"],
                "technical_depth": res["technical_depth"],
                "problem_solving_adaptability": res["problem_solving_adaptability"],
                "detailed_technical": res["detailed_technical"],
                "feedback": res["feedback"],
                "mode": "online"
            }
        except Exception as e:
            pass
            
    res = generate_evaluation_offline(req.history)
    return {
        "overall_score": res["overall_score"],
        "scoring_formula": res["scoring_formula"],
        "verdict": res["verdict"],
        "key_strengths": res["key_strengths"],
        "growth_areas": res["growth_areas"],
        "communication_skills": res["communication_skills"],
        "technical_depth": res["technical_depth"],
        "problem_solving_adaptability": res["problem_solving_adaptability"],
        "detailed_technical": res["detailed_technical"],
        "feedback": res["feedback"],
        "mode": "offline"
    }

@app.post("/api/upload_audio")
async def api_upload_audio(file: UploadFile = File(...), question_index: int = Form(...)):
    try:
        os.makedirs("data/audio", exist_ok=True)
        file_path = f"data/audio/question_{question_index}.wav"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio file: {str(e)}")

if __name__ == "__main__":
    print("Starting FastAPI backend server locally...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
