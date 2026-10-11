# BushSignal

BushSignal is a project I'm building to make it easier to record and keep track of environmental observations.

The idea is simple: collect observations in one place, map them, and make it easier to see what might need attention.

## What it does

- Record observations, including species, location, severity, affected area, and notes.
- View observations on a map.
- Explore data through charts and a dashboard.
- Import and export observations using CSV files.
- Check datasets for invalid entries and potential duplicates.
- Edit and delete records.
- Experiment with AI-assisted image analysis.

## Built with

Python, Streamlit, SQLite, Pandas and Plotly, with PyTorch and OpenCLIP for the image-analysis component.

## Running locally

Clone the repository, then open the project folder.

Create and activate a virtual environment:

bash
python3 -m venv .venv
source .venv/bin/activate


Install the dependencies:

bash
pip install -r requirements.txt


Start the app:

bash
streamlit run app.py


## Notes

BushSignal is still a prototype. Its priority scores are heuristic estimates, not scientifically validated risk assessments, and AI-generated suggestions need to be checked independently.

The app uses a local SQLite database. Don't upload private observations, sensitive location data, or credentials to a public repository.
