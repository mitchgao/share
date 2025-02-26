from sqlalchemy import create_engine, Column, String, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import uuid
from langchain_openai import AzureChatOpenAI
import dash
from dash import dcc, html, Input, Output, State
import dash

# Database Setup
Base = declarative_base()
DATABASE_URL = "postgresql://user:password@localhost/chatbot_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")

Conversation.messages = relationship("Message", order_by=Message.timestamp, back_populates="conversation")
Base.metadata.create_all(engine)

# Chat Model
chat_model = AzureChatOpenAI(deployment_name="your_deployment", model="gpt-4")

def create_conversation(user_id, title):
    session = SessionLocal()
    conversation = Conversation(user_id=user_id, title=title)
    session.add(conversation)
    session.commit()
    session.close()
    return conversation.id

def delete_conversation(conversation_id):
    session = SessionLocal()
    session.query(Message).filter(Message.conversation_id == conversation_id).delete()
    session.query(Conversation).filter(Conversation.id == conversation_id).delete()
    session.commit()
    session.close()

def get_user_conversations(user_id):
    session = SessionLocal()
    conversations = session.query(Conversation).filter_by(user_id=user_id).order_by(Conversation.created_at.desc()).all()
    session.close()
    return [{"id": conv.id, "title": conv.title, "created_at": conv.created_at} for conv in conversations]

def get_conversation_history(conversation_id):
    session = SessionLocal()
    messages = session.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
    session.close()
    return [{"role": msg.role, "content": msg.content} for msg in messages]

def chat_with_gpt(conversation_id, user_input):
    messages = get_conversation_history(conversation_id)
    messages.append({"role": "user", "content": user_input})
    response = chat_model.invoke(messages)
    session = SessionLocal()
    session.add(Message(conversation_id=conversation_id, role="user", content=user_input))
    session.add(Message(conversation_id=conversation_id, role="assistant", content=response))
    session.commit()
    session.close()
    return response

# Dash App
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("ChatGPT Chatbot"),
    dcc.Dropdown(id="conversation-dropdown", placeholder="Select a conversation"),
    html.Button("New Conversation", id="new-conversation-btn", n_clicks=0),
    html.Button("Delete Conversation", id="delete-conversation-btn", n_clicks=0, style={"margin-left": "10px"}),
    html.Div(id="chat-history", style={"height": "400px", "overflowY": "scroll", "border": "1px solid black", "padding": "10px"}),
    dcc.Input(id="user-input", type="text", placeholder="Type a message", style={"width": "80%"}),
    html.Button("Send", id="send-btn", n_clicks=0),
    dcc.Store(id="selected-conversation")
])

@app.callback(
    Output("conversation-dropdown", "options"),
    Output("conversation-dropdown", "value"),
    Input("new-conversation-btn", "n_clicks"),
    Input("delete-conversation-btn", "n_clicks"),
    State("conversation-dropdown", "value"),
    prevent_initial_call=True
)
def update_conversation_list(new_clicks, delete_clicks, selected_conversation):
    user_id = "test_user"
    ctx = dash.callback_context
    if ctx.triggered_id == "new-conversation-btn":
        new_id = create_conversation(user_id, f"Conversation {uuid.uuid4().hex[:6]}")
    elif ctx.triggered_id == "delete-conversation-btn" and selected_conversation:
        delete_conversation(selected_conversation)
    conversations = get_user_conversations(user_id)
    return [{"label": conv["title"], "value": conv["id"]} for conv in conversations], None

@app.callback(
    Output("chat-history", "children"),
    Input("conversation-dropdown", "value")
)
def load_chat_history(conversation_id):
    if conversation_id:
        history = get_conversation_history(conversation_id)
        return [html.P(f"{msg['role']}: {msg['content']}") for msg in history]
    return ""

@app.callback(
    Output("chat-history", "children", allow_duplicate=True),
    Input("send-btn", "n_clicks"),
    State("user-input", "value"),
    State("conversation-dropdown", "value"),
    prevent_initial_call="initial_duplicate"
)
def handle_message_sending(n_clicks, user_input, conversation_id):
    if user_input and conversation_id:
        response = chat_with_gpt(conversation_id, user_input)
        history = get_conversation_history(conversation_id)
        return [html.P(f"{msg['role']}: {msg['content']}") for msg in history]
    return dash.no_update

if __name__ == "__main__":
    app.run_server(debug=True)
