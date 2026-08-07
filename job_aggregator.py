"""
Job Aggregator v3 - pulls remote jobs from 3 free APIs and extracts
structured fields (location, category, salary, currency) for filtering.
"""

import json
import time
from datetime import datetime, timezone

import requests

ENTRY_LEVEL_KEYWORDS = [
    "junior", "jr.", "jr ", "entry level", "entry-level", "graduate",
    "new grad", "trainee", "intern", "associate", "no experience required",
    "0-2 years", "1-2 years",
]

HEADERS = {"User-Agent": "job-aggregator-bot/1.0 (personal project)"}


def is_entry_level(title: str, description: str = "") -> bool:
    text = f"{title} {description}".lower()
    return any(kw in text for kw in ENTRY_LEVEL_KEYWORDS)


def fetch_remoteok():
    jobs = []
    try:
        resp = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        for item in data[1:]:
            title = item.get("position", "")
            if not title:
                continue
            desc = item.get("description", "") or ""
            tags = item.get("tags", []) or []
            jobs.append({
                "source": "RemoteOK",
                "title": title,
                "company": item.get("company", "Unknown"),
                "url": item.get("url") or f"https://remoteok.com/l/{item.get('id','')}",
                "tags": tags,
                "category": tags[0] if tags else "General",
                "location": item.get("location") or "Remote",
                "salary_min": item.get("salary_min") or None,
                "salary_max": item.get("salary_max") or None,
                "currency": "USD" if (item.get("salary_min") or item.get("salary_max")) else None,
                "date_posted": item.get("date", ""),
                "is_entry_level": is_entry_level(title, desc),
            })
    except Exception as e:
        print(f"[warn] RemoteOK fetch failed: {e}")
    return jobs


def fetch_arbeitnow():
    jobs = []
    try:
        resp = requests.get(
            "https://www.arbeitnow.com/api/job-board-api", headers=HEADERS, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("data", []):
            title = item.get("title", "")
            if not title or not item.get("remote", False):
                continue
            desc = item.get("description", "") or ""
            tags = item.get("tags", []) or []
            jobs.append({
                "source": "Arbeitnow",
                "title": title,
                "company": item.get("company_name", "Unknown"),
                "url": item.get("url", ""),
                "tags": tags,
                "category": tags[0] if tags else "General",
                "location": item.get("location") or "Remote",
                "salary_min": None,
                "salary_max": None,
                "currency": None,
                "date_posted": datetime.fromtimestamp(
                    item.get("created_at", time.time()), tz=timezone.utc
                ).strftime("%Y-%m-%d") if item.get("created_at") else "",
                "is_entry_level": is_entry_level(title, desc),
            })
    except Exception as e:
        print(f"[warn] Arbeitnow fetch failed: {e}")
    return jobs


def fetch_jobicy():
    jobs = []
    try:
        resp = requests.get(
            "https://jobicy.com/api/v2/remote-jobs?count=100",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("jobs", []):
            title = item.get("jobTitle", "")
            if not title:
                continue
            desc = item.get("jobExcerpt", "") or ""
            tags = []
            if item.get("jobIndustry"):
                tags.extend(item["jobIndustry"])
            if item.get("jobType"):
                tags.extend(item["jobType"])
            jobs.append({
                "source": "Jobicy",
                "title": title,
                "company": item.get("companyName", "Unknown"),
                "url": item.get("url", ""),
                "tags": tags,
                "category": (item.get("jobIndustry") or ["General"])[0],
                "location": item.get("jobGeo") or "Remote",
                "salary_min": item.get("annualSalaryMin") or None,
                "salary_max": item.get("annualSalaryMax") or None,
                "currency": item.get("salaryCurrency") or None,
                "date_posted": item.get("pubDate", "")[:10] if item.get("pubDate") else "",
                "is_entry_level": is_entry_level(title, desc),
            })
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
