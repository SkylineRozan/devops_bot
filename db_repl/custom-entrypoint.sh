#!/bin/bash
set -e

echo "Запуск реплики PostgreSQL..."

export PGPASSWORD='repl_password'

# Ждём мастер
until pg_isready -h db_main -U repl_user; do
    echo "Ожидание мастера..."
    sleep 2
done

# Если данные уже есть и standby.signal существует — запускаем как реплику
if [ -f /var/lib/postgresql/data/standby.signal ]; then
    echo "Реплика уже настроена, запускаем PostgreSQL..."
    exec docker-entrypoint.sh postgres
fi

# Иначе настраиваем реплику с нуля
echo "Настройка реплики с нуля..."
rm -rf /var/lib/postgresql/data/*

pg_basebackup -h db_main -D /var/lib/postgresql/data -U repl_user -P -R --slot=replica_slot -C

cat > /var/lib/postgresql/data/postgresql.auto.conf << EOF
primary_conninfo = 'host=db_main port=5432 user=repl_user password=repl_password'
primary_slot_name = 'replica_slot'
hot_standby = on
EOF

echo "Реплика настроена! Запускаем PostgreSQL..."
exec docker-entrypoint.sh postgres
