(function ($) {
    'use strict';

    var styleAdded = false;

    function addStyle() {
        if (styleAdded) {
            return;
        }
        styleAdded = true;
        $('head').append(
            '<style>' +
            '.camera-capture-box{border:1px solid #dee2e6;border-radius:6px;padding:12px;margin-top:10px;background:#f8f9fa;}' +
            '.camera-capture-preview{position:relative;overflow:hidden;border-radius:6px;background:#111;min-height:180px;display:flex;align-items:center;justify-content:center;}' +
            '.camera-capture-preview video,.camera-capture-preview img{display:block;width:100%;max-height:340px;object-fit:contain;background:#111;}' +
            '.camera-capture-empty{color:#6c757d;font-size:14px;text-align:center;padding:28px 12px;background:#fff;width:100%;}' +
            '.camera-capture-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}' +
            '.camera-capture-status{font-size:12px;color:#6c757d;margin-top:8px;}' +
            '</style>'
        );
    }

    function fileName(prefix) {
        var stamp = new Date().toISOString().replace(/[:.]/g, '-');
        return prefix + '-' + stamp + '.jpg';
    }

    function CameraCapture(input) {
        this.input = input;
        this.$input = $(input);
        this.stream = null;
        this.devices = [];
        this.deviceIndex = 0;
        this.facingMode = 'environment';
        this.filePrefix = this.$input.data('cameraFilename') || 'foto';
        this.build();
        this.bind();
    }

    CameraCapture.prototype.build = function () {
        addStyle();
        this.$box = $(
            '<div class="camera-capture-box">' +
            '  <div class="camera-capture-preview">' +
            '    <div class="camera-capture-empty">Puede seleccionar una imagen o tomar una foto con la camara.</div>' +
            '  </div>' +
            '  <div class="camera-capture-actions">' +
            '    <button type="button" class="btn btn-secondary btn-sm js-camera-open"><i class="fas fa-camera"></i> Abrir camara</button>' +
            '    <button type="button" class="btn btn-primary btn-sm js-camera-shot" disabled><i class="fas fa-circle"></i> Tomar foto</button>' +
            '    <button type="button" class="btn btn-info btn-sm js-camera-switch" style="display:none;"><i class="fas fa-sync-alt"></i> Cambiar camara</button>' +
            '    <button type="button" class="btn btn-outline-secondary btn-sm js-camera-stop" disabled><i class="fas fa-stop"></i> Detener</button>' +
            '  </div>' +
            '  <div class="camera-capture-status"></div>' +
            '  <canvas style="display:none;"></canvas>' +
            '</div>'
        );
        this.$preview = this.$box.find('.camera-capture-preview');
        this.$status = this.$box.find('.camera-capture-status');
        this.$open = this.$box.find('.js-camera-open');
        this.$shot = this.$box.find('.js-camera-shot');
        this.$switch = this.$box.find('.js-camera-switch');
        this.$stop = this.$box.find('.js-camera-stop');
        this.canvas = this.$box.find('canvas')[0];
        this.$input.after(this.$box);
    };

    CameraCapture.prototype.bind = function () {
        var self = this;
        this.$open.on('click', function () {
            self.start();
        });
        this.$shot.on('click', function () {
            self.capture();
        });
        this.$switch.on('click', function () {
            self.switchCamera();
        });
        this.$stop.on('click', function () {
            self.stop();
        });
        this.$input.on('change', function () {
            self.previewSelectedFile();
        });
        $(window).on('beforeunload', function () {
            self.stop();
        });
    };

    CameraCapture.prototype.setStatus = function (message) {
        this.$status.text(message || '');
    };

    CameraCapture.prototype.constraints = function () {
        if (this.devices.length) {
            return {video: {deviceId: {exact: this.devices[this.deviceIndex].deviceId}}, audio: false};
        }
        return {video: {facingMode: this.facingMode}, audio: false};
    };

    CameraCapture.prototype.start = function () {
        var self = this;

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.setStatus('Este navegador no permite abrir la camara desde la pagina.');
            return;
        }

        this.stop();
        this.setStatus('Solicitando permiso de camara...');

        navigator.mediaDevices.getUserMedia(this.constraints()).then(function (stream) {
            self.stream = stream;
            self.video = document.createElement('video');
            self.video.autoplay = true;
            self.video.playsInline = true;
            self.video.muted = true;
            self.video.srcObject = stream;
            self.$preview.empty().append(self.video);
            self.$shot.prop('disabled', false);
            self.$stop.prop('disabled', false);
            self.setStatus('Camara lista.');
            self.loadDevices();
        }).catch(function (error) {
            self.setStatus('No se pudo abrir la camara: ' + error.message);
        });
    };

    CameraCapture.prototype.loadDevices = function () {
        var self = this;
        navigator.mediaDevices.enumerateDevices().then(function (devices) {
            self.devices = devices.filter(function (device) {
                return device.kind === 'videoinput';
            });
            self.$switch.toggle(self.devices.length > 1);
        });
    };

    CameraCapture.prototype.switchCamera = function () {
        if (this.devices.length > 1) {
            this.deviceIndex = (this.deviceIndex + 1) % this.devices.length;
        } else {
            this.facingMode = this.facingMode === 'environment' ? 'user' : 'environment';
        }
        this.start();
    };

    CameraCapture.prototype.capture = function () {
        var self = this;
        if (!this.video || !this.video.videoWidth) {
            this.setStatus('La camara aun no esta lista.');
            return;
        }

        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        this.canvas.getContext('2d').drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        this.canvas.toBlob(function (blob) {
            if (!blob) {
                self.setStatus('No se pudo capturar la foto.');
                return;
            }

            var file = new File([blob], fileName(self.filePrefix), {type: 'image/jpeg'});
            var dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            self.input.files = dataTransfer.files;
            self.$input.trigger('change');
            self.setStatus('Foto capturada. Guarde el formulario para conservarla.');
        }, 'image/jpeg', 0.9);
    };

    CameraCapture.prototype.previewSelectedFile = function () {
        var file = this.input.files && this.input.files[0];
        if (!file || !file.type || file.type.indexOf('image/') !== 0) {
            return;
        }
        var url = URL.createObjectURL(file);
        this.$preview.empty().append($('<img>', {src: url, alt: 'Vista previa'}));
    };

    CameraCapture.prototype.stop = function () {
        if (this.stream) {
            this.stream.getTracks().forEach(function (track) {
                track.stop();
            });
        }
        this.stream = null;
        this.$shot.prop('disabled', true);
        this.$stop.prop('disabled', true);
    };

    $.fn.cameraCapture = function () {
        return this.each(function () {
            if (!$(this).data('cameraCapture')) {
                $(this).data('cameraCapture', new CameraCapture(this));
            }
        });
    };

    $(function () {
        $('input[type="file"][name="image"]').cameraCapture();
    });
})(jQuery);
