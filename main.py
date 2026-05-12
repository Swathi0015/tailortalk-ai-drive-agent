from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from groq import Groq

import os

# ---------------------------
# INIT
# ---------------------------

app = FastAPI()
load_dotenv(dotenv_path="backend/.env")

class Query(BaseModel):
    question: str

# ---------------------------
# GROQ SETUP
# ---------------------------

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("❌ GROQ_API_KEY missing in .env")

client = Groq(api_key=api_key)

# ---------------------------
# GOOGLE DRIVE SETUP
# ---------------------------

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

creds = service_account.Credentials.from_service_account_file(
    "backend/service_account.json",
    scopes=SCOPES
)

service = build("drive", "v3", credentials=creds)

# ---------------------------
# DRIVE SEARCH
# ---------------------------

def search_drive(q: str):
    results = service.files().list(
        q=q,
        pageSize=10,
        fields="files(id,name,mimeType,webViewLink)"
    ).execute()

    files = results.get("files", [])

    if not files:
        return "No files found."

    return [
        {
            "name": f["name"],
            "type": f["mimeType"],
            "link": f["webViewLink"]
        }
        for f in files
    ]

# ---------------------------
# GROQ → DRIVE QUERY GENERATOR (FIXED)
# ---------------------------

def generate_query(user_input: str):

    prompt = f"""
You are a Google Drive API query generator.

STRICT RULES:
- NO spaces around '='
- ALWAYS include: trashed=false
- ONLY return query string
- NO explanations

Examples:
mimeType='application/pdf' and trashed=false
mimeType contains 'image/' and trashed=false
name contains 'report' and trashed=false

User request:
{user_input}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return only valid Google Drive API queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        query = response.choices[0].message.content.strip()

        # Safety cleanup
        if not query or query.lower() in ["none", "null"]:
            return "trashed=false"

        query = query.replace(" = ", "=")
        query = query.replace("= ", "=")
        query = query.replace(" =", "=")

        if "trashed" not in query:
            query += " and trashed=false"

        return query

    except Exception as e:
        print("Groq error:", e)
        return "trashed=false"

# ---------------------------
# API ROUTES
# ---------------------------

@app.get("/")
def home():
    return {"message": "TailorTalk AI Drive Agent running 🚀"}

@app.post("/ask")
def ask(query: Query):

    try:
        drive_query = generate_query(query.question)
        results = search_drive(drive_query)

        return {
            "user_question": query.question,
            "generated_query": drive_query,
            "results": results
        }

    except Exception as e:
        return {"error": str(e)}