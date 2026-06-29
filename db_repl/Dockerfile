FROM postgres:14

RUN echo "hot_standby = on" >> /usr/share/postgresql/postgresql.conf.sample

COPY setup_replica.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/setup_replica.sh

# Переопределяем entrypoint чтобы не запускать временный сервер
COPY custom-entrypoint.sh /custom-entrypoint.sh
RUN chmod +x /custom-entrypoint.sh
ENTRYPOINT ["/custom-entrypoint.sh"]
CMD ["postgres"]
