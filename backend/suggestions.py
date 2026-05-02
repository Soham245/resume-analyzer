from google import genai

def get_improvement_suggestions(resume_text, missing_skills, api_key):
    # NEW SYNTAX: Initialize the Client
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    CONTEXT:
    You are a professional Career Coach. I am providing a user's Current Resume and a list of Missing Skills identified from a Job Description.
    
    USER'S CURRENT RESUME:
    {resume_text[:4000]} 
    
    MISSING SKILLS FROM JD:
    {', '.join(missing_skills)}
    
    TASK:
    1. Analyze the 'Current Resume' to see if any existing experience can be "re-framed" to cover the 'Missing Skills'.
    2. Provide 3-4 highly specific, professional suggestions in Markdown format:
    
    ### 🚩 Critical Gaps
    * (Identify the most important skill the user lacks based on their current background)
    
    ### 💡 How to Re-frame Your Experience
    * (Look at their current projects and explain how to describe them using JD-relevant keywords)
    
    ### 🛠️ Upskilling Roadmap
    * (Suggest 1 specific certification or tool to learn that bridges the gap)
    """
    
    # NEW SYNTAX: Call generate_content on the client
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite-preview',
        contents=prompt
    )
    return response.text

def rewrite_resume_section(text, api_key):
    # NEW SYNTAX: Initialize the Client
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Rewrite the following resume section to be more impactful, data-driven, and professional. 
    Use strong action verbs (e.g., 'Spearheaded', 'Optimized', 'Architected').
    
    ORIGINAL TEXT:
    {text}
    
    REWRITTEN VERSION:
    """
    
    # NEW SYNTAX: Call generate_content on the client
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text