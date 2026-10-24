import pytest
import respx
from httpx import Response

from src.clients.stackoverflow_client import (
    get_question_answers,
    _strip_html_tags,
)


class TestStripHtmlTags:
    """Тесты очистки HTML."""

    def test_simple_tags(self):
        """Простые теги."""
        html = "<p>Hello <b>world</b></p>"
        assert _strip_html_tags(html) == "Hello world"

    def test_html_entities(self):
        """HTML-сущности."""
        html = "Tom &amp; Jerry &lt;3"
        assert _strip_html_tags(html) == "Tom & Jerry <3"

    def test_complex_html(self):
        """Сложный HTML."""
        html = """
        <div class="post">
            <p>First paragraph</p>
            <code>print("hello")</code>
        </div>
        """
        result = _strip_html_tags(html)
        assert "First paragraph" in result
        assert 'print("hello")' in result
        assert "<" not in result


class TestGetQuestionAnswers:
    """Тесты получения ответов."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self):
        """Успешное получение ответов."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={"items": [{"title": "How to parse JSON?"}]},
            )
        )

        mock_response = {
            "items": [
                {
                    "answer_id": 67890,
                    "owner": {"display_name": "Expert User"},
                    "creation_date": 1705315800,
                    "body": "<p>Use json.loads() method</p>",
                }
            ]
        }

        respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_question_answers(12345)

        assert len(updates) == 1
        assert updates[0].question_id == 12345
        assert updates[0].question_title == "How to parse JSON?"
        assert updates[0].answer_id == 67890
        assert updates[0].author == "Expert User"
        assert "json.loads()" in updates[0].preview
        assert updates[0].url == "https://stackoverflow.com/a/67890"

    @respx.mock
    @pytest.mark.asyncio
    async def test_html_cleaned(self):
        """HTML очищается из ответа."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={"items": [{"title": "Question"}]},
            )
        )

        mock_response = {
            "items": [
                {
                    "answer_id": 1,
                    "owner": {"display_name": "User"},
                    "creation_date": 1705315800,
                    "body": "<p>Answer with <code>code</code> &amp; symbols</p>",
                }
            ]
        }

        respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_question_answers(12345)

        assert "<p>" not in updates[0].preview
        assert "<code>" not in updates[0].preview
        assert "&" in updates[0].preview

    @respx.mock
    @pytest.mark.asyncio
    async def test_long_answer_truncated(self):
        """Длинный ответ обрезается."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={"items": [{"title": "Question"}]},
            )
        )

        long_body = "<p>" + "word " * 100 + "</p>"

        mock_response = {
            "items": [
                {
                    "answer_id": 1,
                    "owner": {"display_name": "User"},
                    "creation_date": 1705315800,
                    "body": long_body,
                }
            ]
        }

        respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_question_answers(12345)

        assert len(updates[0].preview) <= 203
        assert updates[0].preview.endswith("...")

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_not_found(self):
        """Вопрос не найден."""
        respx.get("https://api.stackexchange.com/2.3/questions/999999").mock(
            return_value=Response(404)
        )

        respx.get("https://api.stackexchange.com/2.3/questions/999999/answers").mock(
            return_value=Response(404)
        )

        updates = await get_question_answers(999999)
        assert updates == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_items(self):
        """Пустой список ответов."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={"items": [{"title": "Question"}]},
            )
        )

        respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
            return_value=Response(200, json={"items": []})
        )

        updates = await get_question_answers(12345)
        assert updates == []
