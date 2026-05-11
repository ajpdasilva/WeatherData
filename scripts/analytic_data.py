import os
import psycopg2
import logging
from dotenv import load_dotenv

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


def weather_summary(conn):
    """Create or refresh the materialized view of weather summary."""
    query_weather_summary = """
		CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_summary AS
        SELECT
            dd.date,
            dl.city_name,
            fw.temperature,
            fw.precipitation,
            fw.wind_speed,
            dwc.weather_description 
        FROM fact_weather fw
        JOIN dim_date dd ON fw.date_key = dd.date_key
        JOIN dim_location dl ON fw.location_key = dl.location_key
        JOIN dim_weather_condition dwc on fw.weather_key = dwc.weather_key 
        ORDER BY date desc, city_name
	"""

    try:
        cur = conn.cursor()

        # Check if the materialized view exists
        cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'mv_weather_summary'")
        exists = cur.fetchone()[0] > 0

        if not exists:
            cur.execute(query_weather_summary)
            conn.commit()
            logging.info("Materialized View 'mv_weather_summary' was created successfully.")
        else:
            logging.info("Materialized View exists. Refreshing data concurrently...")
            try:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_summary;") # CONCURRENTLY -- allows users to query the view while it refreshes
                conn.commit()
                logging.info("Refresh of Materialized View 'mv_weather_summary' completed successfully.")
            except psycopg2.Error as e:
                logging.error(f"Error refreshing materialized view: {e}")
                raise Exception("Materialized view refresh failed")
        
        cur.close()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        conn.close()


def seven_day_trend(conn):
    """Create or refresh the materialized view of weather trend."""
    query_weather_trend = """
		CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_trend AS
        SELECT
            dd.date,
            dl.city_name,
            fw.temperature,
            AVG(fw.temperature) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS avg_temp_7d,
            fw.precipitation,
            SUM(fw.precipitation) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS total_precip_7d
        FROM fact_weather fw
        JOIN dim_location dl ON fw.location_key = dl.location_key
        JOIN dim_date dd ON fw.date_key = dd.date_key
	"""

    try:
        cur = conn.cursor()

        # Check if the materialized view exists
        cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'mv_weather_trend'")
        exists = cur.fetchone()[0] > 0

        if not exists:
            cur.execute(query_weather_trend)
            conn.commit()
            logging.info("Materialized View 'mv_weather_trend' was created successfully.")
        else:
            logging.info("Materialized View exists. Refreshing data concurrently...")
            try:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_trend;") # CONCURRENTLY -- allows users to query the view while it refreshes
                conn.commit()
                logging.info("Refresh of Materialized View 'mv_weather_trend' completed successfully.")
            except psycopg2.Error as e:
                logging.error(f"Error refreshing materialized view: {e}")
                raise Exception("Materialized view refresh failed")
        
        cur.close()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        conn.close()


def monthly_aggregates(conn):
    """Create or refresh the materialized view of weather aggregates."""
    query_weather_agg = """
		CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_agg AS
        SELECT
            dd.month,
            AVG(fw.temperature) AS avg_temp,
            SUM(fw.precipitation) AS total_precipitation,
            AVG(fw.wind_speed) AS avg_windspeed
        FROM fact_weather fw
        JOIN dim_date dd ON fw.date_key = dd.date_key
        GROUP BY dd.month
        ORDER BY dd.month DESC
	"""

    try:
        cur = conn.cursor()

        # Check if the materialized view exists
        cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'mv_weather_agg'")
        exists = cur.fetchone()[0] > 0

        if not exists:
            cur.execute(query_weather_agg)
            conn.commit()
            logging.info("Materialized View 'mv_weather_agg' was created successfully.")
        else:
            logging.info("Materialized View exists. Refreshing data concurrently...")
            try:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_agg;") # CONCURRENTLY -- allows users to query the view while it refreshes
                conn.commit()
                logging.info("Refresh of Materialized View 'mv_weather_agg' completed successfully.")
            except psycopg2.Error as e:
                logging.error(f"Error refreshing materialized view: {e}")
                raise Exception("Materialized view refresh failed")
        
        cur.close()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        conn.close()
    

def analytics_main():
    db = db_connect(db_host, db_name, db_user, db_password, db_port)
    logging.info("Connected to the database successfully.")

    try:
        weather_summary(db)
        seven_day_trend(db)
        monthly_aggregates(db)
        db.close()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        db.close()
        raise Exception("Data load failed")

if __name__ == "__main__":
    analytics_main()
