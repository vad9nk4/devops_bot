-- Создание пользователя с правами репликации
CREATE USER ${DB_REPL_USER} WITH REPLICATION LOGIN PASSWORD '${DB_REPL_PASSWORD}';

-- Подключение к базе данных
\connect ${DB_DATABASE};

-- Создание таблицы с электронными адресами, если не существует
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE
);

-- Создание таблицы с номерами телефонов, если не существует
CREATE TABLE IF NOT EXISTS phone_numbers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE
);

-- Вставка данных в таблицу emails
INSERT INTO emails (email) VALUES ('test@qwerty.ru'), ('qwerty@test.com');

-- Вставка данных в таблицу phone_numbers
INSERT INTO phone_numbers (phone_number) VALUES ('+71233211231'), ('+76665554443');