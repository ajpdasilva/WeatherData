import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

weather_api_url = os.getenv("WEATHER_API_URL")
weather_lat = os.getenv("WEATHER_LAT")
weather_lon = os.getenv("WEATHER_LON")
weather_timezone = os.getenv("WEATHER_TIMEZONE")

current_dir = Path.cwd()
raw_path = os.getenv("RAW_DIR", '/data/raw/')
file_path = current_dir / raw_path.lstrip("\\/")

def extract_weather(url, latitude, longitude, timezone, file_path) -> str:
    today = date.today().isoformat()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["sunrise", "sunset", "weather_code"],
        "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "rain", "showers", "snowfall", "weather_code", "cloud_cover", "wind_speed_10m", "wind_direction_10m"],
        "timezone": timezone,
        "start_date": "2026-04-01",
        "end_date":"2026-04-07",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    print(data)

    # Flatten everything into one row
    df = pd.json_normalize(data)

    output_path = file_path / f"weather_raw_{timestamp}.csv"
    df.to_csv(output_path, encoding='utf‑8‑sig', index=False)

    return output_path


if __name__ == "__main__":
    try:
        file_path = extract_weather(weather_api_url, weather_lat, weather_lon, weather_timezone, file_path)
        print(f"Weather data extracted and saved to: {file_path}")
    except Exception as e:
        print(f"An error occurred during extraction: {e}")
    