import requests
import xml.etree.ElementTree as ET
import math
import datetime
import logging
import pytz
from typing import List, Dict
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

def fetch_iss_data(url: str) -> List[Dict]:
    response = requests.get(url)
    response.raise_for_status()
    tree = ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()
    data = []
    for state_vector in root.findall(".//stateVector"):
        epoch = state_vector.find("EPOCH").text
        x = float(state_vector.find("X").text)
        y = float(state_vector.find("Y").text)
        z = float(state_vector.find("Z").text)
        x_dot = float(state_vector.find("X_DOT").text)
        y_dot = float(state_vector.find("Y_DOT").text)
        z_dot = float(state_vector.find("Z_DOT").text)
        data.append({
            "epoch": epoch,
            "position": {"x": x, "y": y, "z": z},
            "velocity": {"x_dot": x_dot, "y_dot": y_dot, "z_dot": z_dot}
        })
    return data

def calculate_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    return math.sqrt(x_dot ** 2 + y_dot ** 2 + z_dot ** 2)

def find_closest_epoch(data: List[Dict]) -> Dict:
    now = datetime.datetime.now(pytz.UTC)
    closest = min(data, key=lambda x: abs(datetime.datetime.strptime(x["epoch"], "%Y-%jT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC) - now))
    return closest

def calculate_average_speed(data: List[Dict]) -> float:
    total_speed = sum(calculate_speed(d["velocity"]["x_dot"], d["velocity"]["y_dot"], d["velocity"]["z_dot"]) for d in data)
    return total_speed / len(data)

@app.route('/epochs', methods=['GET'])
def get_epochs():
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = fetch_iss_data(url)
    return jsonify([entry["epoch"] for entry in data])

@app.route('/epochs/<epoch>', methods=['GET'])
def get_epoch_data(epoch):
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = fetch_iss_data(url)
    result = next((entry for entry in data if entry["epoch"] == epoch), None)
    return jsonify(result) if result else ("Epoch not found", 404)

@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_epoch_speed(epoch):
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = fetch_iss_data(url)
    entry = next((entry for entry in data if entry["epoch"] == epoch), None)
    if entry:
        speed = calculate_speed(entry["velocity"]["x_dot"], entry["velocity"]["y_dot"], entry["velocity"]["z_dot"])
        return jsonify({"epoch": epoch, "speed_km_s": speed})
    return ("Epoch not found", 404)

@app.route('/now', methods=['GET'])
def get_closest_epoch_api():
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = fetch_iss_data(url)
    now = datetime.datetime.now(pytz.UTC)
    closest = min(data, key=lambda x: abs(datetime.datetime.strptime(x["epoch"], "%Y-%jT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC) - now))
    speed = calculate_speed(closest["velocity"]["x_dot"], closest["velocity"]["y_dot"], closest["velocity"]["z_dot"])
    return jsonify({"epoch": closest["epoch"], "position": closest["position"], "velocity": closest["velocity"], "speed_km_s": speed})

def main():
    url = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"
    data = fetch_iss_data(url)
    if not data:
        logging.error("No data available. Exiting.")
        return
    first_epoch = data[0]["epoch"]
    last_epoch = data[-1]["epoch"]
    logging.info(f"Data Range: {first_epoch} to {last_epoch}")
    closest_epoch = find_closest_epoch(data)
    logging.info(f"Closest Epoch to Now: {closest_epoch['epoch']}")
    logging.info(f"Position: {closest_epoch['position']}, Velocity: {closest_epoch['velocity']}")
    avg_speed = calculate_average_speed(data)
    logging.info(f"Average Speed: {avg_speed:.2f} km/s")
    instantaneous_speed = calculate_speed(closest_epoch["velocity"]["x_dot"], closest_epoch["velocity"]["y_dot"], closest_epoch["velocity"]["z_dot"])
    logging.info(f"Instantaneous Speed at Closest Epoch: {instantaneous_speed:.2f} km/s")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
