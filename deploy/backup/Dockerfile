# Daily backups: database dump (encrypted) and copy of the media, to a separate bucket.
FROM postgres:16-alpine

RUN apk add --no-cache rclone gnupg curl

COPY backup.sh restore.sh scheduler.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/backup.sh /usr/local/bin/restore.sh /usr/local/bin/scheduler.sh \
    && chmod +x /usr/local/bin/backup.sh /usr/local/bin/restore.sh /usr/local/bin/scheduler.sh

ENV GNUPGHOME=/tmp/gnupg \
    HOME=/tmp
USER postgres
# Unhealthy when no backup has worked for 26 hours.
HEALTHCHECK --interval=5m --timeout=10s --start-period=1m \
    CMD test -n "$(find /tmp/last-run-ok -mmin -1560 2>/dev/null)"
ENTRYPOINT []
CMD ["scheduler.sh"]
