import requests
import xml.etree.ElementTree as ET
import math
import datetime
import logging
import pytz
import redis
from typing import List, Dict
from flask import Flask, jsonify
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from pyproj import Transformer

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

r = redis.Redis(host='redis', port=6379, decode_responses=True)
NASA_ISS_URL = "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml"

def fetch_iss_data(url: str) -> List[Dict]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching ISS data: {e}")
        return []
    
    try:
        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()
    except ET.ParseError:
        logging.error("Failed to parse ISS data XML.")
        return []
    
    data = []
    for state_vector in root.findall(".//stateVector"):
        try:
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
        except (AttributeError, ValueError) as e:
            logging.warning(f"Skipping malformed state vector: {e}")

    return data

def load_data_to_redis():
    if not r.exists("iss_data"):
        data = fetch_iss_data(NASA_ISS_URL)
        if data:
            r.set("iss_data", str(data), ex=3600)

def fetch_iss_data_cached() -> List[Dict]:
    if r.exists("iss_data"):
        return eval(r.get("iss_data"))
    
    data = fetch_iss_data(NASA_ISS_URL)
    if data:
        r.set("iss_data", str(data), ex=3600)

    return data

def calculate_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    return math.sqrt(x_dot ** 2 + y_dot ** 2 + z_dot ** 2)

def find_closest_epoch(data: List[Dict]) -> Dict:
    now = datetime.datetime.now(pytz.UTC)
    closest = min(data, key=lambda x: abs(datetime.datetime.strptime(x["epoch"], "%Y-%jT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC) - now))
    return closest

@app.route('/epochs', methods=['GET'])
def get_epochs():
    data = fetch_iss_data_cached()
    return jsonify([entry["epoch"] for entry in data])

@app.route('/epochs/<epoch>', methods=['GET'])
def get_epoch_data(epoch):
    data = fetch_iss_data_cached()
    result = next((entry for entry in data if entry["epoch"] == epoch), None)
    return jsonify(result) if result else ("Epoch not found", 404)

@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_epoch_speed(epoch):
    data = fetch_iss_data_cached()
    entry = next((entry for entry in data if entry["epoch"] == epoch), None)
    if entry:
        speed = calculate_speed(entry["velocity"]["x_dot"], entry["velocity"]["y_dot"], entry["velocity"]["z_dot"])
        return jsonify({"epoch": epoch, "speed_km_s": speed})
    return ("Epoch not found", 404)
from pyproj import Transformer

@app.route('/epochs/<epoch>/location', methods=['GET'])
def get_epoch_location(epoch):
    data = fetch_iss_data_cached()
    entry = next((entry for entry in data if entry["epoch"] == epoch), None)

    if not entry:
        return jsonify({"error": "Epoch not found"}), 404

    x, y, z = entry["position"]["x"], entry["position"]["y"], entry["position"]["z"]
    transformer = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)
    longitude, latitude, altitude = transformer.transform(x, y, z)

    geolocator = Nominatim(user_agent="iss_tracker")

    try:
        location = geolocator.reverse((latitude, longitude), language="en")
        address = location.address if location else "Unknown"
    except:
        address = "Geolocation unavailable"

    return jsonify({
        "epoch": epoch,
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "geoposition": address
    })


@app.route('/now', methods=['GET'])
def get_closest_epoch_api():
    data = fetch_iss_data_cached()
    now = datetime.datetime.now(pytz.UTC)

    closest = min(data, key=lambda x: abs(datetime.datetime.strptime(x["epoch"], "%Y-%jT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC) - now))
    
    speed = calculate_speed(closest["velocity"]["x_dot"], closest["velocity"]["y_dot"], closest["velocity"]["z_dot"])
    
    x, y, z = closest["position"]["x"], closest["position"]["y"], closest["position"]["z"]
    
    latitude = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))
    longitude = math.degrees(math.atan2(y, x))
    altitude = math.sqrt(x**2 + y**2 + z**2) - 6371  

    geolocator = Nominatim(user_agent="iss_tracker")
    location = geolocator.reverse((latitude, longitude), language="en", exactly_one=True)

    return jsonify({
        "epoch": closest["epoch"],
        "latitude": latitude,
        "longitude": longitude,
        "altitude": altitude,
        "geoposition": location.address if location else "Unknown",
        "speed_km_s": speed
    })

if __name__ == "__main__":
    load_data_to_redis()
    app.run(host='0.0.0.0', port=5000, debug=True)

