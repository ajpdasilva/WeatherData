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


def city_weather_summary(conn):
    """Create or refresh the materialized view of weather summary by city."""
    query_weather_summary = """
		CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_city_summary AS
        SELECT 
            dl.city_name,
            ROUND(AVG(fw.temperature)::numeric, 2) AS avg_temp,
            MIN(fw.temperature) AS min_temp,
            MAX(fw.temperature) AS max_temp,
            ROUND(AVG(fw.precipitation)::numeric, 2) AS avg_precip,
            SUM(fw.precipitation) AS total_precip,
            ROUND(AVG(fw.wind_speed)::numeric, 2) AS avg_wind_speed,
            MAX(fw.wind_speed) AS max_wind_speed,
            ROUND(AVG(fw.rain)::numeric, 2) AS avg_rainfall,
            ROUND(AVG(fw.snowfall)::numeric, 2) AS avg_snowfall,
            COUNT(*) AS obs_days
        FROM fact_weather fw
        JOIN dim_location dl ON fw.location_key = dl.location_key
        GROUP BY dl.city_name
        ORDER BY dl.city_name
	"""
    
    create_ws_view_index = """
		CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_city_summary_city 
		ON mv_weather_city_summary (city_name)
	"""

    try:
        cur = conn.cursor()

        # Check if the materialized view exists
        cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'mv_weather_city_summary'")
        exists = cur.fetchone()[0] > 0

        if not exists:
            cur.execute(query_weather_summary)
            conn.commit()
            logging.info("Materialized View 'mv_weather_city_summary' was created successfully.")
            cur.execute(create_ws_view_index)
            conn.commit()
            logging.info("Index for Materialized View 'mv_weather_city_summary' was created successfully.")
        else:
            logging.info("Materialized View exists. Refreshing data concurrently...")
            try:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_city_summary;") # CONCURRENTLY -- allows users to query the view while it refreshes
                conn.commit()
                logging.info("Refresh of Materialized View 'mv_weather_city_summary' completed successfully.")
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

    create_wt_view_index = """
		CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_trend_date_city 
		ON mv_weather_trend (date, city_name)
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
            cur.execute(create_wt_view_index)
            conn.commit()
            logging.info("Index for Materialized View 'mv_weather_trend' was created successfully.")
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


def city_weekly_summary(conn):
    """Create or refresh the materialized view of weekly weather summary by city."""
    query_weather_agg = """
		CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_city_weekly AS
        SELECT 
            dd.week,
            dl.city_name,
            ROUND(AVG(fw.temperature)::numeric, 2) AS avg_temp,
            ROUND(AVG(fw.precipitation)::numeric, 2) AS avg_precip,
            ROUND(AVG(fw.wind_speed)::numeric, 2) AS avg_wind_speed
        FROM fact_weather fw
        JOIN dim_location dl ON fw.location_key = dl.location_key
        JOIN dim_date dd ON fw.date_key = dd.date_key 
        GROUP BY dd.week, dl.city_name
        ORDER BY dd.week, dl.city_name
	"""

    create_wa_view_index = """
		CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_city_weekly_week 
		ON mv_weather_city_weekly (week, city_name)
	"""

    try:
        cur = conn.cursor()

        # Check if the materialized view exists
        cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'mv_weather_city_weekly'")
        exists = cur.fetchone()[0] > 0

        if not exists:
            cur.execute(query_weather_agg)
            conn.commit()
            logging.info("Materialized View 'mv_weather_city_weekly' was created successfully.")
            cur.execute(create_wa_view_index)
            conn.commit()
            logging.info("Index for Materialized View 'mv_weather_city_weekly' was created successfully.")
        else:
            logging.info("Materialized View exists. Refreshing data concurrently...")
            try:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_city_weekly;") # CONCURRENTLY -- allows users to query the view while it refreshes
                conn.commit()
                logging.info("Refresh of Materialized View 'mv_weather_city_weekly' completed successfully.")
            except psycopg2.Error as e:
                logging.error(f"Error refreshing materialized view: {e}")
                raise Exception("Materialized view refresh failed")
        
        cur.close()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        conn.close()
    

def weather_condition_summary(conn):
    """Create or refresh the materialized view of weather conditions summary."""
    query_weather_agg = """
		CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weather_condition_summary AS
        SELECT 
            dwc.weather_description,
            count(*) as day_count,
            ROUND(AVG(fw.temperature)::numeric, 2) AS avg_temp,
            ROUND(AVG(fw.precipitation)::numeric, 2) AS avg_precip
        FROM fact_weather fw
        JOIN dim_weather_condition dwc ON fw.weather_key = dwc.weather_key
        GROUP BY dwc.weather_description
        ORDER BY dwc.weather_description
	"""

    create_wa_view_index = """
		CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_condition_summary 
		ON mv_weather_condition_summary (weather_description)
	"""

    try:
        cur = conn.cursor()

        # Check if the materialized view exists
        cur.execute("SELECT count(*) FROM pg_matviews WHERE matviewname = 'mv_weather_condition_summary'")
        exists = cur.fetchone()[0] > 0

        if not exists:
            cur.execute(query_weather_agg)
            conn.commit()
            logging.info("Materialized View 'mv_weather_condition_summary' was created successfully.")
            cur.execute(create_wa_view_index)
            conn.commit()
            logging.info("Index for Materialized View 'mv_weather_condition_summary' was created successfully.")
        else:
            logging.info("Materialized View exists. Refreshing data concurrently...")
            try:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_weather_condition_summary;") # CONCURRENTLY -- allows users to query the view while it refreshes
                conn.commit()
                logging.info("Refresh of Materialized View 'mv_weather_condition_summary' completed successfully.")
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
        city_weather_summary(db)
        seven_day_trend(db)
        city_weekly_summary(db)
        weather_condition_summary(db)
        db.close()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        db.close()
        raise Exception("Data load failed")

if __name__ == "__main__":
    analytics_main()
