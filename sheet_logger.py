import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup Google Sheets API connection
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Connect to your sheet
sheet = client.open("MediBuddy Logs").worksheet("Logs")

def log_to_sheet(user_input, bot_response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, user_input, bot_response])
