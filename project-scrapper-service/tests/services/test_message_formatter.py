"""Тесты форматирования сообщений (проверка данных, а не оформления)."""

from datetime import datetime, timezone

from src.services.message_formatter import (
    format_github_issue_message,
    format_github_pr_message,
    format_stackoverflow_answer_message,
    format_update_message,
    truncate_preview,
    format_datetime,
)


class TestTruncatePreview:
    def test_short_text(self):
        assert truncate_preview("Hello", 200) == "Hello"

    def test_exact_length(self):
        text = "a" * 200
        assert truncate_preview(text, 200) == text

    def test_long_text_truncated(self):
        text = "word " * 100
        result = truncate_preview(text, 200)
        assert len(result) <= 203
        assert result.endswith("...")

    def test_empty_text(self):
        assert truncate_preview("", 200) == ""
        assert truncate_preview(None, 200) == ""


class TestFormatDatetime:
    def test_utc_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_datetime(dt)
        assert "13:30" in result
        assert "15.01.2024" in result


class TestFormatGithubIssueMessage:
    def test_contains_all_required_data(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        message = format_github_issue_message(
            title="Fix bug in parser",
            author="john_doe",
            created_at=dt,
            preview="This is a bug description",
            url="https://github.com/test/repo/issues/42",
            issue_number=42,
        )

        assert "New Issue #42" in message
        assert "Fix bug in parser" in message
        assert "Author: john_doe" in message
        assert "15.01.2024" in message
        assert "This is a bug description" in message
        assert "Link: https://github.com/test/repo/issues/42" in message

    def test_empty_preview_excluded(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        message = format_github_issue_message(
            title="Test",
            author="user",
            created_at=dt,
            preview="",
            url="https://github.com/test/repo/issues/1",
            issue_number=1,
        )

        assert "Link: https://github.com/test/repo/issues/1" in message


class TestFormatGithubPrMessage:
    def test_contains_all_required_data(self):
        dt = datetime(2024, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        message = format_github_pr_message(
            title="Add new feature",
            author="jane_smith",
            created_at=dt,
            preview="This PR adds...",
            url="https://github.com/test/repo/pull/100",
            pr_number=100,
        )

        assert "New Pull Request #100" in message
        assert "Add new feature" in message
        assert "Author: jane_smith" in message
        assert "Link: https://github.com/test/repo/pull/100" in message


class TestFormatStackOverflowAnswerMessage:
    def test_contains_all_required_data(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        message = format_stackoverflow_answer_message(
            question_title="How to parse JSON?",
            author="Expert User",
            created_at=dt,
            preview="Use json.loads() method",
            url="https://stackoverflow.com/a/67890",
            answer_id=67890,
        )

        assert "New Answer #67890" in message
        assert "Question: How to parse JSON?" in message
        assert "Author: Expert User" in message
        assert "Use json.loads() method" in message
        assert "Link: https://stackoverflow.com/a/67890" in message


class TestFormatUpdateMessage:
    def test_github_issue_routing(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        message = format_update_message(
            update_type="github_issue",
            title="Test",
            author="user",
            created_at=dt,
            preview="Preview",
            url="https://github.com/test/repo/issues/1",
            issue_number=1,
        )
        assert "New Issue #1" in message

    def test_unknown_type_handling(self):
        message = format_update_message(update_type="unknown", title="Test")
        assert "Unknown update type" in message
        assert "Test" in message
