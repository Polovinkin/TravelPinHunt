// Показывает эмодзи или кастомное изображение флага страны рядом с Select2-виджетом
// и обновляет его при смене выбранного значения. Используется в двух местах:
//   - City admin:     #id_country + JSON в <script id="country-flags-data">
//   - Location admin: #id_city    + JSON в <script id="city-flags-data">
(function () {
    var CONFIGS = [
        { selectId: "id_country", dataId: "country-flags-data" },
        { selectId: "id_city", dataId: "city-flags-data" },
    ];

    function getFlagsMap(dataId) {
        var el = document.getElementById(dataId);
        if (!el) return {};
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return {};
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        var $ = window.django && window.django.jQuery;
        if (!$) return;

        CONFIGS.forEach(function (config) {
            var $select = $("#" + config.selectId);
            if ($select.length === 0) return;

            var flags = getFlagsMap(config.dataId);

            var $flag = $('<span class="country-flag-preview"></span>');
            // Кнопки «изменить», «добавить» и «посмотреть» — прямые потомки обёртки
            // related-widget-wrapper. Ставим флаг перед первой из них: так он всегда
            // находится между выбором страны и этими кнопками, независимо от того,
            // когда Select2 добавил свой видимый контейнер.
            var $wrapper = $select.closest(".related-widget-wrapper");
            var $firstLink = $wrapper.children(".related-widget-wrapper-link").first();
            if ($firstLink.length) {
                $flag.insertBefore($firstLink);
            } else if ($wrapper.length) {
                $wrapper.append($flag);
            } else {
                $flag.insertAfter($select);
            }

            function updateFlag() {
                var id = $select.val();
                var flag = id && flags[id];
                $flag.empty();
                if (!flag) return;

                if (typeof flag === "string") {
                    $flag.text(flag);
                } else if (flag.image_url) {
                    $("<img>", {
                        src: flag.image_url,
                        alt: "",
                        "aria-hidden": "true",
                        class: "country-flag-preview-image",
                    }).appendTo($flag);
                } else {
                    $flag.text(flag.emoji || "");
                }
            }

            updateFlag();
            // select2 триггерит нативный change на скрытом <select>, поэтому обычного .on("change") достаточно
            $select.on("change", updateFlag);
        });
    });
})();
