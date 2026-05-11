import os
import json
import shutil
import glob
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

"""This script collects the raw weather data JSON file(s), loads all the data into a dataframe for data cleaning/validation. 
Processed data is saved as CSV files and the original JSON files are moved to a backup directory."""

# --- configs ---
load_dotenv()

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

RAW_DIR = os.getenv("RAW_DIR", 'data/raw/')
BACKUP_DIR = os.getenv("BACK_DIR", 'data/raw/backup/')
PROCESSED_DIR = os.getenv("PROCESSED_DIR", 'data/processed/')

CURRENT_DIR = Path.cwd()
INPUT_PATH = CURRENT_DIR / RAW_DIR.lstrip("\\/")
BACKUP_PATH = CURRENT_DIR / BACKUP_DIR.lstrip("\\/")
OUTPUT_PATH = CURRENT_DIR / PROCESSED_DIR.lstrip("\\/")

# Ensure directories exist
BACKUP_PATH.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


def get_weather_data_files(file_path):
    """Check if the defined directories exist and retrieve JSON files."""
    if not file_path.exists():
        logging.error(f"Error: Input Path '{file_path}' does not exist.")
        raise FileNotFoundError(f"Error: Input Path '{file_path}' does not exist.")
    
    files = glob.glob(f"{file_path}/weather_*.json")
    logging.info(f"Files retrieved from '{file_path}': {files}")
            
    return files


def clean_weather_data(df):
    """Data clean up: removing unnecessary columns, formatting date/time fields and converting offset to hours."""
    df.drop(columns=['daily_time', 'current_interval'], inplace=True)

    df['utc_offset'] = df['utc_offset'] / 3600
    
    df['current_time'] = pd.to_datetime(df['current_time']).dt.strftime('%Y-%m-%d %H:%M')
    df['daily_sunrise'] = pd.to_datetime(df['daily_sunrise']).dt.strftime('%Y-%m-%d %H:%M')
    df['daily_sunset'] = pd.to_datetime(df['daily_sunset']).dt.strftime('%Y-%m-%d %H:%M')

    df['current_temperature_2m'] = df['current_temperature_2m'].fillna(0)
    df['current_precipitation'] = df['current_precipitation'].fillna(0)
    df['current_rain'] = df['current_rain'].fillna(0)
    df['current_showers'] = df['current_showers'].fillna(0)
    df['current_snowfall'] = df['current_snowfall'].fillna(0)
    df['current_weather_code'] = df['current_weather_code'].fillna(0)
    df['current_wind_speed_10m'] = df['current_wind_speed_10m'].fillna(0)
    df['current_wind_direction_10m'] = df['current_wind_direction_10m'].fillna(0)
 
    logging.info("Data cleanup completed.")

    return df


def process_weather_data(files, backup_path, output_path):
    """Collect and transform the data from files."""
    all_dfs = []

    for file in files:
        logging.info(f"Processing file: {file}")
        try:
            with open(file, "r") as f:
                data = json.load(f)
            
            flat_data = []
            
            for city, city_data in data.items():
                record = {
                    'city': city,
                    'country': city_data.get('country'),                        
                    'latitude': city_data.get('latitude'),
                    'longitude': city_data.get('longitude'),
                    'timezone': city_data.get('timezone'),
                    'utc_offset': city_data.get('utc_offset_seconds'),
                }

                # Flatten 'daily' nested dictionary
                daily = city_data.get('daily', {})
                for key, value in daily.items():
                    if isinstance(value, list) and len(value) > 0:
                        record[f'daily_{key}'] = value[0]

                # Flatten 'current' nested dictionary
                current = city_data.get('current', {})
                for key, value in current.items():
                    record[f'current_{key}'] = value
                    
                flat_data.append(record)
            
            df = pd.DataFrame(flat_data)

            cleaned_df = clean_weather_data(df)

            all_dfs.append(cleaned_df)

            output_file = output_path / f"{Path(file).stem}_processed.csv"

            try:
                cleaned_df.to_csv(output_file, index=False)
                logging.info(f"Processed file created and saved successfully: '{output_file}'")
            except Exception as e:
                logging.error(f"An error occurred while saving the file: '{e}'")

            try:
                shutil.move(file, backup_path)
                logging.info(f"Successfully moved '{file}' to '{backup_path}'")
            except FileNotFoundError:
                logging.error("Source file not found, check the file name or path.")
            except Exception as e:
                logging.error(f"An error occurred while moving the file: '{e}'")

        except Exception as e:
            logging.error(f"An error occurred during data transformation: '{e}'")

    merged_df = pd.concat(all_dfs, ignore_index=True)

    return merged_df


def transform_daily_main():
    """Main function to orchestrate the data transformation process."""
    files = get_weather_data_files(INPUT_PATH)
    if not files:
        logging.warning(f"No data files to process in directory: '{INPUT_PATH}'")
        return None

    final_df = process_weather_data(files, BACKUP_PATH, OUTPUT_PATH)
    logging.info("Data transformation completed.")
    logging.info(f"Transformed DataFrame columns: {final_df.columns}")
    logging.debug(f"Transformed DataFrame head:\n{final_df.head()}") 
    return final_df


if __name__ == "__main__":
    transform_daily_main()
