import dash
from dash import dcc, html, Input, Output, State
import psycopg2
import uuid
from sqlalchemy import create_engine, Column, Integer, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.pgvector import PGVector
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Database connection
DATABASE_URL = "postgresql://user:password@localhost/chatbot_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Define database tables
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Text, ForeignKey("conversations.id"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)

Base.metadata.create_all(engine)

# Initialize vector store
def load_or_create_vectorstore():
    embeddings = OpenAIEmbeddings()
    vectorstore = PGVector(
        connection_string=DATABASE_URL,
        table_name="knowledge_base",
        embedding_function=embeddings
    )
    return vectorstore

vectorstore = load_or_create_vectorstore()
retriever = vectorstore.as_retriever()

# Structured prompt template
query_prompt = PromptTemplate(
    input_variables=["question"],
    template="You are a helpful assistant. Retrieve relevant knowledge and generate an accurate answer.\n\nQuestion: {question}\n\nAnswer:"
)

def chat_with_rag(conversation_id, user_input):
    chat_model = AzureChatOpenAI(deployment_name="your_deployment", model="gpt-4")
    qa_chain = RetrievalQA.from_chain_type(
        llm=chat_model,
        retriever=retriever,
        chain_type_kwargs={"prompt": query_prompt}
    )
    response = qa_chain.run(user_input)
    
    session = SessionLocal()
    session.add(Message(conversation_id=conversation_id, role="user", content=user_input))
    session.add(Message(conversation_id=conversation_id, role="assistant", content=response))
    session.commit()
    session.close()
    
    return response

# Dash layout
app.layout = html.Div([
    html.H1("Chatbot with RAG & Persistent Conversations"),
    dcc.Input(id="conversation-name", type="text", placeholder="Enter conversation name"),
    html.Button("Start New Conversation", id="start-conversation"),
    html.H3("Existing Conversations"),
    dcc.Dropdown(id="conversation-list", placeholder="Select a conversation"),
    html.Button("Delete Conversation", id="delete-conversation"),
    html.H3("Chat"),
    dcc.Textarea(id="chat-history", style={"width": "100%", "height": "300px"}, readOnly=True),
    dcc.Input(id="user-input", type="text", placeholder="Type your message"),
    html.Button("Send", id="send-message"),
])

# Callbacks
@app.callback(
    Output("conversation-list", "options"),
    Input("start-conversation", "n_clicks"),
    State("conversation-name", "value"),
    prevent_initial_call=True
)
def create_conversation(n_clicks, name):
    session = SessionLocal()
    conversation_id = str(uuid.uuid4())
    session.add(Conversation(id=conversation_id, name=name))
    session.commit()
    session.close()
    
    return load_conversation_list()

@app.callback(
    Output("conversation-list", "options"),
    Input("delete-conversation", "n_clicks"),
    State("conversation-list", "value"),
    prevent_initial_call=True
)
def delete_conversation(n_clicks, conversation_id):
    session = SessionLocal()
    session.query(Message).filter(Message.conversation_id == conversation_id).delete()
    session.query(Conversation).filter(Conversation.id == conversation_id).delete()
    session.commit()
    session.close()
    return load_conversation_list()

def load_conversation_list():
    session = SessionLocal()
    conversations = session.query(Conversation).all()
    session.close()
    return [{"label": conv.name, "value": conv.id} for conv in conversations]

@app.callback(
    Output("chat-history", "value"),
    Input("send-message", "n_clicks"),
    State("conversation-list", "value"),
    State("user-input", "value"),
    prevent_initial_call=True
)
def send_message(n_clicks, conversation_id, user_input):
    if not conversation_id:
        return "Please select a conversation."
    
    response = chat_with_rag(conversation_id, user_input)
    session = SessionLocal()
    messages = session.query(Message).filter(Message.conversation_id == conversation_id).all()
    session.close()
    
    chat_history = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
    return chat_history

if __name__ == "__main__":
    app.run_server(debug=True)
