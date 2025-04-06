import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import base64
import json

# Setup Google Sheets API connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Try to get credentials from environment variable (Render)
creds_b64 = os.getenv("CREDS_JSON_B64")

if creds_b64:
    # Decode and use credentials from environment variable (for Render)
    creds_json = base64.b64decode(creds_b64).decode("utf-8")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    # Use local creds.json file (for local development)
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)

# Authorize the client
client = gspread.authorize(creds)

# Connect to your Google Sheet
sheet = client.open("MediBuddy Logs").worksheet("Logs")

def log_to_sheet(user_input, bot_response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, user_input, bot_response])
