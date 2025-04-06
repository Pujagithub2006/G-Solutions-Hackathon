from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import google.generativeai as genai # importing generativeai module from google library and setting alias as genai
import requests
import sqlite3
import os
from dotenv import load_dotenv
import unicodedata  
from flask_cors import CORS
from datetime import timedelta
from sheet_logger import log_to_sheet # Importing the log_to_sheet function from sheet_logger.py

# for twilio
from twilio.rest import Client

load_dotenv(".env") # loading the environment variables from .env file

account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_NUMBER')
emergency_number = os.getenv('EMERGENCY_NUMBER')
# HERE API credentials
HERE_API_KEY = os.getenv("SERP_API_KEY")

DEFAULT_CITY = "Pune"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # loading the gemini api key from the .env file


genai.configure(api_key=GOOGLE_API_KEY) # setting the gemini api key to the api_key attribute

# for twilio
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

# for chatbot
def get_ai_response(prompt): 
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    
    try:
        return response.text.strip()  # Preferred method if works
    except AttributeError:
        try:
            return response.parts[0].text.strip()  # Gemini 1.5 often uses this
        except Exception as e:
            print(f"Gemini response error: {e}")
            return "Sorry, I couldn't generate a response."


# Initialize Flask app
app = Flask(__name__)

CORS(app)

app.secret_key = os.getenv("SECRET_KEY")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    conversations = db.relationship('Conversation', back_populates = 'user', lazy = 'dynamic')

    def __repr__(self):
        return f'<User {self.username}>'
    
# Define the Conversation model
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    user_message = db.Column(db.String(1000), nullable = False)
    chat_response = db.Column(db.String(1000), nullable = False)
    timestamp = db.Column(db.DateTime, default = db.func.current_timestamp())
    user = db.relationship('User', back_populates = 'conversations')

# Define the Appointment model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
    hospital_name = db.Column(db.String(200), nullable = False)
    doctor_name = db.Column(db.String(200), nullable = False)
    final_condition = db.Column(db.String(50), nullable = False)
    appointment_time = db.Column(db.String(50), nullable = False)
    time_stamp = db.Column(db.DateTime(), default = db.func.now(), nullable = False)

    def __repr__(self):
        return f"<Appointment with {self.doctor_name} at {self.hospital_name} at {self.appointment_time}>"


# Function to add predefined users
def add_predefined_users():
    predefined_users = [
        {"username": "Puja", "password": "Puja@123"},
        {"username": "Shreya", "password": "Shreya@987"}
    ]

    for user_data in predefined_users:
        existing_user = User.query.filter_by(username=user_data["username"]).first()
        if not existing_user:
            hashed_password = generate_password_hash(user_data["password"])
            new_user = User(username=user_data["username"], password=hashed_password)
            db.session.add(new_user)
    
    db.session.commit()

# Create the database and tables
with app.app_context():
    db.create_all()
    add_predefined_users()  # Call the function to ensure users exist
    users = User.query.all()
    # print(users)

    conversations = Conversation.query.all()
    # print(conversations)


def extract_condition(user_id):
    past_conversations = Conversation.query.filter_by(user_id = user_id).all()
    conversation_history = ""
    for conv in past_conversations:
        conversation_history += f"User: {conv.user_message}\n Buddy: {conv.chat_response}\n"
    
    condition_prompt = f"From the following conversation, identify any medical condition or health issue the user has mentioned. Only return the condition name without extra text. If no condition is found, return 'none'.\n\n{conversation_history}"
    condition_response = get_ai_response(condition_prompt).strip().lower()

    print(f"Extracted condition: {condition_response}")  # Debugging print

    return condition_response if condition_response != "none" else "general checkup"



def extract_location_nearbyHospitals(condition, latitude, longitude):
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        (
          node["amenity"="hospital"](around:5000,{latitude},{longitude});
          way["amenity"="hospital"](around:5000,{latitude},{longitude});
          relation["amenity"="hospital"](around:5000,{latitude},{longitude});
        );
        out center tags;
        """
        response = requests.post(overpass_url, data=overpass_query)
        data = response.json()

        hospitals = []
        for element in data["elements"]:
            name = element["tags"].get("name", "Unknown Hospital")
            address_parts = [
                element["tags"].get("addr:street", ""),
                element["tags"].get("addr:city", ""),
                element["tags"].get("addr:postcode", "")
            ]
            address = ", ".join([part for part in address_parts if part])
            contact = element["tags"].get("contact:phone", "Not available")
            website = element["tags"].get("contact:website", "Not available")

            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")
            maps_link = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}" if lat and lon else "Not available"

            hospitals.append({
                "name": name,
                "speciality": condition,
                "address": address or "Not available",
                "phone": contact,
                "rating": "Not available",
                "link": website if website != "Not available" else maps_link
            })

        return hospitals

    except Exception as e:
        print(f"Overpass API error: {e}")
        return []

with app.app_context():
    db.create_all() # create all the tables
    add_predefined_users() # call the function to ensure users exist



# Routes
 # for twilio
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

 # for chatbot
@app.route('/') # route to intro page
def index():
    return render_template('index.html')

@app.route("/home")
def home():
    return render_template("home.html") # render the home page (automatically looks for home.html in templates folder)

@app.route("/hospital")
def hospital():
    return render_template("hospital.html") # render the hospital page (automatically looks for hospital.html in templates folder)

@app.route('/login', methods=['GET', 'POST']) # route to login after submitting the login form and render the login form
def login():
    if request.method == 'POST':
        
        username = request.form.get("username")
        password = request.form.get("password")

        return redirect(url_for('http://127.0.0.1:5000/home')) # redirect to home page after login

        # Query the database for the user
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            return jsonify({"success": True, "message": f"Welcome {username}! "})
        else:
            return jsonify({"success": False})        
        
    
    return render_template('login.html') # if GET request then, render the login page

@app.route('/chat_ui')
def chat_ui():
    return render_template('chatbot.html')


def normalize(text):
    return unicodedata.normalize('NFKD, text').casefold()
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    username = data.get("username", "Anonymous")
    location = data.get("location", {})
    latitude = location.get("lat", 18.45724228948669)
    longitude = location.get("lon", 73.88036779027553)

    city = DEFAULT_CITY


    session.setdefault("history", [])
    session.setdefault("nearby_hospitals", [])


    # Booking logic — Problem 3 fix
    if user_message.lower().startswith("book appointment with"):
        hospital_name = user_message[len("book appointment with"):].strip()
        for hospital in session["nearby_hospitals"]:
            if hospital_name.lower() in hospital["name"].lower():
                conn = sqlite3.connect("chat_history.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO appointments (username, hospital_name, location, timestamp) VALUES (?, ?, ?, ?)",
                    (username, hospital["name"], hospital["location"], str(datetime.now()))
                )
                conn.commit()
                conn.close()
                response_text = f"✅ Appointment booked with {hospital['name']} at {hospital['location']}."
                session["history"].append({"user": user_message, "bot": response_text})
                log_to_sheet(user_message, response_text) 
                return jsonify({"response": response_text})

        response_text = "❌ Hospital not found. Please check the name and try again."
        session["history"].append({"user": user_message, "bot": response_text})
        log_to_sheet(user_message, response_text) 
        return jsonify({"response": response_text})

    # Hospital search logic — Problem 2 fix
    if "find" in user_message.lower() and ("hospital" in user_message.lower() or "doctor" in user_message.lower()):
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            osm_data = res.json()
            city = osm_data.get("address", {}).get("city", "Pune")

        except Exception as e:
            city = DEFAULT_CITY

        hospitals = extract_location_nearbyHospitals(city, latitude, longitude)
        session["nearby_hospitals"] = hospitals

        if hospitals:
            hospital_list = "\n".join([
                f"🏥 {hospital.get('name', 'City Hospital')} ({hospital.get('type', 'General')}) - {hospital.get('location', 'NA')}"
                for hospital in hospitals[:10] # Limit to 10 hospitals
            ])
            response_text = (
                f"Here are 10 hospitals near you:\n\n{hospital_list}\n\n"
                 " To book an appointment, type: `Book appointment with <hospital name>`"
            )
            response_text += '<br><br>🔗 <a href="http://127.0.0.1:5500/templates/hospital.html" target="_blank">Find these hospitals here</a>'
        else:
            response_text = "Sorry, I couldn't find any hospitals near you at the moment."

        session["history"].append({"user": user_message, "bot": response_text})
        log_to_sheet(user_message, response_text) 
        return jsonify({"response": response_text})

    # Default chatbot logic
    response_text = get_ai_response(user_message)
    session["history"].append({"user": user_message, "bot": response_text})

    log_to_sheet(user_message, response_text)  # Log the conversation to Google Sheets
    return jsonify({"response": response_text})


@app.route('/appointment', methods = ['POST'])
def make_appointment():
    data = request.json
    latitude = data.get("lat")
    longitude = data.get("lon")
    user_name = data.get("username")
    user_message = data.get("message")

    if not user_name or not user_message:
        return jsonify({"error": "Username and message are required"}), 400
    
    user = User.query.filter_by(username = user_name).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    condition = extract_condition(user.id) or "general checkup"
    # location = extract_location_nearbyHospitals(user.id)
    avail_hospitals = extract_location_nearbyHospitals(condition, latitude, longitude)


    chosen_hospital = None
    final_appointment = None

    extracted_name = user_message.lower().replace("book appointment with", "").replace("🏥", "").split("(")[0].strip()

    for hospital_var in avail_hospitals:
        cleaned_extracted_name = hospital_var["name"].replace("🏥", "").split('(')[0].strip().lower()

        if extracted_name == cleaned_extracted_name:
            chosen_hospital = hospital_var
            # available_slots_var = hospital_var.get("available_slots_var", [])
            # if available_slots_var:
            final_appointment = "10:00 AM Tomorrow" # available_slots_var[0]
            break

    if not chosen_hospital or not final_appointment:
        return jsonify({"error": "❌ Hospital not found. Please check the name and try again"}), 400
    
    # Booking of the new appointment and storing it in the database
    new_appointment = Appointment(
        user_id = user.id,
        hospital_name = chosen_hospital,
        doctor_name = "None currently",
        final_condition = condition,
        appointment_time = final_appointment,
    )

    db.session.add(new_appointment)
    db.session.commit() 

    return jsonify({"message": f"Appointment booked with {chosen_hospital} at {final_appointment}"}), 200

if __name__ == '__main__': # entry point check
    print("Server is running on port 5000")
    app.run(debug= os.getenv("FLASK_DEBUG", "False").lower() == "true")


