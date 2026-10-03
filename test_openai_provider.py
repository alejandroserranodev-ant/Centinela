#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("TESTING OPENAI PROVIDER WITH REAL API CALL")
print("=" * 70)

api_key = os.getenv("OPENAI_API_KEY")
provider_name = os.getenv("LLM_PROVIDER")
model_name = os.getenv("LLM_MODEL")

print("\n[CHECKING] Environment Variables:")
print(f"  LLM_PROVIDER: {provider_name}")
print(f"  LLM_MODEL: {model_name}")
print(f"  OPENAI_API_KEY: {api_key[:20]}..." if api_key else "  OPENAI_API_KEY: NOT SET")

if not api_key or provider_name != "openai" or not model_name:
    print("\n[ERROR] Missing configuration!")
    sys.exit(1)

print("\n[INIT] Getting OpenAI provider...")
from packages.agents.centinela_agents.provider_factory import get_provider
provider = get_provider()
print(f"  OK - Provider: {type(provider).__name__}")
print(f"  OK - Model: {provider.config.model}")

print("\n[CALLING] Making real OpenAI API request...")
from packages.agents.centinela_agents.llm_provider import LLMRequest

request = LLMRequest(
    system_prompt="You are helpful.",
    user_prompt="Say 'OpenAI works!' briefly.",
    max_tokens=30,
)

response = provider.generate_text(request)

print("\n[RESPONSE]")
print(f"  Text: {response.text}")
print(f"  Prompt tokens: {response.usage['prompt_tokens']}")
print(f"  Completion tokens: {response.usage['completion_tokens']}")
print(f"  Total tokens: {response.usage['prompt_tokens'] + response.usage['completion_tokens']}")

from packages.agents.centinela_agents.observability import TokenUsage
usage = TokenUsage(
    prompt_tokens=response.usage['prompt_tokens'],
    completion_tokens=response.usage['completion_tokens'],
    model=model_name,
    provider="openai"
)

print(f"\n[COST] ${usage.cost():.6f} USD")
print("\n" + "=" * 70)
print("[SUCCESS] OPENAI PROVIDER IS WORKING WITH REAL API!")
print("=" * 70)
