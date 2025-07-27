**Stock Data API**
**Overview**
A modern REST API for fetching, caching, storing, and exporting stock data, built with FastAPI, SQLite, Redis, and Docker Compose.

**Tech Stack**
Python 3.13.5

FastAPI – async REST API framework

Redis – for caching

SQLite  – for persistent storage

pandas– for data analysis and Excel export

Docker & Docker Compose – to run everything anywhere, instantly

**Setup Instructions**

**Local (No Docker)**

1) Clone the repository:
                       git clone https://github.com/nommy04/Stock_data_api.git
                       cd Stock_data_api
                       
2) Create & activate a virtual environment(Optional):
                                                      python3 -m venv venv
                                                      source venv/bin/activate
3) Install dependencies:
                         pip install -r requirements.txt
4) Run the API:
                uvicorn app:app --reload --host 0.0.0.0 --port 8000
5) Visit http://localhost:8000/docs for interactive Swagger UI!

 **Docker**
1)Build and launch:
                   docker compose up --build

2) Check endpoints:

API docs: http://localhost:8000/docs

**Data Acquisition job**

1) python data_ingestion.py

it takes the from_date and to_date and drags the s&p 500 data from the yahoo finance library and stores the information in a table named **raw_stock_data**

**stock_metadata** was also formed from this 

**API Usage**

Docs: Complete interactive documentation at /

1) **build-index url**


  url=http://127.0.0.1:8000/build-index
  sample curl-
               curl -X 'POST' \
  'http://127.0.0.1:8000/build-index' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "start_date": "2024-07-19",
  "end_date": "2024-07-20"
}'

2) **export data**

  url=http://127.0.0.1:8000/export-data?start_date=2024-06-01&end_date=2024-06-18
   
  sample curl=
           curl -X 'POST' \
  'http://127.0.0.1:8000/export-data?start_date=2024-06-01&end_date=2024-06-18' \
  -H 'accept: application/json' \
  -d ''
   

3) **index performance for a range of data**

  url=  http://127.0.0.1:8000/index-performance?start_date=2024-06-01&end_date=2024-07-12

  sample Curl-
   curl -X 'GET' \
  'http://127.0.0.1:8000/index-performance?start_date=2024-06-01&end_date=2024-07-12' \
  -H 'accept: application/json

4) **index composition at a particular date** **
  url= http://127.0.0.1:8000/index-composition?date=2024-06-03
  sample curl-
   curl -X 'GET' \
  'http://127.0.0.1:8000/index-composition?date=2024-06-03' \
  -H 'accept: application/json' 
5) **composition changes as per dates**
  url= http://127.0.0.1:8000/composition-changes?start_date=2024-06-01&end_date=2024-06-18
  sample curl=
   curl -X 'GET' \
  'http://127.0.0.1:8000/composition-changes?start_date=2024-06-01&end_date=2024-06-18' \
  -H 'accept: application/json'

**DATABASE SCHEMA OVERVIEW**
Note -**The current database only holds data from 2024-06-01 to 2024-07-18**
**Tables**

1) **raw_stock_data**
this is created from the data_ingestion.py
   -- raw_stock_data definition

CREATE TABLE raw_stock_data (
	ticker TEXT, 
	name TEXT, 
	sector TEXT, 
	industry TEXT, 
	price FLOAT, 
	market_cap BIGINT, 
	date TEXT
);

CREATE INDEX idx_ticker_date ON raw_stock_data (ticker,date);

2) **stock_metadata**
   this is created from raw_stock_data
    -- stock_metadata definition

CREATE TABLE "stock_metadata"(
  ticker TEXT,
  name TEXT,
  sector TEXT,
  industry TEXT
);

CREATE INDEX idx_ticker_meta ON stock_metadata (ticker)

;
3) **daily_index_composition**
this is created from the build index api
-- daily_index_composition definition

CREATE TABLE daily_index_composition (
	ticker TEXT, 
	price TEXT, 
	market_cap BIGINT, 
	date TEXT
, weight REAL);

CREATE INDEX idx_ticker ON daily_index_composition (ticker);

4) **index_performance**
    this is created from the build index api
   -- index_performance definition

CREATE TABLE index_performance (
    date TEXT PRIMARY KEY,
    index_value REAL
, normalized_index_value REAL);

CREATE INDEX idx_date ON index_performance (date);

**Redis:**
Used to cache recent or expensive queries for rapid API responses

**Production & Scaling Suggestions**
Use PostgreSQL instead of SQLite:
SQLite is great for testing and small projects, but PostgreSQL is better for bigger apps because it handles more users at once and is safer with data.

Deploy with container tools like Kubernetes:
Tools like Kubernetes or AWS ECS help your app handle a lot of traffic, keep it running if something fails, and make updates safer and easier.This is useful if the app outgrows a single server and we need multi service architecture.

Make long tasks run in the background:
For things that take a while (like getting lots of data), use helpers like Celery or FastAPI’s background jobs so the app stays fast for users.Use a task scheduler for the data ingestion and can keep it as a cronjob.

Add monitoring and logs:
Use tools like Prometheus and Grafana to watch your app and see if there are problems. Also add logging so you can track errors and usage.

Keep secrets safe:
Never put passwords or keys directly in your code. Store them in environment variables or a secrets manager.




   
