$(function () {
    $('.select2').select2({
        theme: "bootstrap4",
        language: 'es',
        placeholder: 'Buscar..'
    });

    const $password = $('#id_password');

    if ($password.length) {
        const $group = $('<div class="input-group"></div>');
        const $toggle = $(
            '<div class="input-group-append">' +
            '<button type="button" class="btn btn-outline-secondary" title="Mostrar password" aria-label="Mostrar password">' +
            '<i class="fas fa-eye"></i>' +
            '</button>' +
            '</div>'
        );
        const $button = $toggle.find('button');
        const $icon = $toggle.find('i');

        $password.wrap($group);
        $password.after($toggle);

        $button.on('click', function () {
            const isHidden = $password.attr('type') === 'password';
            $password.attr('type', isHidden ? 'text' : 'password');
            $button.attr('title', isHidden ? 'Ocultar password' : 'Mostrar password');
            $button.attr('aria-label', isHidden ? 'Ocultar password' : 'Mostrar password');
            $icon.toggleClass('fa-eye', !isHidden);
            $icon.toggleClass('fa-eye-slash', isHidden);
        });
    }
});
