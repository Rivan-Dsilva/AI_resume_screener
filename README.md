# AI Resume Screening & Analysis System (Offline)

A modern, offline AI Resume Screening & Analysis web app built with **Flask + MySQL + Bootstrap 5**.
No external AI APIs — uses TF-IDF, Cosine Similarity, rule-based ATS scoring, spaCy and NLTK.

## Tech Stack
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js, Font Awesome, Google Fonts (Poppins)
- **Backend:** Python Flask
- **Database:** MySQL
- **ML / NLP:** scikit-learn (TF-IDF, Cosine Similarity), spaCy, NLTK
- **Resume parsing:** pdfplumber, python-docx
- **PDF report:** reportlab

## Folder Structure
```
resume_screening/
├── app.py                  # Main Flask app
├── config.py               # MySQL & app config
├── requirements.txt
├── README.md
├── database/
│   └── schema.sql          # MySQL schema + sample data
├── utils/
│   ├── __init__.py
│   ├── parser.py           # Resume parsing (PDF/DOCX)
│   ├── analyzer.py         # ATS, scoring, skill match, suggestions
│   └── pdf_report.py       # Downloadable PDF report
├── templates/
│   ├── base.html
│   ├── index.html          # Home + Hero
│   ├── upload.html         # Upload + JD
│   ├── features.html
│   ├── about.html
│   └── dashboard.html      # Results + Charts
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── img/
└── uploads/                # Uploaded resumes (gitignored)
```

## Setup

### 1. Install Python deps
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### 2. MySQL
Create database and import schema:
```bash
mysql -u root -p < database/schema.sql
```

Update credentials in `config.py`:
```python
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "your_password"
MYSQL_DB = "resume_screening"
```

### 3. (Optional) Import the `resume_data_cvc.csv` dataset
Place the file **`resume_data_cvc.csv`** directly inside the `resume_screening/` folder
(next to `app.py`), then run:
```bash
python import_dataset.py
# or with a custom path:
python import_dataset.py path/to/resume_data_cvc.csv
```

The importer auto-handles the BOM on `job_position_name`, the duplicate
`responsibilities.1` column, and the `educationaL_requirements` / `experiencere_requirement`
typos in the original headers.

### 4. Run
```bash
python app.py
```
Open http://127.0.0.1:5000

## Features
- Drag & drop resume upload (PDF/DOCX)
- Resume parsing: name, email, phone, LinkedIn, GitHub, education, skills, experience, projects, certifications
- Resume Score (0–100), ATS Score, Completeness %
- Job Match % vs pasted Job Description (TF-IDF + Cosine Similarity)
- Skill match: matched / missing skills
- Strengths, weaknesses, improvement suggestions
- Career recommendations from CVC dataset
- Dashboard with Chart.js (Radar, Pie, Bar, Line)
- Downloadable PDF report (reportlab)
- Fully responsive, glassmorphism SaaS UI

## Resume Score Formula
| Component       | Weight |
|-----------------|--------|
| Skills          | 40%    |
| Experience      | 20%    |
| Projects        | 15%    |
| Education       | 10%    |
| Certifications  | 5%     |
| ATS             | 10%    |
| **Total**       | 100%   |
