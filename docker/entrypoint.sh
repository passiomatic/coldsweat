#!/bin/sh

UWSGI_PORT="${UWSGI_PORT:-9001}"
UWSGI_PROCS=${UWSGI_PROCS:-4}
UWSGI_THREADS=${UWSGI_THREADS:-4}

export COLDSWEAT_INSTALL_DIR=/run/coldsweat
export COLDSWEAT_CONFIG_PATH=/etc/coldsweat/config

chdir /run/coldsweat

# if you want to use python's reference server ...
# good for debugging, don't use in production
#exec python3 sweat.py serve -p 9001

exec uwsgi --need-app --plugins-dir /usr/lib/uwsgi  --need-plugin python3 \
	--honour-stdin \
	--pythonpath /run/coldsweat \
	--plugin python3 --processes "${UWSGI_PROCS}" \
	--threads "${UWSGI_THREADS}" --http-socket 0.0.0.0:"${UWSGI_PORT}" \
	--static-map /static=/run/coldsweat/static/ \
	--static-map /stylesheets=/run/coldsweat/static/stylesheets \
	--static-map /javascripts/=/run/coldsweat/static/javascripts \
	--static-map /fonts/=/run/coldsweat/static/fonts \
	--wsgi-file=/run/coldsweat/wsgi.py --callable=app --master \
	--log-master \
	--logformat 'pid: %(pid)|app: -|req: -/-] %(var.HTTP_X_REAL_IP) (%(user)) {%(vars) vars in %(pktsize) bytes} [%(ctime)] %(method) %(uri) => generated %(rsize) bytes in %(msecs) msecs (%(proto) %(status)) %(headers) headers in %(hsize) bytes (%(switches) switches on core %(core))'
