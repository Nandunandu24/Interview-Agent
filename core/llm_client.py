import os
import json
from dotenv import load_dotenv

# Clear proxy environment variables to prevent httpx/urllib3 proxies arguments collision in SDKs
for var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(var, None)

# Load environment variables
load_dotenv()

# We import the SDKs lazily inside functions to prevent import errors
# if one of them fails to install or is not used.

def _get_groq_client():
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or "your_groq_api_key" in api_key:
            return None
        return Groq(api_key=api_key)
    except Exception:
        return None

def _get_gemini_client():
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or "your_gemini_api_key" in api_key:
            return None
        genai.configure(api_key=api_key)
        return genai
    except Exception:
        return None

def ask_llm(prompt: str, expect_json: bool = False, provider: str = None) -> str:
    """
    Queries the selected LLM provider (Groq or Gemini).
    Enforces JSON mode if expect_json is True.
    Automatically falls back to the alternate provider if the primary provider fails or has no key.
    """
    # 1. Determine provider order based on preferences & configuration
    configured_provider = provider or os.getenv("LLM_PROVIDER", "gemini").lower()
    
    providers_to_try = [configured_provider]
    if configured_provider == "groq":
        providers_to_try.append("gemini")
    else:
        providers_to_try.append("groq")
        
    errors = []
    
    for current_provider in providers_to_try:
        if current_provider == "groq":
            client = _get_groq_client()
            if not client:
                errors.append("Groq API key not set or groq library not installed.")
                continue
            
            model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            try:
                kwargs = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                }
                if expect_json:
                    # Groq JSON mode requires the word "json" to be present in the prompt.
                    # We ensure the prompt instructs the model to return JSON.
                    kwargs["response_format"] = {"type": "json_object"}
                    
                chat_completion = client.chat.completions.create(**kwargs)
                response_text = chat_completion.choices[0].message.content
                
                # Sanity check JSON if expected
                if expect_json:
                    json.loads(response_text) # check if valid JSON
                    
                return response_text
            except Exception as e:
                errors.append(f"Groq API call failed: {str(e)}")
                
        elif current_provider == "gemini":
            genai_client = _get_gemini_client()
            if not genai_client:
                errors.append("Gemini API key not set or google-generativeai library not installed.")
                continue
                
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            try:
                generation_config = {
                    "temperature": 0.2,
                }
                if expect_json:
                    generation_config["response_mime_type"] = "application/json"
                    
                model = genai_client.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config
                )
                
                response = model.generate_content(prompt)
                response_text = response.text
                
                # Sanity check JSON if expected
                if expect_json:
                    json.loads(response_text)
                    
                return response_text
            except Exception as e:
                errors.append(f"Gemini API call failed: {str(e)}")
                
    raise RuntimeError(
        f"All configured LLM API calls failed. Errors encountered:\n" + "\n".join(errors)
    )
