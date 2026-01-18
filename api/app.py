from flask import Flask , request , jsonify, make_response
import requests
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*"}})

# reCAPTCHA v3 verification settings
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
RECAPTCHA_SCORE_THRESHOLD = 0.5  # Adjust threshold as needed (0.0 to 1.0)

def verify_recaptcha(token):
    """Verify reCAPTCHA v3 token with Google's API"""
    secret_key = os.environ.get('RECAPTCHA_SERVER_SIDE_KEY')
    
    if not secret_key:
        return False, "reCAPTCHA secret key not configured"
    
    if not token:
        return False, "reCAPTCHA token is missing"
    
    response = requests.post(
        RECAPTCHA_VERIFY_URL,
        data={
            'secret': secret_key,
            'response': token
        }
    )
    
    result = response.json()
    
    if not result.get('success'):
        error_codes = result.get('error-codes', [])
        return False, f"reCAPTCHA verification failed: {error_codes}"
    
    score = result.get('score', 0)
    if score < RECAPTCHA_SCORE_THRESHOLD:
        return False, f"reCAPTCHA score too low: {score}"
    
    return True, None

def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/',methods=['POST', 'OPTIONS'])
def send_mail():
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        return response
    
    data = request.json
    
    # Verify reCAPTCHA token
    recaptcha_token = data.get('recaptchaToken')
    is_valid, error_message = verify_recaptcha(recaptcha_token)
    
    if not is_valid:
        return jsonify({"success": False, "error": error_message}), 400
    
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization":f"Bearer {os.environ['RESEND_API_KEY']}",
            "content-type": "application/json"
        },
        json={
            "from":"onboarding@resend.dev",
            "to": [data["to"]],
            "subject":data["subject"],
            "html": f"<p> {data['message']} </p>"
        }
    )

    if response.status_code != 200:
        return jsonify({"success":False , "error": response.text()}),400
    
    return jsonify({"success":True})