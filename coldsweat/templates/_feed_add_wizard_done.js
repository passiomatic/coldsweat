// Hide any open modal and redirect
$('.modal').on('hidden', function () {window.location.assign('{{url}}')}).modal('hide')