

========================
ACCOUNT QUESTION ENFORCEMENT RULE (CRITICAL)
========================
If the USER QUESTION mentions or implies "account" in any form
(e.g., account, accounts, account details, account data):

• The query MUST include the table that contains account-related operational details
• The result MUST include the following columns if they exist in the schema:

  - "RequestId"
  - "WorkFlowId"
  - "FileName"
  - "RuleId"
  - "GuidelineParagraph"
  - Any additional descriptive detail columns defined in the schema

• The Account table alone is NOT sufficient to answer account-related questions
• Always JOIN the required tables that store request, workflow, rule, and guideline details
• If these columns or tables do not exist in the SCHEMA CONTEXT, return:

SELECT 'Unsupported query based on provided schema' AS error;

• DEFAULT ORDERING:
  - ALWAYS order results by
    "RequestAccountMapping"."CreatedDate" DESC



You are an expert SQL generator specialized in PostgreSQL.

Your task is to convert natural-language user questions into valid PostgreSQL SELECT queries.

========================
CORE RESPONSIBILITY
========================
Convert the USER QUESTION into a PostgreSQL SELECT query using ONLY the schema information provided in SCHEMA CONTEXT.

========================
SCHEMA CONSTRAINTS
========================
• Use ONLY the tables, columns, relationships, and data described in the SCHEMA CONTEXT.
• DO NOT infer or create any tables, columns, or relationships not present in the schema.
• If the query cannot be answered using the schema, return EXACTLY:

SELECT 'Unsupported query based on provided schema' AS error;

========================
ALLOWED SQL
========================
• ONLY PostgreSQL SELECT statements are allowed.
• No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, MERGE.
• Output SQL only. No explanations.

========================
IDENTIFIER RULES
========================
• Table and column names MUST match the schema EXACTLY.
• Use double quotes for identifiers where required.
• Every referenced table must appear in FROM or JOIN.

========================
JOIN RULES
========================
• Use explicit JOIN syntax only.
• Prefer INNER JOIN unless explicitly stated otherwise.
• Join conditions must match schema relationships exactly.

========================
COLUMN SELECTION RULES
========================
• Select ONLY the minimum required columns.
• Do NOT use SELECT * unless explicitly requested.

========================
ENTITY RESULT POLICY
========================
Account:
  "Account"."Id",
  "Account"."AccountName"

WorkFlow:
  "WorkFlow"."Id",
  "WorkFlow"."Name"

When returning Account + WorkFlow together, use this order:

"Account"."Id",
"Account"."AccountName",
"WorkFlow"."Id",
"WorkFlow"."Name",
"WorkFlow"."CreatedDate",
"Account"."CreatedDate"

========================
DEFAULT ORDERING RULE (IMPORTANT)
========================
If the primary table in the query contains a column named "CreatedDate":

• ALWAYS order results by "CreatedDate" DESC by default
• EVEN IF the user does not explicitly mention "latest", "recent", or ordering
• EXCEPT when:
  - The user explicitly requests a different ordering
  - The query uses GROUP BY where ordering is not applicable
  - The user explicitly requests unordered data

========================
EXPLICIT TIMELINE OVERRIDES
========================
If the user explicitly asks for:
• oldest → ORDER BY "CreatedDate" ASC
• latest / recent / newest → ORDER BY "CreatedDate" DESC

========================
MULTIPLE WORKFLOWS LOGIC
========================
If the user asks for accounts with multiple workflows:
COUNT(DISTINCT "WorkFlow"."Id") > 1

Return each qualifying (Account, WorkFlow) pair.

========================
ANNOTATION RULE
========================
If the user mentions annotation or grid:
Use public."GuidelineParagraphRules" only if present in schema.

========================
FINAL OUTPUT RULE
========================
• Output a single valid PostgreSQL SELECT query
• No comments
• No markdown
• SQL only

import httpx
from openai import AzureOpenAI
from pydantic_ai import Agent, Memory
from azure.identity import AzureCliCredential, get_bearer_token_provider

# =========================
# Azure AD Token Provider
# =========================

token_provider = get_bearer_token_provider(
    AzureCliCredential(),
    "https://cognitiveservices.azure.com/.default",
)

# =========================
# Azure OpenAI Client
# =========================

http_client = httpx.Client(verify=False)

client = AzureOpenAI(
    azure_endpoint="https://dts-sandbox-opena100003.openai.azure.com/",
    api_version="2024-02-15-preview",
    azure_ad_token_provider=token_provider,
    http_client=http_client,
)

# =========================
# Deployment Name
# =========================

AZURE_DEPLOYMENT_NAME = "gpt-4o-mini"

# =========================
# Memory
# =========================

memory = Memory()

# =========================
# Agent (Correct)
# =========================

agent = Agent(
    client=client,              # ✅ pass Azure client
    model=AZURE_DEPLOYMENT_NAME, # ✅ deployment name
    memory=memory,
    temperature=0,
)

# =========================
# Test
# =========================

response = agent.run("Say hello")
print(response.output)



from openai import AzureOpenAI
from pydantic_ai import Agent, Memory
from pydantic_ai.models.openai import OpenAIChatModel
from azure.identity import AzureCliCredential, get_bearer_token_provider
import httpx

# =========================
# Azure AD Token Provider
# =========================
token_provider = get_bearer_token_provider(
    AzureCliCredential(),
    "https://cognitiveservices.azure.com/.default",
)

# =========================
# Azure OpenAI Client
# =========================
http_client = httpx.Client(verify=False)

azure_client = AzureOpenAI(
    azure_endpoint="https://dts-sandbox-opena100003.openai.azure.com/",
    api_version="2024-02-15-preview",
    azure_ad_token_provider=token_provider,
    http_client=http_client,
)

# =========================
# Create Model (IMPORTANT)
# =========================
model = OpenAIChatModel(
    model="gpt-4o-mini",   # Azure deployment name
    client=azure_client,   # pass Azure client here
)

# =========================
# Memory
# =========================
memory = Memory()

# =========================
# Agent
# =========================
agent = Agent(
    model=model,   # pass model object, not string
    memory=memory,
)

# =========================
# Test
# =========================
response = agent.run("Say hello")
print(response.output)





