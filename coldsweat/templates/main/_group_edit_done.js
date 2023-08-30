{% import "main/macros.html" as macros %}
const fragment = `{{ macros.render_group_label(group.id, group.title) }}`
var target = document.getElementById('label-group-{{group.id}}')
Sweat.morph(target, fragment);
