CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS links (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    filters TEXT[] DEFAULT ARRAY[]::TEXT[],
    last_checked TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_links (
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    PRIMARY KEY (chat_id, link_id)
);

CREATE INDEX IF NOT EXISTS idx_links_url ON links(url);
CREATE INDEX IF NOT EXISTS idx_chat_links_chat_id ON chat_links(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_links_link_id ON chat_links(link_id);
CREATE INDEX IF NOT EXISTS idx_links_last_checked ON links(last_checked);
CREATE INDEX IF NOT EXISTS idx_links_last_updated ON links(last_updated);

COMMENT ON TABLE chats IS 'Зарегистрированные телеграм чаты';
COMMENT ON TABLE links IS 'Отслеживаемые ссылки (GitHub, StackOverflow)';
COMMENT ON TABLE chat_links IS 'Связь чатов с отслеживаемыми ссылками';