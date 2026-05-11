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
    cols = ['city', 'country', 'latitude', 'longitude', 'timezone', 'utc_offset', 'sunrise', 'sunset', 'time', 
            'temperature_2m_max', 'precipitation_sum', 'rain_sum', 'showers_sum', 'snowfall_sum', 'weather_code', 
            'wind_speed_10m_max', 'wind_direction_10m_dominant']
    df = df[cols]

    """Data clean up: formatting date/time fields and converting offset to hours."""

    df['utc_offset'] = df['utc_offset'] / 3600
    
    df['sunrise'] = pd.to_datetime(df['sunrise']).dt.strftime('%Y-%m-%d %H:%M')
    df['sunset'] = pd.to_datetime(df['sunset']).dt.strftime('%Y-%m-%d %H:%M')

    df['temperature_2m_max'] = df['temperature_2m_max'].fillna(0)
    df['precipitation_sum'] = df['precipitation_sum'].fillna(0)
    df['rain_sum'] = df['rain_sum'].fillna(0)
    df['showers_sum'] = df['showers_sum'].fillna(0)
    df['snowfall_sum'] = df['snowfall_sum'].fillna(0)
    df['weather_code'] = df['weather_code'].fillna(0)
    df['wind_speed_10m_max'] = df['wind_speed_10m_max'].fillna(0)
    df['wind_direction_10m_dominant'] = df['wind_direction_10m_dominant'].fillna(0)

    logging.info("Data cleanup completed.")

    return df


def process_weather_data(files, backup_path, destination_path):
    """Collect and transform the data from files."""
    all_dfs = []

    for file in files:
        logging.info(f"Processing file: {file}")
        try:
            with open(file, "r") as f:
                data = json.load(f)

            city_df = []

            for city_name, city_info in data.items():
                # Convert the 'daily' dictionary (which contains lists) into a DataFrame
                df = pd.DataFrame(city_info['daily'])

                df['city'] = city_name
                df['country'] = city_info.get('country')
                df['latitude'] = city_info.get('latitude')
                df['longitude'] = city_info.get('longitude')
                df['timezone'] = city_info.get('timezone')
                df['utc_offset'] = city_info.get('utc_offset_seconds')
     
                city_df.append(df)
            

            # Combine all city DataFrames into one final DataFrame
            flattened_df = pd.concat(city_df, ignore_index=True)

            cleaned_df = clean_weather_data(flattened_df)

            all_dfs.append(cleaned_df)

            output_file = destination_path / f"{Path(file).stem}_processed.csv"
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
            return None
    
    merged_df = pd.concat(all_dfs, ignore_index=True)

    return merged_df

def transform_hist_main():
    """Main function to orchestrate the data transformation process."""

    files = get_weather_data_files(INPUT_PATH)
    if not files:
        logging.warning(f"No data files to process in directory: '{INPUT_PATH}'")
        return None

    final_df = process_weather_data(files, BACKUP_PATH, OUTPUT_PATH)

    if final_df is not None and not final_df.empty:
        logging.info("Data transformation completed.")
        logging.info(f"Transformed DataFrame head:\n{final_df.head()}")
        return final_df
    else:
        logging.error(f"No data available in file(s) to process")
        raise Exception("No data returned")
    

if __name__ == "__main__":
    transform_hist_main()
