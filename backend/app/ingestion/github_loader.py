"""
Scrape GitHub repos via the public API and create chunks for Pinecone.
For each repo: description, languages, README content.
"""

import time

import httpx

from app.config import settings

GITHUB_HEADERS = {"Accept": "application/vnd.github.v3+json"}
# Add a GitHub token if you have one (raises rate limit from 60 to 5000/hr)
if hasattr(settings, "github_token") and settings.github_token:
    GITHUB_HEADERS["Authorization"] = f"token {settings.github_token}"


def _github_get(url: str, headers: dict | None = None, **kwargs) -> httpx.Response:
    """GET with rate limit handling."""
    h = {**GITHUB_HEADERS, **(headers or {})}
    resp = httpx.get(url, headers=h, timeout=30, **kwargs)
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        reset_time = int(resp.headers.get("x-ratelimit-reset", 0))
        wait = max(reset_time - int(time.time()), 5)
        print(f"    Rate limited. Waiting {wait}s...")
        time.sleep(min(wait, 60))  # wait max 60s
        resp = httpx.get(url, headers=h, timeout=30, **kwargs)
    return resp


def _fetch_repos(username: str) -> list[dict]:
    """Fetch all public repos for a user."""
    repos = []
    page = 1
    while True:
        resp = _github_get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "page": page, "sort": "updated"},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def _fetch_readme(owner: str, repo_name: str) -> str:
    """Fetch the README content for a repo. Returns empty string if none."""
    try:
        resp = _github_get(
            f"https://api.github.com/repos/{owner}/{repo_name}/readme",
            headers={"Accept": "application/vnd.github.v3.raw"},
        )
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return ""


def _fetch_languages(owner: str, repo_name: str) -> dict:
    """Fetch languages used in a repo."""
    try:
        resp = _github_get(
            f"https://api.github.com/repos/{owner}/{repo_name}/languages",
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def load_github_repos() -> list[dict]:
    """
    Scrape all public repos and return chunks for Pinecone.
    Returns: [{"id": str, "text": str, "metadata": {"source": "github", ...}}]
    """
    username = settings.github_username
    print(f"  Fetching repos for {username}...")
    repos = _fetch_repos(username)

    # Filter: skip forks and empty repos
    repos = [r for r in repos if not r.get("fork") and r.get("size", 0) > 0]
    print(f"  Found {len(repos)} non-fork repos")

    chunks = []
    for repo in repos:
        name = repo["name"]
        description = repo.get("description") or "No description"
        topics = repo.get("topics", [])
        stars = repo.get("stargazers_count", 0)
        url = repo.get("html_url", "")

        # Fetch extra data
        languages = _fetch_languages(username, name)
        readme = _fetch_readme(username, name)

        # Chunk 1: Repo overview (always created)
        lang_str = ", ".join(languages.keys()) if languages else "Unknown"
        topic_str = ", ".join(topics) if topics else "None"
        overview = (
            f"Repository: {name}\n"
            f"URL: {url}\n"
            f"Description: {description}\n"
            f"Languages: {lang_str}\n"
            f"Topics: {topic_str}\n"
            f"Stars: {stars}"
        )
        chunks.append(
            {
                "id": f"github_{name}_overview",
                "text": overview,
                "metadata": {
                    "source": "github",
                    "repo_name": name,
                    "doc_type": "overview",
                },
            }
        )

        # Chunk 2+: README (if exists, may be multiple chunks)
        if readme:
            # Truncate very long READMEs to first 3000 chars
            readme_text = readme[:3000] if len(readme) > 3000 else readme
            chunks.append(
                {
                    "id": f"github_{name}_readme",
                    "text": f"README for {name}:\n\n{readme_text}",
                    "metadata": {
                        "source": "github",
                        "repo_name": name,
                        "doc_type": "readme",
                    },
                }
            )

        print(f"    {name}: overview + {'readme' if readme else 'no readme'}")

    print(f"  Total GitHub chunks: {len(chunks)}")
    return chunks
