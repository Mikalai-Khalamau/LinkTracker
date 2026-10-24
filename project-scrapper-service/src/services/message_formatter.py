from datetime import datetime, timezone, timedelta


def format_datetime(dt: datetime) -> str:
    """Форматирует datetime в читаемый вид."""
    if dt.tzinfo is not None:
        moscow_tz = timezone(timedelta(hours=3))
        dt = dt.astimezone(moscow_tz)

    return dt.strftime("%d.%m.%Y %H:%M")


def truncate_preview(text: str | None, max_length: int = 200) -> str:
    """Обрезает превью до указанной длины."""
    if not text:
        return ""

    text = " ".join(text.split())

    if len(text) <= max_length:
        return text

    return text[:max_length].rsplit(" ", 1)[0] + "..."


def format_github_issue_message(
    title: str,
    author: str,
    created_at: datetime,
    preview: str,
    url: str,
    issue_number: int,
) -> str:
    """Форматирует сообщение для GitHub Issue."""
    formatted_time = format_datetime(created_at)
    preview_text = truncate_preview(preview, 200)

    message = (
        f"New Issue #{issue_number}: {title}\n"
        f"Author: {author}\n"
        f"Time: {formatted_time}\n"
    )

    if preview_text:
        message += f"\n{preview_text}\n"

    message += f"\nLink: {url}"

    return message


def format_github_pr_message(
    title: str,
    author: str,
    created_at: datetime,
    preview: str,
    url: str,
    pr_number: int,
) -> str:
    """Форматирует сообщение для GitHub Pull Request."""
    formatted_time = format_datetime(created_at)
    preview_text = truncate_preview(preview, 200)

    message = (
        f"New Pull Request #{pr_number}: {title}\n"
        f"Author: {author}\n"
        f"Time: {formatted_time}\n"
    )

    if preview_text:
        message += f"\n{preview_text}\n"

    message += f"\nLink: {url}"

    return message


def format_stackoverflow_answer_message(
    question_title: str,
    author: str,
    created_at: datetime,
    preview: str,
    url: str,
    answer_id: int,
) -> str:
    """Форматирует сообщение для StackOverflow ответа."""
    formatted_time = format_datetime(created_at)
    preview_text = truncate_preview(preview, 200)

    message = (
        f"New Answer #{answer_id}\n"
        f"Question: {question_title}\n"
        f"Author: {author}\n"
        f"Time: {formatted_time}\n"
    )

    if preview_text:
        message += f"\n{preview_text}\n"

    message += f"\nLink: {url}"

    return message


def format_update_message(update_type: str, **kwargs) -> str:
    """Универсальный форматировщик."""
    formatters = {
        "github_issue": format_github_issue_message,
        "github_pr": format_github_pr_message,
        "stackoverflow_answer": format_stackoverflow_answer_message,
    }

    formatter = formatters.get(update_type)
    if not formatter:
        return f"Unknown update type: {update_type}\nTitle: {kwargs.get('title', '')}"

    return formatter(**kwargs)
