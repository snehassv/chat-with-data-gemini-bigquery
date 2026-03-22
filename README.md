# Chat with Your Data using Gemini + BigQuery

An AI-powered analytics assistant that converts natural language questions into SQL, executes them on BigQuery, and returns plain-English insights.

## Overview

This project allows users to ask questions about a structured dataset in natural language, such as:

- What are the top 10 most watched shows?
- Which countries have the highest watch time?
- What is the average watch duration per user?

The application uses a Gemini model to generate BigQuery SQL from the user’s question, validates the SQL, executes it against BigQuery, and summarizes the results in readable language.

## Features

- Natural language to SQL generation
- BigQuery-backed analytics
- Automatic schema extraction from BigQuery
- SQL safety validation for read-only queries
- Plain-English result summarization
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
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── sample_data/
    └── netflix_sample.csv