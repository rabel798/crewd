"""
Grok API Integration for tech stack analysis
"""
import os
from openai import OpenAI

def analyze_tech_stack(description):
    """
    Analyze a project description with Grok API to suggest a tech stack
    
    Args:
        description (str): Project description text
        
    Returns:
        str: Comma-separated list of suggested technologies
    """
    try:
        # Create a custom OpenAI client with the X.AI endpoint
        client = OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ.get("XAI_API_KEY"))
        
        # Send request to Grok API
        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {
                    "role": "system",
                    "content": "You are a tech stack advisor. Based on the project description, recommend the most appropriate technologies (programming languages, frameworks, libraries, databases) needed for successful implementation. Return the result as a comma-separated list of technologies. Only include the most relevant items, maximum 10 items."
                },
                {
                    "role": "user",
                    "content": description
                }
            ],
            max_tokens=200
        )
        
        # Extract and return the result
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        # Log the error and re-raise it
        print(f"Error analyzing tech stack: {str(e)}")
        raise e