from langchain_openai import AzureChatOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx


# =========================
# Pydantic Output Model
# =========================
class SqlQueryOutput(BaseModel):
    can_generate: bool = Field(description="Whether SQL can be generated")
    sql_query: Optional[str] = Field(
        default=None,
        description="PostgreSQL SELECT query"
    )
    explanation: str = Field(description="Explanation")
    tables_used: List[str] = Field(default_factory=list)
    columns_selected: List[str] = Field(default_factory=list)


# =========================
# Azure OpenAI LLM
# =========================
def create_azure_llm():
    token_provider = get_bearer_token_provider(
        AzureCliCredential(),
        "https://cognitiveservices.azure.com/.default",
    )

    llm = AzureChatOpenAI(
        deployment_name="GPT-4o-mini",
        openai_api_version="2024-02-15-preview",
        azure_endpoint="https://YOUR-ENDPOINT.openai.azure.com/",
        azure_ad_token_provider=token_provider,
        http_client=httpx.Client(verify=False),
        temperature=0,
    )
    return llm


# =========================
# Parser
# =========================
parser = JsonOutputParser(pydantic_object=SqlQueryOutput)
format_instructions = parser.get_format_instructions()


# =========================
# PROMPTS
# =========================

system_template = f"""
You are a STRICT PostgreSQL query generator.

OUTPUT FORMAT:
{format_instructions}

IMPORTANT:
Validate tables and columns before generating SQL.
"""

user_template = """
USER QUESTION: {user_question}

Generate SQL if valid, else explain why not.
"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_template),
        ("human", user_template),
    ]
)


# =========================
# CHAIN
# =========================
llm = create_azure_llm()
chain = prompt | llm | parser


# =========================
# RUN
# =========================
result = chain.invoke(
    {"user_question": "List all the accounts"}
)

print(result)
