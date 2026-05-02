def compare_skills(resume_skills, jd_skills):
    # Standardize all to lowercase for better matching
    resume_set = set(resume_skills)
    jd_set = set(jd_skills)
    
    matched = list(resume_set.intersection(jd_set))
    missing = list(jd_set - resume_set)
    
    return matched, missing

def calculate_score(matched_count, total_required):
    if total_required == 0:
        return 0
    return round((matched_count / total_required) * 100, 2)