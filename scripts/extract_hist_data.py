import os
import json
import time
import requests
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

"""This script extracts historical weather data via API and saves the data as a JSON file in the raw data directory."""

# --- configs ---
load_dotenv()

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

API_URL = os.getenv("WEATHER_API_URL")

CURRENT_DIR = Path.cwd()
RAW_DIR = os.getenv("RAW_DIR", 'data/raw/')
INPUT_DIR = os.getenv("INPUT_DIR", 'data/input/')

OUTPUT_PATH = CURRENT_DIR / RAW_DIR.lstrip("\\/")
INPUT_PATH = CURRENT_DIR / INPUT_DIR.lstrip("\\/")

# Ensure directories exist
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
INPUT_PATH.mkdir(parents=True, exist_ok=True)

DAILY_PARAMS = [
    "showers_sum", "sunset", "sunrise", "rain_sum", "snowfall_sum", "precipitation_sum", "wind_direction_10m_dominant", "wind_speed_10m_max", "weather_code", "temperature_2m_max"
],


def extract_historical_data(start_date, end_date, url, input_path, output_path):
    input_file = input_path / "city_hist_list.json"

    if not input_file.exists():
        logging.error(f"Input file not found at {input_file}")
        return

    with open(input_file, "r") as f:
            city_data = json.load(f)

    logging.info(f"City data loaded successfully from {input_file}")

    city_weather_dict = {}

    for city_dict in city_data:
        city_name = city_dict["city"]
        country = city_dict["country"]
        latitude = city_dict["latitude"]
        longitude = city_dict["longitude"]
        timezone = city_dict["timezone"]

        logging.info(f"Processing weather data for {city_name} for date range : {start_date} - {end_date}")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,                    
            "daily": DAILY_PARAMS,
            "start_date": start_date,
            "end_date": end_date,
        }

        try:
            logging.info(f"Fetching data for {city_name} with params: {params}")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                logging.error(f"Failed to fetch data for {city_name}: HTTP {response.status_code}")
            
            data = response.json()
            city_weather_dict[city_name] = data
            city_weather_dict[city_name]["country"] = country
            logging.info(f"Data for {city_name} fetched successfully.")
            time.sleep(1)

        except requests.RequestException as e:
            logging.error(f"Error fetching data for {city_name}: {e}")
            continue
        except:
            logging.warning(f"No data received for {city_name}.")

    if city_weather_dict:
        # Ensure the output directory exists
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_file_path = output_path / f"weather_historical_{timestamp}.json"
            
        with open(dest_file_path, "w") as f:
            json.dump(city_weather_dict, f, indent=4)

        logging.info(f"Successfully saved data to {dest_file_path}")

    else:
        logging.warning("No data was collected. Skipping file creation.")

def collect_hist_main(start_date, end_date):
    """Main extraction function."""
    try:
        logging.info(f"Parameters:- {start_date}, {end_date}, {API_URL}, {INPUT_PATH}, {OUTPUT_PATH}")
        extract_historical_data(start_date, end_date, API_URL, INPUT_PATH, OUTPUT_PATH)
    except Exception as e:
        logging.error(f"An error occurred: {e}")

