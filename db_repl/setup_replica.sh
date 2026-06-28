#!/bin/bash
set -e

echo "Настройка реплики PostgreSQL..."

# Ожидание доступности мастера
until pg_isready -h db_main -U postgres; do
    echo "Ожидание мастера..."
    sleep 2
done

# Создаём базовую резервную копию с мастера
pg_basebackup -h db_main -D /var/lib/postgresql/data -U repl_user -P -R --slot=replica_slot -C

echo "Реплика настроена!"
