from typing import List
from langchain_openai import AzureOpenAI
from langchain_sql_database import SQLDatabase
from langchain.tools.sql_database.tool import (
    QuerySQLDataBaseTool,
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
)
from langchain.memory import ConversationSummaryBufferMemory
import langgraph

# --- LLM and DB setup ---
llm = AzureOpenAI(
    api_key="YOUR_AZURE_OPENAI_KEY",
    azure_endpoint="https://YOUR_RESOURCE_NAME.openai.azure.com/",
    deployment_name="YOUR_DEPLOYMENT_NAME",
    api_version="2023-05-15",
    model="gpt-35-turbo"
)
db = SQLDatabase.from_uri("postgresql+psycopg2://user:password@host:port/dbname")

# --- Load product code mapping from DB ---
def load_product_map_table(db) -> List[dict]:
    res = db._execute(
        "SELECT pro_clasfn_c, pro_lvl2_c, pro_clasfn_t, pro_lvl2_t, first_level, second_level "
        "FROM product_mapping").fetchall()
    return [dict(row) for row in res]

product_map = load_product_map_table(db)
pro_clasfn_c_set = sorted({row["pro_clasfn_c"] for row in product_map})
pro_lvl2_c_set = sorted({row["pro_lvl2_c"] for row in product_map})

# --- Compose schema and constraints context ---
def build_schema_documentation(product_map: List[dict]) -> str:
    doc = []
    doc.append("Table: trade_volume_by_product")
    doc.append("Columns:")
    doc.append("- pro_clasfn_c: VARCHAR. Product classification code. Must be one of: " +
               ", ".join(f"{c}" for c in pro_clasfn_c_set))
    doc.append("- pro_lvl2_c: VARCHAR, Level 2 product code. Must be one of: " +
                ", ".join(f"{c}" for c in pro_lvl2_c_set))
    doc.append("- trd_d: DATE. Trade date, format YYYY-MM-DD.")
    doc.append("- acc_macc_c: VARCHAR. Account management code.")
    doc.append("- txn_buy_sell_c: VARCHAR. Must be 'BUY' or 'SELL'.")
    doc.append("- txn_count: INT. Number of transactions.")
    doc.append("- txn_q: FLOAT. Quantity.")
    doc.append("- txn_princ_a: FLOAT, Notional.")
    doc.append("- txn_gr_prft_a: FLOAT, Commission/Gross profit.")

    doc.append("\nTable: product_mapping")
    doc.append("Columns:")
    doc.append("- pro_clasfn_c, pro_clasfn_t: Code and description of first-level product classification.")
    doc.append("- pro_lvl2_c, pro_lvl2_t: Code and description of second-level product.")
    doc.append("- first_level, second_level: business groupings.")

    doc.append("\nBusiness code-to-meaning mapping examples (from 'product_mapping'):")
    for row in product_map[:6]:
        doc.append(f"  {row['pro_clasfn_c']} ({row['pro_clasfn_t']}), {row['pro_lvl2_c']} ({row['pro_lvl2_t']}) -> "
                   f"{row['first_level']} > {row['second_level']}")

    doc.append("\nField constraints:")
    doc.append("- Only values from the code lists above are valid for pro_clasfn_c and pro_lvl2_c.")
    doc.append("- Only 'BUY' or 'SELL' allowed for txn_buy_sell_c.")
    doc.append("- trd_d must be a valid date in YYYY-MM-DD.")
    doc.append("\nALWAYS join product_mapping ON pro_clasfn_c+pro_lvl2_c to provide code explanations. Explain code meanings in output.")
    return "\n".join(doc)

schema_context = build_schema_documentation(product_map)

SYSTEM_PROMPT = f"""
You are a senior business analyst agent for the trading desk and senior management.

- Your job is to answer business questions about trade volume, commissions, and trends.
- You always analyze, summarize, and compare (sum, avg, count, % delta) as needed.
- You use the tables and schema below, and strictly apply all field constraints.
- You must JOIN trade_volume_by_product with product_mapping (ON pro_clasfn_c, pro_lvl2_c) when returning or grouping by codes, and always explain product codes and business groupings.
- Only use code values and filters that are allowed by the code lists in the schema below, and never hallucinate values.
- For time periods like "week over week", "YTD", etc. do any calendar logic in SQL.

Here is your schema, field constraints, and mapping context:
{schema_context}
"""

# --- ConversationSummaryBufferMemory: summarize history automatically after k exchanges ---
memory = ConversationSummaryBufferMemory(
    llm=llm,
    k=8,  # number of recent exchanges to keep before summarizing
)

# --- SQL Database Tools (directly from DB object) ---
tools = [
    QuerySQLDataBaseTool(db=db),
    InfoSQLDatabaseTool(db=db),
    ListSQLDatabaseTool(db=db),
]

# --- LangGraph node as a multi-modal "agent" ---
from langgraph.graph import MessageGraph

graph = MessageGraph()
# Memory can be attached to the graph state or passed explicitly if needed

@graph.node
def business_agent_node(state, message):
    # The memory object keeps the conversation state and can summarize long histories.
    # The tools are passed in; LLM prompt is in SYSTEM_PROMPT.
    from langchain.agents.react import create_react_agent
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        memory=memory,
        verbose=True
    )
    result = agent.invoke({"input": message})
    return result["output"]

graph.add_edge(graph.start, business_agent_node)
graph.add_edge(business_agent_node, graph.end)

# --- How to use with a user query ---
def ask_agent(question):
    print('\nUSER:', question)
    result = graph.run(message=question)
    print('AGENT:', result)

if __name__ == "__main__":
    ask_agent("Why are equity commissions down 10% week over week?")
    ask_agent("What is the trading volume and commission of year to date fixed income etfs?")
    ask_agent("What is the average commission for each second_level business in product_mapping for this month?")
    ask_agent("How many buy-side bond trades did we do this quarter? Please explain what codes mean.")
