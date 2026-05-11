-- ============================================
-- 1. CREATE DATABASE
-- ============================================
-- create database weather_db;

-- ============================================
-- 2. CONNECT TO THE DATABASE
-- ============================================
\connect weather_db;

-- ============================================
-- 3. CREATE ACCOUNTS/ROLES
-- ============================================
-- Allow user to connect
GRANT CONNECT ON DATABASE weather_db TO weatherman;

-- Grant schema access
GRANT USAGE ON SCHEMA public TO weatherman;
GRANT ALL ON SCHEMA public TO weatherman;

-- Grant table access (existing tables)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO weatherman;

-- Grant sequence access (required for SERIAL/IDENTITY)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO weatherman;

-- Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL PRIVILEGES ON TABLES TO weatherman;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO weatherman;

-- ============================================
-- 4. CREATE TABLES
-- ============================================
CREATE TABLE IF NOT EXISTS public.weather_data (
	id serial4 NOT NULL,
	city_name varchar(255) NULL,
	country text NULL,
	latitude numeric(9, 6) NULL,
	longitude numeric(9, 6) NULL,
	timezone varchar(100) NULL,
	utc_offset float8 NULL,
	sunrise timestamp NULL,
	sunset timestamp NULL,
	local_time timestamp NULL,
	temperature float8 NULL,
	precipitation numeric(4, 1) NULL,
	rain numeric(4, 1) NULL,
	showers numeric(4, 1) NULL,
	snowfall numeric(4, 1) NULL,
	weather_code int4 NULL,
	wind_speed numeric(4, 1) NULL,
	wind_direction int4 NULL,
	insert_date timestamp DEFAULT now() NULL,
	CONSTRAINT weather_data_pk PRIMARY KEY (id)
);
CREATE INDEX weather_data_city_name_idx ON public.weather_data (city_name, latitude, longitude);


CREATE TABLE public.dim_location (
	location_key int NOT NULL,
	city_name varchar(255) NOT NULL,
	country text NULL,
	latitude numeric(9, 6) NOT NULL,
	longitude numeric(9, 6) NOT NULL,
	timezone text NULL,
	utc_offset float8 NULL,
	CONSTRAINT dim_location_pk PRIMARY KEY (location_key)
);
CREATE INDEX dim_cities_city_name_idx ON public.dim_location USING btree (city_name, latitude, longitude);


CREATE TABLE IF NOT EXISTS public.dim_date (
	date_key int NOT NULL,
	"date" date NOT NULL,
	"year" int NOT NULL,
	"month" int NOT NULL,
	"day" int NOT NULL,
	"week" int NOT NULL,
    "day_name" text NOT NULL,
	CONSTRAINT dim_date_pkey PRIMARY KEY (date_key)
);


CREATE TABLE IF NOT EXISTS public.dim_weather_condition (
    weather_key serial4 NOT NULL,
	weather_description text NOT NULL,
	CONSTRAINT dim_weather_condition_pk PRIMARY KEY (weather_key)
);


CREATE TABLE public.fact_weather (
	location_key int4 NOT NULL,
	date_key int NOT NULL,
	weather_key int4 NOT NULL,
	temperature float8 NOT NULL,
	precipitation numeric(4, 1) NOT NULL,
	rain numeric(4, 1) NOT NULL,
	showers numeric(4, 1) NOT NULL,
	snowfall numeric(4, 1) NOT NULL,
	wind_speed numeric(4, 1) NOT NULL,
	insert_date timestamp DEFAULT now() NOT NULL,
	CONSTRAINT fact_weather_pk PRIMARY KEY (location_key, date_key, weather_key),
	CONSTRAINT fact_weather_date_key_fkey FOREIGN KEY (date_key) REFERENCES public.dim_date(date_key),
	CONSTRAINT fact_weather_location_fkey FOREIGN KEY (location_key) REFERENCES public.dim_location(location_key),
	CONSTRAINT fact_weather_weather_key_fkey FOREIGN KEY (weather_key) REFERENCES public.dim_weather_condition(weather_key)
);
