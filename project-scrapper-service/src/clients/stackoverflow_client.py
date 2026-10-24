from datetime import datetime, timezone
from typing import Optional, List
from urllib.parse import urlparse
from dataclasses import dataclass
import re

from src.logger import get_logger
from src.clients.resilient_http_client import ResilientHttpClient

logger = get_logger()

http_client = ResilientHttpClient()


@dataclass
class StackOverflowUpdate:
    """Информация об обновлении StackOverflow (ответ или комментарий)."""

    question_id: int
    question_title: str
    answer_id: int
    author: str
    created_at: datetime
    preview: str
    url: str

    def __str__(self) -> str:
        return (
            f"Answer #{self.answer_id} to Q#{self.question_id}: {self.question_title}"
        )


def parse_stackoverflow_url(url: str) -> int | None:
    """Извлекает ID вопроса из StackOverflow URL."""
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ("stackoverflow.com", "www.stackoverflow.com"):
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "questions":
            return int(parts[1])
        return None
    except (ValueError, IndexError) as e:
        logger.warning("parse_so_url_error", url=url, error=str(e))
        return None


def _strip_html_tags(html: str) -> str:
    """Удаляет HTML-теги из строки."""
    clean = re.compile("<.*?>")
    text = re.sub(clean, "", html)
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")
    return text


def _truncate_text(text: str | None, max_length: int = 200) -> str:
    """Обрезает текст до указанной длины."""
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


async def get_question_last_activity(question_id: int) -> datetime | None:
    """Получает время последней активности вопроса."""
    url = f"https://api.stackexchange.com/2.3/questions/{question_id}"
    params = {
        "order": "desc",
        "sort": "activity",
        "site": "stackoverflow",
    }
    logger.debug("so_api_request", url=url, question_id=question_id, params=params)

    try:
        response = await http_client.get(url, params=params)
        logger.debug(
            "so_api_response",
            status=response.status_code,
            content_preview=response.text[:200] if response.content else "empty",
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items and len(items) > 0:
                last_activity = items[0].get("last_activity_date")
                if last_activity:
                    result = datetime.fromtimestamp(last_activity, tz=timezone.utc)
                    logger.debug(
                        "so_api_success", question_id=question_id, last_activity=result
                    )
                    return result
                else:
                    logger.warning(
                        "so_field_not_found",
                        question_id=question_id,
                        available_fields=list(items[0].keys()),
                    )
        elif response.status_code == 404:
            logger.warning("so_question_not_found", question_id=question_id)
        elif response.status_code == 429:
            logger.warning("so_rate_limited", question_id=question_id)
        else:
            logger.error(
                "so_api_error",
                status=response.status_code,
                question_id=question_id,
                response_text=response.text[:200],
            )
        return None
    except Exception as e:
        logger.error("so_request_error", url=url, error=str(e))
        return None


async def get_question_title(question_id: int) -> str | None:
    """Получает заголовок вопроса."""
    url = f"https://api.stackexchange.com/2.3/questions/{question_id}"
    params = {
        "order": "desc",
        "sort": "activity",
        "site": "stackoverflow",
    }
    logger.debug("so_title_request", question_id=question_id)

    try:
        response = await http_client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            if items:
                title = items[0].get("title", "")
                logger.debug(
                    "so_title_fetched", question_id=question_id, title=title[:50]
                )
                return title
        logger.warning("so_title_not_found", question_id=question_id)
        return None
    except Exception as e:
        logger.error("so_title_error", question_id=question_id, error=str(e))
        return None


async def get_question_answers(
    question_id: int,
    since: Optional[datetime] = None,
    per_page: int = 30,
) -> List[StackOverflowUpdate]:
    """Получает новые ответы на вопрос."""
    question_title = await get_question_title(question_id)
    if not question_title:
        logger.warning("so_cannot_get_title", question_id=question_id)
        question_title = f"Question #{question_id}"

    url = f"https://api.stackexchange.com/2.3/questions/{question_id}/answers"
    params = {
        "order": "desc",
        "sort": "activity",
        "site": "stackoverflow",
        "filter": "withbody",
        "per_page": per_page,
    }
    if since:
        params["fromdate"] = int(since.timestamp())

    logger.debug(
        "so_answers_request",
        question_id=question_id,
        since=since.isoformat() if since else None,
        per_page=per_page,
    )

    try:
        response = await http_client.get(url, params=params)
        if response.status_code == 404:
            logger.warning("so_question_not_found", question_id=question_id)
            return []
        elif response.status_code == 429:
            logger.warning("so_rate_limited", question_id=question_id)
            return []
        elif response.status_code != 200:
            logger.error(
                "so_answers_api_error",
                status=response.status_code,
                question_id=question_id,
                response_text=response.text[:200],
            )
            return []

        data = response.json()
        items = data.get("items", [])
        updates = []

        for item in items:
            try:
                answer_id = item.get("answer_id")
                owner = item.get("owner", {})
                author = owner.get("display_name", "Anonymous")
                creation_date_ts = item.get("creation_date")
                body_html = item.get("body", "")

                if not creation_date_ts:
                    logger.warning("so_missing_creation_date", answer_id=answer_id)
                    continue

                created_at = datetime.fromtimestamp(creation_date_ts, tz=timezone.utc)
                body_text = _strip_html_tags(body_html)
                preview = _truncate_text(body_text, max_length=200)
                answer_url = f"https://stackoverflow.com/a/{answer_id}"

                update = StackOverflowUpdate(
                    question_id=question_id,
                    question_title=question_title,
                    answer_id=answer_id,
                    author=author,
                    created_at=created_at,
                    preview=preview,
                    url=answer_url,
                )
                updates.append(update)
                logger.debug(
                    "so_answer_parsed",
                    answer_id=answer_id,
                    author=author,
                    preview_length=len(preview),
                )
            except Exception as e:
                logger.error("so_parse_item_error", item=item, error=str(e))
                continue

        logger.info(
            "so_answers_fetched",
            question_id=question_id,
            count=len(updates),
            since=since.isoformat() if since else None,
        )
        return updates
    except Exception as e:
        logger.error("so_unexpected_error", error=str(e), exc_info=True)
        return []


async def close_http_client():
    await http_client.close()
