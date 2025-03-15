def get_system_prompt() -> str:
    """
    Returns a general system prompt for the Mistral LLM.
    This prompt instructs the assistant to act as a recruiting expert.
    """
    system_message = (
        "You are an expert recruiting assistant. You will be provided with candidate profile information, "
        "a job description, and a query. Your task is to intelligently answer the query by highlighting "
        "relevant skills, experience, and attributes that match the job description. Provide a clear, concise, and "
        "comprehensive response."
    )
    return system_message
