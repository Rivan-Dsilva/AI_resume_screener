"""Resume parsing utilities (PDF / DOCX) + entity extraction."""
import re
import os
import pdfplumber
import docx

# ---------- Skill bank (extendable) ----------
SKILL_BANK = [
    # Programming
    "python","java","c","c++","c#","javascript","typescript","go","rust","kotlin","swift","php","ruby","scala","r","matlab",
    # Web / Frameworks
    "html","css","bootstrap","tailwind","react","next.js","angular","vue","svelte","node.js","express","django","flask","fastapi","spring","spring boot","laravel",
    # Databases
    "mysql","postgresql","mongodb","sqlite","oracle","sql server","redis","cassandra","dynamodb",
    # Data / ML / AI
    "pandas","numpy","scipy","matplotlib","seaborn","scikit-learn","tensorflow","pytorch","keras","nltk","spacy","opencv",
    "machine learning","deep learning","nlp","computer vision","data analysis","data science","statistics","mlops",
    # Cloud / DevOps
    "aws","azure","gcp","docker","kubernetes","jenkins","terraform","ansible","ci/cd","linux","bash","git","github","gitlab",
    # BI
    "power bi","tableau","excel","looker",
    # Other
    "rest api","graphql","microservices","agile","scrum","oop","data structures","algorithms","system design",
]

SOFT_SKILLS = [
    "communication","teamwork","leadership","problem solving","time management","adaptability",
    "creativity","critical thinking","collaboration","presentation","analytical","decision making",
]

DEGREE_KEYWORDS = [
    "b.tech","btech","b.e","be ","bachelor","b.sc","bsc","bca","m.tech","mtech","m.e","master","m.sc","msc","mca",
    "mba","phd","ph.d","diploma","intermediate","high school","12th","10th",
]

SECTION_HEADINGS = [
    "summary","objective","education","experience","work experience","projects","skills","technical skills",
    "certifications","achievements","awards","languages","interests","hobbies","contact",
]


def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def extract_text(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower()
    text = ""
    if ext == "pdf":
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    elif ext == "docx":
        d = docx.Document(path)
        text = "\n".join(p.text for p in d.paragraphs)
    return text


# ---------- Entity helpers ----------
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
PHONE_LINE_HINTS = ("phone", "mobile", "tel", "contact", "cell", "ph:", "mob")


def extract_phone(text: str) -> str:
    """Extract a phone number with strict validation.

    Rules:
      - Must contain 10-15 digits after stripping non-digit chars
      - Must not be a pure 4-digit year or a year range
      - Prefer matches on a line that mentions phone/mobile/contact OR
        starts with '+'
    """
    candidates = []
    for line in text.splitlines():
        for m in PHONE_RE.finditer(line):
            raw = m.group(0).strip()
            digits = re.sub(r"\D", "", raw)
            if not (10 <= len(digits) <= 15):
                continue
            # reject obvious non-phones: years, ID numbers attached to words
            if re.fullmatch(r"(19|20)\d{2}", digits):
                continue
            # reject if the surrounding token looks like a date range e.g. 2019-2022
            if re.search(r"(19|20)\d{2}\s*[-\u2013]\s*(19|20)\d{2}", raw):
                continue
            score = 0
            low = line.lower()
            if any(h in low for h in PHONE_LINE_HINTS):
                score += 5
            if raw.lstrip().startswith("+"):
                score += 3
            if 10 <= len(digits) <= 13:
                score += 2
            candidates.append((score, raw))
    if not candidates:
        return "Not Found"
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]
LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/[A-Za-z0-9_\-/]+", re.I)
GITHUB_RE = re.compile(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9_\-/]+", re.I)
YEAR_RE = re.compile(r"(19|20)\d{2}")


def _first(rx, text, default=""):
    m = rx.search(text)
    return m.group(0) if m else default


def extract_name(text: str) -> str:
    # Heuristic: first non-empty line that looks like a name (2-4 capitalized words)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        words = line.split()
        if 1 < len(words) <= 5 and sum(w[:1].isupper() for w in words) >= 2 and len(line) < 60:
            return line
    return "Not Found"


def extract_skills(text: str, bank=None):
    bank = bank or SKILL_BANK
    low = text.lower()
    found = []
    for s in bank:
        # word-boundary match for multi-word and single-word skills
        pattern = r"(?<![a-z0-9])" + re.escape(s.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, low):
            found.append(s)
    return sorted(set(found))


def extract_education(text: str):
    edu = []
    low = text.lower()
    for kw in DEGREE_KEYWORDS:
        if kw in low:
            edu.append(kw.strip().title())
    # universities (very rough)
    unis = re.findall(r"([A-Z][A-Za-z&.,'\- ]+(University|Institute|College|School))", text)
    universities = sorted({u[0].strip() for u in unis})
    years = sorted(set(YEAR_RE.findall(text)))
    return {
        "degrees": sorted(set(edu)),
        "universities": universities[:5],
        "graduation_year": years[-1] if years else "",
    }


def extract_experience_years(text: str) -> float:
    """Infer years of experience.

    1. Look for explicit "X years" / "X yrs" mentions.
    2. Else parse date ranges (YYYY - YYYY / Mon YYYY - Present) inside
       Experience / Work / Employment / Internship sections and sum them.
    3. Else fall back to (current_year - earliest_work_year) if a work
       section exists.
    """
    import datetime
    now_year = datetime.datetime.now().year

    # 1. explicit mention
    years = 0.0
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\b", text, re.I):
        years = max(years, float(m.group(1)))
    if years > 0:
        return years

    # 2/3. focus on experience / work sections
    low = text.lower()
    section_idx = -1
    for kw in ("work experience", "professional experience", "experience",
               "employment", "internship"):
        i = low.find(kw)
        if i != -1:
            section_idx = i
            break
    chunk = text[section_idx: section_idx + 3000] if section_idx != -1 else text

    months = ("jan","feb","mar","apr","may","jun",
              "jul","aug","sep","sept","oct","nov","dec")
    month_alt = "|".join(months)
    range_re = re.compile(
        rf"(?:(?:{month_alt})[a-z]*\.?\s+)?((?:19|20)\d{{2}})"
        rf"\s*[-\u2013to]+\s*"
        rf"(?:(?:{month_alt})[a-z]*\.?\s+)?((?:19|20)\d{{2}}|present|current|now)",
        re.I,
    )

    total = 0.0
    earliest = None
    for m in range_re.finditer(chunk):
        start = int(m.group(1))
        end_s = m.group(2).lower()
        end = now_year if end_s in ("present", "current", "now") else int(end_s)
        if end < start or end > now_year + 1 or start < 1970:
            continue
        total += max(0, end - start)
        earliest = start if earliest is None else min(earliest, start)

    if total > 0:
        return float(round(total + 0.5, 1)) if total < 1 else float(total)

    if earliest is not None:
        return float(now_year - earliest)

    return 0.0


def extract_companies(text: str):
    # naive: capitalized words followed by Inc/Ltd/LLC/Pvt/Technologies/Solutions
    companies = re.findall(
        r"([A-Z][A-Za-z0-9&.,'\- ]+(?:Inc|Ltd|LLC|Pvt|Technologies|Solutions|Systems|Labs|Corp|Company))",
        text,
    )
    return sorted({c.strip() for c in companies})[:10]


def extract_projects(text: str):
    """Look for a Projects section and pull bullet/line items."""
    low = text.lower()
    idx = low.find("project")
    if idx == -1:
        return []
    chunk = text[idx: idx + 1500]
    lines = [l.strip("•-*\t ").strip() for l in chunk.splitlines()]
    projects = [l for l in lines if 5 < len(l) < 120 and not l.lower().startswith(("project", "projects"))]
    return projects[:8]


def extract_certifications(text: str):
    low = text.lower()
    if "certification" not in low and "certified" not in low:
        return []
    idx = max(low.find("certification"), low.find("certified"))
    chunk = text[idx: idx + 1000]
    items = [l.strip("•-*\t ").strip() for l in chunk.splitlines() if l.strip()]
    return [i for i in items if 3 < len(i) < 120][:8]


def extract_languages(text: str):
    langs = ["english","hindi","spanish","french","german","mandarin","japanese","arabic","telugu","tamil","marathi","bengali","kannada","malayalam"]
    low = text.lower()
    return sorted({l.title() for l in langs if l in low})


def parse_resume(path: str) -> dict:
    text = extract_text(path)
    return {
        "raw_text": text,
        "name": extract_name(text),
        "email": _first(EMAIL_RE, text, "Not Found"),
        "phone": extract_phone(text),
        "linkedin": _first(LINKEDIN_RE, text, ""),
        "github": _first(GITHUB_RE, text, ""),
        "education": extract_education(text),
        "experience_years": extract_experience_years(text),
        "companies": extract_companies(text),
        "projects": extract_projects(text),
        "certifications": extract_certifications(text),
        "languages": extract_languages(text),
        "technical_skills": extract_skills(text, SKILL_BANK),
        "soft_skills": extract_skills(text, SOFT_SKILLS),
        "sections_present": [s for s in SECTION_HEADINGS if s in text.lower()],
    }
