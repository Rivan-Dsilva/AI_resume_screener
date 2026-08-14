"""Import the resume_data_cvc.csv dataset into MySQL.

Usage:
    python import_dataset.py                       # uses ./resume_data_cvc.csv
    python import_dataset.py path/to/dataset.csv

The CSV is expected to have the following columns (a leading BOM and
the duplicate "responsibilities.1" header from pandas are handled):

  address, career_objective, skills, educational_institution_name,
  degree_names, passing_years, educational_results, result_types,
  major_field_of_studies, professional_company_names, company_urls,
  start_dates, end_dates, related_skils_in_job, positions, locations,
  responsibilities, extra_curricular_activity_types,
  extra_curricular_organization_names, extra_curricular_organization_links,
  role_positions, languages, proficiency_levels, certification_providers,
  certification_skills, online_links, issue_dates, expiry_dates,
  job_position_name, educationaL_requirements, experiencere_requirement,
  age_requirement, responsibilities.1, skills_required, matched_score
"""
import os
import sys
from utils.analyzer import import_csv_to_mysql


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "resume_data_cvc.csv"
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV not found: {csv_path}")
        print("Place the file 'resume_data_cvc.csv' inside the resume_screening folder.")
        sys.exit(1)
    n = import_csv_to_mysql(csv_path)
    print(f"[OK] Imported {n} rows into resume_screening.resume_data_cvc")


if __name__ == "__main__":
    main()
