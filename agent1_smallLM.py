
# --- Step 6: Use a Small Language Model for RAG Demonstration ---
def generate_response_with_rag(query, retrieved_documents):
    # Load a small language model (e.g., distilgpt2)
    model_name = "distilgpt2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    lm_model = AutoModelForCausalLM.from_pretrained(model_name)
    generator = pipeline("text-generation", model=lm_model, tokenizer=tokenizer)
    
    # Concatenate retrieved documents to form context
    context = " ".join(retrieved_documents)
    prompt = f"Context: {context}\nQuestion: {query}\nAnswer:"
    
    # Generate a response using the language model
    generated_output = generator(prompt, max_length=200, num_return_sequences=1)
    return generated_output[0]['generated_text']

# Extract retrieved documents from query result (adjust key if necessary)
retrieved_docs = query_result["documents"]
question = "Based on the profiles, what insights can be drawn about Python Developers in India?"
rag_response = generate_response_with_rag(question, retrieved_docs)
print("Generated RAG Response:\n", rag_response)