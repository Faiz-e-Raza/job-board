"""
Job Aggregator v6 - splits location into `location_country` and
`location_area` (city/state/sub-region where available) so the site can
offer a country dropdown, then an area dropdown filtered by that country.
"""

import json
import re
import time
from datetime import datetime, timezone

import requests

ENTRY_KEYWORDS = [
    "junior", "jr.", "jr ", "entry level", "entry-level", "graduate",
    "new grad", "trainee", "intern", "0-2 years", "1-2 years",
]
SENIOR_KEYWORDS = [
    "senior", "sr.", "sr ", "lead", "staff", "principal", "director",
    "head of", "vp ", "vice president", "chief", "expert", "architect",
    "5+ years", "7+ years", "10+ years",
]

CATEGORY_RULES = [
    ("Accounting & Finance", ["accountant", "accounting", "bookkeep", "finance", "financial analyst",
                               "tax ", "audit", "payroll", "controller", "cfo"]),
    ("Marketing", ["marketing", "seo", "sem", "content strategist", "growth", "brand", "social media",
                   "email marketing", "ppc", "campaign"]),
    ("Sales", ["sales", "account executive", "business development", "bdr", "sdr", "account manager",
               "renewal", "partner "]),
    ("Design", ["designer", "ux", "ui ", "graphic design", "product design", "figma"]),
    ("Customer Support", ["customer support", "customer success", "support specialist", "help desk",
                           "customer service", "onboarding"]),
    ("Human Resources", ["hr ", "human resources", "recruiter", "recruiting", "talent acquisition",
                          "people ops"]),
    ("Writing & Content", ["writer", "copywriter", "content writer", "editor", "journalist",
                            "technical writer"]),
    ("Operations", ["operations", "project manager", "program manager", "product manager", "ops manager"]),
    ("Technology", ["engineer", "developer", "programmer", "software", "backend", "frontend",
                     "full stack", "devops", "data scientist", "data engineer", "qa ", "sre",
                     "machine learning", "cybersecurity", "cloud", "systems admin"]),
]

REGION_LABELS = ["EMEA", "APAC", "LATAM", "Anywhere", "Remote", "Europe", "Worldwide"]

COUNTRIES = [
    "United States", "USA", "US", "Canada", "United Kingdom", "UK", "Germany", "France",
    "Spain", "Italy", "Portugal", "Netherlands", "Belgium", "Switzerland", "Austria",
    "Ireland", "Sweden", "Norway", "Denmark", "Finland", "Poland", "Romania", "Ukraine",
    "Australia", "New Zealand", "India", "Pakistan", "China", "Japan", "South Korea",
    "Singapore", "Philippines", "Vietnam", "Thailand", "Indonesia", "Malaysia",
    "Hong Kong", "UAE", "United Arab Emirates", "Israel", "Saudi Arabia", "Mexico",
    "Brazil", "Argentina", "Chile", "Colombia", "South Africa", "Nigeria", "Egypt",
    "Turkey", "Greece", "Czech Republic", "Hungary", "Bulgaria",
]

CITY_TO_COUNTRY = {
    "berlin": "Germany", "munich": "Germany", "münster": "Germany", "hamburg": "Germany",
    "cologne": "Germany", "usingen": "Germany", "frankfurt": "Germany",
    "london": "United Kingdom", "bristol": "United Kingdom", "luton": "United Kingdom",
    "manchester": "United Kingdom", "birmingham": "United Kingdom",
    "toronto": "Canada", "vancouver": "Canada", "montreal": "Canada",
    "los angeles": "United States", "new york": "United States", "chicago": "United States",
    "san francisco": "United States", "austin": "United States", "seattle": "United States",
    "paris": "France", "madrid": "Spain", "barcelona": "Spain", "rome": "Italy",
    "milan": "Italy", "amsterdam": "Netherlands", "dublin": "Ireland",
    "sydney": "Australia", "melbourne": "Australia", "gold coast": "Australia",
    "queensland": "Australia", "gurgaon": "India", "bengaluru": "India", "bangalore": "India",
}

HEADERS = {"User-Agent": "job-aggregator-bot/1.0 (personal project)"}


def normalize_location(raw_location: str):
    """Returns (country, area). area is city/state/sub-region where the
    data actually contains one; otherwise 'Not specified'."""
    if not raw_location:
        return "Not specified", "Not specified"

    text = raw_location.strip().strip(",").strip()
    if not text:
        return "Not specified", "Not specified"

    for region in REGION_LABELS:
        if region.lower() in text.lower():
            return region, "Not specified"

    parts = [p.strip() for p in text.split(",") if p.strip()]

    # Try to find a country among the comma-separated parts.
    country_found = None
    remaining_parts = []
    for part in parts:
        matched = False
        for country in COUNTRIES:
            if re.fullmatch(re.escape(country), part, re.IGNORECASE):
                country_found = "United States" if country in ("USA", "US") else (
                    "United Kingdom" if country == "UK" else country
                )
                matched = True
                break
        if not matched:
            remaining_parts.append(part)

    if country_found:
        # Dedupe remaining parts, keep first as the area.
        seen = set()
        unique_remaining = []
        for p in remaining_parts:
            if p.lower() not in seen:
                seen.add(p.lower())
                unique_remaining.append(p)
        area = unique_remaining[0] if unique_remaining else "Not specified"
        return country_found, area

    # No explicit country - try matching a known city.
    for part in parts:
        key = part.lower()
        if key in CITY_TO_COUNTRY:
            return CITY_TO_COUNTRY[key], part

    return "Other / Unspecified", (parts[0] if parts else "Not specified")


def is_entry_level(title: str, description: str = "") -> bool:
    text = f"{title} {description}".lower()
    return any(kw in text for kw in ENTRY_KEYWORDS)


def classify_experience(title: str) -> str:
    t = title.lower()
    if any(kw in t for kw in SENIOR_KEYWORDS):
        return "Senior"
    if any(kw in t for kw in ENTRY_KEYWORDS):
        return "Entry"
    return "Mid"


def classify_category(title: str, tags: list) -> str:
    text = f"{title} {' '.join(tags)}".lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def build_job(source, title, company, url, tags, location, salary_min, salary_max, currency, date_posted):
    country, area = normalize_location(location)
    return {
        "source": source,
        "title": title,
        "company": company,
        "url": url,
        "tags": tags,
        "category": classify_category(title, tags),
        "experience_level": classify_experience(title),
        "location_country": country,
        "location_area": area,
        "remote": True,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "currency": currency,
        "date_posted": date_posted,
    }


def fetch_remoteok():
    jobs = []
    try:
        resp = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        for item in resp.json()[1:]:
            title = item.get("position", "")
            if not title:
                continue
            tags = item.get("tags", []) or []
            jobs.append(build_job(
                "RemoteOK", title, item.get("company", "Unknown"),
                item.get("url") or f"https://remoteok.com/l/{item.get('id','')}",
                tags, item.get("location"),
                item.get("salary_min") or None, item.get("salary_max") or None,
                "USD" if (item.get("salary_min") or item.get("salary_max")) else None,
                item.get("date", ""),
            ))
    except Exception as e:
        print(f"[warn] RemoteOK fetch failed: {e}")
    return jobs


def fetch_arbeitnow():
    jobs = []
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        for item in resp.json().get("data", []):
            title = item.get("title", "")
            if not title or not item.get("remote", False):
                continue
            tags = item.get("tags", []) or []
            date_posted = datetime.fromtimestamp(
                item.get("created_at", time.time()), tz=timezone.utc
            ).strftime("%Y-%m-%d") if item.get("created_at") else ""
            jobs.append(build_job(
                "Arbeitnow", title, item.get("company_name", "Unknown"), item.get("url", ""),
                tags, item.get("location"), None, None, None, date_posted,
            ))
    except Exception as e:
        print(f"[warn] Arbeitnow fetch failed: {e}")
    return jobs


def fetch_jobicy():
    jobs = []
    try:
        resp = requests.get("https://jobicy.com/api/v2/remote-jobs?count=100", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        for item in resp.json().get("jobs", []):
            title = item.get("jobTitle", "")
            if not title:
                continue
            tags = []
            if item.get("jobIndustry"):
                tags.extend(item["jobIndustry"])
            if item.get("jobType"):
                tags.extend(item["jobType"])
            jobs.append(build_job(
                "Jobicy", title, item.get("companyName", "Unknown"), item.get("url", ""),
                tags, item.get("jobGeo"),
                item.get("annualSalaryMin") or None, item.get("annualSalaryMax") or None,
                item.get("salaryCurrency") or None,
                item.get("pubDate", "")[:10] if item.get("pubDate") else "",
            ))
    except Exception as e:
        print(f"[warn] Jobicy fetch failed: {e}")
    return jobs


def dedupe(jobs):
    seen = set()
    unique = []
    for j in jobs:
        key = (j["title"].strip().lower(), j["company"].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)
    return unique


def main():
    all_jobs = []
    all_jobs.extend(fetch_remoteok())
    all_jobs.extend(fetch_arbeitnow())
    all_jobs.extend(fetch_jobicy())
    all_jobs = dedupe(all_jobs)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_jobs),
        "jobs": all_jobs,
    }

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(all_jobs)} jobs to jobs.json")


if __name__ == "__main__":
    main()
