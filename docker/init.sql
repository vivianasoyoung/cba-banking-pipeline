CREATE DATABASE cba_pipeline;
\c cba_pipeline;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE TABLE IF NOT EXISTS raw.transactions (transaction_id VARCHAR(36) PRIMARY KEY, account_id VARCHAR(20) NOT NULL, bsb VARCHAR(7) NOT NULL, account_number VARCHAR(10) NOT NULL, transaction_date TIMESTAMP NOT NULL, amount NUMERIC(12,2) NOT NULL, transaction_type VARCHAR(20) NOT NULL, merchant_name VARCHAR(100), merchant_category VARCHAR(50), merchant_state VARCHAR(3), description TEXT, balance_after NUMERIC(12,2), channel VARCHAR(20), status VARCHAR(20) DEFAULT 'SETTLED', loaded_at TIMESTAMP DEFAULT NOW());
CREATE TABLE IF NOT EXISTS raw.accounts (account_id VARCHAR(20) PRIMARY KEY, customer_id VARCHAR(20) NOT NULL, bsb VARCHAR(7) NOT NULL, account_number VARCHAR(10) NOT NULL, account_type VARCHAR(30) NOT NULL, open_date DATE NOT NULL, balance NUMERIC(12,2) NOT NULL, credit_limit NUMERIC(12,2), loaded_at TIMESTAMP DEFAULT NOW());
CREATE TABLE IF NOT EXISTS raw.pipeline_runs (run_id SERIAL PRIMARY KEY, dag_id VARCHAR(100), run_date DATE NOT NULL, rows_ingested INTEGER, rows_rejected INTEGER, status VARCHAR(20), started_at TIMESTAMP, completed_at TIMESTAMP);
GRANT ALL PRIVILEGES ON DATABASE cba_pipeline TO airflow;
