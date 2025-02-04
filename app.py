from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import shlex
import re
import speedtest
from functools import wraps
import time

app = Flask(__name__)
CORS(app)

# Security: List of allowed commands and their parameters
ALLOWED_COMMANDS = {
    'ping': {
        'base_cmd': 'ping',
        'params': ['-c', '4'],  # Limit to 4 packets
        'timeout': 10
    },
    'nslookup': {
        'base_cmd': 'nslookup',
        'params': [],
        'timeout': 5
    },
    'traceroute': {
        'base_cmd': 'traceroute',
        'params': ['-I','-m','15'],  # Limit to 15 hops
        'timeout': 15
    },
    'netstat': {
        'base_cmd': 'netstat',
        'params': ['-tuln'],
        'timeout': 5
    }
}

def validate_hostname(hostname):
    """Validate hostname/IP address"""
    if not hostname:
        return False
    # Basic pattern for hostname and IP validation
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-\._]{0,253}[a-zA-Z0-9]$'
    return bool(re.match(pattern, hostname))

def error_response(message, status_code=400):
    """Generate consistent error responses"""
    return jsonify({
        "success": False,
        "error": message if isinstance(message, list) else [message]
    }), status_code

def run_command(command_type, host=None):
    """Run system command with proper security measures"""
    if command_type not in ALLOWED_COMMANDS:
        return {"success": False, "error": ["Invalid command"]}

    cmd_config = ALLOWED_COMMANDS[command_type]
    command = [cmd_config['base_cmd']] + cmd_config['params']

    if host:
        if not validate_hostname(host):
            return {"success": False, "error": ["Invalid hostname"]}
        command.append(shlex.quote(host))

    try:
        # Use subprocess.run with proper security settings
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=cmd_config['timeout'],
            shell=False  # Security: Avoid shell injection
        )

        output_lines = result.stdout.strip().split('\n') if result.stdout else []
        error_lines = result.stderr.strip().split('\n') if result.stderr else []

        return {
            "success": result.returncode == 0,
            "output": output_lines,
            "error": error_lines
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": ["Command timed out"]}
    except Exception as e:
        return {"success": False, "error": [str(e)]}

def require_api_key(f):
    """Optional: Decorator for API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if app.config.get('API_KEY_REQUIRED', False) and (
            not api_key or api_key != app.config.get('API_KEY')):
            return error_response("Invalid API key", 401)
        return f(*args, **kwargs)
    return decorated_function

@app.route("/diagnose", methods=["GET"])
@require_api_key
def diagnose():
    host = request.args.get("host")
    if not host:
        return error_response("Host parameter is required")

    results = {
        "ping": run_command('ping', host),
        "nslookup": run_command('nslookup', host),
        "traceroute": run_command('traceroute', host)
    }
    return jsonify(results)

@app.route("/netstat", methods=["GET"])
@require_api_key
def netstat():
    result = run_command('netstat')
    return jsonify(result)

@app.route("/speedtest", methods=["GET"])
@require_api_key
def speed_test():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        # Create response dict
        result = {
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server": {
                "name": st.get_best_server()['sponsor'],
                "location": f"{st.get_best_server()['name']}, {st.get_best_server()['country']}"
            }
        }

        # Test download speed
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        result["download_speed"] = round(download_speed, 2)

        # Test upload speed
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        result["upload_speed"] = round(upload_speed, 2)

        # Test ping
        ping = st.results.ping
        result["ping"] = round(ping, 2)

        return jsonify(result)

    except Exception as e:
        return error_response(f"Speed test failed: {str(e)}")

@app.errorhandler(404)
def not_found(e):
    return error_response("Resource not found", 404)

@app.errorhandler(500)
def internal_error(e):
    return error_response("Internal server error", 500)

if __name__ == "__main__": # Change this to your secret key

    # Run the application
    app.run(debug=True, host='127.0.0.1', port=5173)
