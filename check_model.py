import google.generativeai as genai # importing generativeai module from google library and setting alias as genai

GEMINI_API_KEY = "AIzaSyDIBk7dAKRtq5scQBdva6R6fZcTLBJukck"

genai.configure(api_key=GEMINI_API_KEY) # setting the gemini api key to the api_key attribute

models = genai.list_models()
for model in models:
    print(model.name)