import secrets
import string
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Allow requests from anywhere (Extension and Website)
CORS(app) 

# This dictionary is our temporary database. 
# It holds unique keys for every person using the app.
# Format -> {"16_digit_key": expiration_timestamp}
active_keys = {}

def cleanup_expired_keys():
    """Silently removes old keys so the server's memory doesn't fill up."""
    current_time = time.time()
    expired = [k for k, v in active_keys.items() if current_time > v]
    for k in expired:
        del active_keys[k]

# ==========================================
# 1. THE GENERATOR (Called by your Website)
# ==========================================
@app.route('/generate', methods=['POST', 'GET'])
def generate_key():
    cleanup_expired_keys()
    
    # 1. Generate a brand new 16-digit key for this specific user
    new_key = ''.join(secrets.choice(string.digits) for _ in range(16))
    
    # 2. Give them 5 minutes to copy/paste it before it expires
    expiration_time = time.time() + (5 * 60)
    
    # 3. Add it to the pool of valid keys
    active_keys[new_key] = expiration_time
    
    print(f"[GENERATED] New key created: {new_key}")
    print(f"[SYSTEM] Total active keys in pool: {len(active_keys)}")
    
    # 4. Send the key back to the website to display
    return jsonify({"key": new_key, "expires_in_minutes": 5}), 200

# ==========================================
# 2. THE VALIDATOR (Called by your Extension)
# ==========================================
@app.route('/validate', methods=['POST'])
def validate_key():
    cleanup_expired_keys()
    
    data = request.json
    if not data or 'key' not in data:
        return jsonify({"valid": False, "message": "No key provided"}), 400
        
    # Grab the key the user pasted into the extension
    client_key = data.get('key').strip()
    
    # Check if this specific key is in the valid pool
    if client_key in active_keys:
        
        # SUCCESS! Delete the key so they can't reuse it later.
        del active_keys[client_key]
        print(f"[VALIDATED] Key consumed and destroyed: {client_key}")
        
        # NOTE: If you wanted the server to give them a "freebie" code for their 
        # NEXT purchase, you could generate one here and include it in the JSON.
        # But that defeats the sobriety test, so we'll just send a success message!
        
        return jsonify({"valid": True, "message": "Cart unlocked!"}), 200
        
    else:
        # Key was either typed wrong, belongs to someone else, or expired
        print(f"[REJECTED] Invalid key attempted: {client_key}")
        return jsonify({"valid": False, "message": "Invalid or expired key."}), 401

if __name__ == '__main__':
    # Running on 0.0.0.0 makes it ready for online cloud hosting
    app.run(host='0.0.0.0', port=2600)