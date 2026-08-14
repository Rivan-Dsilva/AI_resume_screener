"""Resume analysis: ATS score, resume score, job match, skill gap, recommendations.
Uses MySQL (resume_screening.resume_data), TF-IDF + Cosine Similarity, and rule-based ATS.
"""
import re
import mysql.connector
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config
from .parser import SKILL_BANK, SECTION_HEADINGS


# ---------- MySQL ----------
def get_db():
    return mysql.connector.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DB,
        port=config.MYSQL_PORT,
    )


# Columns of the resume_data_cvc table (must match database/schema.sql)
CVC_COLUMNS = [
    "address","career_objective","skills","educational_institution_name",
    "degree_names","passing_years","educational_results","result_types",
    "major_field_of_studies","professional_company_names","company_urls",
    "start_dates","end_dates","related_skils_in_job","positions","locations",
    "responsibilities","extra_curricular_activity_types",
    "extra_curricular_organization_names","extra_curricular_organization_links",
    "role_positions","languages","proficiency_levels","certification_providers",
    "certification_skills","online_links","issue_dates","expiry_dates",
    "job_position_name","educational_requirements","experience_requirement",
    "age_requirement","responsibilities_1","skills_required","matched_score",
]


def fetch_dataset():
    """Return list of dicts from resume_data_cvc, or [] if unavailable.

    The fields are renamed to the generic names used by the rest of the
    analyzer (job_position, required_skills, resume_skills, ...).
    """
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT job_position_name      AS job_position,
                   skills_required        AS required_skills,
                   skills                 AS resume_skills,
                   degree_names           AS degree,
                   experience_requirement AS experience,
                   certification_providers AS certifications,
                   professional_company_names AS company_names,
                   responsibilities,
                   responsibilities_1,
                   languages,
                   matched_score
            FROM resume_data_cvc
            WHERE job_position_name IS NOT NULL AND job_position_name <> ''
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print("[DB] fetch_dataset error:", e)
        return []


def import_csv_to_mysql(csv_path: str) -> int:
    """Bulk import resume_data_cvc.csv into MySQL.

    Handles:
      * UTF-8 BOM on the first column (ï»¿job_position_name)
      * "responsibilities.1" duplicate column → responsibilities_1
      * "educationaL_requirements" typo  → educational_requirements
      * "experiencere_requirement" typo → experience_requirement
    Returns number of rows inserted.
    """
    import pandas as pd

    df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    # Normalize headers
    rename = {}
    for c in df.columns:
        key = c.strip().lstrip("\ufeff").lower().replace(" ", "_").replace(".", "_")
        # Fix known typos so they line up with the DB schema
        if key == "educational_requirements":         key = "educational_requirements"
        if key == "educationaL_requirements".lower(): key = "educational_requirements"
        if key == "experiencere_requirement":         key = "experience_requirement"
        rename[c] = key
    df = df.rename(columns=rename)

    # Make sure every expected column exists
    for col in CVC_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    conn = get_db(); cur = conn.cursor()
    cur.execute("TRUNCATE TABLE resume_data_cvc")
    placeholders = ",".join(["%s"] * len(CVC_COLUMNS))
    sql = f"INSERT INTO resume_data_cvc ({','.join(CVC_COLUMNS)}) VALUES ({placeholders})"

    inserted = 0
    batch = []
    for _, row in df.iterrows():
        values = []
        for col in CVC_COLUMNS:
            v = row.get(col, "")
            if col == "matched_score":
                try:
                    v = float(v) if str(v).strip() not in ("", "nan", "None") else 0.0
                except Exception:
                    v = 0.0
            else:
                v = "" if v is None else str(v)
            values.append(v)
        batch.append(tuple(values))
        if len(batch) >= 500:
            cur.executemany(sql, batch); inserted += len(batch); batch = []
    if batch:
        cur.executemany(sql, batch); inserted += len(batch)

    conn.commit(); cur.close(); conn.close()
    print(f"[DB] Imported {inserted} rows into resume_data_cvc.")
    return inserted


# ---------- Similarity ----------
def tfidf_cosine(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    try:
        v = TfidfVectorizer(stop_words="english")
        m = v.fit_transform([a, b])
        return float(cosine_similarity(m[0:1], m[1:2])[0][0])
    except Exception:
        return 0.0


# ---------- ATS (rule-based) ----------
def ats_score(text: str, parsed: dict) -> dict:
    checks = {}
    words = len(text.split())
    checks["length_ok"] = 250 <= words <= 1200
    checks["has_email"] = parsed.get("email") not in ("", "Not Found")
    checks["has_phone"] = parsed.get("phone") not in ("", "Not Found")
    checks["has_linkedin"] = bool(parsed.get("linkedin"))
    checks["has_sections"] = len(parsed.get("sections_present", [])) >= 4
    checks["has_bullets"] = bool(re.search(r"(^|\n)\s*[•\-\*]\s+", text))
    checks["has_skills_section"] = bool(parsed.get("technical_skills"))
    checks["has_education"] = bool(parsed.get("education", {}).get("degrees"))
    checks["has_experience"] = parsed.get("experience_years", 0) > 0 or bool(parsed.get("companies"))
    checks["has_projects"] = bool(parsed.get("projects"))
    score = round(100 * sum(1 for v in checks.values() if v) / len(checks))
    return {"score": score, "checks": checks}


# ---------- Completeness ----------
def completeness(parsed: dict) -> int:
    required = ["summary","skills","education","experience","projects","certifications","achievements","languages"]
    present = set(parsed.get("sections_present", []))
    present |= {"skills"} if parsed.get("technical_skills") else set()
    present |= {"education"} if parsed.get("education", {}).get("degrees") else set()
    present |= {"experience"} if parsed.get("companies") or parsed.get("experience_years") else set()
    present |= {"projects"} if parsed.get("projects") else set()
    present |= {"certifications"} if parsed.get("certifications") else set()
    present |= {"languages"} if parsed.get("languages") else set()
    hits = sum(1 for r in required if r in present)
    return round(100 * hits / len(required))


# ---------- Skill match ----------
_STOP = set("""a an the and or for with to of in on at by from as is are be been being
this that these those you your we our it its their they them i me my using use used
work works role roles year years experience experiences strong good excellent ability
required must should will can may also etc including including: knowledge familiar
familiarity hands-on hands handson plus minimum responsible responsibilities team
""".split())


def _tokens_from_jd(jd_text: str):
    """Extract skill-like tokens from a JD: SKILL_BANK hits + comma/bullet
    lists + capitalized tech tokens. Falls back to any 2-25 char tokens
    that aren't stopwords.
    """
    if not jd_text:
        return []
    low = jd_text.lower()

    # 1. SKILL_BANK exact hits (multi-word + single)
    found = set()
    for s in SKILL_BANK:
        if re.search(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])", low):
            found.add(s.lower())

    # 2. comma / bullet / pipe / slash separated tokens after the words
    #    "skills", "requirements", "technologies", "stack"
    list_re = re.compile(
        r"(?:skills?|requirements?|tech(?:nologies)?|stack|tools?|languages?)"
        r"\s*[:\-]\s*([^\n\r]{2,400})",
        re.I,
    )
    for m in list_re.finditer(jd_text):
        parts = re.split(r"[,/|;\u2022\u2023\u25E6\u2043\u00B7]+|\band\b", m.group(1))
        for part in parts:
            t = part.strip(" .;-\t()[]").lower()
            if 2 <= len(t) <= 30 and t not in _STOP and not t.isdigit():
                found.add(t)

    # 3. Tokens immediately following a bullet/dash line
    for line in jd_text.splitlines():
        s = line.strip("\t -*\u2022\u00B7")
        if 2 <= len(s) <= 60 and ":" not in s and any(c.isalpha() for c in s):
            # only short bullet lines
            if len(s.split()) <= 4:
                t = s.lower().strip(" .;-")
                if t not in _STOP:
                    found.add(t)

    # 4. fallback: alphabetic tokens 3-20 chars, not stopwords; cap 30
    if len(found) < 3:
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9+.#\-]{1,24}", jd_text):
            t = tok.lower()
            if t in _STOP or len(t) < 3 or t.isdigit():
                continue
            found.add(t)
            if len(found) > 40:
                break

    return sorted(found)


def skill_match(resume_skills, jd_text: str):
    resume_set = {s.lower() for s in resume_skills}
    jd_skills = _tokens_from_jd(jd_text)
    jd_set = set(jd_skills)

    # match resume skill against any jd token that contains it or vice-versa
    matched = set()
    for r in resume_set:
        for j in jd_set:
            if r == j or (len(r) >= 3 and (r in j or j in r)):
                matched.add(j)
                break
    missing = jd_set - matched
    pct = round(100 * len(matched) / len(jd_set)) if jd_set else 0
    return {
        "matched": sorted(matched),
        "missing": sorted(missing)[:25],
        "percent": pct,
        "jd_skills": jd_skills[:40],
    }


# ---------- Career recommendations from dataset ----------
def recommend_careers(resume_skills, top_k=6):
    rows = fetch_dataset()
    if not rows:
        # graceful fallback
        return [
            {"job_position": j, "score": 0} for j in
            ["Software Engineer","Python Developer","Data Scientist","AI Engineer",
             "Machine Learning Engineer","Backend Developer","Full Stack Developer"]
        ]
    resume_text = ", ".join(resume_skills)
    scored = []
    for r in rows:
        req = (r.get("required_skills") or "") + " " + (r.get("resume_skills") or "")
        sim = tfidf_cosine(resume_text, req)
        scored.append({"job_position": r.get("job_position") or "Role",
                       "score": round(sim * 100)})
    # pick best per job position
    best = {}
    for s in scored:
        jp = s["job_position"]
        if jp not in best or s["score"] > best[jp]["score"]:
            best[jp] = s
    out = sorted(best.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    return out


# ---------- Final composite score ----------
def resume_score(parsed: dict, jd_text: str):
    sk = skill_match(parsed["technical_skills"], jd_text)
    ats = ats_score(parsed["raw_text"], parsed)

    # sub-scores 0-100
    skills_s = sk["percent"] if jd_text else min(100, len(parsed["technical_skills"]) * 8)
    exp_years = parsed.get("experience_years", 0)
    exp_s = min(100, exp_years * 20) if exp_years else (60 if parsed.get("companies") else 0)
    proj_s = min(100, len(parsed.get("projects", [])) * 20)
    edu_s = 80 if parsed.get("education", {}).get("degrees") else 0
    cert_s = min(100, len(parsed.get("certifications", [])) * 25)
    ats_s = ats["score"]

    overall = round(
        skills_s * 0.40 +
        exp_s    * 0.20 +
        proj_s   * 0.15 +
        edu_s    * 0.10 +
        cert_s   * 0.05 +
        ats_s    * 0.10
    )
    return {
        "overall": overall,
        "breakdown": {
            "Skills (40%)": skills_s,
            "Experience (20%)": exp_s,
            "Projects (15%)": proj_s,
            "Education (10%)": edu_s,
            "Certifications (5%)": cert_s,
            "ATS (10%)": ats_s,
        },
        "ats": ats,
        "skill_match": sk,
    }


# ---------- Strengths / weaknesses / suggestions ----------
def strengths_and_gaps(parsed: dict, score: dict):
    """Generate content-specific strengths, weaknesses and suggestions.

    These vary per resume because they cite concrete details: actual
    skill names, project count, named companies, certifications,
    degrees, missing JD skills, and which ATS checks failed.
    """
    strengths, weaknesses, suggestions = [], [], []
    b = score["breakdown"]
    tech = parsed.get("technical_skills", []) or []
    soft = parsed.get("soft_skills", []) or []
    projects = parsed.get("projects", []) or []
    certs = parsed.get("certifications", []) or []
    companies = parsed.get("companies", []) or []
    edu = parsed.get("education", {}) or {}
    degrees = edu.get("degrees", []) or []
    unis = edu.get("universities", []) or []
    grad_year = edu.get("graduation_year", "")
    langs = parsed.get("languages", []) or []
    exp_years = parsed.get("experience_years", 0) or 0
    sm = score.get("skill_match", {}) or {}
    matched = sm.get("matched", []) or []
    missing = sm.get("missing", []) or []
    ats_checks = (score.get("ats", {}) or {}).get("checks", {}) or {}

    # ----- Strengths (cite real values) -----
    if len(tech) >= 8:
        strengths.append(
            f"Broad technical stack ({len(tech)} skills) including "
            + ", ".join(tech[:5]) + ("..." if len(tech) > 5 else "")
        )
    elif tech:
        strengths.append("Core skills detected: " + ", ".join(tech[:5]))

    if exp_years >= 3:
        strengths.append(f"Around {exp_years:g} years of work experience")
    elif companies:
        strengths.append(
            f"Industry exposure at {len(companies)} organisation"
            + ("s" if len(companies) > 1 else "")
            + ": " + ", ".join(companies[:3])
        )

    if len(projects) >= 3:
        strengths.append(f"{len(projects)} projects showcased in the resume")
    elif projects:
        strengths.append(f"Project work demonstrated: '{projects[0][:60]}'")

    if degrees:
        strengths.append(
            "Qualification: " + ", ".join(degrees[:2])
            + (f" ({grad_year})" if grad_year else "")
        )

    if certs:
        strengths.append(
            f"{len(certs)} certification(s) listed"
            + (f", e.g. '{certs[0][:50]}'" if certs else "")
        )

    if len(matched) >= 3:
        strengths.append(
            f"Matches {len(matched)} JD skills: " + ", ".join(matched[:5])
        )

    if soft:
        strengths.append("Soft skills present: " + ", ".join(soft[:4]))

    if parsed.get("linkedin") and parsed.get("github"):
        strengths.append("Has both LinkedIn and GitHub profiles")

    if len(langs) >= 2:
        strengths.append("Multilingual: " + ", ".join(langs))

    # ----- Weaknesses (cite missing specifics) -----
    if len(tech) < 5:
        weaknesses.append(
            f"Only {len(tech)} technical skill(s) detected"
            + (" - resume looks light on tech keywords" if len(tech) < 3 else "")
        )
    if exp_years == 0 and not companies:
        weaknesses.append("No work experience or company names found")
    elif exp_years == 0 and companies:
        weaknesses.append(
            f"Companies listed ({', '.join(companies[:2])}) but no clear duration / years"
        )

    if not projects:
        weaknesses.append("No project section detected")
    elif len(projects) < 2:
        weaknesses.append("Only one project listed - portfolio feels thin")

    if not degrees:
        weaknesses.append("Education / degree not detected")
    elif not grad_year:
        weaknesses.append("Graduation year missing from education section")
    if not unis and degrees:
        weaknesses.append("University / institution name not found")

    if not certs:
        weaknesses.append("No certifications listed")

    if missing:
        weaknesses.append(
            f"Missing {len(missing)} JD skill(s): " + ", ".join(missing[:6])
        )

    if parsed.get("email") in ("", "Not Found"):
        weaknesses.append("Email address not detected")
    if parsed.get("phone") in ("", "Not Found"):
        weaknesses.append("Phone number not detected")
    if not parsed.get("linkedin"):
        weaknesses.append("LinkedIn profile not listed")
    if not parsed.get("github") and any("python" in t or "java" in t or "developer" in t for t in tech):
        weaknesses.append("GitHub profile missing for a developer resume")
    if not soft:
        weaknesses.append("No soft skills mentioned (communication, teamwork, ...)")

    # ATS specifics
    if ats_checks:
        if ats_checks.get("length_ok") is False:
            weaknesses.append("Resume length is outside the recommended 250-1200 words")
        if ats_checks.get("has_bullets") is False:
            weaknesses.append("Bullet points not used - hurts ATS parsing")
        if ats_checks.get("has_sections") is False:
            weaknesses.append("Standard section headings not detected")

    # ----- Suggestions (actionable, tied to the gaps above) -----
    for ms in missing[:6]:
        suggestions.append(f"Learn / mention '{ms}' - it's required by the JD")

    if exp_years == 0 and not companies:
        suggestions.append("Add an internship, freelance gig or open-source contribution")
    elif exp_years == 0:
        suggestions.append("Add start - end dates next to each role so experience can be measured")

    if len(projects) < 3:
        suggestions.append(
            f"Add {3 - len(projects)} more project(s) with tech stack, your role and measurable impact"
        )

    if not certs:
        suggestions.append(
            "Add a relevant certification (e.g. AWS Cloud Practitioner, Google Data Analytics, Coursera ML)"
        )
    elif len(certs) < 3:
        suggestions.append("Add 1-2 more domain-specific certifications to strengthen credibility")

    if not parsed.get("linkedin"):
        suggestions.append("Add your LinkedIn profile URL near the contact details")
    if not parsed.get("github") and any(t in ("python","java","javascript","react","node.js") for t in tech):
        suggestions.append("Add your GitHub URL to showcase code")
    if not grad_year and degrees:
        suggestions.append("Mention the graduation year alongside your degree")
    if not unis and degrees:
        suggestions.append("Include the name of your university / college")
    if not soft:
        suggestions.append("Sprinkle in soft skills like communication, teamwork and problem solving")
    if len(tech) < 5:
        suggestions.append("Expand the Skills section - list languages, frameworks, databases and tools separately")
    if ats_checks.get("has_bullets") is False:
        suggestions.append("Format achievements as bullet points starting with action verbs")
    if ats_checks.get("length_ok") is False:
        suggestions.append("Aim for a 1-2 page resume (~400-900 words)")
    if exp_years and exp_years < 1 and projects:
        suggestions.append("Quantify project impact (users, %, time saved) since experience is limited")

    # de-duplicate while preserving order
    def _dedup(seq):
        seen = set(); out = []
        for x in seq:
            if x not in seen:
                seen.add(x); out.append(x)
        return out
    return _dedup(strengths), _dedup(weaknesses), _dedup(suggestions)


def analyze(parsed: dict, jd_text: str) -> dict:
    score = resume_score(parsed, jd_text)
    job_match_pct = round(tfidf_cosine(parsed["raw_text"], jd_text) * 100) if jd_text else 0
    strengths, weaknesses, suggestions = strengths_and_gaps(parsed, score)
    return {
        "parsed": parsed,
        "score": score,
        "completeness": completeness(parsed),
        "job_match_percent": job_match_pct,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "careers": recommend_careers(parsed["technical_skills"]),
    }
