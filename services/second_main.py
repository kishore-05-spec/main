import asyncio
from openai import AsyncAzureOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from azure.identity import AzureCliCredential, get_bearer_token_provider

# =========================
# 1. Azure AD Token Provider
# =========================
token_provider = get_bearer_token_provider(
    AzureCliCredential(),
    "https://cognitiveservices.azure.com/.default",
)

# =========================
# 2. Azure OpenAI Client (MUST be Async)
# =========================
# PydanticAI requires the AsyncAzureOpenAI client
azure_client = AsyncAzureOpenAI(
    azure_endpoint="https://dts-sandbox-opena100003.openai.azure.com/",
    api_version="2024-02-15-preview",
    azure_ad_token_provider=token_provider,
)

# =========================
# 3. Model Setup (The Fix)
# =========================
# The client is now passed inside 'OpenAIProvider'
model = OpenAIModel(
    "gpt-4o-mini",
    provider=OpenAIProvider(openai_client=azure_client)
)

# =========================
# 4. Agent Setup
# =========================
agent = Agent(
    model=model,
    system_prompt="You are a helpful AI assistant."
)

# =========================
# 5. Run
# =========================
if __name__ == "__main__":
    # Use run_sync for simple scripts, or await agent.run() in async functions
    result = agent.run_sync("Say hello")
    print(result.data)
