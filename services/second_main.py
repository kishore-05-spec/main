import asyncio
from openai import AsyncAzureOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
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
# 2. Async Azure Client
# =========================
# Note: Pydantic-AI requires the Async client for its execution engine
azure_client = AsyncAzureOpenAI(
    azure_endpoint="https://dts-sandbox-opena100003.openai.azure.com/",
    api_version="2024-02-15-preview",
    azure_ad_token_provider=token_provider,
)

# =========================
# 3. OpenAIChatModel Setup
# =========================
# 'openai_client' is passed inside the OpenAIProvider wrapper
model = OpenAIChatModel(
    "gpt-4o-mini", # This should match your Azure deployment name
    provider=OpenAIProvider(openai_client=azure_client)
)

# =========================
# 4. Agent Setup
# =========================
agent = Agent(model=model)

# =========================
# 5. Execution
# =========================
if __name__ == "__main__":
    # run_sync is a helper for non-async environments
    result = agent.run_sync("Say hello")
    print(result.data)
