# StatusMonkey Lead Finder

A Flask dashboard for finding and organizing Reddit posts that may relate to website uptime monitoring. It scans configured subreddits, scores posts using keyword matches, and stores matching leads in PostgreSQL.

## Features

- Scans configured subreddits for recent posts
- Scores posts based on uptime problems, monitoring tool requests, competitor mentions, and customer-profile keywords
- Assigns a lead priority and suggested response-template category
- Tracks lead details and status in a PostgreSQL database
- Provides dashboard and admin pages
- Supports optional Unsplash images for the dashboard background
- Includes Notion integration code

## How lead scoring works

The app checks post titles and text for keywords in several groups:

- Urgent downtime reports
- Requests for monitoring tools
- Complaints or comparisons involving monitoring services
- Potential customer-profile terms
- Budget-related terms

Matches contribute to a score used to assign a priority. The keyword lists and scoring logic are in `app.py`.

## Technology

- Python
- Flask
- PostgreSQL
- HTML, CSS, and JavaScript
- Notion API client
- Unsplash API

## Requirements

- Python 3
- PostgreSQL database
- API credentials for optional integrations you enable

## Setup

Clone the repository and move into its directory:

```bash
git clone https://github.com/git-nath/statusmonkey-lead-finder.git
cd statusmonkey-lead-finder
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project's dependencies:

```bash
pip install -r requirements.txt
```

Configure required environment variables in your local environment or deployment settings. The app needs a PostgreSQL connection string in `DATABASE_URL`. Optional integrations use `UNSPLASH_ACCESS_KEY` and Notion credentials. Keep credentials private and out of public documentation.

The database schema is defined in `schema.sql`. Database initialization is handled by the application's initialization flow.

Start the Flask development server:

```bash
flask --app app run
```

Open the local address printed by Flask in your browser.

## Configuration

### Database

The app uses PostgreSQL through `DATABASE_URL`. Table definitions are in `schema.sql`. If no subreddits are configured, the initialization code inserts a default set.

### Unsplash

The dashboard background-image endpoint uses `UNSPLASH_ACCESS_KEY`. The app can run without this integration; the endpoint reports that the key is not configured.

### Notion

The application includes a Notion client integration. Configure Notion credentials and a database before using features that send or store leads in Notion.

## Project structure

```text
.
├── app.py           # Flask routes, Reddit scanning, and lead scoring
├── db.py            # Database connection lifecycle
├── db_postgres.py   # PostgreSQL connection and initialization
├── schema.sql       # PostgreSQL table definitions
├── templates/       # Dashboard and admin pages
└── static/          # Stylesheets and front-end assets
```

## Notes

- Reddit scanning uses Reddit's public JSON endpoints.
- Scanning is limited to the newest posts fetched for each configured subreddit.
- Review each post's context and community rules before responding.
