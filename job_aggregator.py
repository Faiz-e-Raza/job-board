"""
Job Aggregator v4 - adds category classification and experience-level
inference on top of v3. Both are keyword-based best-effort guesses since
the source APIs don't provide these fields natively - labeled as such
on the site.
"""

import json
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
    ("Sales", ["sales", "account executive", "business development", "bdr", "sdr", "account manager"]),
    ("Design", ["designer", "ux", "ui ", "graphic design", "product design", "figma"]),
    ("Customer Support", ["customer support", "customer success", "support specialist", "help desk",
                           "customer service"]),
    ("Human Resources", ["hr ", "human resources", "recruiter", "recruiting", "talent acquisition",
                          "people ops"]),
    ("Writing & Content", ["writer", "copywriter", "content writer", "editor", "journalist",
                            "technical writer"]),
    ("Operations", ["operations", "project manager", "program manager", "product manager", "ops manager"]),
    ("Technology", ["engineer", "developer", "programmer", "software", "backend", "frontend",
                     "full stack", "devops", "data scientist", "data engineer", "qa ", "sre",
                     "machine learning", "cybersecurity", "cloud", "systems admin"]),
]

HEADERS = {"User-Agent": "job-aggregator-bot/1.0 (personal project)"}


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
    return {
        "source": source,
        "title": title,
        "company": company,
        "url": url,
        "tags": tags,
        "category": classify_category(title, tags),
        "experience_level": classify_experience(title),
        "location": location or "Remote",
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
