FROM alpine:3.10
MAINTAINER  Oz Tiram <oz.tiram@gmail.com>

RUN apk update && \
    apk add py3-pip uwsgi uwsgi-python3 gnupg sqlite && \
    pip3 install --upgrade pip && \
    test -d /run/coldsweat || mkdir /run/coldsweet && \
    test -d /var/lib/coldsweat || mkdir /var/lib/coldsweat && \
    test -d /etc/coldsweat || mkdir /etc/coldsweat

ADD requirements.txt /run/coldsweat/
RUN pip install -r /run/coldsweat/requirements.txt

RUN adduser -D coldsweat
ADD docker/entrypoint.sh /usr/bin/
ADD docker/config /etc/coldsweat/
ADD sweat.py /run/coldsweat/
ADD coldsweat /run/coldsweat/coldsweat
ADD plugins /run/coldsweat/
ADD wsgi.py /run/coldsweat/
ADD static /run/coldsweat/static

VOLUME ["/var/lib/coldsweat/db"]

EXPOSE 9001
USER coldsweat

CMD ["/usr/bin/entrypoint.sh"]
