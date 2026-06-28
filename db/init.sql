-- Создаём пользователей
CREATE USER db_admin WITH PASSWORD 'db_admin_password';
CREATE USER repl_user WITH PASSWORD 'repl_password' REPLICATION;

-- Создаём базу данных
CREATE DATABASE mydb OWNER db_admin;

-- Подключаемся к базе
\c mydb

-- Даём права
GRANT ALL PRIVILEGES ON DATABASE mydb TO db_admin;
GRANT ALL ON SCHEMA public TO db_admin;

-- Создаём таблицы
CREATE TABLE IF NOT EXISTS EMAIL (
    ID SERIAL PRIMARY KEY,
    Email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS PHONE (
    ID SERIAL PRIMARY KEY,
    Phone VARCHAR(50) UNIQUE NOT NULL
);

-- Тестовые данные
INSERT INTO EMAIL (Email) VALUES
    ('test1@example.com'),
    ('test2@example.com'),
    ('admin@test.org');

INSERT INTO PHONE (Phone) VALUES
    ('+79161234567'),
    ('+79031234567'),
    ('+79169876543');

-- Права для db_admin
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO db_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO db_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO db_admin;

-- Настройки репликации
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET wal_keep_size = 64;
