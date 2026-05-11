import os
import logging
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

"""This script loads the processed data into the weather_data table."""

# --- configs ---
load_dotenv()

# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Db parameters
db_host = os.getenv("POSTGRES_HOST")
db_name = os.getenv("POSTGRES_DB")
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_port = os.getenv("POSTGRES_PORT")


def db_connect(db_host, db_name, db_user, db_password, db_port):
    """Check connection to PostgreSQL database"""
    try:
        conn = psycopg2.connect(host=db_host, 
                                database=db_name, 
                                user=db_user, 
                                password=db_password, 
                                port=db_port
        )

        logging.info(f"Database connection established: {conn}")
        return conn
    except Exception as e:
        logging.error(f"Unable to connect to the database: {e}")
        raise Exception("Database connection failed")
        # exit(1)


def load_data_to_table(conn, df):
    """Insert/load the processed data into the table"""

    sql_qry = """INSERT INTO weather_data (city_name, country, latitude, longitude, timezone, utc_offset, sunrise, sunset, local_time, 
    temperature, precipitation, rain, showers, snowfall, weather_code, wind_speed, wind_direction, insert_date)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    cur = conn.cursor()

    for city_data in df.values:
        city = city_data[0]
        country = city_data[1]
        lat = city_data[2]
        lon = city_data[3]
        tz = city_data[4]
        utc = city_data[5]
        sunrise = city_data[6]
        sunset = city_data[7]
        local_time = city_data[8]
        temperature = city_data[9]
        precipitation = city_data[10]
        rain = city_data[11]
        showers = city_data[12]
        snowfall = city_data[13]
        weather_code = city_data[14]
        wind_speed = city_data[15]
        wind_direction = city_data[16]
        insert_date = datetime.now()

        cur.execute(
            sql_qry, (city, country, lat, lon, tz, utc, sunrise, sunset, local_time, temperature, precipitation, rain, showers, snowfall, 
                      weather_code, wind_speed, wind_direction, insert_date)
            )
    
    cur.close()
    logging.info("Data loaded successfully into the weather_data table. Committing transaction.")
    conn.commit()


def load_to_dim_location(conn):
    """ Load or update unique city information into the dim_location table."""
    try:
        cursor = conn.cursor()
        loc_query = ("""
                INSERT INTO dim_location (location_key, city_name, country, latitude, longitude, timezone, utc_offset)
                SELECT distinct
                    DENSE_RANK() OVER (ORDER BY city_name, country, latitude, longitude, timezone, utc_offset) as location_key,
                    city_name, country, latitude, longitude, timezone, utc_offset
                FROM weather_data
                WHERE insert_date::date = (SELECT MAX(insert_date::date) FROM weather_data)
                ON CONFLICT (location_key) DO NOTHING
                """)
        cursor.execute(loc_query)
        cursor.close()
        logging.info("Data loaded successfully into dim_location table. Committing transaction.")
        conn.commit()

    except Exception as e:
        logging.error(f"Error loading city data: {e}")
        conn.close()
        raise Exception("Loading of City data failed")


def load_to_dim_date(conn):
    """ Load unique date information into the dim_date table."""
    try:
        cursor = conn.cursor()
        date_query = ("""
                INSERT INTO dim_date (date_key, date, year, month, day, week, day_name)
                SELECT DISTINCT
                    to_char(local_time::date, 'YYYYMMDD')::integer as date_key,
                    local_time::date,
                    EXTRACT(YEAR FROM local_time),
                    EXTRACT(MONTH FROM local_time),
                    EXTRACT(DAY FROM local_time),
                    EXTRACT(WEEK FROM local_time),
                    TO_CHAR(local_time, 'Day')
                FROM weather_data
                WHERE insert_date::date = (SELECT MAX(insert_date::date) FROM weather_data)
                ON CONFLICT (date_key) DO NOTHING
                """)
        cursor.execute(date_query)
        cursor.close()
        logging.info("Data loaded successfully into dim_date table. Committing transaction.")
        conn.commit()

    except Exception as e:
        logging.error(f"Error loading date data: {e}")
        conn.close()
        raise Exception("Loading of Date data failed")
    

def load_fact_weather(conn):
    """ Load data into the fact_weather table."""
    try:
        cursor = conn.cursor()
        fact_query = ("""
                INSERT INTO fact_weather (location_key, date_key, weather_key, temperature, precipitation, rain, showers, snowfall, wind_speed, insert_date)
                SELECT
                    l.location_key,
                    to_char(wd.local_time::date, 'YYYYMMDD')::integer as date_key,
                    wd.weather_code,
                    wd.temperature,
                    wd.precipitation,
                    wd.rain,
                    wd.showers,
                    wd.snowfall,
                    wd.wind_speed,
                    wd.insert_date
                FROM weather_data wd
                JOIN dim_location l ON 
                    wd.city_name = l.city_name AND wd.latitude = l.latitude AND wd.longitude = l.longitude
                WHERE insert_date::date = (SELECT MAX(insert_date::date) FROM weather_data)
                ON CONFLICT (location_key, date_key, weather_key) DO UPDATE
                SET
                    temperature = EXCLUDED.temperature,
                    precipitation = EXCLUDED.precipitation,
                    rain = EXCLUDED.rain,
                    showers = EXCLUDED.showers,
                    snowfall = EXCLUDED.snowfall,
                    wind_speed = EXCLUDED.wind_speed,           
                    insert_date = EXCLUDED.insert_date
                """)
        cursor.execute(fact_query)
        cursor.close()
        logging.info("Data loaded successfully into fact_weather table. Committing transaction.")
        conn.commit()

    except Exception as e:
        logging.error(f"Error loading weather fact data: {e}")
        conn.close()
        raise Exception("Loading of Weather fact data failed")
    

def load_main(final_df):
    """Main function to load the data into the database."""

    db = db_connect(db_host, db_name, db_user, db_password, db_port)
    logging.info("Connected to the database successfully.")

    try:    
        if final_df is not None and not final_df.empty:
            load_data_to_table(db, final_df)
            load_to_dim_location(db)
            load_to_dim_date(db)
            load_fact_weather(db)
        else:
            logging.warning("No data to load into the table.")
        
        db.close()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        db.close()
        raise Exception("Data load failed")
