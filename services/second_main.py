from langchain_openai import AzureChatOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider
from langchain_core.prompts import ChatPromptTemplate
import httpx


# =========================
# Azure OpenAI LLM
# =========================
def create_azure_llm():
    token_provider = get_bearer_token_provider(
        AzureCliCredential(),
        "https://cognitiveservices.azure.com/.default",
    )

    llm = AzureChatOpenAI(
        deployment_name="GPT-4o-mini",   # change to your deployment
        openai_api_version="2024-02-15-preview",
        azure_endpoint="https://YOUR-ENDPOINT.openai.azure.com/",
        azure_ad_token_provider=token_provider,
        http_client=httpx.Client(verify=False),
        temperature=0,
    )
    return llm


# =========================
# PROMPT — STRICT SQL ONLY
# =========================
system_prompt = """
You are an expert PostgreSQL query generator.

RULES:
- Output ONLY a PostgreSQL SELECT query
- Do NOT include explanation
- Do NOT include markdown
- Do NOT include comments
- Do NOT include anything except SQL
"""

user_prompt = """
Convert the following question into PostgreSQL query:

Question: {user_question}
"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", user_prompt),
    ]
)


# =========================
# CHAIN
# =========================
llm = create_azure_llm()
chain = prompt | llm


# =========================
# RUN
# =========================
result = chain.invoke(
    {"user_question": "List all the accounts"}
)

print(result.content)
