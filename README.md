# Snap & Study

Snap & Study is a Streamlit study assistant. Upload or capture a question, notes, or a diagram to get a student-friendly Gemini explanation, ask follow-up questions, and email the explanation.

## Features
- AI image understanding
- Gemini Vision analysis
- Student-friendly explanations
- Follow-up AI chat
- Email delivery
- Camera input
- Image upload

## Tech Stack
- Python 3.11+
- Streamlit
- Google Gemini API (`google-genai`)
- Gmail SMTP

## Installation
```bash
git clone <your-public-repository-url>
cd snap-study
python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the app:
```bash
streamlit run app.py
```

## Secrets Setup
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace the placeholders with your credentials:

Windows PowerShell:
```powershell
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

The template looks like this:
```toml
GEMINI_API_KEY = "paste_your_gemini_api_key_here"
GEMINI_MODEL = "gemini-3.8-flash"

GMAIL_ADDRESS = "your_sender_gmail@gmail.com"
GMAIL_APP_PASSWORD = "paste_your_google_app_password_here"
```

Important:
- Never hard-code secrets in `app.py`, `prompts.py`, or `README.md`.
- Never commit `.streamlit/secrets.toml`; `.gitignore` excludes it. Commit only `.streamlit/secrets.toml.example`.
- Never use your real Gmail password. Use a Google App Password instead.
- Use a Gemini model that is available for your API key/account; the model name is configurable in secrets.

## Gmail App Password
To send mail through Gmail SMTP, the sender account must have:
1. 2-Step Verification enabled
2. A Google App Password generated
3. The App Password saved in `.streamlit/secrets.toml`

Do not publish or share the App Password.

## Deploy on Streamlit Community Cloud
1. Push this project to a public GitHub repository. Do not upload `.streamlit/secrets.toml`.
2. In Streamlit Community Cloud, create an app from that repository, select the branch, and set the app file to `app.py`.
3. In the app's **Settings → Secrets**, copy the TOML settings from `.streamlit/secrets.toml.example` and replace all placeholders with your real values.
4. Deploy the app, then open its public URL and test an image upload, a follow-up question, and email delivery.

The local `secrets.toml` file is not automatically sent to Streamlit Community Cloud. Configure the values in the Cloud app's Secrets settings.

## How to Test the Workflow
1. Open the app in the browser.
2. Enter a valid email address.
3. Upload or take a photo of a question, notes, or a diagram.
4. Wait for Gemini to explain the image.
5. Ask a follow-up question in the chat.
6. Click the email button to send the explanation.
7. Check that the email is delivered to the configured Gmail address.

## Project Structure
```text
snap-study/
├── app.py
├── prompts.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml.example
```
