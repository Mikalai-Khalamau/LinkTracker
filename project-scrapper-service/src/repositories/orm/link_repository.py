from sqlalchemy import select, delete, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
from src.repositories.base import LinkRepositoryProtocol
from src.models import AddLinkRequest, LinkDomain
from src.repositories.orm.models import LinkORM, ChatLinkORM


class OrmLinkRepository(LinkRepositoryProtocol):
    """Реализация репозитория ссылок."""

    def __init__(self, session_factory):
        """."""
        self.session_factory = session_factory

    async def add(self, chat_id: int, request: AddLinkRequest) -> Optional[LinkDomain]:
        """Добавляет ссылку для отслеживания."""
        url_str = str(request.link)

        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(LinkORM).where(LinkORM.url == url_str)
                result = await session.execute(stmt)
                link_orm = result.scalar_one_or_none()

                if not link_orm:
                    link_orm = LinkORM(
                        url=url_str,
                        tags=request.tags or [],
                        filters=request.filters or [],
                    )
                    session.add(link_orm)
                    await session.flush()

                stmt = select(ChatLinkORM).where(
                    and_(
                        ChatLinkORM.chat_id == chat_id,
                        ChatLinkORM.link_id == link_orm.id,
                    )
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    return None

                chat_link = ChatLinkORM(chat_id=chat_id, link_id=link_orm.id)
                session.add(chat_link)

                return LinkDomain(
                    id=link_orm.id,
                    chat_id=chat_id,
                    url=link_orm.url,
                    tags=link_orm.tags or [],
                    filters=link_orm.filters or [],
                    last_checked=link_orm.last_checked,
                    last_updated=link_orm.last_updated,
                )

    async def get_by_chat(
        self, chat_id: int, tag: Optional[str] = None
    ) -> List[LinkDomain]:
        async with self.session_factory() as session:
            stmt = (
                select(LinkORM)
                .join(ChatLinkORM, LinkORM.id == ChatLinkORM.link_id)
                .where(ChatLinkORM.chat_id == chat_id)
            )

            if tag:
                from sqlalchemy import text

                stmt = stmt.where(text(f"('{tag}' = ANY(links.tags))"))

            result = await session.execute(stmt)
            links_orm = result.scalars().all()

            return [
                LinkDomain(
                    id=link.id,
                    chat_id=chat_id,
                    url=link.url,
                    tags=link.tags or [],
                    filters=link.filters or [],
                    last_checked=link.last_checked,
                    last_updated=link.last_updated,
                )
                for link in links_orm
            ]

    async def remove(self, chat_id: int, url: str) -> bool:
        """Удаляет связь чата со ссылкой."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(LinkORM).where(LinkORM.url == url)
                result = await session.execute(stmt)
                link_orm = result.scalar_one_or_none()

                if not link_orm:
                    return False

                stmt = delete(ChatLinkORM).where(
                    and_(
                        ChatLinkORM.chat_id == chat_id,
                        ChatLinkORM.link_id == link_orm.id,
                    )
                )
                result = await session.execute(stmt)

                return result.rowcount > 0

    async def get_all_for_check(self, limit: int = 100) -> List[LinkDomain]:
        """Получает ссылки для проверки обновлений."""
        async with self.session_factory() as session:
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

            stmt = (
                select(LinkORM, ChatLinkORM.chat_id)
                .join(ChatLinkORM, LinkORM.id == ChatLinkORM.link_id)
                .where(
                    or_(
                        LinkORM.last_checked.is_(None),
                        LinkORM.last_checked < five_minutes_ago,
                    )
                )
                .order_by(LinkORM.last_checked.nulls_first())
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            return [
                LinkDomain(
                    id=link.id,
                    chat_id=chat_id,
                    url=link.url,
                    tags=link.tags or [],
                    filters=link.filters or [],
                    last_checked=link.last_checked,
                    last_updated=link.last_updated,
                )
                for link, chat_id in rows
            ]

    async def update_last_checked(
        self, link_id: int, last_updated: Optional[datetime]
    ) -> bool:
        """Обновляет время последней проверки и обновления."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(LinkORM).where(LinkORM.id == link_id)
                result = await session.execute(stmt)
                link_orm = result.scalar_one_or_none()

                if not link_orm:
                    return False

                link_orm.last_checked = datetime.utcnow()
                if last_updated:
                    link_orm.last_updated = last_updated

                return True

    async def get_by_url(self, url: str) -> Optional[LinkDomain]:
        """Получает ссылку по URL."""
        async with self.session_factory() as session:
            stmt = select(LinkORM).where(LinkORM.url == url)
            result = await session.execute(stmt)
            link_orm = result.scalar_one_or_none()

            if not link_orm:
                return None

            stmt = select(ChatLinkORM.chat_id).where(ChatLinkORM.link_id == link_orm.id)
            result = await session.execute(stmt)
            chat_id_row = result.first()
            chat_id = chat_id_row[0] if chat_id_row else 0

            return LinkDomain(
                id=link_orm.id,
                chat_id=chat_id,
                url=link_orm.url,
                tags=link_orm.tags or [],
                filters=link_orm.filters or [],
                last_checked=link_orm.last_checked,
                last_updated=link_orm.last_updated,
            )
