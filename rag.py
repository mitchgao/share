from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.pgvector import PGVector
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI

# Database connection
DATABASE_URL = "postgresql://user:password@localhost/chatbot_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Define the PGVector table
class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)

# Initialize the vector store
def load_or_create_vectorstore():
    embeddings = OpenAIEmbeddings()
    
    # Connect to PostgreSQL-based vector store
    vectorstore = PGVector(
        connection_string=DATABASE_URL,
        table_name="knowledge_base",
        embedding_function=embeddings
    )

    session = SessionLocal()
    documents = session.query(KnowledgeBase).all()
    session.close()

    # If the table is empty, load data and store embeddings
    if not documents:
        print("No data found in vector store. Ingesting data...")
        session = SessionLocal()
        raw_data = session.query(KnowledgeBase).all()
        session.close()

        docs = [Document(page_content=row.content) for row in raw_data]
        vectorstore.add_documents(docs)

    return vectorstore

vectorstore = load_or_create_vectorstore()
retriever = vectorstore.as_retriever()

# Define structured prompt template
query_prompt = PromptTemplate(
    input_variables=["question"],
    template="You are a helpful assistant. Retrieve relevant knowledge and generate an accurate answer.\n\nQuestion: {question}\n\nAnswer:"
)

# RAG-based chatbot using PostgreSQL vector store
def chat_with_rag(conversation_id, user_input):
    chat_model = AzureChatOpenAI(deployment_name="your_deployment", model="gpt-4")

    qa_chain = RetrievalQA.from_chain_type(
        llm=chat_model,
        retriever=retriever,
        chain_type_kwargs={"prompt": query_prompt}
    )

    response = qa_chain.run(user_input)

    # Store conversation in PostgreSQL
    session = SessionLocal()
    session.add(Message(conversation_id=conversation_id, role="user", content=user_input))
    session.add(Message(conversation_id=conversation_id, role="assistant", content=response))
    session.commit()
    session.close()

    return response