from datetime import datetime
from typing import Optional, List
from urllib.parse import urlparse
from dataclasses import dataclass

from src.logger import get_logger
from src.clients.resilient_http_client import ResilientHttpClient

logger = get_logger()

http_client = ResilientHttpClient()


@dataclass
class GitHubUpdate:
    """Информация об обновлении GitHub (Issue или PR)."""

    issue_number: int
    title: str
    author: str
    created_at: datetime
    preview: str
    url: str
    is_pull_request: bool

    def __str__(self) -> str:
        type_str = "PR" if self.is_pull_request else "Issue"
        return f"{type_str} #{self.issue_number}: {self.title}"


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Извлекает owner/repo из GitHub URL."""
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ("github.com", "www.github.com"):
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None
    except Exception as e:
        logger.error("parse_github_url_error", url=url, error=str(e))
        return None


def _truncate_text(text: str | None, max_length: int = 200) -> str:
    """Обрезает текст до указанной длины."""
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


async def get_repo_last_update(
    owner: str, repo: str, token: Optional[str] = None
) -> datetime | None:
    """Получает время последнего обновления репозитория."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LinkTracker-Bot/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    logger.debug("github_api_request", url=url, owner=owner, repo=repo)

    try:
        response = await http_client.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            last_updated = data.get("pushed_at") or data.get("updated_at")
            if last_updated:
                result = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                logger.debug(
                    "github_api_success", owner=owner, repo=repo, last_updated=result
                )
                return result
        elif response.status_code == 404:
            logger.warning("github_repo_not_found", owner=owner, repo=repo)
        elif response.status_code == 429:
            logger.warning("github_rate_limited", owner=owner, repo=repo)
        else:
            logger.error(
                "github_api_error", status=response.status_code, owner=owner, repo=repo
            )
        return None
    except Exception as e:
        logger.error("github_request_error", url=url, error=str(e))
        return None


async def get_repo_issues_and_prs(
    owner: str,
    repo: str,
    since: Optional[datetime] = None,
    token: Optional[str] = None,
    per_page: int = 30,
) -> List[GitHubUpdate]:
    """Получает список новых Issues и PRs репозитория."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "LinkTracker-Bot/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "state": "all",
        "sort": "created",
        "direction": "desc",
        "per_page": per_page,
    }
    if since:
        params["since"] = since.isoformat()

    logger.debug(
        "github_issues_request",
        url=url,
        owner=owner,
        repo=repo,
        since=since.isoformat() if since else None,
        per_page=per_page,
    )

    try:
        response = await http_client.get(url, headers=headers, params=params)
        if response.status_code == 404:
            logger.warning("github_repo_not_found", owner=owner, repo=repo)
            return []
        elif response.status_code == 429:
            logger.warning("github_rate_limited", owner=owner, repo=repo)
            return []
        elif response.status_code != 200:
            logger.error(
                "github_issues_api_error",
                status=response.status_code,
                owner=owner,
                repo=repo,
                response_text=response.text[:200],
            )
            return []

        data = response.json()
        updates = []

        for item in data:
            try:
                is_pull_request = "pull_request" in item
                issue_number = item.get("number")
                title = item.get("title", "")
                author = item.get("user", {}).get("login", "unknown")
                created_at_str = item.get("created_at")
                body = item.get("body") or ""
                html_url = item.get("html_url", "")

                if not created_at_str:
                    logger.warning(
                        "github_missing_created_at", issue_number=issue_number
                    )
                    continue

                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
                preview = _truncate_text(body, max_length=200)

                update = GitHubUpdate(
                    issue_number=issue_number,
                    title=title,
                    author=author,
                    created_at=created_at,
                    preview=preview,
                    url=html_url,
                    is_pull_request=is_pull_request,
                )
                updates.append(update)
                logger.debug(
                    "github_update_parsed",
                    issue_number=issue_number,
                    is_pr=is_pull_request,
                    title=title[:50],
                )
            except Exception as e:
                logger.error("github_parse_item_error", item=item, error=str(e))
                continue

        logger.info(
            "github_issues_fetched",
            owner=owner,
            repo=repo,
            count=len(updates),
            since=since.isoformat() if since else None,
        )
        return updates
    except Exception as e:
        logger.error("github_unexpected_error", error=str(e), exc_info=True)
        return []


async def close_http_client():
    await http_client.close()
