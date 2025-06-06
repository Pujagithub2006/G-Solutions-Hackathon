#Message sent 
from flask import Flask, request, jsonify
from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv(".env")  # Load environment variables from .env file
import requests

app = Flask(__name__)

# Twilio credentials
account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')

twilio_number = os.getenv('TWILIO_NUMBER')
emergency_number = os.getenv('EMERGENCY_NUMBER')

# HERE API credentials
HERE_API_KEY = os.getenv("SERP_API_KEY")

def get_location():
    """ Get current location coordinates (latitude & longitude) """
    # Using a public IP location service (for testing) - replace with real GPS data in production
    response = requests.get("https://ipinfo.io/json")
    data = response.json()
    
    if "loc" in data:
        lat, lon = data["loc"].split(",")
        return lat, lon
    return None, None

def reverse_geocode(lat, lon):
    """ Convert latitude & longitude to an address using HERE API """
    url = f"https://revgeocode.search.hereapi.com/v1/revgeocode?at={lat},{lon}&apiKey={HERE_API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["address"]["label"]  # Returns full address
    return "Unknown Location"

def send_sms(message):
    """ Send an SMS using Twilio """
    client = Client(account_sid, auth_token)
    
    sms = client.messages.create(
        body=message,
        from_=twilio_number,
        to=emergency_number
    )
    return sms.sid

@app.route("/send_help", methods=["GET"])
def send_help():
    lat, lon = get_location()
    
    if not lat or not lon:
        return jsonify({"error": "Unable to get location"}), 500

    address = reverse_geocode(lat, lon)
    location_link = f"https://www.google.com/maps?q={lat},{lon}"
    
    # Emergency message with location
    message = f" HELP! There is an emergency! \n📍 Location: {address}\n🔗 {location_link}"
    
    sms_id = send_sms(message)
    
    return jsonify({"message": "Emergency SMS Sent!", "sms_id": sms_id, "location": address})

if __name__ == "__main__":
    app.run(debug=True)





