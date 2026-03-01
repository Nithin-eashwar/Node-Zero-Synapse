"""
LLM provider factory.

Returns the appropriate LLM instance based on configuration.
Default is Google Gemini for local development.

Set LLM_PROVIDER env var to switch:
    - "gemini"   → Google Gemini (default, requires GOOGLE_API_KEY)
    - "bedrock"  → Amazon Bedrock (requires AWS credentials)

Bedrock config env vars:
    AWS_REGION             (default: us-east-1)
    BEDROCK_MODEL_ID       (default: anthropic.claude-3-5-sonnet-20241022-v2:0)
"""

import os
import dotenv
from typing import Optional

dotenv.load_dotenv()


def create_llm(temperature: float = 0.2, provider: Optional[str] = None):
    """
    Create and return an LLM instance via LangChain.
    
    Args:
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        provider: "gemini" or "bedrock". If None, reads LLM_PROVIDER env var.
        
    Returns:
        A LangChain BaseChatModel, or None if credentials are missing.
    """
    provider = provider or os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "bedrock":
        return _create_bedrock(temperature)
    elif provider == "gemini":
        return _create_gemini(temperature)
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported: 'gemini', 'bedrock'"
        )


def _create_gemini(temperature: float):
    """Create Google Gemini LLM via LangChain."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[LLM] Warning: GOOGLE_API_KEY not found. AI features disabled.")
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=api_key,
            temperature=temperature,
            convert_system_message_to_human=True,
        )
        print(f"[LLM] Using Google Gemini ({llm.model})")
        return llm
    except ImportError:
        print("[LLM] Error: langchain-google-genai not installed.")
        return None


def _create_bedrock(temperature: float):
    """Create Amazon Bedrock LLM via LangChain."""
    region = os.getenv("AWS_REGION", "us-east-1")
    model_id = os.getenv(
        "BEDROCK_MODEL_ID",
        "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )

    try:
        from langchain_aws import ChatBedrock

        llm = ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={
                "temperature": temperature,
                "max_tokens": 4096,
            },
        )
        print(f"[LLM] Using Amazon Bedrock ({model_id}) in {region}")
        return llm
    except ImportError:
        print(
            "[LLM] Error: langchain-aws not installed. "
            "Install with: pip install langchain-aws"
        )
        return None
    except Exception as e:
        print(f"[LLM] Error initializing Bedrock: {e}")
        return None
