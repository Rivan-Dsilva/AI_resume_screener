-- AI Resume Screening & Analysis - MySQL schema
-- Matches the columns of the dataset file: resume_data_cvc.csv

CREATE DATABASE IF NOT EXISTS resume_screening
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE resume_screening;

DROP TABLE IF EXISTS resume_data_cvc;
CREATE TABLE resume_data_cvc (
  id                                   INT AUTO_INCREMENT PRIMARY KEY,

  -- ---------- Resume side ----------
  address                              TEXT,
  career_objective                     TEXT,
  skills                               TEXT,
  educational_institution_name         TEXT,
  degree_names                         TEXT,
  passing_years                        TEXT,
  educational_results                  TEXT,
  result_types                         TEXT,
  major_field_of_studies               TEXT,
  professional_company_names           TEXT,
  company_urls                         TEXT,
  start_dates                          TEXT,
  end_dates                            TEXT,
  related_skils_in_job                 TEXT,
  positions                            TEXT,
  locations                            TEXT,
  responsibilities                     TEXT,
  extra_curricular_activity_types      TEXT,
  extra_curricular_organization_names  TEXT,
  extra_curricular_organization_links  TEXT,
  role_positions                       TEXT,
  languages                            TEXT,
  proficiency_levels                   TEXT,
  certification_providers              TEXT,
  certification_skills                 TEXT,
  online_links                         TEXT,
  issue_dates                          TEXT,
  expiry_dates                         TEXT,

  -- ---------- Job side ----------
  job_position_name                    VARCHAR(255),
  educational_requirements             TEXT,
  experience_requirement               TEXT,
  age_requirement                      TEXT,
  responsibilities_1                   TEXT,
  skills_required                      TEXT,
  matched_score                        FLOAT DEFAULT 0,

  created_at                           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_job_position (job_position_name),
  INDEX idx_score (matched_score)
) ENGINE=InnoDB;

-- Minimal seed (works even before importing resume_data_cvc.csv)
INSERT INTO resume_data_cvc
(skills, degree_names, professional_company_names, responsibilities, languages,
 certification_providers, job_position_name, educational_requirements,
 experience_requirement, responsibilities_1, skills_required, matched_score) VALUES
('Python, Java, SQL, Git, REST API','B.Tech Computer Science','Infosys, TCS','Backend development, API design','English, Hindi','Oracle','Software Engineer','B.Tech / B.E. in CS or IT','1-3 years','Build and maintain backend services','Python, Java, SQL, Git, REST API, Data Structures',82),
('Python, Django, Flask, MySQL','B.Tech IT','Wipro','Django apps, REST APIs','English','Python Institute','Python Developer','B.Tech / B.Sc in CS or IT','1-2 years','Develop Django/Flask apps and APIs','Python, Django, Flask, SQL, REST API, Docker',78),
('Python, Pandas, NumPy, scikit-learn','M.Tech Data Science','Accenture','Model building, EDA','English','IBM','Data Scientist','M.Tech / M.Sc in DS / Stats','2-4 years','Build ML models, dashboards and reports','Python, Pandas, NumPy, scikit-learn, SQL, Statistics, ML',85),
('Python, TensorFlow, NLP','M.Tech AI','Nvidia','LLM fine-tuning, NLP pipelines','English','DeepLearning.AI','AI Engineer','M.Tech / M.S in AI / ML','2-4 years','Design and ship AI / NLP solutions','Python, TensorFlow, PyTorch, NLP, Deep Learning, MLOps',88),
('Python, scikit-learn, AWS','B.Tech CSE','Amazon','Model deployment, pipelines','English','AWS','Machine Learning Engineer','B.Tech / M.Tech CSE','2-4 years','Deploy ML models in production','Python, scikit-learn, TensorFlow, MLflow, AWS, Docker',84),
('Java, Spring, MySQL, Docker','B.E. CSE','Cognizant','Microservices, DB design','English','Oracle','Backend Developer','B.E. / B.Tech CSE','2-4 years','Build microservices and REST APIs','Java, Spring Boot, SQL, REST, Microservices, Docker, Kubernetes',80),
('React, Node, MongoDB, JS','B.Tech IT','Freelance','MERN apps, REST APIs','English','Meta','Full Stack Developer','B.Tech / B.Sc IT','1-3 years','Develop end-to-end MERN applications','HTML, CSS, JavaScript, React, Node.js, MongoDB, Express',81),
('HTML, CSS, JS, React','B.Sc CS','Startup','UI development, components','English','FreeCodeCamp','Frontend Developer','B.Sc / B.Tech CS','0-2 years','Build responsive UI components','HTML, CSS, JavaScript, React, TypeScript, Redux',74),
('Docker, AWS, Jenkins','B.Tech CSE','HCL','CI/CD pipelines, infra automation','English','AWS','DevOps Engineer','B.Tech CSE','2-4 years','Automate infra and deployments','Linux, Docker, Kubernetes, AWS, CI/CD, Jenkins, Terraform',83),
('SQL, Excel, Power BI','B.Com / B.Sc','Deloitte','Dashboards, SQL reports','English','Microsoft','Data Analyst','B.Com / B.Sc','0-2 years','Build dashboards and reports','SQL, Excel, Power BI, Tableau, Python, Statistics',76);
