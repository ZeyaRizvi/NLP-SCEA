# Smart Electricity Complaint Analyzer  

An **AI-powered NLP web application** that analyzes electricity-related complaints and converts them into structured insights such as **issue type**, **location**, **priority**, and **suggested action**.  
The system uses a **hybrid NLP approach** combining a **transformer-based model** (HuggingFace / DistilBERT embeddings) and **rule-based logic** for reliability.

---
Preview - https://nlp-scea.vercel.app/
## Tech Stack

- **Frontend**: React (Vite)
- **Backend**: FastAPI (Python)
- **NLP**: spaCy + HuggingFace Transformers (DistilBERT)
- **Database**: SQLite
- **Charts**: Recharts

---

## Key Features

- **Complaint input and analysis**
- **NLP-based issue classification** (hybrid: AI + keyword fallback)
- **Location extraction** from complaint text
- **Priority detection**: Low / Medium / High
- **Suggested action generation**
- **Analytics dashboard**
  - Pie chart: priority distribution
  - Bar chart: issue type distribution
  - Summary cards + insights
- **Dark mode UI** with toggle + persisted preference
- **Toast notifications** on success/error
- **Highlighted keywords** in complaint (issue phrase + location)
- **Filters** for issue type and priority

---

## Project Structure

> Note: The backend code currently lives at the repository root (e.g. `main.py`, `routes/`, `nlp/`, `database/`).  
> The `frontend/` folder contains the React app.

```text
nlp-seca/
  README.md
  requirements.txt
  main.py
  routes/
    root.py
    analyze.py
    complaints.py
  nlp/
    pipeline.py
    processor.py
  database/
    complaints_db.py
    complaints.sqlite3
  frontend/
    package.json
    vite.config.*
    src/
      App.jsx
      App.css
      index.css
```

Requested high-level folders:

- `frontend/`
- `backend/` (conceptually the FastAPI app; currently at repo root)
- `nlp/`
- `routes/`
- `database/`

---

## API Endpoints

### `POST /analyze`
Analyze a complaint and store the result in SQLite.

**Request**

```json
{
  "complaint": "Power cut in Mirpur for 5 hours"
}
```

**Response**

```json
{
  "issue_type": "power_cut",
  "location": "Mirpur",
  "priority": "high",
  "suggested_action": "..."
}
```

### `GET /complaints`
Retrieve all stored complaints (latest first).

**Response**

```json
[
  {
    "id": 1,
    "complaint": "Power cut in Mirpur for 5 hours",
    "issue": "power_cut",
    "location": "Mirpur",
    "priority": "high",
    "timestamp": "2026-04-06T17:30:26.044133+00:00"
  }
]
```

---

## Installation & Setup

## 1) Clone the repository

```bash
git clone <your-repo-url>
cd nlp-seca
```

## 2) Backend (FastAPI) setup

### Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the FastAPI server

```bash
uvicorn main:app --reload
```

Backend deployed at: Render
https://nlp-scea.onrender.com
- `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## 3) Frontend (React / Vite) setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: Vercel
https://nlp-scea.vercel.app/
- `http://127.0.0.1:5173` (default Vite port)

---

## Environment Variables

### Frontend

- **`VITE_API_BASE_URL`**: Base URL for the FastAPI backend.

Create `frontend/.env` (optional):

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## Usage

1. Start the **backend** (`uvicorn main:app --reload`)
2. Start the **frontend** (`npm run dev`)
3. In the dashboard:
   - Enter an electricity complaint
   - Submit to receive structured analysis:
     - issue type
     - location
     - priority
     - suggested action
   - View analytics:
     - charts + summary cards
     - complaint history
     - filters by issue type / priority

---

## Screenshots

- **Dashboard (Dark Mode)**
- <img width="1259" height="802" alt="Screenshot 2026-04-07 at 1 37 56 AM" src="https://github.com/user-attachments/assets/26a2eb1d-714a-40cc-b5b0-162cd327f8c9" />


- **Analysis Output + Highlighted Text**
- <img width="667" height="320" alt="Screenshot 2026-04-07 at 1 41 08 AM" src="https://github.com/user-attachments/assets/7fa6fe51-a9e2-4a17-b4fd-27e73c3c40e8" />

- **Charts (Priority + Issue Types)**
- <img width="497" height="365" alt="Screenshot 2026-04-07 at 1 42 09 AM" src="https://github.com/user-attachments/assets/60a5d32e-29b6-42c9-a888-c85643cf7229" />


---

## Future Improvements

- **Multilingual support** (Hindi/Urdu/Bengali + more)
- **Map integration** for location-based complaint clustering
- **Model fine-tuning** for higher accuracy on real complaint data
- **Authentication** (admin dashboard, user accounts, audit logs)

