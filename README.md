# Entry-Level Remote Tech Job Aggregator

Fully automated, $0 cost. Pulls entry-level/junior remote tech jobs daily from
free public APIs (RemoteOK, Arbeitnow), publishes them to a free website.

## Setup (10 minutes, one time)

1. Create a free GitHub account (done).
2. Create a repo (done).
3. Upload/create these files: job_aggregator.py, index.html, .github/workflows/scrape.yml, README.md
4. Enable GitHub Actions: Actions tab -> "I understand my workflows, go ahead and enable them."
5. Run it once manually: Actions tab -> "Update Job Listings" -> "Run workflow"
6. Enable GitHub Pages: Settings -> Pages -> Source: Deploy from a branch -> Branch: main, folder: / (root) -> Save
7. Site goes live at https://<your-username>.github.io/job-board/ and updates daily automatically.

## How this makes money

1. Get it in front of your niche - post the link in relevant subreddits (r/cscareerquestions, r/remotejs), Discord servers for bootcamp grads, LinkedIn.
2. Once you have steady visitors, apply for Google AdSense (free) and add the ad snippet to index.html.
3. Alternative: offer a paid weekly email digest via a free Mailchimp/Beehiiv tier, charge via Gumroad.
4. Later, once you have an audience, companies will pay you to post their job listings.

## Customizing your niche

Edit ENTRY_LEVEL_KEYWORDS in job_aggregator.py to target a different niche.
