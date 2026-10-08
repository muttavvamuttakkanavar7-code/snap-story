import re
import smtplib
import time
from email.mime.text import MIMEText

import streamlit as st

from prompts import build_chat_prompt

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - handled gracefully in the app UI.
    genai = None
    types = None


def validate_email(email: str) -> bool:
    """Return True when the email appears valid."""
    if not email:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.fullmatch(pattern, email.strip()))


def format_gemini_error(exc: Exception) -> str:
    """Return a useful provider error without exposing the configured API key."""
    message = str(exc)
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if api_key:
            message = message.replace(api_key, "[redacted]")
    except Exception:
        pass

    return f"{type(exc).__name__}: {message or 'No additional details were provided.'}"


def initialize_gemini():
    """Return the Gemini client and configured model, or a friendly error message."""
    if genai is None or types is None:
        return None, None, "Gemini SDK is missing. Please install the project requirements first."

    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        model_name = st.secrets.get("GEMINI_MODEL", "gemini-3.8-flash")
        if not api_key:
            return None, None, "Gemini API key is not configured.\nPlease add GEMINI_API_KEY to Streamlit secrets."

        client = genai.Client(api_key=api_key)
        return client, model_name, None
    except Exception as exc:  # pragma: no cover - runtime API error.
        return None, None, f"Gemini could not be initialized: {format_gemini_error(exc)}"


def generate_content_with_retry(client, model_name, contents):
    """Retry transient Gemini capacity and rate-limit errors a few times."""
    retryable_errors = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "INTERNAL",
    )
    for attempt in range(3):
        try:
            return client.models.generate_content(model=model_name, contents=contents)
        except Exception as exc:
            if attempt == 2 or not any(code in str(exc).upper() for code in retryable_errors):
                raise
            time.sleep(attempt + 1)


def analyze_image(image_file):
    """Ask Gemini to explain the uploaded educational image."""
    if image_file is None:
        return "Please upload an image or take a photo first."

    client, model_name, error = initialize_gemini()
    if error:
        return error

    prompt = build_chat_prompt(
        conversation_history=[],
        image_context="",
        user_question=(
            "Analyze this image and explain the academic content in a student-friendly way. "
            "If the image is unreadable or incomplete, say what cannot be read instead of inventing facts."
        ),
    )

    try:
        image_bytes = image_file.getvalue()
        mime_type = image_file.type or "image/png"
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = generate_content_with_retry(
            client,
            model_name,
            [prompt, image_part],
        )

        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                content = candidate.content
                if hasattr(content, "parts") and content.parts:
                    text = "".join(getattr(part, "text", "") for part in content.parts)

        if not text:
            return "Sorry, I couldn't analyze this image.\nPlease try again with a clearer image."

        return text.strip()
    except Exception as exc:
        if "503" in str(exc) or "UNAVAILABLE" in str(exc).upper():
            return (
                "Gemini is temporarily busy and could not analyze the image after "
                "several attempts. Please wait a little and select **Retry image analysis**."
            )
        return (
            "Sorry, I couldn't analyze this image. Please check the Gemini error details "
            "below and try again.\n\n"
            f"Gemini error: {format_gemini_error(exc)}"
        )


def generate_chat_response(message_history, analysis_text):
    """Use the current explanation and saved chat history to answer follow-up questions."""
    client, model_name, error = initialize_gemini()
    if error:
        return error

    if not message_history:
        return "Please ask a question about the image."

    prompt = build_chat_prompt(
        conversation_history=message_history,
        image_context=analysis_text,
        user_question="",
    )

    try:
        response = generate_content_with_retry(client, model_name, prompt)
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                content = candidate.content
                if hasattr(content, "parts") and content.parts:
                    text = "".join(getattr(part, "text", "") for part in content.parts)

        if not text:
            return "I couldn't answer that question right now. Please try again."

        return text.strip()
    except Exception as exc:
        return (
            "I couldn't answer that question right now. Please check the Gemini error "
            f"details below.\n\nGemini error: {format_gemini_error(exc)}"
        )


def send_email(to_address, subject, body):
    """Send a plain-text email using Gmail SMTP with an app password."""
    try:
        gmail_address = st.secrets["GMAIL_ADDRESS"]
        gmail_app_password = st.secrets["GMAIL_APP_PASSWORD"]

        message = MIMEText(body, "plain", "utf-8")
        message["From"] = gmail_address
        message["To"] = to_address
        message["Subject"] = subject

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.send_message(message)
        return True
    except Exception:
        return False


def reset_session():
    """Clear session state to return to the onboarding flow."""
    keys = [
        "email",
        "messages",
        "image",
        "analysis",
        "last_explanation",
        "last_image_hash",
        "email_saved",
        "analysis_failed",
    ]
    for key in keys:
        st.session_state.pop(key, None)


def initialize_session_state():
    if "email" not in st.session_state:
        st.session_state.email = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "image" not in st.session_state:
        st.session_state.image = None
    if "analysis" not in st.session_state:
        st.session_state.analysis = ""
    if "last_explanation" not in st.session_state:
        st.session_state.last_explanation = ""
    if "last_image_hash" not in st.session_state:
        st.session_state.last_image_hash = None
    if "analysis_failed" not in st.session_state:
        st.session_state.analysis_failed = False
    if "email_saved" not in st.session_state:
        st.session_state.email_saved = False


def main():
    st.set_page_config(page_title="Snap & Study", page_icon="📚", layout="wide")
    initialize_session_state()

    st.sidebar.markdown("## 📚 Snap & Study")
    st.sidebar.markdown("**Your AI-powered study assistant**")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About Snap & Study")
    st.sidebar.write("Upload a question, note, diagram, or textbook image and get a clear explanation in student-friendly language.")
    st.sidebar.markdown("### How it works")
    st.sidebar.write("1. Enter your email\n2. Upload or capture an image\n3. Gemini explains the content\n4. Ask follow-up questions\n5. Email the explanation")
    st.sidebar.markdown("### Email destination")
    if st.session_state.email:
        st.sidebar.success(st.session_state.email)
    else:
        st.sidebar.write("No email saved yet.")

    if st.sidebar.button("Reset Session", use_container_width=True):
        reset_session()
        st.rerun()

    st.title("📚 Snap & Study")
    st.caption("Learn from any question, page, note, or diagram.")
    st.markdown("---")

    if not st.session_state.email:
        st.markdown("### Welcome to Snap & Study 📚")
        st.write("Enter your email address to receive AI explanations outside the app.")
        email_input = st.text_input(
            "Where should we send your explanation?",
            placeholder="student@example.com",
            key="email_input",
        )

        if email_input:
            if validate_email(email_input):
                st.session_state.email = email_input.strip()
                st.session_state.email_saved = True
                st.rerun()
            else:
                st.error("Please enter a valid email address.")
        return

    st.markdown("### 📧 Step 1 — Student Email")
    st.info(f"Current email: {st.session_state.email}")

    st.markdown("### 📸 Step 2 — Add Study Material")
    uploaded_image = st.file_uploader(
        "📤 Upload an image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Upload an image of a question, notes, diagram, or textbook page.",
    )
    camera_image = st.camera_input("📷 Take a photo")

    chosen_image = uploaded_image if uploaded_image is not None else camera_image

    if chosen_image is not None:
        st.session_state.image = chosen_image
        st.image(chosen_image, caption="Selected study material", use_container_width=True)

        image_hash = hash(chosen_image.getvalue())
        if st.session_state.get("last_image_hash") != image_hash:
            st.session_state.last_image_hash = image_hash
            with st.spinner("Analyzing your image with Gemini..."):
                explanation = analyze_image(chosen_image)
            st.session_state.analysis = explanation
            st.session_state.last_explanation = explanation
            st.session_state.analysis_failed = (
                explanation.startswith("Sorry, I couldn't analyze")
                or explanation.startswith("Gemini is temporarily busy")
                or explanation.startswith("Gemini ")
            )

            st.session_state.messages = (
                [] if st.session_state.analysis_failed else [{"role": "assistant", "content": explanation}]
            )

    if st.session_state.get("analysis"):
        st.markdown("### 🤖 AI Explanation")
        if st.session_state.analysis_failed:
            st.warning(st.session_state.analysis)
        else:
            st.markdown(st.session_state.analysis)
        if st.session_state.analysis_failed and st.button("Retry image analysis"):
            st.session_state.last_image_hash = None
            st.rerun()

        if not st.session_state.analysis_failed:
            st.markdown("### 💬 Ask a Follow-up")
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            user_question = st.chat_input("Ask a follow-up question about the image")
            if user_question:
                st.session_state.messages.append({"role": "user", "content": user_question})
                with st.chat_message("user"):
                    st.markdown(user_question)

                with st.spinner("Thinking..."):
                    answer = generate_chat_response(st.session_state.messages, st.session_state.analysis)

                st.session_state.messages.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant"):
                    st.markdown(answer)

            st.markdown("---")
            st.markdown("### 📧 Save Your Explanation")
        if not st.session_state.analysis_failed and st.button(
            "📧 Send Explanation to Email",
            use_container_width=True,
        ):
            if not validate_email(st.session_state.email):
                st.error("Please enter a valid email address.")
            elif not st.session_state.analysis:
                st.error("The explanation was not generated yet.")
            else:
                subject = "📚 Snap & Study — Your Study Explanation"
                email_body = (
                    "Snap & Study\n"
                    "Your AI Study Explanation\n\n"
                    "--------------------------------\n\n"
                    "Question / Topic:\nStudy material\n\n"
                    "AI Explanation:\n"
                    f"{st.session_state.analysis}\n\n"
                    "--------------------------------\n\n"
                    "Generated by Snap & Study\n"
                )
                sent = send_email(st.session_state.email, subject, email_body)
                if sent:
                    st.success("✅ Explanation sent successfully!")
                else:
                    st.error("❌ We couldn't send the email.\nPlease check your email configuration and try again.")

    if not st.session_state.get("analysis") and not chosen_image:
        st.info("Please upload an image or take a photo first.")


if __name__ == "__main__":
    main()
