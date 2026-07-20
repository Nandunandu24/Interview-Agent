import os
import time
import requests
import subprocess
import unittest
from core.resume_parser import parse_resume

class TestInterviewAgentAPI(unittest.TestCase):
    
    server_process = None
    
    @classmethod
    def setUpClass(cls):
        """Starts the FastAPI server as a background process for integration testing."""
        print("\nStarting local FastAPI backend server for integration tests...")
        
        # Start server.py in a background process
        cls.server_process = subprocess.Popen(
            ["python", "server.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait a moment for server to bind to port 8000
        time.sleep(3.0)

    @classmethod
    def tearDownClass(cls):
        """Terminates the background FastAPI server process."""
        print("\nTerminating background FastAPI server...")
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait()
            print("Server process shut down successfully.")

    def setUp(self):
        self.api_url = "http://127.0.0.1:8000/api"
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        self.txt_resume = os.path.join(self.data_dir, "sample_resume.txt")
        self.pdf_resume = os.path.join(self.data_dir, "sample_resume.pdf")

    def test_01_api_parse(self):
        """Test the /api/parse endpoint."""
        print("Testing /api/parse endpoint...")
        abs_path = os.path.abspath(self.txt_resume)
        response = requests.post(f"{self.api_url}/parse", json={"file_path": abs_path})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("text", data)
        self.assertIn("inferred_role", data)
        self.assertIn("skills", data)
        self.assertIn("mode", data)
        print("[OK] /api/parse returned valid response.")

    def test_02_api_first_question(self):
        """Test the /api/question/first endpoint."""
        print("Testing /api/question/first endpoint...")
        resume_text = "JANE DOE\nLead Backend Developer at TechCorp.\nSkills: Python, FastAPI, Redis."
        response = requests.post(f"{self.api_url}/question/first", json={
            "resume_text": resume_text,
            "target_role": "Lead Backend Developer"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("question", data)
        self.assertIn("mode", data)
        print("[OK] /api/question/first returned valid question.")

    def test_03_api_next_question(self):
        """Test the /api/question/next endpoint."""
        print("Testing /api/question/next endpoint...")
        resume_text = "JANE DOE\nLead Backend Developer at TechCorp.\nSkills: Python, FastAPI, Redis."
        history = [
            {"role": "interviewer", "content": "What is connection pooling?", "is_follow_up": False},
            {"role": "candidate", "content": "A pool of reusable connections.", "score": 7, "justification": "Good", "breakdown": {}, "is_follow_up": False}
        ]
        response = requests.post(f"{self.api_url}/question/next", json={
            "resume_text": resume_text,
            "target_role": "Lead Backend Developer",
            "history": history
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("question", data)
        print("[OK] /api/question/next returned valid question.")

    def test_04_api_follow_up(self):
        """Test the /api/question/follow-up endpoint."""
        print("Testing /api/question/follow-up endpoint...")
        response = requests.post(f"{self.api_url}/question/follow-up", json={
            "resume_text": "Python, FastAPI",
            "target_role": "Backend Developer",
            "question": "What databases do you use?",
            "answer": "FastAPI is nice."
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("question", data)
        print("[OK] /api/question/follow-up returned valid follow-up.")

    def test_05_api_score(self):
        """Test the /api/score endpoint."""
        print("Testing /api/score endpoint...")
        response = requests.post(f"{self.api_url}/score", json={
            "question": "What is Redis?",
            "answer": "Redis is an in-memory key-value cache database.",
            "target_role": "Backend Developer"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("score", data)
        self.assertIn("is_weak", data)
        self.assertIn("justification", data)
        self.assertIn("breakdown", data)
        print("[OK] /api/score evaluated answer.")

    def test_06_api_evaluate(self):
        """Test the /api/evaluate endpoint."""
        print("Testing /api/evaluate endpoint...")
        history = [
            {"role": "interviewer", "content": "What is Redis?"},
            {"role": "candidate", "content": "An in-memory database.", "score": 8, "justification": "Good", "breakdown": {}}
        ]
        response = requests.post(f"{self.api_url}/evaluate", json={
            "target_role": "Backend Developer",
            "history": history
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("overall_score", data)
        self.assertIn("verdict", data)
        self.assertIn("key_strengths", data)
        self.assertIn("growth_areas", data)
        self.assertIn("communication_skills", data)
        self.assertIn("technical_depth", data)
        self.assertIn("problem_solving_adaptability", data)
        print("[OK] /api/evaluate generated structured assessment report.")

    def test_07_api_upload_audio(self):
        """Test the /api/upload_audio endpoint."""
        print("Testing /api/upload_audio endpoint...")
        # Create a mock audio payload
        mock_audio_content = b"RIFF....WAVEfmt....data...."
        files = {
            "file": ("test_recording.wav", mock_audio_content, "audio/wav")
        }
        data = {
            "question_index": 999
        }
        response = requests.post(f"{self.api_url}/upload_audio", files=files, data=data)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["status"], "success")
        self.assertTrue("question_999.wav" in json_data["file_path"])
        
        # Verify file exists on disk
        target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "audio", "question_999.wav")
        self.assertTrue(os.path.exists(target_path))
        
        # Cleanup
        if os.path.exists(target_path):
            os.remove(target_path)
        print("[OK] /api/upload_audio uploaded and stored file successfully.")

    def test_08_rag_vector_search(self):
        """Test the RAG engine chunking and vector similarity retrieval."""
        print("Testing RAG vector engine...")
        from core.rag_engine import ResumeRAG
        sample_resume = """
        JANE DOE
        Lead Backend Developer at TechCorp.
        
        EXPERIENCE:
        Designed high-throughput microservices using Python, FastAPI, and gRPC.
        Resolved database connection pool bottlenecks using SQLAlchemy and Redis caching.
        
        PROJECTS:
        Equilibria - Dynamic Supply Chain Decision Engine built with Kafka and Apache Spark.
        Optimized ETL pipelines handling over 10TB of daily data stream using partition salting.
        """
        rag = ResumeRAG(sample_resume)
        chunk_count = rag.get_indexed_chunk_count()
        self.assertGreater(chunk_count, 0)
        
        retrieved_spark = rag.query("Apache Spark ETL pipelines 10TB data", top_k=1)
        self.assertEqual(len(retrieved_spark), 1)
        self.assertTrue("Spark" in retrieved_spark[0] or "ETL" in retrieved_spark[0] or "10TB" in retrieved_spark[0])
        print(f"[OK] RAG engine successfully indexed {chunk_count} chunks and retrieved vector matches.")

if __name__ == "__main__":
    unittest.main()
