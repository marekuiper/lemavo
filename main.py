import requests
import os
import json
from flask import Flask, request, jsonify

# Create a Flask app instance.
# The `app` object must be named this way for the default Cloud Run entrypoint to find it.
app = Flask(__name__)

# This is the entry point for your Cloud Run service.
@app.route('/', methods=['POST'])
def handle_dialogflow_webhook():
    """
    Handles POST requests from Dialogflow CX.
    """
    # Get the request payload from Dialogflow.
    req = request.get_json(silent=True)
    
    # Log the full request for debugging.
    print(json.dumps(req, indent=2))
    
    # Extract the location parameter from the session.
    try:
        location = req['sessionInfo']['parameters']['location']
    except (KeyError, IndexError):
        # Fallback to a different way of getting the parameter if the first one fails.
        try:
            location = req['pageInfo']['formInfo']['parameterInfo'][0]['value']
        except (KeyError, IndexError):
            # If all else fails, return an error message to Dialogflow.
            return jsonify({'fulfillmentResponse': {'messages': [{'text': {'text': ['I was unable to get the location parameter from your request.']}}]}})

    # Your OpenWeatherMap API key should be stored securely as an environment variable.
    # NEVER hardcode API keys in your code.
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        return jsonify({'fulfillmentResponse': {'messages': [{'text': {'text': ['The API key for the weather service is not configured.']}}]}})

    # The base URL for the OpenWeatherMap API.
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    # Parameters for the API request.
    params = {
        'q': location,
        'appid': api_key,
        'units': 'metric'  # Use 'imperial' for Fahrenheit
    }

    # Make the API call to OpenWeatherMap.
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({'fulfillmentResponse': {'messages': [{'text': {'text': [f'An error occurred while fetching the weather: {e}.']}}]}})

    # Extract the relevant weather information from the API response.
    if data.get('cod') == 200:
        weather = data['weather'][0]['description']
        temperature = data['main']['temp']
        
        # Format the response to be sent back to Dialogflow.
        fulfillment_text = f"The weather in {location} is {weather} with a temperature of {temperature}°C."
    else:
        # Handle cases where the city is not found.
        fulfillment_text = f"I could not find the weather for {location}. Please try again."

    # Return the final response in the format Dialogflow expects.
    return jsonify({
        "fulfillmentResponse": {
            "messages": [
                {
                    "text": {
                        "text": [fulfillment_text]
                    }
                }
            ]
        }
    })

# This block allows you to run the app locally for testing.
if __name__ == "__main__":
    # Use 0.0.0.0 to listen on all public IPs, which is standard for containers.
    # The port will be provided by Cloud Run, so this is for local testing only.
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))
