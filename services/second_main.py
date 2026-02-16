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


"""
Working LangChain Text-to-SQL Generator
Fixed version with proper syntax and variable handling
"""

from langchain_openai import AzureChatOpenAI
from azure.identity import AzureCliCredential, get_bearer_token_provider
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx

# Import your rules and schema
from rules import STRICT_ANTI_HALLUCINATION_RULES
from datainsertion import a


# =============================================================================
# PYDANTIC MODEL
# =============================================================================

class SqlQueryOutput(BaseModel):
    can_generate: bool = Field(description="Whether a valid SQL query can be generated")
    sql_query: Optional[str] = Field(default=None, description="PostgreSQL SELECT query, only if can_generate=True")
    explanation: str = Field(description="Explanation or reason for this query")
    tables_used: List[str] = Field(default_factory=list, description="Tables used")
    columns_selected: List[str] = Field(default_factory=list, description="Columns selected")


# =============================================================================
# AZURE LLM SETUP
# =============================================================================

def create_azure_llm():
    """Create Azure OpenAI LLM"""
    token_provider = get_bearer_token_provider(
        AzureCliCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    
    llm = AzureChatOpenAI(
        deployment_name="GPT-40-mini",
        openai_api_version="2024-02-15-preview",
        azure_endpoint="https://dts-sandbox-openai00003.openai.azure.com/",
        azure_ad_token_provider=token_provider,
        http_client=httpx.Client(verify=False),
        temperature=0  # Deterministic
    )
    
    return llm


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

def create_sql_chain():
    """Create the LangChain chain"""
    
    # Get schema context
    schema_context = a.get_schema_context()
    
    # Create parser
    parser = JsonOutputParser(pydantic_object=SqlQueryOutput)
    
    # System template - Note: Double curly braces {{}} to escape JSON
    system_template = f"""You are a STRICT PostgreSQL query generator with ZERO TOLERANCE for hallucination.

{STRICT_ANTI_HALLUCINATION_RULES}

{schema_context}

════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
════════════════════════════════════════════════════════════════════════════

You MUST respond with valid JSON in this format:

{{{{
  "can_generate": true or false,
  "sql_query": "SELECT ... FROM ..." or null,
  "explanation": "Explanation here",
  "tables_used": ["Table1", "Table2"],
  "columns_selected": ["column1", "column2"]
}}}}

{parser.get_format_instructions()}

════════════════════════════════════════════════════════════════════════════
REMEMBER: VALIDATION BEFORE GENERATION
════════════════════════════════════════════════════════════════════════════

1. Extract required tables from question
2. Check each against ALLOWED TABLES list
3. If ANY table not in list → ERROR
4. Extract required columns from question
5. Check each against table's ALLOWED COLUMNS list
6. If ANY column not in list → ERROR
7. Check required JOINs against ALLOWED RELATIONSHIPS
8. If ANY relationship not documented → ERROR
9. ONLY THEN generate SQL

DO NOT SKIP THESE STEPS.
"""
    
    # User template - Note: Single curly braces for variables
    user_template = """USER QUESTION: {user_question}

VALIDATION CHECKLIST (complete before generating SQL):

1. What tables are needed? [LIST THEM]
2. Are they in ALLOWED TABLES? [CHECK EACH]
3. What columns are needed? [LIST THEM]
4. Are they in table's ALLOWED COLUMNS? [CHECK EACH]
5. What JOINs are needed? [LIST THEM]
6. Are they in ALLOWED RELATIONSHIPS? [CHECK EACH]

If ALL checks pass → Generate SQL
If ANY check fails → Return ERROR with specific reason

Generate your response:"""
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("human", user_template)
    ])
    
    # Create LLM
    llm = create_azure_llm()
    
    # Create chain
    chain = prompt | llm | parser
    
    return chain


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function"""
    
    print("="*80)
    print("TEXT-TO-SQL GENERATOR")
    print("="*80)
    
    # Create chain
    print("\n🔧 Creating LangChain chain...")
    chain = create_sql_chain()
    print("✅ Chain created\n")
    
    # Test queries
    test_queries = [
        "list all the accounts",
        "show accounts with workflows",
        "show customers",  # Should fail if no Customer table
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"🔵 USER QUESTION: {query}")
        print(f"{'='*80}")
        
        try:
            # IMPORTANT: Use "user_question" as the key (matches template variable)
            result = chain.invoke({"user_question": query})
            
            print(f"\n✅ Result:")
            print(f"   Can Generate: {result['can_generate']}")
            print(f"   Explanation: {result['explanation']}")
            
            if result['can_generate']:
                print(f"\n📝 SQL Query:")
                print(f"   {result['sql_query']}")
                print(f"\n📊 Metadata:")
                print(f"   Tables: {', '.join(result['tables_used'])}")
                print(f"   Columns: {', '.join(result['columns_selected'])}")
            else:
                print(f"\n❌ Cannot generate query")
                if result['sql_query']:
                    print(f"   {result['sql_query']}")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
        
        print()
    
    # Interactive mode
    print(f"\n{'='*80}")
    print("INTERACTIVE MODE")
    print(f"{'='*80}\n")
    print("Type your questions (or 'quit' to exit):\n")
    
    while True:
        try:
            user_input = input("🔵 Your question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            print("\n🔄 Processing...\n")
            
            # Invoke chain with correct variable name
            result = chain.invoke({"user_question": user_input})
            
            print(f"✅ Result:")
            print(f"   Can Generate: {result['can_generate']}")
            print(f"   Explanation: {result['explanation']}")
            
            if result['can_generate']:
                print(f"\n📝 SQL Query:")
                print(f"   {result['sql_query']}")
            else:
                print(f"\n❌ Cannot generate query")
                if result['sql_query']:
                    print(f"   {result['sql_query']}")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    main()
