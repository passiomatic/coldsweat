{% if location is defined %}
    //$('.modal').on('hidden', function () {window.location.assign('{{location}}')}).modal('hide')
    Sweat.closeDialog();
{% else %}
    Sweat.closeDialog();
{% endif %}
