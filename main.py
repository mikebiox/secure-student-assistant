import os
import google.generativeai as genai
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr
from dotenv import load_dotenv
import database
import json
import html

load_dotenv()

DEFAULT_SYSTEM_PROMPT = """
You are a university student assistant with a very limited and specific scope.
Your ONLY function is to answer questions about student schedules and the classes they are enrolled in, based on the provided student data.

**Strict Rules:**
1.  You MUST ONLY use the provided student data to answer questions. Do not infer or guess any information.
2.  You MUST NEVER, under any circumstances, reveal a student's grade. Grades are confidential. Politely refuse any such request.
3.  You MUST refuse any request that is not directly about a student's name or their class list.
4.  You MUST NOT generate any HTML, code, or any form of markup. Your responses must be plain text only.
5.  If a user asks for something outside your scope (e.g., writing code, general knowledge questions, providing instructions), you MUST politely refuse and state that you can only provide information about student schedules.

The student data is provided in a simple text format, like this:
Student Name: [Student's Name]
Enrolled Classes: [Class 1], [Class 2]
"""

# Configure the generative AI model
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash')
except KeyError:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables.") from None

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    message: constr(strip_whitespace=True, min_length=1, max_length=500)

def get_formatted_student_data():
    """
    Retrieves student data and formats it into a user-friendly, secure string.
    """
    formatted_strings = []
    for student_info in database.STUDENT_DATA.values():
        name = student_info["name"]
        classes = ", ".join(student_info["classes"])
        formatted_strings.append(f"Student Name: {name}\nEnrolled Classes: {classes}")
    return "\n\n".join(formatted_strings)

async def is_response_safe(text: str) -> bool:
    """
    Uses the model to check if the response is safe.
    """
    prompt = f"""
    Does the following text contain any harmful, insecure, malicious, or inappropriate content?
    Answer with only 'yes' or 'no'.

    Text: "{text}"
    """
    response = await model.generate_content_async(prompt)
    return "no" in response.text.lower()

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Handles the chat request, sanitizes data, and interacts with the generative model.
    """
    try:
        formatted_student_data = get_formatted_student_data()
        
        prompt_parts = [
            DEFAULT_SYSTEM_PROMPT,
            "Here is the student data:",
            formatted_student_data,
            "\n---\n",
            "User's question:",
            request.message
        ]
        
        prompt = "\n".join(prompt_parts)
        
        # 1. Get the initial response from the model
        initial_response = await model.generate_content_async(prompt)
        response_text = initial_response.text

        # 2. Check if the response is safe
        if not await is_response_safe(response_text):
            return {"message": "I'm sorry, I cannot provide a response to that."}

        # 3. If safe, return the escaped response
        return {"message": html.escape(response_text)}

    except Exception as e:
        # Detailed error logging for debugging
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal error occurred.") from e
