# Chat with Your Data using Streamlit, Gemini, and BigQuery

An AI-powered analytics assistant that converts natural language questions into SQL, executes them on BigQuery, and returns plain-English insights.

## Overview

This project is an AI-powered analytics assistant that allows users to ask natural language questions about a structured dataset through a Streamlit web interface.

The application:
- accepts a user question in plain English,
- fetches the BigQuery table schema,
- uses Gemini to generate BigQuery SQL,
- validates and executes the SQL,
- retries failed queries with AI-assisted correction,
- and returns both tabular results and a plain-English summary.

This project was built to demonstrate how LLMs can be integrated into modern data engineering workflows for self-service analytics.

## Features

- Streamlit-based web interface for natural language querying
- Automatic BigQuery schema extraction
- Gemini-powered SQL generation
- SQL validation for safe query execution
- BigQuery query execution with tabular result display
- Plain-English summarization of results
- Automatic SQL retry and correction using BigQuery error feedback
- Easy to extend to other structured datasets

## Tech Stack

- Python
- Google BigQuery
- Gemini API (`google-genai`)
- `google-cloud-bigquery`
- `python-dotenv`

## Dataset

This project was built using the **Netflix User Watching Behavior Dataset** from Kaggle.

> Replace this section with the exact dataset URL you used.

The raw dataset is **not committed** to this repository.  
To run the project yourself, download the dataset locally and upload it to your own BigQuery table.

## Project Structure

```text
chat-with-data/
├── app.py                  # core CLI version
├── streamlit_app.py        # Streamlit web application
├── requirements.txt
├── README.md
├── .gitignore
└── sample_data/
    └── netflix_sample.csv

## Run the App

Start the Streamlit app locally:

```bash
streamlit run streamlit_app.py

## User Interface

The Streamlit app provides a simple local web interface where users can:

- enter natural language analytics questions,
- view the generated SQL,
- inspect retry attempts when SQL correction is needed,
- see query results in tabular format,
- and read a plain-English summary of the output.