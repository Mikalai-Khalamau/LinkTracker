from pydantic import AnyUrl, BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ApiErrorResponse(BaseModel):
    """Стандартный формат ошибки."""

    description: str
    code: str
    exception_name: str | None = Field(default=None, alias="exceptionName")
    exception_message: str | None = Field(default=None, alias="exceptionMessage")
    stacktrace: list[str] | None = None

    class Config:
        populate_by_name = True


class AddLinkRequest(BaseModel):
    """Тело запроса на добавление ссылки."""

    link: AnyUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)

    @field_validator("link")
    @classmethod
    def validate_https(cls, v: AnyUrl) -> AnyUrl:
        if v.scheme not in ("https", "http"):
            raise ValueError("Ссылка должна использовать http/https")
        return v


class RemoveLinkRequest(BaseModel):
    """Тело запроса на удаление ссылки."""

    link: AnyUrl


class LinkResponse(BaseModel):
    """Ответ с информацией о ссылке."""

    id: int = Field(..., alias="id")
    url: AnyUrl
    tags: list[str]
    filters: list[str]

    class Config:
        populate_by_name = True


class ListLinksResponse(BaseModel):
    """Ответ со списком ссылок."""

    links: list[LinkResponse]
    size: int


class LinkUpdate(BaseModel):
    """Уведомление об обновлении ссылки."""

    id: int
    url: AnyUrl
    description: str
    tg_chat_ids: list[int] = Field(..., alias="tgChatIds")

    class Config:
        populate_by_name = True


class LinkDomain:
    """Ссылка (не зависит от ORM или SQL)."""

    def __init__(
        self,
        id: int,
        chat_id: int,
        url: str,
        tags: List[str],
        filters: List[str],
        last_checked: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
    ):
        self.id = id
        self.chat_id = chat_id
        self.url = url
        self.tags = tags
        self.filters = filters
        self.last_checked = last_checked
        self.last_updated = last_updated

    def to_response(self) -> LinkResponse:
        """Конвертация в ответ API."""
        return LinkResponse(
            id=self.id,
            url=self.url,
            tags=self.tags,
            filters=self.filters,
        )


class UpdateType(str, Enum):
    """Типы обновлений."""

    GITHUB_ISSUE = "github_issue"
    GITHUB_PR = "github_pull_request"
    STACKOVERFLOW_ANSWER = "stackoverflow_answer"
    STACKOVERFLOW_COMMENT = "stackoverflow_comment"


class DetailedUpdate(BaseModel):
    """Детальная информация об обновлении."""

    update_type: UpdateType
    title: str
    author: str
    created_at: datetime
    preview: str
    url: str

    class Config:
        use_enum_values = True


class GitHubIssueUpdate(DetailedUpdate):
    """Обновление для GitHub Issue/PR."""

    issue_number: int
    is_pull_request: bool = False


class StackOverflowAnswerUpdate(DetailedUpdate):
    """Обновление для StackOverflow ответа."""

    question_id: int
    answer_id: int
