{% import "main/macros.html" as macros %}
const fragment = `{{ macros.render_feed_label(feed) }}`
var target = document.getElementById('label-feed-{{feed.id}}')
Sweat.morph(target, fragment);
