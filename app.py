
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai # importing generativeai module from google library and setting alias as genai

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

# Function to add predefined users
def add_predefined_users():
    predefined_users = [
        {"username": "admin", "password": "admin123"},
        {"username": "testuser", "password": "test123"}
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

    if user_input:
        ai_response = get_ai_response(user_input) # get response based on the user input and store it in ai_response
        return jsonify({"response": ai_response}) # return response in json format
    else:
        return jsonify({"error": "Enter valid input"}), 400



if __name__ == '__main__':
    app.run(debug=True)
