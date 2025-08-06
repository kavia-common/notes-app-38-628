# Flask Backend for Notes App Monolith

## Getting Started

1. (Optional) Create venv, activate it.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Initialize the SQLite db:
   ```
   flask --app app.py init-db
   ```
4. Run the server:
   ```
   flask --app app.py run
   ```
   The API will be at `http://localhost:5000/api/`
