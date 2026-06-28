FROM postgres:14

RUN echo "hot_standby = on" >> /usr/share/postgresql/postgresql.conf.sample && \
    echo "primary_conninfo = 'host=db_main port=5432 user=repl_user password=repl_password'" >> /usr/share/postgresql/postgresql.conf.sample

COPY setup_replica.sh /docker-entrypoint-initdb.d/
