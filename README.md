# Secure AI Student Assistant

A (more) secure AI-powered student assistant application built with FastAPI and Google Gemini. This project was originally designed with intentional vulnerabilities for training purposes and has since been refactored to incorporate multiple layers of security.

## Security Enhancements

The application has been significantly hardened from its original insecure state. The following is a detailed breakdown of the security measures that have been implemented to protect against common vulnerabilities, particularly those relevant to Large Language Model (LLM) applications.

### 1. Hardened System Prompt (Prompt Injection Mitigation)

**The Problem:** The original system prompt was too open-ended, making it susceptible to "prompt injection." A malicious user could craft an input to override the assistant's original instructions, potentially causing it to ignore its rules, reveal sensitive information, or perform unintended actions.

**The Solution:** The system prompt in `main.py` has been rewritten to be extremely strict and specific.
- It clearly defines the assistant's **only** function: answering questions about student schedules based on provided data.
- It includes a set of **Strict Rules** that explicitly forbid revealing grades, generating code or HTML, or answering out-of-scope questions.
- It instructs the model to refuse any request that violates these rules.

This creates a strong "guardrail" that makes it much more difficult for a user to manipulate the LLM's behavior.

### 2. Sensitive Data Sanitization

**The Problem:** The original application loaded the entire `database.py` file—including sensitive student grades—directly into the LLM's context. This is a major security risk, as a successful prompt injection attack could easily lead to the exposure of this confidential data.

**The Solution:** A data sanitization layer was introduced in `main.py`.
- The `get_formatted_student_data()` function now acts as a gatekeeper. It processes the student data and **only** extracts the non-sensitive information (student names and their enrolled classes).
- This sanitized, user-friendly text is then passed to the LLM. The model **never has access** to the grades or the underlying database structure, completely eliminating the risk of that data being leaked in a response.

### 3. Secure Frontend Rendering (DOM XSS Prevention)

**The Problem:** The frontend JavaScript file (`static/script.js`) used the `innerHTML` property to display the assistant's response in the chat window. If the model's response contained any HTML (e.g., an image tag with an `onerror` alert), the browser would execute it, leading to a DOM-based Cross-Site Scripting (XSS) vulnerability.

**The Solution:** The vulnerable code was fixed by replacing `innerHTML` with `textContent`.
- `messageElement.textContent = message;`
- `textContent` safely renders all input as plain text. It does not parse HTML, so any malicious scripts or tags sent by the model are displayed as harmless text instead of being executed by the browser. This is the standard, secure way to handle dynamic text in JavaScript.

### 4. Backend Output Validation and Sanitization

To add multiple layers of defense, the backend also validates and sanitizes the model's output before it's even sent to the frontend.

**a) LLM-Based Safety Check:**
- A unique function, `is_response_safe()`, was created. This function takes the initial response from the Gemini model and feeds it back into the model with a new, simple prompt: "Does this text contain harmful content? Answer yes or no."
- If the model flags its own output as potentially unsafe, the application discards the response and sends a generic, safe message to the user. This acts as a self-correction and validation layer.

**b) HTML Escaping:**
- As a final line of defense, the application uses `html.escape(response.text)` on the model's output. This function converts characters like `<` and `>` into their HTML-safe equivalents (`&lt;` and `&gt;`).
- Even if a malicious response got past the other defenses and the frontend was vulnerable, this would prevent the browser from interpreting it as executable HTML.

### 5. Robust Input Validation

**The Problem:** The application did not validate the user's input on the backend. A malicious user could send extremely long messages to try and cause a denial-of-service (DoS) attack, or send other malformed data.

**The Solution:** The application now uses Pydantic's modern validation features.
- The `ChatRequest` model uses `Annotated[str, Field(strip_whitespace=True, min_length=1, max_length=500)]`.
- This ensures that any message received at the `/api/chat` endpoint is automatically validated to be between 1 and 500 characters, with leading/trailing whitespace removed. FastAPI will automatically reject any invalid requests.

### 6. Dependency and Environment Security

**The Problem:** The project's `requirements.txt` file did not specify package versions, and the `.env` file containing the API key could have been accidentally committed to version control.

**The Solution:**
- The `.gitignore` file was verified to correctly exclude the `.env` file, preventing the accidental exposure of the `GEMINI_API_KEY`.
- The `requirements.txt` file was updated to pin dependencies to their latest secure versions (e.g., `fastapi>=0.118.0`). This ensures the project uses up-to-date libraries with known security vulnerabilities patched.
