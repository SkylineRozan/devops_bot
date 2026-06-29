FROM postgres:14

COPY init.sql /docker-entrypoint-initdb.d/
COPY configure_replication.sh /docker-entrypoint-initdb.d/

RUN echo "wal_level = replica" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "max_wal_senders = 10" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "wal_keep_size = 64" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "host replication all 0.0.0.0/0 md5" >> /usr/share/postgresql/pg_hba.conf.sample
