import secrets
import string
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS is required so your Chrome Extension can talk to localhost
CORS(app) 

# Generate a 16-digit secure key
# If you want alphanumeric, change string.digits to string.ascii_letters + string.digits
VALID_KEY = ''.join(secrets.choice(string.digits) for _ in range(16))

print("="*40)
print(f" YOUR 16-DIGIT AUTH KEY IS: {VALID_KEY} ")
print("="*40)

@app.route('/validate', methods=['POST'])
def validate_key():
    data = request.json
    
    if not data or 'key' not in data:
        return jsonify({"valid": False, "message": "No key provided"}), 400
        
    client_key = data.get('key')
    
    if client_key == VALID_KEY:
        return jsonify({"valid": True, "message": "Authentication successful!"}), 200
    else:
        return jsonify({"valid": False, "message": "Invalid authentication key."}), 401

if __name__ == '__main__':
    # Run the local server on port 5000
    app.run(host='127.0.0.1', port=5000)