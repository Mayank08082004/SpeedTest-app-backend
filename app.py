from flask import Flask, request, jsonify
import subprocess
import platform
import speedtest

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

app = Flask(__name__)

@app.route("/ping", methods=["GET"])
def ping():
    target = request.args.get("target")
    if not target:
        return jsonify({"error": "Target parameter is required"}), 400
    command = f"ping -c 4 {target}" if platform.system() != "Windows" else f"ping -n 4 {target}"
    return jsonify({
        "result": run_command(command),
        "description": "Ping measures the round-trip time for messages sent from your device to a server. Lower values indicate a more responsive connection."
    })

@app.route("/nslookup", methods=["GET"])
def nslookup():
    target = request.args.get("target")
    if not target:
        return jsonify({"error": "Target parameter is required"}), 400
    return jsonify({
        "result": run_command(f"nslookup {target}"),
        "description": "Nslookup retrieves DNS information for a domain, showing the IP address and server details. Useful for troubleshooting domain resolution issues."
    })

@app.route("/ipconfig", methods=["GET"])
def ip_config():
    command = "ifconfig" if platform.system() != "Windows" else "ipconfig"
    return jsonify({
        "result": run_command(command),
        "description": "IP Config provides network configuration details such as IP address, subnet mask, and gateway information."
    })

@app.route("/netstat", methods=["GET"])
def netstat():
    return jsonify({
        "result": run_command("netstat -an"),
        "description": "Netstat displays active network connections, helping diagnose network issues and monitor traffic."
    })

@app.route("/traceroute", methods=["GET"])
def traceroute():
    target = request.args.get("target")
    if not target:
        return jsonify({"error": "Target parameter is required"}), 400
    command = f"traceroute {target}" if platform.system() != "Windows" else f"tracert {target}"
    return jsonify({
        "result": run_command(command),
        "description": "Traceroute maps the path data takes to reach a destination, showing each hop along the route and the delay at each step."
    })

@app.route("/speedtest", methods=["GET"])
def speed_test():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        upload_speed = st.upload() / 1_000_000  # Convert to Mbps
        return jsonify({
            "download_speed_mbps": round(download_speed, 2),
            "upload_speed_mbps": round(upload_speed, 2),
            "description": "Speed test measures download and upload speeds in Mbps. Higher values indicate faster internet performance."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

