#!/bin/bash
echo "host replication repl_user all md5" >> /var/lib/postgresql/data/pg_hba.conf
psql -U postgres -c "SELECT pg_reload_conf();"
echo "Правило репликации добавлено в pg_hba.conf"
