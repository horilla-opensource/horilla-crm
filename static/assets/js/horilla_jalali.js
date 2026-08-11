/**
 * Horilla Jalali calendar integration (Phase 1).
 *
 * - type="date" → Shamsi datepicker styled like native date inputs
 * - type="datetime-local" → Shamsi date + time picker, styled like native datetime-local
 */
(function (window, document) {
    "use strict";

    var INIT_FLAG = "horillaJalaliInit";
    var pickerStarted = false;
    var activeTimePicker = null;

    var DEFAULT_INPUT_CLASS =
        "text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md " +
        "mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] " +
        "focus:border-primary-600";

    var COMPOUND_CLASS =
        "horilla-jalali-datetime flex w-full items-stretch border border-dark-50 rounded-md " +
        "text-sm [transition:.3s] focus-within:border-primary-600 bg-white dark:bg-gray-800";

    var INNER_INPUT_CLASS =
        "horilla-jalali-inner-input flex-1 min-w-0 border-0 bg-transparent p-2 " +
        "text-color-600 placeholder:text-xs placeholder:text-dark-100 text-sm " +
        "focus-visible:outline-0 cursor-pointer";

    var LABELS = {
        fa: {
            datePlaceholder: "yyyy/mm/dd",
            timePlaceholder: "hh:mm",
            hour: "ساعت",
            minute: "دقیقه",
            apply: "تأیید",
            now: "اکنون",
        },
        ar: {
            datePlaceholder: "yyyy/mm/dd",
            timePlaceholder: "hh:mm",
            hour: "ساعة",
            minute: "دقيقة",
            apply: "تأكيد",
            now: "الآن",
        },
        en: {
            datePlaceholder: "dd/mm/yyyy",
            timePlaceholder: "hh:mm",
            hour: "Hour",
            minute: "Minute",
            apply: "Apply",
            now: "Now",
        },
    };

    function pad(value) {
        return String(value).padStart(2, "0");
    }

    function getLabels() {
        var lang = (document.documentElement.lang || "en").split("-")[0].toLowerCase();
        return LABELS[lang] || LABELS.en;
    }

    function resolveInputClass(sourceInput, stripMargin) {
        var classes = (sourceInput && sourceInput.className) || DEFAULT_INPUT_CLASS;
        if (stripMargin) {
            classes = classes.replace(/\bmt-1\b/g, "").replace(/\bw-full\b/g, "").trim();
        }
        return classes;
    }

    function gregorianToJalaliParts(gy, gm, gd) {
        var gDaysInMonth = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
        var jy = gy <= 1600 ? 0 : 979;
        gy -= gy <= 1600 ? 621 : 1600;
        var gy2 = gm > 2 ? gy + 1 : gy;
        var days =
            365 * gy +
            Math.floor((gy2 + 3) / 4) -
            Math.floor((gy2 + 99) / 100) +
            Math.floor((gy2 + 399) / 400) -
            80 +
            gd +
            gDaysInMonth[gm - 1];
        jy += 33 * Math.floor(days / 12053);
        days %= 12053;
        jy += 4 * Math.floor(days / 1461);
        days %= 1461;
        if (days > 365) {
            jy += Math.floor((days - 1) / 365);
            days = (days - 1) % 365;
        }
        var jm = days < 186 ? 1 + Math.floor(days / 31) : 7 + Math.floor((days - 186) / 30);
        var jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30);
        return { year: jy, month: jm, day: jd };
    }

    function jalaliToGregorianParts(jy, jm, jd) {
        var salA = jy > 979 ? 979 : 0;
        var gy = jy > 979 ? 1600 : 621;
        jy -= salA;
        var days =
            365 * jy +
            Math.floor(jy / 33) * 8 +
            Math.floor(((jy % 33) + 3) / 4) +
            78 +
            jd +
            (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);
        gy += 400 * Math.floor(days / 146097);
        days %= 146097;
        if (days > 36524) {
            gy += 100 * Math.floor(--days / 36524);
            days %= 36524;
            if (days >= 365) {
                days += 1;
            }
        }
        gy += 4 * Math.floor(days / 1461);
        days %= 1461;
        if (days > 365) {
            gy += Math.floor((days - 1) / 365);
            days = (days - 1) % 365;
        }
        var gd = days + 1;
        var monthDays = [
            0,
            31,
            (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0 ? 29 : 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ];
        var gm = 0;
        while (gm < 13 && gd > monthDays[gm]) {
            gd -= monthDays[gm];
            gm += 1;
        }
        return { year: gy, month: gm, day: gd };
    }

    function isoDateToJalaliString(isoDate) {
        if (!isoDate) {
            return "";
        }
        var parts = isoDate.split("-");
        if (parts.length !== 3) {
            return "";
        }
        var jalali = gregorianToJalaliParts(
            parseInt(parts[0], 10),
            parseInt(parts[1], 10),
            parseInt(parts[2], 10)
        );
        return jalali.year + "/" + pad(jalali.month) + "/" + pad(jalali.day);
    }

    function jalaliStringToIsoDate(jalaliValue) {
        if (!jalaliValue) {
            return "";
        }
        var datePart = jalaliValue.trim().split(" ")[0];
        var chunks = datePart.split("/");
        if (chunks.length !== 3) {
            return "";
        }
        var gregorian = jalaliToGregorianParts(
            parseInt(chunks[0], 10),
            parseInt(chunks[1], 10),
            parseInt(chunks[2], 10)
        );
        return gregorian.year + "-" + pad(gregorian.month) + "-" + pad(gregorian.day);
    }

    function splitDatetimeLocal(value) {
        if (!value) {
            return { date: "", time: "" };
        }
        var chunks = value.split("T");
        var time = chunks[1] || "";
        if (time.length > 5) {
            time = time.substring(0, 5);
        }
        return { date: chunks[0] || "", time: time };
    }

    function usesJalaliCalendar() {
        return document.body && document.body.dataset.useJalaliCalendar === "true";
    }

    function closeActiveTimePicker() {
        if (activeTimePicker) {
            activeTimePicker.classList.remove("is-open");
            var shell = activeTimePicker.horillaTimeShell;
            if (shell) {
                var display = shell.querySelector("[data-horilla-jalali-time-display]");
                if (display) {
                    display.setAttribute("aria-expanded", "false");
                }
            }
            activeTimePicker = null;
        }
    }

    function positionTimePicker(picker, anchor) {
        var rect = anchor.getBoundingClientRect();
        var pickerHeight = picker.offsetHeight || 220;
        var spaceBelow = window.innerHeight - rect.bottom;
        var top = spaceBelow >= pickerHeight + 8 ? rect.bottom + 6 : rect.top - pickerHeight - 6;
        var left = rect.left;
        var width = Math.max(rect.width, 220);
        if (document.documentElement.dir === "rtl") {
            left = rect.right - width;
        }
        if (left + width > window.innerWidth - 8) {
            left = window.innerWidth - width - 8;
        }
        if (left < 8) {
            left = 8;
        }
        picker.style.top = top + "px";
        picker.style.left = left + "px";
        picker.style.minWidth = width + "px";
    }

    function buildSelectOptions(min, max, selected) {
        var fragment = document.createDocumentFragment();
        for (var i = min; i <= max; i += 1) {
            var option = document.createElement("option");
            option.value = pad(i);
            option.textContent = pad(i);
            if (pad(i) === selected) {
                option.selected = true;
            }
            fragment.appendChild(option);
        }
        return fragment;
    }

    function updateTimeDisplay(displayInput, timeValue) {
        displayInput.value = timeValue || "";
    }

    function attachTimePicker(timeShell, displayInput, hiddenTimeInput, onSync) {
        var labels = getLabels();
        var picker = document.createElement("div");
        picker.className = "horilla-time-picker";
        picker.setAttribute("role", "dialog");
        picker.setAttribute("aria-label", labels.timePlaceholder);
        picker.horillaTimeShell = timeShell;

        var columns = document.createElement("div");
        columns.className = "horilla-time-picker__columns";

        var hourWrap = document.createElement("div");
        hourWrap.className = "horilla-time-picker__column";
        var hourLabel = document.createElement("span");
        hourLabel.className = "horilla-time-picker__label";
        hourLabel.textContent = labels.hour;
        var hourSelect = document.createElement("select");
        hourSelect.className = "horilla-time-picker__select";
        hourSelect.setAttribute("aria-label", labels.hour);

        var colon = document.createElement("span");
        colon.className = "horilla-time-picker__colon";
        colon.textContent = ":";

        var minuteWrap = document.createElement("div");
        minuteWrap.className = "horilla-time-picker__column";
        var minuteLabel = document.createElement("span");
        minuteLabel.className = "horilla-time-picker__label";
        minuteLabel.textContent = labels.minute;
        var minuteSelect = document.createElement("select");
        minuteSelect.className = "horilla-time-picker__select";
        minuteSelect.setAttribute("aria-label", labels.minute);

        hourWrap.appendChild(hourLabel);
        hourWrap.appendChild(hourSelect);
        minuteWrap.appendChild(minuteLabel);
        minuteWrap.appendChild(minuteSelect);
        columns.appendChild(hourWrap);
        columns.appendChild(colon);
        columns.appendChild(minuteWrap);

        var actions = document.createElement("div");
        actions.className = "horilla-time-picker__actions";
        var nowBtn = document.createElement("button");
        nowBtn.type = "button";
        nowBtn.className = "horilla-time-picker__btn horilla-time-picker__btn--ghost";
        nowBtn.textContent = labels.now;
        var applyBtn = document.createElement("button");
        applyBtn.type = "button";
        applyBtn.className = "horilla-time-picker__btn horilla-time-picker__btn--primary";
        applyBtn.textContent = labels.apply;
        actions.appendChild(nowBtn);
        actions.appendChild(applyBtn);

        picker.appendChild(columns);
        picker.appendChild(actions);
        document.body.appendChild(picker);

        function populateSelects(timeValue) {
            var parts = (timeValue || "09:00").split(":");
            var hour = pad(parseInt(parts[0], 10) || 0);
            var minute = pad(parseInt(parts[1], 10) || 0);
            hourSelect.innerHTML = "";
            minuteSelect.innerHTML = "";
            hourSelect.appendChild(buildSelectOptions(0, 23, hour));
            minuteSelect.appendChild(buildSelectOptions(0, 59, minute));
        }

        function applyTime(closePicker) {
            var timeValue = hourSelect.value + ":" + minuteSelect.value;
            hiddenTimeInput.value = timeValue;
            updateTimeDisplay(displayInput, timeValue);
            onSync();
            if (closePicker) {
                closeActiveTimePicker();
            }
        }

        function openPicker() {
            if (displayInput.disabled) {
                return;
            }
            closeActiveTimePicker();
            populateSelects(hiddenTimeInput.value);
            positionTimePicker(picker, timeShell);
            picker.classList.add("is-open");
            displayInput.setAttribute("aria-expanded", "true");
            activeTimePicker = picker;
            hourSelect.focus();
        }

        displayInput.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            openPicker();
        });

        displayInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openPicker();
            }
        });

        hourSelect.addEventListener("change", function () {
            applyTime(false);
        });
        minuteSelect.addEventListener("change", function () {
            applyTime(false);
        });

        nowBtn.addEventListener("click", function () {
            var now = new Date();
            var timeValue = pad(now.getHours()) + ":" + pad(now.getMinutes());
            populateSelects(timeValue);
            hiddenTimeInput.value = timeValue;
            updateTimeDisplay(displayInput, timeValue);
            onSync();
        });

        applyBtn.addEventListener("click", function () {
            applyTime(true);
        });

        picker.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    }

    function stylePickerInput(input) {
        input.readOnly = true;
        input.autocomplete = "off";
    }

    function syncDateInput(visibleInput) {
        var hiddenInput = visibleInput.horillaIsoInput;
        if (!hiddenInput) {
            return;
        }
        hiddenInput.value = jalaliStringToIsoDate(visibleInput.value.trim());
    }

    function syncDatetimeWrapper(wrapper) {
        var hiddenInput = wrapper.querySelector('input[data-horilla-jalali-iso="true"]');
        var dateInput = wrapper.querySelector("[data-horilla-jalali-date-part]");
        var timeInput = wrapper.querySelector("[data-horilla-jalali-time-part]");
        if (!hiddenInput || !dateInput) {
            return;
        }
        var isoDate = jalaliStringToIsoDate(dateInput.value.trim());
        var timeValue = timeInput && timeInput.value ? timeInput.value : "";
        if (!isoDate || !timeValue) {
            hiddenInput.value = "";
        } else {
            hiddenInput.value = isoDate + "T" + timeValue;
        }
    }

    function ensurePickerStarted() {
        if (pickerStarted || !window.jalaliDatepicker) {
            return;
        }
        window.jalaliDatepicker.startWatch({
            selector: "input[data-jdp]",
            autoShow: true,
            autoHide: true,
            hideAfterChange: true,
            persianDigits: false,
            time: false,
            zIndex: 10050,
        });
        pickerStarted = true;
    }

    function wrapDateInput(input) {
        if (!input || input.dataset[INIT_FLAG] === "true" || input.type !== "date") {
            return;
        }

        var labels = getLabels();
        var isoValue = input.value || "";
        var inputId = input.id;
        var inputRequired = input.required;
        var inputDisabled = input.disabled;

        var hiddenInput = document.createElement("input");
        hiddenInput.type = "hidden";
        hiddenInput.name = input.name || "";
        hiddenInput.id = inputId ? inputId + "_iso" : "";
        hiddenInput.value = isoValue;
        hiddenInput.dataset.horillaJalaliIso = "true";

        var dateInput = document.createElement("input");
        dateInput.type = "text";
        dateInput.className = resolveInputClass(input, false);
        stylePickerInput(dateInput);
        dateInput.setAttribute("data-jdp", "");
        dateInput.setAttribute("data-jdp-only-date", "");
        dateInput.setAttribute("data-horilla-jalali-visible", "true");
        dateInput.placeholder = labels.datePlaceholder;
        dateInput.dataset.horillaJalaliMode = "date";
        dateInput.dataset[INIT_FLAG] = "true";
        dateInput.value = isoDateToJalaliString(isoValue);
        if (inputId) {
            dateInput.id = inputId;
        }
        if (inputRequired) {
            dateInput.required = true;
        }
        if (inputDisabled) {
            dateInput.disabled = true;
        }
        dateInput.horillaIsoInput = hiddenInput;

        var outer = document.createElement("div");
        outer.className = "w-full";
        outer.appendChild(hiddenInput);
        outer.appendChild(dateInput);

        dateInput.addEventListener("jdp:change", function () {
            syncDateInput(dateInput);
        });
        dateInput.addEventListener("change", function () {
            syncDateInput(dateInput);
        });

        input.parentNode.replaceChild(outer, input);
    }

    function wrapDatetimeInput(input) {
        if (!input || input.dataset[INIT_FLAG] === "true" || input.type !== "datetime-local") {
            return;
        }

        var labels = getLabels();
        var isoValue = input.value || "";
        var parts = splitDatetimeLocal(isoValue);
        var inputId = input.id;
        var inputRequired = input.required;
        var inputDisabled = input.disabled;
        var hasMt = input.className.indexOf("mt-1") >= 0;

        var wrapper = document.createElement("div");
        wrapper.className = COMPOUND_CLASS;
        if (hasMt) {
            wrapper.classList.add("mt-1");
        }
        wrapper.dataset.horillaJalaliDatetime = "true";
        wrapper.dataset[INIT_FLAG] = "true";

        var hiddenInput = document.createElement("input");
        hiddenInput.type = "hidden";
        hiddenInput.name = input.name || "";
        hiddenInput.id = inputId ? inputId + "_iso" : "";
        hiddenInput.value = isoValue;
        hiddenInput.dataset.horillaJalaliIso = "true";

        var dateInput = document.createElement("input");
        dateInput.type = "text";
        dateInput.className = INNER_INPUT_CLASS + " horilla-jalali-datetime__date";
        stylePickerInput(dateInput);
        dateInput.setAttribute("data-jdp", "");
        dateInput.setAttribute("data-jdp-only-date", "");
        dateInput.setAttribute("data-horilla-jalali-date-part", "true");
        dateInput.placeholder = labels.datePlaceholder;
        dateInput.value = isoDateToJalaliString(parts.date);
        if (inputId) {
            dateInput.id = inputId;
        }
        if (inputRequired) {
            dateInput.required = true;
        }
        if (inputDisabled) {
            dateInput.disabled = true;
        }

        var separator = document.createElement("span");
        separator.className = "horilla-jalali-datetime__separator";
        separator.setAttribute("aria-hidden", "true");

        var timeShell = document.createElement("div");
        timeShell.className = "horilla-jalali-datetime__time";

        var timeDisplay = document.createElement("input");
        timeDisplay.type = "text";
        timeDisplay.className = INNER_INPUT_CLASS + " horilla-jalali-datetime__time-input";
        stylePickerInput(timeDisplay);
        timeDisplay.setAttribute("data-horilla-jalali-time-display", "true");
        timeDisplay.placeholder = labels.timePlaceholder;
        timeDisplay.setAttribute("role", "combobox");
        timeDisplay.setAttribute("aria-expanded", "false");
        timeDisplay.setAttribute("aria-haspopup", "dialog");
        if (inputDisabled) {
            timeDisplay.disabled = true;
        }

        var hiddenTimeInput = document.createElement("input");
        hiddenTimeInput.type = "hidden";
        hiddenTimeInput.setAttribute("data-horilla-jalali-time-part", "true");
        hiddenTimeInput.value = parts.time;

        updateTimeDisplay(timeDisplay, parts.time);
        timeShell.appendChild(timeDisplay);
        timeShell.appendChild(hiddenTimeInput);

        function syncWrapper() {
            syncDatetimeWrapper(wrapper);
        }

        dateInput.addEventListener("jdp:change", syncWrapper);
        dateInput.addEventListener("change", syncWrapper);
        attachTimePicker(timeShell, timeDisplay, hiddenTimeInput, syncWrapper);

        wrapper.appendChild(hiddenInput);
        wrapper.appendChild(dateInput);
        wrapper.appendChild(separator);
        wrapper.appendChild(timeShell);
        input.parentNode.replaceChild(wrapper, input);
    }

    function initHorillaJalaliInputs(root) {
        if (!usesJalaliCalendar()) {
            return;
        }
        ensurePickerStarted();
        var scope = root && root.querySelectorAll ? root : document;
        if (!scope.querySelectorAll) {
            return;
        }
        scope.querySelectorAll('input[type="date"]').forEach(wrapDateInput);
        scope.querySelectorAll('input[type="datetime-local"]').forEach(wrapDatetimeInput);
    }

    function syncAllHiddenInputs(root) {
        if (!usesJalaliCalendar()) {
            return;
        }
        var scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll("input[data-horilla-jalali-visible]").forEach(function (input) {
            syncDateInput(input);
        });
        scope.querySelectorAll("[data-horilla-jalali-datetime]").forEach(function (wrapper) {
            syncDatetimeWrapper(wrapper);
        });
    }

    document.addEventListener("click", function () {
        closeActiveTimePicker();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeActiveTimePicker();
        }
    });

    window.initHorillaJalaliInputs = initHorillaJalaliInputs;
    window.syncHorillaJalaliInputs = syncAllHiddenInputs;

    document.addEventListener("DOMContentLoaded", function () {
        initHorillaJalaliInputs(document);
    });

    document.body.addEventListener("htmx:afterSettle", function (event) {
        initHorillaJalaliInputs(event.detail.elt || document);
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        initHorillaJalaliInputs(event.detail.elt || document);
    });

    document.body.addEventListener("htmx:beforeRequest", function (event) {
        syncAllHiddenInputs(event.detail.elt || document);
    });

    document.body.addEventListener("submit", function (event) {
        syncAllHiddenInputs(event.target);
    }, true);
})(window, document);
