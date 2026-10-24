import asyncpg
from typing import Optional, List
from datetime import datetime

from src.repositories.base import LinkRepositoryProtocol
from src.models import AddLinkRequest, LinkDomain


class SqlLinkRepository(LinkRepositoryProtocol):
    """Реализация репозитория ссылок."""

    def __init__(self, pool: asyncpg.Pool):
        """."""
        self.pool = pool

    async def add(self, chat_id: int, request: AddLinkRequest) -> Optional[LinkDomain]:
        """Добавляет ссылку для отслеживания."""
        url_str = str(request.link)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                link_row = await conn.fetchrow(
                    """
                    INSERT INTO links (url, tags, filters)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (url) DO UPDATE
                    SET tags = EXCLUDED.tags, filters = EXCLUDED.filters
                    RETURNING id, url, tags, filters, last_checked, last_updated
                    """,
                    url_str,
                    request.tags or [],
                    request.filters or [],
                )

                link_id = link_row["id"]

                existing = await conn.fetchval(
                    """
                    SELECT 1 FROM chat_links
                    WHERE chat_id = $1 AND link_id = $2
                    """,
                    chat_id,
                    link_id,
                )

                if existing:
                    return None

                await conn.execute(
                    """
                    INSERT INTO chat_links (chat_id, link_id)
                    VALUES ($1, $2)
                    """,
                    chat_id,
                    link_id,
                )

                return LinkDomain(
                    id=link_row["id"],
                    chat_id=chat_id,
                    url=link_row["url"],
                    tags=link_row["tags"] or [],
                    filters=link_row["filters"] or [],
                    last_checked=link_row["last_checked"],
                    last_updated=link_row["last_updated"],
                )

    async def get_by_chat(
        self, chat_id: int, tag: Optional[str] = None
    ) -> List[LinkDomain]:
        """Получает ссылки чата через JOIN."""
        async with self.pool.acquire() as conn:
            if tag:
                rows = await conn.fetch(
                    """
                    SELECT l.id, l.url, l.tags, l.filters,
                           l.last_checked, l.last_updated,
                           cl.chat_id
                    FROM links l
                    JOIN chat_links cl ON l.id = cl.link_id
                    WHERE cl.chat_id = $1 AND $2 = ANY(l.tags)
                    """,
                    chat_id,
                    tag,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT l.id, l.url, l.tags, l.filters,
                           l.last_checked, l.last_updated,
                           cl.chat_id
                    FROM links l
                    JOIN chat_links cl ON l.id = cl.link_id
                    WHERE cl.chat_id = $1
                    """,
                    chat_id,
                )

            return [
                LinkDomain(
                    id=row["id"],
                    chat_id=row["chat_id"],
                    url=row["url"],
                    tags=row["tags"] or [],
                    filters=row["filters"] or [],
                    last_checked=row["last_checked"],
                    last_updated=row["last_updated"],
                )
                for row in rows
            ]

    async def remove(self, chat_id: int, url: str) -> bool:
        """Удаляет связь чата со ссылкой."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                link_row = await conn.fetchrow(
                    "SELECT id FROM links WHERE url = $1",
                    url,
                )

                if not link_row:
                    return False

                result = await conn.execute(
                    """
                    DELETE FROM chat_links
                    WHERE chat_id = $1 AND link_id = $2
                    """,
                    chat_id,
                    link_row["id"],
                )

                rows_deleted = result.split()[-1]
                return rows_deleted != "0"

    async def get_all_for_check(self, limit: int = 100) -> List[LinkDomain]:
        """Получает ссылки для проверки обновлений."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT l.id, l.url, l.tags, l.filters,
                       l.last_checked, l.last_updated,
                       cl.chat_id
                FROM links l
                JOIN chat_links cl ON l.id = cl.link_id
                WHERE l.last_checked IS NULL
                   OR l.last_checked < NOW() - INTERVAL '5 minutes'
                ORDER BY l.last_checked NULLS FIRST
                LIMIT $1
                """,
                limit,
            )

            return [
                LinkDomain(
                    id=row["id"],
                    chat_id=row["chat_id"],
                    url=row["url"],
                    tags=row["tags"] or [],
                    filters=row["filters"] or [],
                    last_checked=row["last_checked"],
                    last_updated=row["last_updated"],
                )
                for row in rows
            ]

    async def update_last_checked(
        self, link_id: int, last_updated: Optional[datetime]
    ) -> bool:
        """Обновляет время последней проверки."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE links
                SET last_checked = NOW(),
                    last_updated = COALESCE($2, last_updated)
                WHERE id = $1
                """,
                link_id,
                last_updated,
            )

            rows_updated = result.split()[-1]
            return rows_updated != "0"

    async def get_by_url(self, url: str) -> Optional[LinkDomain]:
        """Получает ссылку по URL для проверки дубликатов."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT l.id, l.url, l.tags, l.filters,
                       l.last_checked, l.last_updated,
                       cl.chat_id
                FROM links l
                LEFT JOIN chat_links cl ON l.id = cl.link_id
                WHERE l.url = $1
                LIMIT 1
                """,
                url,
            )

            if not row:
                return None

            return LinkDomain(
                id=row["id"],
                chat_id=row["chat_id"] or 0,
                url=row["url"],
                tags=row["tags"] or [],
                filters=row["filters"] or [],
                last_checked=row["last_checked"],
                last_updated=row["last_updated"],
            )
