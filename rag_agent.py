import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

from mistralai import Mistral
from system_prompt import get_system_prompt

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Define the job description (to be used in the user prompt)
job_description = """
Looking for a Python Developer in India with strong skills in software development.
"""

class ExcelLoader:
    """Loader that converts each Excel sheet into a Document."""
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self):
        docs = []
        xls = pd.ExcelFile(self.file_path)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            text = df.to_string(index=False)
            docs.append(Document(
                page_content=text,
                metadata={"source": self.file_path, "sheet_name": sheet_name}
            ))
        return docs

class RAGAgent:
    """
    RAGAgent loads candidate profiles from an Excel file, splits and embeds the text,
    performs a similarity search, and then passes the retrieved context along with the
    job description and query to the Mistral LLM using ChatPromptTemplate.
    """
    def __init__(self, excel_file: str):
        self.excel_file = excel_file

    def load_documents(self):
        logging.info("Loading Excel file from: %s", self.excel_file)
        loader = ExcelLoader(self.excel_file)
        return loader.load()

    def split_documents(self, documents):
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        return splitter.split_documents(documents)

    def get_embedding(self):
        model_path = "mixedbread-ai/mxbai-embed-large-v1"
        device = "cpu"  # Change to "cuda" if a GPU is available
        model_kwargs = {"device": device}
        encode_kwargs = {"normalize_embeddings": False}
        embeddings = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        return embeddings

    def build_vector_db(self, documents):
        splits = self.split_documents(documents)
        embeddings = self.get_embedding()
        current_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        persist_directory = f"docs/chroma/{current_timestamp}"
        vectordb = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=persist_directory
        )
        return vectordb

    def retrieve_context(self, query: str) -> str:
        docs = self.load_documents()
        logging.info("Documents loaded from Excel.")
        vectordb = self.build_vector_db(docs)
        logging.info("Vector database built.")
        results = vectordb.similarity_search(query)
        context = "\n\n".join(doc.page_content for doc in results)
        return context

    def call_mistral(self, context: str, query: str) -> str:
        # Retrieve the system prompt from system_prompt.py
        system_message = get_system_prompt()
        
        # Build the chat prompt using ChatPromptTemplate
        human_template = (
            "Candidate Context:\n{context}\n\n"
            "Job Description:\n{job_description}\n\n"
            "Query:\n{query}\n\n"
            "Based on the above, please provide an intelligent and detailed response that highlights the candidates' "
            "qualifications and how they align with the job requirements."
        )
        
        chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_message),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
        
        # Format the prompt with dynamic variables
        prompt_messages = chat_prompt.format_prompt(
            context=context, job_description=job_description, query=query
        ).to_messages()
        
        # Load Mistral API key from environment
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            logging.error("MISTRAL_API_KEY not found in environment variables.")
            return "Error: MISTRAL_API_KEY not set."
        
        model = "mistral-large-latest"
        client = Mistral(api_key=api_key)
        
        logging.info("Calling Mistral LLM with messages: %s", prompt_messages)
        response = client.chat.complete(
            model=model,
            messages=prompt_messages,
            stream=False
        )
        return response.choices[0].message.content

    def get_response(self, query: str) -> str:
        logging.info("Retrieving context for query: %s", query)
        context = self.retrieve_context(query)
        logging.info("Context retrieved. Querying Mistral LLM...")
        response = self.call_mistral(context, query)
        return response

if __name__ == "__main__":
    # Path to the Excel file produced by linkedin_scraper.py
    excel_file_path = "linkedin_details.xlsx"  # Adjust path if necessary
    agent = RAGAgent(excel_file=excel_file_path)
    
    # Example query to test the agent
    query = "What skills do the Python Developers have that match the job description?"
    final_response = agent.get_response(query)
    print("Final Response:\n", final_response)
