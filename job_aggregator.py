"""
Job Aggregator - pulls entry-level/junior remote tech jobs from FREE public
job APIs (no scraping, no API keys needed) and outputs a clean jobs.json.

Data sources (both free, no auth required):
- RemoteOK: https://remoteok.com/api
- Arbeitnow: https://www.arbeitnow.com/api/job-board-api
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
            desc = item.get("description", "") or ""
            if not is_entry_level(title, desc):
                continue
            jobs.append({
                "source": "RemoteOK",
                "title": title,
                "company": item.get("company", "Unknown"),
                "url": item.get("url") or f"https://remoteok.com/l/{item.get('id','')}",
                "tags": item.get("tags", []),
                "date_posted": item.get("date", ""),
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
            desc = item.get("description", "") or ""
            if not item.get("remote", False):
                continue
            if not is_entry_level(title, desc):
                continue
            jobs.append({
                "source": "Arbeitnow",
                "title": title,
                "company": item.get("company_name", "Unknown"),
                "url": item.get("url", ""),
                "tags": item.get("tags", []),
                "date_posted": datetime.fromtimestamp(
                    item.get("created_at", time.time()), tz=timezone.utc
                ).strftime("%Y-%m-%d") if item.get("created_at") else "",
            })
    except Exception as e:
        print(f"[warn] Arbeitnow fetch failed: {e}")
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
    all_jobs = dedupe(all_jobs)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_jobs),
        "jobs": all_jobs,
    }

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(all_jobs)} entry-level remote jobs to jobs.json")


if __name__ == "__main__":
    main()
