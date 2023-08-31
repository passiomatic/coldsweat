{% set request_url = url_for('main.entry_list', _external=True, feed_id=feed.id, xhr=1) %}
Sweat.loadFolder('{{ request_url }}', '{{feed.title}}')
