// Предупреждает об уходе со страницы с несохранёнными изменениями формы админки.
(function () {
    document.addEventListener("DOMContentLoaded", function () {
        var form = document.querySelector("#location_form, #city_form, #locationsubmission_form");
        if (!form) return;

        var formSubmitted = false;

        function getValues() {
            return JSON.stringify(Array.from(form.elements).filter(function (field) {
                // Служебные поля и кнопки не относятся к редактируемым данным.
                return field.name && !["hidden", "submit", "button", "reset"].includes(field.type);
            }).map(function (field) {
                if (field.type === "checkbox" || field.type === "radio") {
                    return [field.name, field.value, field.checked];
                }
                if (field.tagName === "SELECT" && field.multiple) {
                    return [field.name, Array.from(field.selectedOptions).map(function (option) {
                        return option.value;
                    })];
                }
                return [field.name, field.value];
            }));
        }

        var initialValues = getValues();

        form.addEventListener("submit", function () {
            formSubmitted = true;
        });

        // При возврате через историю браузера защита должна снова работать.
        window.addEventListener("pageshow", function () {
            formSubmitted = false;
        });

        window.addEventListener("beforeunload", function (event) {
            if (!formSubmitted && getValues() !== initialValues) {
                event.preventDefault();
                event.returnValue = "";
            }
        });
    });
})();
