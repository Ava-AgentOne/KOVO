"""
Send the Human Sexuality HTML report to the owner's email.
"""
import sys
sys.path.insert(0, "/opt/kovo")

from src.tools.google_api import GoogleAPI

TO      = "Time@eim.ae"
SUBJECT = "📊 Human Sexuality — Comprehensive Report by Ava"

with open("/opt/kovo/data/documents/Human_Sexuality_Report_20260331.html", "r") as f:
    HTML_BODY = f.read()

api    = GoogleAPI()
result = api.send_email(to=TO, subject=SUBJECT, body=HTML_BODY, html=True)
print(f"✅ Report sent to {TO} | message_id: {result['message_id']}")
