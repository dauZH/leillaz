# CoursePilot project studio

## Run locally

1. Install Python 3.10 or newer.
2. Copy `.env.example` to `.env` and replace `your-key-here` with your API key. Alternatively, set the variables in PowerShell:

   ```powershell
   $env:OPENAI_API_KEY="your-key"
   $env:OPENAI_MODEL="gpt-4.1-mini"
   python app.py
   ```

3. Run `python app.py` and open <http://localhost:8000>.

Without `OPENAI_API_KEY`, the website runs but the AI sandbox shows that live AI is not configured. The key stays on the server and is never sent to the browser. Text and image requests are sent to the OpenAI Responses API. Do not submit private course material or personal data without permission.

The `.txt`, `.pdf`, and pasted text inputs work with CoursePilot. CitySignal and RescueChef AI accept images. Uploaded files are sent to the configured AI provider for processing.

## Evidence fields

CustDev and usability results are intentionally blank until the team conducts the survey and tests with real participants. Do not report the placeholders as findings.
