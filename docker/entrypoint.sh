#!/bin/sh

UWSGI_PORT="${UWSGI_PORT:-9001}"
UWSGI_PROCS=${UWSGI_PROCS:-4}
UWSGI_THREADS=${UWSGI_THREADS:-2}

export COLDSWEAT_INSTALL_DIR=/run/coldsweat
export COLDSWEAT_CONFIG_PATH=/etc/coldsweat/config

chdir /run/coldsweat

ls /etc/coldsweat/
cat /etc/coldsweat/config

exec uwsgi --need-app --plugins-dir /usr/lib/uwsgi  --need-plugin python3 \
	--pythonpath /run/coldsweat \
	--plugin python3 --processes "${UWSGI_PROCS}" \
	--threads "${UWSGI_THREADS}" --http-socket 0.0.0.0:"${UWSGI_PORT}" \
	--static-map /static=/var/lib/coldsweat/static \
	--wsgi-file=/run/coldsweat/wsgi.py --callable=app --master \
	--log-master \
	--logformat 'pid: %(pid)|app: -|req: -/-] %(var.HTTP_X_REAL_IP) (%(user)) {%(vars) vars in %(pktsize) bytes} [%(ctime)] %(method) %(uri) => generated %(rsize) bytes in %(msecs) msecs (%(proto) %(status)) %(headers) headers in %(hsize) bytes (%(switches) switches on core %(core))'
