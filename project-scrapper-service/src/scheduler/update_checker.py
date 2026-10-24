import asyncio
from typing import List, Optional
from urllib.parse import urlparse

from src.logger import get_logger
from src.config import settings
from src.repositories.base import LinkRepositoryProtocol
from src.models import LinkDomain
from src.clients.github_client import (
    parse_github_url,
    get_repo_issues_and_prs,
    GitHubUpdate,
)
from src.clients.stackoverflow_client import (
    parse_stackoverflow_url,
    get_question_answers,
    StackOverflowUpdate,
)
from src.services.message_sender import MessageSenderProtocol, UpdateMessage

logger = get_logger()


def classify_url(url: str) -> Optional[str]:
    """Определяет тип ссылки (github или stackoverflow)."""
    try:
        domain = urlparse(url).netloc
        if domain in ("github.com", "www.github.com"):
            return "github"
        elif domain in ("stackoverflow.com", "www.stackoverflow.com"):
            return "stackoverflow"
        return None
    except Exception:
        return None


async def process_github_link(
    link: LinkDomain,
    message_sender: MessageSenderProtocol,
    token: Optional[str] = None,
) -> List[GitHubUpdate]:
    """Обрабатывает GitHub ссылку: получает новые Issues и PRs."""
    parsed = parse_github_url(link.url)
    if not parsed:
        logger.warning("invalid_github_url", link_id=link.id, url=link.url)
        return []

    owner, repo = parsed

    since = link.last_checked or link.last_updated

    logger.info(
        "fetching_github_updates",
        link_id=link.id,
        owner=owner,
        repo=repo,
        since=since.isoformat() if since else None,
    )

    updates = await get_repo_issues_and_prs(
        owner=owner,
        repo=repo,
        since=since,
        token=token,
    )

    if not updates:
        logger.debug("no_github_updates", link_id=link.id)
        return []

    sent_count = 0
    for update in updates:
        try:
            update_type = "github_pr" if update.is_pull_request else "github_issue"

            message = UpdateMessage(
                update_type=update_type,
                source_url=update.url,
                title=update.title,
                author=update.author,
                created_at=update.created_at,
                preview=update.preview,
                chat_ids=[link.chat_id],
            )

            success = await message_sender.send_message(message)
            if success:
                sent_count += 1
                logger.info(
                    "github_update_sent",
                    link_id=link.id,
                    update_type=update_type,
                    number=update.issue_number,
                )
            else:
                logger.error(
                    "github_update_send_failed",
                    link_id=link.id,
                    update_type=update_type,
                    number=update.issue_number,
                )

        except Exception as e:
            logger.error(
                "github_update_processing_error",
                link_id=link.id,
                update_type=(
                    update.update_type if hasattr(update, "update_type") else "unknown"
                ),
                error=str(e),
                exc_info=True,
            )
            continue

    logger.info(
        "github_updates_processed",
        link_id=link.id,
        total=len(updates),
        sent=sent_count,
    )

    return updates


async def process_stackoverflow_link(
    link: LinkDomain,
    message_sender: MessageSenderProtocol,
) -> List[StackOverflowUpdate]:
    """Обрабатывает StackOverflow ссылку: получает новые ответы."""
    question_id = parse_stackoverflow_url(link.url)
    if not question_id:
        logger.warning("invalid_so_url", link_id=link.id, url=link.url)
        return []

    since = link.last_checked or link.last_updated

    logger.info(
        "fetching_so_updates",
        link_id=link.id,
        question_id=question_id,
        since=since.isoformat() if since else None,
    )

    updates = await get_question_answers(
        question_id=question_id,
        since=since,
    )

    if not updates:
        logger.debug("no_so_updates", link_id=link.id)
        return []

    sent_count = 0
    for update in updates:
        try:
            message = UpdateMessage(
                update_type="stackoverflow_answer",
                source_url=update.url,
                title=update.question_title,
                author=update.author,
                created_at=update.created_at,
                preview=update.preview,
                chat_ids=[link.chat_id],
            )

            success = await message_sender.send_message(message)
            if success:
                sent_count += 1
                logger.info(
                    "so_update_sent",
                    link_id=link.id,
                    answer_id=update.answer_id,
                )
            else:
                logger.error(
                    "so_update_send_failed",
                    link_id=link.id,
                    answer_id=update.answer_id,
                )

        except Exception as e:
            logger.error(
                "so_update_processing_error",
                link_id=link.id,
                answer_id=update.answer_id,
                error=str(e),
                exc_info=True,
            )
            continue

    logger.info(
        "so_updates_processed",
        link_id=link.id,
        total=len(updates),
        sent=sent_count,
    )

    return updates


async def check_link_for_updates(
    link: LinkDomain,
    link_repo: LinkRepositoryProtocol,
    message_sender: MessageSenderProtocol,
    github_token: Optional[str] = None,
) -> bool:
    """Проверяет одну ссылку на наличие обновлений и отправляет уведомления."""
    url = link.url
    link_type = classify_url(url)

    if not link_type:
        logger.debug("unsupported_url", link_id=link.id, url=url)
        return False

    logger.debug(
        "checking_link",
        link_id=link.id,
        url=url,
        type=link_type,
        last_checked=link.last_checked.isoformat() if link.last_checked else None,
    )

    try:
        if link_type == "github":
            updates = await process_github_link(
                link=link,
                message_sender=message_sender,
                token=github_token,
            )
        elif link_type == "stackoverflow":
            updates = await process_stackoverflow_link(
                link=link,
                message_sender=message_sender,
            )
        else:
            return False

        if updates:
            latest_update = max(updates, key=lambda u: u.created_at)

            success = await link_repo.update_last_checked(
                link.id,
                latest_update.created_at,
            )

            if success:
                logger.info(
                    "link_last_checked_updated",
                    link_id=link.id,
                    new_last_checked=latest_update.created_at.isoformat(),
                )
            else:
                logger.error(
                    "failed_to_update_last_checked",
                    link_id=link.id,
                )

            return True

        return False

    except Exception as e:
        logger.error(
            "check_link_error",
            link_id=link.id,
            url=url,
            error=str(e),
            exc_info=True,
        )
        return False


async def run_scheduler(
    link_repo: LinkRepositoryProtocol,
    message_sender: MessageSenderProtocol,
):
    """Главный цикл планировщика с пакетной обработкой."""
    interval = settings.check_interval
    batch_size = settings.batch_size

    logger.info(
        "scheduler_started",
        interval_seconds=interval,
        batch_size=batch_size,
    )

    while True:
        try:
            links = await link_repo.get_all_for_check(limit=batch_size)

            logger.debug(
                "scheduler_cycle_start",
                links_count=len(links),
                batch_size=batch_size,
            )

            if not links:
                logger.debug("no_links_to_check")
            else:
                processed_count = 0
                error_count = 0

                for link in links:
                    try:
                        has_updates = await check_link_for_updates(
                            link=link,
                            link_repo=link_repo,
                            message_sender=message_sender,
                            github_token=(
                                settings.github_token.get_secret_value()
                                if settings.github_token
                                else None
                            ),
                        )

                        if has_updates:
                            processed_count += 1

                        await asyncio.sleep(1)

                    except Exception as e:
                        error_count += 1
                        logger.error(
                            "link_processing_failed",
                            link_id=link.id,
                            url=link.url,
                            error=str(e),
                            exc_info=True,
                        )

                logger.info(
                    "scheduler_cycle_complete",
                    total=len(links),
                    processed=processed_count,
                    errors=error_count,
                    next_run_in=interval,
                )

            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info("scheduler_stopped")
            break

        except Exception as e:
            logger.error(
                "scheduler_fatal_error",
                error=str(e),
                exc_info=True,
            )
            await asyncio.sleep(60)
