from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai # importing generativeai module from google library and setting alias as genai
import requests

GEMINI_API_KEY = "AIzaSyDIBk7dAKRtq5scQBdva6R6fZcTLBJukck"

genai.configure(api_key=GEMINI_API_KEY) # setting the gemini api key to the api_key attribute

def get_ai_response(prompt): # function to get AI response
    model= genai.GenerativeModel("models/gemini-1.5-flash-latest")

    response = model.generate_content(prompt)
    return response.text # returning the response or output




app = Flask(__name__)

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

User.conversations = db.relationship('Conversation', back_populates = 'user', lazy = True)

def extract_condition(user_id):
    past_conversations = Conversation.query.filter_by(user_id = user_id).all()
    conversation_history = ""
    for conv in past_conversations:
        conversation_history += f"User: {conv.user_message}\n Buddy: {conv.chat_response}\n"
    
    condition_prompt = f"From the following conversation, identify any medical condition or health issue the user has mentioned. Only return the condition name without extra text. If no condition is found, return 'none'.\n\n{conversation_history}"
    condition_response = get_ai_response(condition_prompt).strip().lower()

    return condition_response if condition_response != "none" else None

def extract_nearby_hospitals(condition, latitude, longitude):
    query = f"{condition} speciality doctor or hospital near me"  # add query

    # SERP API parameters
    params = {
        "engine" : "google",
        "q" : query, # condition extracted from above query
        "location" : f"{latitude}, {longitude}",
        "api_key" : "1de217e1ce919521fb24131160a5dc268d02e5d3e05a9f7a3ce9bca22bcb3ba5",

    }

    # Making a request to the SERP API to extract all the information
    response = requests.get("https://serpapi.com/search.json", params = params)
    results = response.json()

    # Extracting the relavant information
    hospitals = []
    for result in results.get("local_results", []):
        hospitals.append({
            "name" : result.get("title"),
            "speciality" : condition,
            "address" : result.get("address"),
            "phone" : result.get("phone"), 
            "rating": result.get("rating"),
            "link" : result.get("link"),
        })
    
    return hospitals


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
    print(users)

    conversations = Conversation.query.all()
    print(conversations)

# Routes
@app.route('/') # route to home page
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST']) # route to login after submitting the login form and render the login form
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get("username")
        password = data.get("password")

        # Query the database for the user
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False})
    
    return render_template('login.html') # if GET request then, render the login page
    
@app.route('/chat', methods=['POST']) # route to chat with the AI
def chat():
    data = request.json # get data from the request from form in json format
    user_input = data.get("message") # extract the message from the data 
    user_name = data.get("username") 

    if user_input and user_name:
        user = User.query.filter_by(username = user_name).first() # compares the extracted username stored in the user_name variable with the username key in database

        if user:
            if "find hospital" in user_input.lower() or "find doctor" in user_input.lower():
                condition = extract_condition(user.id)

                if condition:

                    latitude, longitude = 18.5204, 73.8567 # Pune's latitude and longitude
                    hospitals = extract_nearby_hospitals(condition, latitude, longitude)

                    if hospitals:
                        hospital_info = ""
                        for hospital in hospitals[:5]:
                            hospital_info += f"{hospital['name']} - Speciality: {hospital['speciality']} - {hospital['address']} - {hospital['phone']} - Rating: {hospital['rating']} - View on Maps: {hospital['link']}\n"
                        return jsonify({"hospital_info" : f"These are the best nearby hospitals nearby:\n{hospital_info}"})

                    else:
                        return jsonify({"response" : "No hospitals found"})
                
                else: 
                    return jsonify({"response" : "No condition found"})


            # Normal conversation
            else:
                past_conversations = Conversation.query.filter_by(user_id = user.id).all()

                conversation_history =""
                for conv in past_conversations:
                    conversation_history += f"User: {conv.user_message}\nBuddy: {conv.chat_response}\n"
                
                conversation_history += f"User: {user_input}\n"

                ai_response = get_ai_response(conversation_history) # get response based on the current user input and past conversation
                    
                new_conversation = Conversation( # created a new Conversation instance
                    user_id = user.id,
                    user_message = user_input,
                    chat_response = ai_response
                )

                db.session.add(new_conversation) # add the new_conversation to the staging area
                db.session.commit() # add the new_conversation permanently to the database

                return jsonify({"response": ai_response}) # return response in json format
        
        else:
            return jsonify({"error": "No user found"}), 404 

    else:
        return jsonify({"error": "Enter valid input"}), 400 
 

if __name__ == '__main__':
    app.run(debug=True)
