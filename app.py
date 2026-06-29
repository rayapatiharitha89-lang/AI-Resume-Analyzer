import os
import json
from flask import Flask, request, jsonify, render_template
from google import genai
import PyPDF2
import io

app = Flask(__name__)

# API Key from environment variable
import os
   GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file."""
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text.strip()

def analyze_resume(resume_text, job_description):
    """Send resume + JD to Gemini API and get structured analysis."""

    prompt = f"""You are an expert HR recruiter and career coach. Analyze the resume against the job description and return a structured JSON response.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY a valid JSON object (no markdown, no extra text, no backticks) with this exact structure:
{{
  "match_score": <integer 0-100>,
  "summary": "<2-3 sentence overall assessment>",
  "strengths": [
    {{"point": "<strength title>", "detail": "<explanation>"}}
  ],
  "gaps": [
    {{"point": "<gap title>", "detail": "<what is missing and why it matters>"}}
  ],
  "suggestions": [
    {{"point": "<suggestion title>", "detail": "<specific actionable advice>"}}
  ],
  "keywords_matched": ["<keyword1>", "<keyword2>"],
  "keywords_missing": ["<keyword1>", "<keyword2>"],
  "verdict": "<one of: Strong Match | Good Match | Partial Match | Weak Match>"
}}

Provide exactly 3-4 items in each of strengths, gaps, and suggestions arrays.
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    response_text = response.text.strip()

    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    response_text = response_text.strip()

    return json.loads(response_text)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        job_description = request.form.get("job_description", "").strip()
        if not job_description:
            return jsonify({"error": "Job description is required."}), 400

        resume_text = ""

        if "resume_pdf" in request.files and request.files["resume_pdf"].filename:
            pdf_file = request.files["resume_pdf"]
            resume_text = extract_text_from_pdf(pdf_file)
        elif request.form.get("resume_text", "").strip():
            resume_text = request.form.get("resume_text").strip()
        else:
            return jsonify({"error": "Please upload a PDF or paste your resume text."}), 400

        if len(resume_text) < 100:
            return jsonify({"error": "Resume text is too short. Please provide a complete resume."}), 400

        result = analyze_resume(resume_text, job_description)
        return jsonify(result)

    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
