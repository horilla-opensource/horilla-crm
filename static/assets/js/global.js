//Generic Reasign Delete Confirm Modal
const horillaMessages = {
    confirm: gettext("Confirm"),
    close: gettext("Close"),
    cancel: gettext("Cancel"),
    selected: gettext("Selected"),
    downloadExcel: gettext("Do you want to download the excel file?"),
    downloadTemplate: gettext("Do you want to download the template?"),
    noRowsSelected: gettext("No rows are selected from the records."),
    confirmBulkDelete: gettext("Do you really want to delete all the selected records?"),
    confirmBulkArchive: gettext("Do you really want to archive all the selected records?"),
    confirmBulkUnArchive: gettext("Do you really want to unarchive all the selected records?"),
}

function OpenDeleteConfirmModal() {

    const $deleteConfirmModal = $("#deleteConfirmModal");
    const $deleteConfirmModalBox = $("#deleteConfirmModalBox");

    $deleteConfirmModal.removeClass("hidden");
    setTimeout(() => {
        $deleteConfirmModalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}


function CloseDeleteConfirmModal() {

    const $deleteConfirmModal = $("#deleteConfirmModal");
    const $deleteConfirmModalBox = $("#deleteConfirmModalBox");
    $deleteConfirmModalBox.html("");
    $deleteConfirmModalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");


    setTimeout(() => {
        $deleteConfirmModal.addClass("hidden");
    }, 300);
}

// end

function openDynamicModal() {

    // Fresh selection each time instead of cached selectors
    const $dynamicCreateModal = $("#dynamicCreateModal");
    const $dynamicCreateModalBox = $("#dynamicCreateModalBox");

    $dynamicCreateModal.removeClass("hidden");
    setTimeout(() => {
        $dynamicCreateModalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}

function closeDynamicModal() {
    // Fresh selection each time
    const $dynamicCreateModal = $("#dynamicCreateModal");
    const $dynamicCreateModalBox = $("#dynamicCreateModalBox");
    $dynamicCreateModalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $dynamicCreateModal.addClass("hidden");
    }, 300);
}

function openContentModal() {

    // Fresh selection each time instead of cached selectors
    const $ContentModal = $("#contentModal");
    const $ContentModalBox = $("#contentModalBox");

    $ContentModal.removeClass("hidden");
    setTimeout(() => {
        $ContentModalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}

function closeContentModal() {
    // Fresh selection each time
    const $ContentModal = $("#contentModal");
    const $ContentModalBox = $("#contentModalBox");
    $ContentModalBox.html("");
    $ContentModalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $ContentModal.addClass("hidden");
    }, 300);
}

function openContentModalSecond() {

    const $ContentModalSecond = $("#contentModalSecond");
    const $ContentModalBoxSecond = $("#contentModalBoxSecond");

    $ContentModalSecond.removeClass("hidden");
    setTimeout(() => {
        $ContentModalBoxSecond.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}

function closeContentModalSecond() {
    // Fresh selection each time
    const $ContentModalSecond = $("#contentModalSecond");
    const $ContentModalBoxSecond = $("#contentModalBoxSecond");

    $ContentModalBoxSecond.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $ContentModalSecond.addClass("hidden");
    }, 300);
}


//detail view modal

function openDetailModal() {

    // Fresh selection each time instead of cached selectors
    const $detailModal = $("#detailModal");
    const $detailModalBox = $("#detailModalBox");

    $detailModal.removeClass("hidden");
    setTimeout(() => {
        $detailModalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}

function closeDetailModal() {
    // Fresh selection each time
    const $detailModal = $("#detailModal");
    const $detailModalBox = $("#detailModalBox");

    $detailModalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $detailModal.addClass("hidden");
    }, 300);
}


function openModal() {

    const $modal = $("#dbmodal");
    const $modalBox = $("#modalBox");

    $modal.removeClass("hidden");
    setTimeout(() => {
        $modalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}


function closeModal() {

    const $modal = $("#dbmodal");
    const $modalBox = $("#modalBox");
    $modalBox.html("");
    $modalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");


    setTimeout(() => {
        $modal.addClass("hidden");
    }, 300);
}


function openhorillaModal() {


    const $modal = $("#horillaModal");
    const $modalBox = $("#horillaModalBox");

    $modal.removeClass("hidden");
    setTimeout(() => {
        $modalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}


function closehorillaModal() {

    const $modal = $("#horillaModal");
    const $modalBox = $("#horillaModalBox");
    $modalBox.html("");
    $modalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");


    setTimeout(() => {
        $modal.addClass("hidden");
    }, 300);
}


//FILTER MODAL

function openFilterModal() {

    const $filtermodal = $("#filtermodal");
    const $filtermodalBox = $("#filtermodalBox");

    $filtermodal.removeClass("hidden");
    setTimeout(() => {
        $filtermodalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}


function closeFilterModal() {

    const $filtermodal = $("#filtermodal");
    const $filtermodalBox = $("#filtermodalBox");

    $filtermodalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $filtermodal.addClass("hidden");
    }, 300);
}

//DELETE MODAL


function openDeleteModal() {
    const $deletemodal = $("#deletemodal");
    const $deletemodalBox = $("#deleteBox");

    $deletemodal.removeClass("hidden");
    setTimeout(() => {
        $deletemodalBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}

function closeDeleteModal() {
    const $deletemodal = $("#deletemodal");
    const $deletemodalBox = $("#deleteBox");

    $deletemodalBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $deletemodal.addClass("hidden");
    }, 300);
}

//MODAL CLOSE ONLY CLOSE CURRENT MODAL
function closeConfirm(button) {
    const modal = button.closest(".modal-wrapper");
    modal.classList.add("hidden");
}



function openDeleteModeModal() {
    //DELETE MODE MODAL
    const $deleteModeModal = $("#deleteModeModal");
    const $deleteModeBox = $("#deleteModeBox");
    $deleteModeModal.removeClass("hidden");
    setTimeout(() => {
        $deleteModeBox.removeClass("opacity-0 scale-95")
            .addClass("opacity-100 scale-100");
    }, 10);
}

function closeDeleteModeModal() {
    //DELETE MODE MODAL
    const $deleteModeModal = $("#deleteModeModal");
    const $deleteModeBox = $("#deleteModeBox");
    $deleteModeBox.removeClass("opacity-100 scale-100")
        .addClass("opacity-0 scale-95");
    setTimeout(() => {
        $deleteModeModal.addClass("hidden");
    }, 300);
}

function toggleAccordion(button) {
    const content = button.nextElementSibling;
    const svg = button.querySelector("svg");

    content.classList.toggle("open");
    svg.classList.toggle("rotate-90");
}

function isElementVisible(element) {
    const $targetSelector = $(element).attr("hx-target");
    const $targetEl = $($targetSelector);
    const isOpen = $targetEl.css("max-height") && $targetEl.css("max-height") !== "0px";

    return !isOpen;
}


function doBulkDeleteRequest(element) {
    const viewId = $(element).attr("id").replace("bulk-delete-btn-", "");
    const selectedIds = selectedRecordIds(viewId);

    if (selectedIds.length > 0) {
        htmx.trigger(element, "doRequest");
    } else {
        const modalContent = `
            <div class="p-6 text-center">
                <!-- Warning icon -->
                <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-red-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M12 9v2m0 4h.01M12 2a10 10 0 11-0 20 10 10 0 010-20z" />
                    </svg>
                </div>

                <h2 class="text-lg font-semibold text-gray-800 mb-2">No Rows Selected</h2>

                <p class="text-sm text-gray-500 mb-6">
                    Please select at least one record before attempting to delete.
                </p>

                <button id="closeDbModal"
                    class="px-6 py-2.5 text-sm border-[1px] border-[solid] bg-secondary-600 rounded-[5px] text-white btn-with-icon border-[#e54f38] [transition:.3s]">
                    Close
                </button>
            </div>
        `;

        // Inject modal content and display
        $("#deleteModeBox").html(modalContent);
        $("#deleteModeModal").removeClass("hidden").addClass("flex");

        // Animate modal appearance
        setTimeout(() => {
            $("#deleteModeBox").removeClass("opacity-0 scale-95").addClass("opacity-100 scale-100");
        }, 10);

        // Close modal logic
        $("#closeDbModal").on("click", function () {
            closeDeleteModeModal();
        });
    }
}


function formatOption(option) {
    if (!option.id) {
        return option.text;
    }
    var imgSrc = $(option.element).data('img');
    if (imgSrc) {
        return $(
            '<span><img src="' + imgSrc + '" class="w-6 h-6 rounded-full inline-block mr-2" /> ' + option.text + '</span>'
        );
    }
    return option.text;
}

var activeSidebarLink = () => {
    let activeLinkId = "#" + localStorage.getItem("activeSidebarLinkId");
    if (activeLinkId) {
        $(activeLinkId).addClass("bg-primary-600 text-white").find("img").css("filter", "brightness(0) invert(1)");
    }
}
// sidebar script start from here onwards

$(document).ready(function () {
    initializeSelect2Pagination();
    safeInitializeSelect2();
    showMessages();


    const ACTIVE_FILTER = "brightness(0) invert(1)";
    const INACTIVE_FILTER = "brightness(0) saturate(100%) invert(52%) sepia(0%) saturate(0%) hue-rotate(179deg) brightness(92%) contrast(85%)";
    const $navLinks = $("nav a.nav-link");

    // Correct sub-sidebar selector

    // const $subSidebar = $("#sideMenu");
    // if ($subSidebar.length === 0) {
    //     console.warn("Sub-sidebar not found with selector '#sideMenu ul'. Check your HTML structure.");
    // }

    const APP_SECTION_MAPPING = window.APP_SECTION_MAPPING || {};

    function getAppLabelFromUrl() {
        const path = window.location.pathname;
        const pathParts = path.split('/').filter(part => part.length > 0);
        return pathParts[0] || 'horilla_core';
    }

    function getSectionFromAppLabel(appLabel) {
        for (const [section, apps] of Object.entries(APP_SECTION_MAPPING)) {
            if (Array.isArray(apps) && apps.includes(appLabel)) {
                return section;
            }
        }
        return 'home';
    }

    function getActiveSection() {
        const urlParams = new URLSearchParams(window.location.search);
        const sectionFromUrl = urlParams.get('section');

        if (sectionFromUrl) {
            return sectionFromUrl;
        }

        const appLabel = getAppLabelFromUrl();
        const sectionFromApp = getSectionFromAppLabel(appLabel);

        return sectionFromApp || localStorage.getItem("currentActiveSection") || 'home';
    }

    // function getActiveSection() {
    //     const appLabel = getAppLabelFromUrl();
    //     const sectionFromApp = getSectionFromAppLabel(appLabel);
    //     const urlParams = new URLSearchParams(window.location.search);
    //     const sectionFromUrl = urlParams.get('section');
    //     const activeSection = sectionFromApp || sectionFromUrl || localStorage.getItem("currentActiveSection") || 'home';

    //     return activeSection;
    // }

    function getSectionSpecificSubsectionId(sectionId) {
        return localStorage.getItem(`activeSidebarLinkId_${sectionId}`) || localStorage.getItem("activeSidebarLinkId");
    }

    function setActiveNavLink($link, sectionId) {
        $navLinks.removeClass('active').find("img").css("filter", "");
        $link.addClass('active').find("img").css("filter", ACTIVE_FILTER);
        localStorage.setItem("activeNavLinkId", sectionId);
        localStorage.setItem("currentActiveSection", sectionId);

        if (sectionId === "home") {
            localStorage.setItem("sidebarClicked", "false");
            localStorage.removeItem("activeSidebarLinkId");
            localStorage.removeItem("activeSidebarLinkId_home");
        }
    }

    function setActiveSubsectionLink($link, sectionId) {
        $("ul a.sidebar-link").removeClass("bg-primary-600 text-white").find("img").css("filter", INACTIVE_FILTER);
        $link.addClass("bg-primary-600 text-white").find("img").css("filter", ACTIVE_FILTER);

        const linkId = $link.attr("id");
        if (linkId && sectionId) {
            localStorage.setItem(`activeSidebarLinkId_${sectionId}`, linkId);
            localStorage.setItem("activeSidebarLinkId", linkId);
            localStorage.setItem("sidebarClicked", "true");
        }
    }

    function activateFirstSubsectionItem(sectionId) {
        const $subsectionLinks = $("ul a.sidebar-link").filter(`[data-section="${sectionId}"]`);
        if (!$subsectionLinks.length) {
            const $allLinks = $("ul a.sidebar-link");
            if ($allLinks.length) {
            } else {
                return;
            }
        }

        let $activeLink = null;
        const sidebarClicked = localStorage.getItem("sidebarClicked") === "true";
        const activeSubItemId = getSectionSpecificSubsectionId(sectionId);
        const lastActiveSection = localStorage.getItem("lastActiveSection");
        const appLabel = getAppLabelFromUrl();

        const isSectionSwitch = lastActiveSection && lastActiveSection !== sectionId;

        const $appLabelLink = $subsectionLinks.filter(`#${appLabel}`);
        if ($appLabelLink.length) {
            $activeLink = $appLabelLink;
        } else if (isSectionSwitch || !sidebarClicked || sectionId === "home") {
            $activeLink = $subsectionLinks.first();
            const firstLinkId = $activeLink ? $activeLink.attr("id") : null;
            if (firstLinkId) {
                localStorage.setItem(`activeSidebarLinkId_${sectionId}`, firstLinkId);
                localStorage.setItem("activeSidebarLinkId", firstLinkId);
                localStorage.setItem("sidebarClicked", "false");
            }
        } else {
            $activeLink = activeSubItemId ? $subsectionLinks.filter(`#${activeSubItemId}`) : $subsectionLinks.first();


            if (!$activeLink.length) {
                $("#hiddenReloadSidebar").click();
                console.warn("No sub-sidebar link found, triggering reload.");
                return; // prevent continuing with null link
            }

        }

        if ($activeLink && $activeLink.length) {
            setActiveSubsectionLink($activeLink, sectionId);
        } else {
            const $fallbackLink = $subsectionLinks.first() || $("ul a.sidebar-link").first();
            if ($fallbackLink.length) {
                setActiveSubsectionLink($fallbackLink, sectionId);
            }
        }

        localStorage.setItem("lastActiveSection", sectionId);
    }

    function initFromUrl() {
        const currentSection = getActiveSection();
        const $sectionLink = $navLinks.filter(`#${currentSection}`);
        if ($sectionLink.length) {
            setActiveNavLink($sectionLink, currentSection);
        }

        const currentHref = window.location.href;
        localStorage.setItem('last-visited-url', currentHref);


        activateFirstSubsectionItem(currentSection);
    }

    document.body.addEventListener("htmx:afterSwap", function () {
        const currentSection = getActiveSection();
        const $sectionLink = $navLinks.filter(`#${currentSection}`);
        if ($sectionLink.length) {
            setActiveNavLink($sectionLink, currentSection);
        }
        activateFirstSubsectionItem(currentSection);
    });

    var activeSidebarLink = () => {
        let activeLinkId = "#" + localStorage.getItem("activeSidebarLinkId");
        if (activeLinkId) {
            $(activeLinkId).addClass("bg-primary-600 text-white").find("img").css("filter", "brightness(0) invert(1)");
        }
    }

    initFromUrl();

    $("nav").on("click", "a.nav-link", function () {
        const $clickedLink = $(this);
        const clickedSection = $clickedLink.attr("id");
        const currentActiveSection = getActiveSection();

        if (currentActiveSection) {
            localStorage.setItem("lastActiveSection", currentActiveSection);
        }

        const isClickingSameSection = currentActiveSection === clickedSection;

        setActiveNavLink($clickedLink, clickedSection);

        if (isClickingSameSection) {
            localStorage.setItem("sidebarClicked", "false");
            localStorage.setItem("lastActiveSection", "temp_reset");
        }
    });

    $("body")
        .on("click", "ul a.sidebar-link", function () {
            const $link = $(this);
            const currentSection = getActiveSection();
            setActiveSubsectionLink($link, currentSection);
            localStorage.setItem('last-visited-url', window.location.href);
        })
        .on("mouseenter", "ul a.sidebar-link", function () {
            const $link = $(this);
            if (!$link.hasClass("bg-primary-600")) {
                $link.find("img").css("filter", ACTIVE_FILTER);
            }
        })
        .on("mouseleave", "ul a.sidebar-link", function () {
            const $link = $(this);
            if (!$link.hasClass("bg-primary-600")) {
                $link.find("img").css("filter", INACTIVE_FILTER);
            }
        });

    const $tableContainer = $("#tableContainer");
    $tableContainer.on("scroll", function () {
        const scrollTop = $tableContainer.scrollTop();
        const scrollHeight = $tableContainer[0].scrollHeight;
        const clientHeight = $tableContainer[0].clientHeight;
        const threshold = 100;

        if (scrollHeight - scrollTop - clientHeight < threshold) {
            const $sentinel = $tableContainer.find("tr.htmx-sentinel");
            if ($sentinel.length && !$sentinel.hasClass("htmx-request")) {
                htmx.trigger($sentinel[0], "htmx:trigger");
            }
        }
    });

    activeSidebarLink();


    document.addEventListener("DOMContentLoaded", function () {
        const hiddenReloadSidebar = document.getElementById("hiddenReloadSidebar");

        if (hiddenReloadSidebar) {
            hiddenReloadSidebar.addEventListener("click", function () {
                const appLabel = this.getAttribute("data-app-label");
                const section = getSectionFromAppLabel(appLabel);

                if (!section) {
                    console.warn("No section found for app label:", appLabel);
                    return;
                }

                const reloadUrl = `${window.location.pathname}?section=${section}`;

                // Let hx-swap-oob handle the swap
                htmx.ajax("GET", reloadUrl)
                    .then(() => {
                        activateFirstSubsectionItem(section);
                    })
                    .catch((err) => {
                        console.error(
                            "Failed to reload sub-sidebar for section:",
                            section,
                            err
                        );
                    });
            });
        }
    });



    document.body.addEventListener("htmx:afterSwap", function () {
        const currentSection = getActiveSection();
        const $sectionLink = $navLinks.filter(`#${currentSection}`);
        if ($sectionLink.length) {
            setActiveNavLink($sectionLink, currentSection);
        }

        activateFirstSubsectionItem(currentSection);
    });
    document.body.addEventListener("htmx:afterSettle", function () {
        const currentSection = getActiveSection();
        const $sectionLink = $navLinks.filter(`#${currentSection}`);
        if ($sectionLink.length) {
            setActiveNavLink($sectionLink, currentSection);
        }

        activateFirstSubsectionItem(currentSection);
    });

});

// Sidebar script end here

const tableData = new Map();

function getCurrentViewId(element) {
    const $tableContainer = $(element).closest("[id^='table-container-']");
    return $tableContainer.data("view-id") || "";
}

function initializeRecordIds(recordIds, viewId) {
    if (!viewId) {
        console.warn("No viewId provided");
        return;
    }

    // Initialize table-specific data
    tableData.set(viewId, {
        allRecordIds: recordIds && Array.isArray(recordIds) && recordIds.length ? recordIds.map(String) : [],
        selectedRecordIds: [],
        allSelected: false,
    });

    const table = tableData.get(viewId);
    const $tableContainer = $(`#table-container-${viewId}`);

    if (table.allRecordIds.length) {
        $tableContainer.find(".total-count").text(table.allRecordIds.length);
        const storedSelections = sessionStorage.getItem(`selectedRecordIds_${viewId}`);
        if (storedSelections) {
            try {
                table.selectedRecordIds = JSON.parse(storedSelections).map(String);
                table.allSelected =
                    table.selectedRecordIds.length === table.allRecordIds.length &&
                    table.allRecordIds.every((id) => table.selectedRecordIds.includes(id));
            } catch (e) {
                console.error("Error parsing stored selections for viewId", viewId, e);
                table.selectedRecordIds = [];
            }
        }
        updateCheckboxStates(viewId);
        updateActionButtonsVisibility(viewId);
    }
}

function selectAll(checked, viewId) {
    if (!viewId) return;
    const table = tableData.get(viewId);
    if (!table) return;

    table.allSelected = checked;
    table.selectedRecordIds = checked ? [...table.allRecordIds] : [];
    sessionStorage.setItem(`selectedRecordIds_${viewId}`, JSON.stringify(table.selectedRecordIds));

    const $tableContainer = $(`#table-container-${viewId}`)

    $tableContainer.find("input[data-role='row-select']").prop("checked", checked);
    $tableContainer.find("input[data-role='select-all']").prop("checked", checked);


    updateActionButtonsVisibility(viewId);
}

function clearSelections(viewId) {
    if (!viewId) return;
    const table = tableData.get(viewId);
    if (!table) return;

    table.selectedRecordIds = [];
    table.allSelected = false;
    sessionStorage.removeItem(`selectedRecordIds_${viewId}`);

    const $tableContainer = $(`#table-container-${viewId}`);

    $tableContainer.find("input[data-role='row-select']").prop("checked", false);
    $tableContainer.find("input[data-role='select-all']").prop("checked", false);


    updateActionButtonsVisibility(viewId);
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Fixed debounced version of updateActionButtonsVisibility with correct selectors
const updateActionButtonsVisibility = debounce(function (viewId) {
    if (!viewId) return;
    const table = tableData.get(viewId);
    if (!table) return;

    const totalSelectedCount = table.selectedRecordIds.length;
    const hasSelections = totalSelectedCount > 0;

    // Use the correct selectors with view ID suffix
    $(`#export-all-btn-${viewId}, #bulk-update-btn-${viewId}, #unselect-all-btn-${viewId}, #bulk-delete-btn-${viewId}, [id^="bulk-action-"][id$="-${viewId}"],#total-selected-count-${viewId}`)
        .toggle(hasSelections);

    if (hasSelections) {
        $(`#selected-text-${viewId}`).text(`${totalSelectedCount}`);
        $(`#unselect-text-${viewId}`).text(`${totalSelectedCount}`);
    }

    $(`#select-all-btn-${viewId}`).toggle(table.allRecordIds.length > 0 && !table.allSelected);
}, 100);

function updateCheckboxStates(viewId) {
    if (!viewId) return;
    const table = tableData.get(viewId);
    if (!table) return;

    const $tableContainer = $(`#table-container-${viewId}`);
    $tableContainer.find("input[data-role='row-select']").each(function () {
        const id = $(this).val();
        $(this).prop("checked", table.selectedRecordIds.includes(id));
    });

    const checkedCount = $tableContainer.find("input[data-role='row-select']:checked").length;
    const totalVisible = $tableContainer.find("input[data-role='row-select']").length;
    $tableContainer
        .find("input[data-role='select-all']")
        .prop("checked", checkedCount === totalVisible && totalVisible > 0);
}

function reorderTableRows(viewId, $rowsToAdd = []) {
    if (!viewId) return;
    const table = tableData.get(viewId);
    if (!table) return;

    const $tbody = $(`#table-container-${viewId} #data-container-${viewId}`);
    const $existingRows = $tbody.find("tr").not(".separator").get();
    const allRows = [...$existingRows, ...$rowsToAdd];

    const selectedRows = [];
    const unselectedRows = [];
    let sentinelRow = null;

    allRows.forEach((row) => {
        const $row = $(row);
        if ($row.hasClass("htmx-sentinel")) {
            sentinelRow = $row;
        } else {
            const id = $row.find("input[data-role='row-select']").val();
            if (table.selectedRecordIds.includes(id)) {
                selectedRows.push($row);
            } else {
                unselectedRows.push($row);
            }
        }
    });

    $tbody.empty();
    selectedRows.forEach(($row) => $tbody.append($row));
    unselectedRows.forEach(($row) => $tbody.append($row));
    if (sentinelRow) {
        $tbody.append(sentinelRow);
    }
}

function processInfiniteScrollRows(viewId, $newRows) {
    if (!viewId) return;
    const table = tableData.get(viewId);
    if (!table) return;

    $newRows.each(function () {
        const $checkbox = $(this).find("input[data-role='row-select']");
        const id = $checkbox.val();
        $checkbox.prop("checked", table.selectedRecordIds.includes(id));
    });

    reorderTableRows(viewId, $newRows);
}

function processNewRecords(viewId) {
    updateCheckboxStates(viewId);
    reorderTableRows(viewId);
    updateActionButtonsVisibility(viewId);
}

// Helper function to get selected record IDs (used by HTMX)
function selectedRecordIds(viewId) {
    const table = tableData.get(viewId);
    return table ? table.selectedRecordIds : [];
}

// Initialize all tables on document ready
$(document).ready(function () {
    $("[id^='table-container-']").each(function () {
        const $tableContainer = $(this);
        const viewId = $tableContainer.data("view-id");
        const recordIds = JSON.parse($tableContainer.attr("data-record-ids") || "[]");
        initializeRecordIds(recordIds, viewId);
    });

    // Checkbox change event for individual rows
    $(document).on("change", "input[data-role='row-select']", function () {
        const viewId = getCurrentViewId(this);
        const table = tableData.get(viewId);
        if (!table) return;

        const id = $(this).val();
        if ($(this).prop("checked")) {
            if (!table.selectedRecordIds.includes(id)) {
                table.selectedRecordIds.push(id);
            }
        } else {
            table.selectedRecordIds = table.selectedRecordIds.filter((selectedId) => selectedId !== id);
            table.allSelected = false;
        }

        sessionStorage.setItem(`selectedRecordIds_${viewId}`, JSON.stringify(table.selectedRecordIds));
        updateCheckboxStates(viewId);
        updateActionButtonsVisibility(viewId);
        // reorderTableRows(viewId); // Add this to reorder rows when individual checkboxes change
    });

    // Select all checkbox event
    $(document).on("change", "input[data-role='select-all']", function () {
        const viewId = getCurrentViewId(this);
        selectAll($(this).prop("checked"), viewId);
        reorderTableRows(viewId);
    });

    $(document).on("htmx:afterSwap", function (event) {
        const $target = $(event.target);

        let $dataContainer = null;
        let viewId = null;

        if ($target.is("[id^='data-container-']")) {
            $dataContainer = $target;
            viewId = $dataContainer.attr("id").replace("data-container-", "");
        }
        else {
            $dataContainer = $target.find("[id^='data-container-']");
            if ($dataContainer.length) {
                viewId = $dataContainer.attr("id").replace("data-container-", "");
            }
        }

        if ($dataContainer && $dataContainer.length && viewId) {
            const isInfiniteScroll = event.detail.elt.classList.contains("htmx-sentinel");
            if (isInfiniteScroll) {
                const $newRows = $(event.detail.xhr.response).filter("tr");
                processInfiniteScrollRows(viewId, $newRows);
            } else {
                const $tableContainer = $(`#table-container-${viewId}`);
                const recordIds = JSON.parse($tableContainer.attr("data-record-ids") || "[]");
                initializeRecordIds(recordIds, viewId);
                processNewRecords(viewId);
            }
        }

        if (event.detail.target.id === "filtermodalBox") {
            $('#filtermodal').removeClass("hidden");
            $('#filtermodalBox').removeClass("opacity-0 scale-95").addClass("opacity-100 scale-100");
        }
    });

});

function closeFilterModal() {
    $('#filtermodal').addClass("hidden");
    $('#filtermodalBox').addClass("opacity-0 scale-95").removeClass("opacity-100 scale-100");
}

// export functionality

function exportSelected(viewId) {
    const table = tableData.get(viewId);
    const $tableContainer = $(`#table-container-${viewId}`);
    const selectedIds = (table && table.selectedRecordIds.length > 0)
        ? table.selectedRecordIds
        : $tableContainer.find("input[data-role='row-select']:checked").map(function () {
            return $(this).val();
        }).get();

    if (selectedIds.length === 0) {
        alert("No items selected for export");
        return;
    }

    openExport();
    $("#exportRecordIds").val(JSON.stringify(selectedIds));
}

function openExport() {
    const modal = document.getElementById("exportModal");
    const modalBox = document.getElementById("exportBox");

    modal.classList.remove("hidden");
    setTimeout(() => {
        modalBox.classList.remove("opacity-0", "scale-95");
        modalBox.classList.add("opacity-100", "scale-100");
    }, 10);
}

function closeExport() {
    const modal = document.getElementById("exportModal");
    const modalBox = document.getElementById("exportBox");

    modalBox.classList.remove("opacity-100", "scale-100");
    modalBox.classList.add("opacity-0", "scale-95");
    setTimeout(() => {
        modal.classList.add("hidden");
    }, 300);
}

// function closeModal() {
//   // Hide the modal
//   document.getElementById('dbmodal').classList.add('hidden');
//   document.getElementById('modalBox').classList.add('opacity-0', 'scale-95');
//   document.getElementById('modalBox').classList.remove('opacity-100', 'scale-100');

//   // Reset the form (assuming the form has an ID, e.g., 'bulkUpdateForm')
//   const form = document.getElementById('bulkUpdateForm');
//   if (form) {
//     form.reset();
//     form.innerHTML = '';
//   }
// }

// Add event handler for form submission
$("#exportForm").on("submit", function (e) {
    const selectedColumns = $("input[name='export_columns']:checked").map(function () {
        return $(this).val();
    }).get();

    const exportFormat = $("#exportFormat").val();
    if (!exportFormat) {
        alert("Please select an export format");
        e.preventDefault();
        return;
    }
});

///end of export functionality





// Initialize dropdowns
$(document).on('htmx:afterSwap', function (event) {
    if (window.Dropdown) {
        $('[data-dropdown-toggle]').each(function () {
            var $toggle = $(this);
            var targetId = $toggle.attr('data-dropdown-toggle');
            var $target = $('#' + targetId);

            if (!$target.data('flowbiteInitialized')) {
                new Dropdown($target[0], $toggle[0], {
                    placement: $toggle.attr('data-dropdown-placement') || 'bottom'
                });
                $target.data('flowbiteInitialized', true);
            }
        });
    }
});

//  $(document).on("click", "#clear-select-btn", function () {
//  clearSelections();
//  });

$(document).on("click", "[id^='clear-select-btn-']", function () {
    const viewId = getCurrentViewId(this);
    clearSelections(viewId);
});

updateActionButtonsVisibility();




let draggedColumn = null;

function drag(ev) {
    ev.dataTransfer.setData("text", ev.target.id);
}

function allowDrop(ev) {
    ev.preventDefault();
    const target = ev.target.closest(".kanban-block");
    if (target) {
        target.classList.add("highlight");
    }
}
function drop(ev) {
    ev.preventDefault();

    if (!ev.dataTransfer) {
        return;
    }

    const data = ev.dataTransfer.getData("text");
    const target = ev.target.closest(".kanban-block");

    if (!target) {
        return;
    }

    target.classList.remove("highlight");

    // Get current query parameters from the URL to preserve filters and search
    const currentQuery = new URLSearchParams(window.location.search);

    if (data.startsWith("column-")) {
        const kanbanView = document.getElementById("kanbanview");
        const allowColumnReorder = kanbanView.dataset.allowColumnReorder === "true";

        if (!allowColumnReorder) {
            return;
        }

        const columnKey = data.replace("column-", "");
        const draggedColumn = document.querySelector(`.kanban-block[data-column-key="${columnKey}"]`);

        if (draggedColumn && draggedColumn !== target) {
            const parent = target.parentNode;
            const allColumns = Array.from(parent.querySelectorAll(".kanban-block"));
            const draggedIndex = allColumns.indexOf(draggedColumn);
            const targetIndex = allColumns.indexOf(target);

            // Insert before or after based on drag direction
            if (draggedIndex < targetIndex) {
                if (target.nextSibling) {
                    parent.insertBefore(draggedColumn, target.nextSibling);
                } else {
                    parent.appendChild(draggedColumn);
                }
            } else {
                parent.insertBefore(draggedColumn, target);
            }

            const appLabel = kanbanView.dataset.appLabel;
            const modelName = kanbanView.dataset.modelName;
            const csrfToken = kanbanView.dataset.csrfToken;
            const className = kanbanView.dataset.className;



            const newColumnOrder = Array.from(document.querySelectorAll(".kanban-block")).map(
                (col) => col.dataset.columnKey
            );

            // Include ALL current query parameters in the POST values
            const postValues = {
                column_order: JSON.stringify(newColumnOrder),
                app_label: appLabel,
                model_name: modelName,

                class_name: className,

            };

            // Append all query parameters
            currentQuery.forEach((value, key) => {
                // Handle multi-value parameters correctly
                if (postValues[key]) {
                    if (!Array.isArray(postValues[key])) {
                        postValues[key] = [postValues[key]];
                    }
                    postValues[key].push(value);
                } else {
                    postValues[key] = value;
                }
            });

            htmx.ajax("POST", `/generics/update-kanban-column-order/${appLabel}/${modelName}/`, {
                target: "#kanbancontainer",
                swap: "innerHTML",
                headers: {
                    "X-CSRFToken": csrfToken,
                },
                values: postValues,
            })
        }
    } else {
        // Handle item dragging
        const draggedElement = document.getElementById(data);
        if (draggedElement && target) {
            target.querySelector(".items-container").appendChild(draggedElement);

            const targetColumn = target.dataset.columnKey;
            const itemId = data.split("-")[1];

            const kanbanView = document.getElementById("kanbanview");
            const appLabel = kanbanView.dataset.appLabel;
            const modelName = kanbanView.dataset.modelName;
            const csrfToken = kanbanView.dataset.csrfToken;
            const className = kanbanView.dataset.className;

            // Include ALL current query parameters in the POST values
            const postValues = {
                item_id: itemId,
                new_column: targetColumn,
                app_label: appLabel,
                model_name: modelName,
                class_name: className,

            };

            // Append all query parameters
            currentQuery.forEach((value, key) => {
                // Handle multi-value parameters correctly
                if (postValues[key]) {
                    if (!Array.isArray(postValues[key])) {
                        postValues[key] = [postValues[key]];
                    }
                    postValues[key].push(value);
                } else {
                    postValues[key] = value;
                }
            });

            htmx.ajax("POST", `/generics/update-kanban-item/${appLabel}/${modelName}/`, {
                target: "#kanbancontainer",
                swap: "innerHTML",
                headers: {
                    "X-CSRFToken": csrfToken,
                },
                values: postValues,
            });
        }
    }
}

function columnDragStart(e) {
    const kanbanView = document.getElementById("kanbanview");
    const allowColumnReorder = kanbanView.dataset.allowColumnReorder === "true";

    if (!allowColumnReorder) {
        e.preventDefault();
        return;
    }

    draggedColumn = $(e.target).closest(".kanban-block");
    const event = e.originalEvent || e;
    if (event.dataTransfer) {
        const columnKey = draggedColumn.data("column-key");
        event.dataTransfer.setData("text", `column-${columnKey}`);
        event.dataTransfer.effectAllowed = "move";
    }
    setTimeout(() => draggedColumn.addClass("opacity-50"), 0);
}

function columnDragEnd(e) {
    if (draggedColumn) {
        draggedColumn.removeClass("opacity-50");
        draggedColumn = null;
    }
}

$(document).ready(function () {
    $(".kanban-block").each(function () {
        const block = $(this);

        block.on("dragover", function (e) {
            if (draggedColumn) {
                e.preventDefault();
            }
        });

        block.on("dragenter", function (e) {
            if (draggedColumn && block[0] !== draggedColumn[0]) {
                block.addClass("swap-highlight");
            }
        });

        block.on("dragleave", function (e) {
            block.removeClass("swap-highlight");
        });

        block.on("drop", function (e) {
            if (!draggedColumn || draggedColumn[0] === block[0]) return;

            block.removeClass("swap-highlight");

            const parent = block.parent();
            const allBlocks = parent.children();
            const draggedIndex = allBlocks.index(draggedColumn);
            const targetIndex = allBlocks.index(block);

            if (draggedIndex < targetIndex) {
                draggedColumn.insertAfter(block);
            } else {
                draggedColumn.insertBefore(block);
            }
        });
    });
});


function hxConfirm(element, messageText, hint) {
    const isCheckbox = element.type === 'checkbox';
    const wasChecked = isCheckbox ? element.checked : null;

    if (isCheckbox) {
        element.checked = !wasChecked;
    }

    let htmlContent = messageText;
    if (hint) {
        htmlContent += `
            <p style="margin: 10px 0; font-size:15px; font-style: italic; background: #fff8c4; padding: 6px 10px; border-radius: 4px; display: inline-block;">
                ${hint}
            </p>
        `;
    }

    Swal.fire({
        html: htmlContent,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: horillaMessages.confirm,
        cancelButtonText: horillaMessages.cancel,
        reverseButtons: true,
        showClass: {
            popup: `
                animate__animated
                animate__fadeInUp
                animate__faster
            `
        },
        hideClass: {
            popup: `
                animate__animated
                animate__fadeOutDown
                animate__faster
            `
        }
    }).then((result) => {
        if (result.isConfirmed) {
            if (isCheckbox) {
                element.checked = !wasChecked;
            }
            htmx.trigger(element, 'confirmed');
        } else {
            return false;
        }
    });
}

function hxConfirmForm(element, messageText) {
    Swal.fire({
        text: messageText,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: horillaMessages.confirm,
        cancelButtonText: horillaMessages.cancel,
        reverseButtons: true,
        showClass: {
            popup: `
  animate__animated
  animate__fadeInUp
  animate__faster
  `
        },
        hideClass: {
            popup: `
  animate__animated
  animate__fadeOutDown
  animate__faster
  `
        }
    }).then((result) => {
        if (result.isConfirmed) {
            htmx.trigger(element.closest('form'), 'submit');
        }
    });
}

function showMessages() {
    $("#messages-container .message").each(function () {
        var $message = $(this);
        var level = $message.data("level");
        var messageText = $message.data("message");

        Swal.fire({
            toast: true,
            position: "top-end",
            icon: level,
            title: messageText,
            showConfirmButton: false,
            timer: 4000,
            timerProgressBar: true,
            customClass: {
                popup: `custom-toast toast-${level}`
            },
            didOpen: (toast) => {
                toast.addEventListener("mouseenter", Swal.stopTimer);
                toast.addEventListener("mouseleave", Swal.resumeTimer);
            }
        });

        $message.remove();
    });
}


function initializeSelect2Pagination() {
    const select2Elements = $('.select2-pagination:not(.select2-hidden-accessible)');
    if (select2Elements.length === 0) {
        return;
    }

    select2Elements.each(function (index) {
        const $this = $(this);
        const url = $this.data('url');
        const placeholder = $this.data('placeholder') || 'Select an option...';
        const initialData = $this.data('initial');
        const fieldName = $this.data('field-name') || `field_${index}`;

        const dependencyField = $this.data('dependency');
        const dependencyModel = $this.data('dependency-model');
        const dependencyFieldName = $this.data('dependency-field');
        const isMultiple = $this.prop('multiple');
        const elementId = $this.attr('id') || `select2_${fieldName}_${Math.random().toString(36).substr(2, 9)}`;

        // Store HTMX attributes
        const htmxAttrs = {
            'hx-get': $this.attr('hx-get'),
            'hx-target': $this.attr('hx-target'),
            'hx-swap': $this.attr('hx-swap'),
            'hx-trigger': $this.attr('hx-trigger'),
            'hx-include': $this.attr('hx-include'),
        };

        if (!$this.attr('id')) {
            $this.attr('id', elementId);
        }

        if (!$this.is(':visible') && !$this.closest('.modal').length) {
            return;
        }

        try {
            $this.select2({
                ajax: {
                    url: url,
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        let dependencyValue = undefined;
                        if (dependencyField) {
                            const $dependentField = $(`#id_${dependencyField}`);

                            dependencyValue = $dependentField.length ? $dependentField.val() : undefined;
                        }

                        return {
                            q: params.term || '',
                            page: params.page || 1,
                            field_name: fieldName,
                            form_class: $this.data('form-class'),
                            dependency_value: dependencyValue,
                            dependency_model: dependencyModel,
                            dependency_field: dependencyFieldName,
                        };
                    },
                    processResults: function (data, params) {
                        params.page = params.page || 1;
                        return {
                            results: data.results || [],
                            pagination: {
                                more: data.pagination && data.pagination.more,
                            },
                        };
                    },
                    cache: false,
                },
                placeholder: placeholder,
                minimumInputLength: 0,
                theme: 'default',
                width: '100%',
                dropdownParent: $this.closest('.modal-content').length ? $this.closest('.modal-content') : $('body'),
            });

            Object.keys(htmxAttrs).forEach((attr) => {
                if (htmxAttrs[attr]) {
                    $this.attr(attr, htmxAttrs[attr]);
                }
            });

            if (typeof htmx !== 'undefined') {
                htmx.process($this[0]);
            }

            $this.on('select2:select select2:unselect', function (e) {
                $(this).trigger('change');
                if (htmxAttrs['hx-get'] && typeof htmx !== 'undefined') {
                    htmx.trigger(this, 'change');
                }
            });

            if (initialData && initialData !== '') {
                loadInitialData($this, url, initialData, fieldName, isMultiple);
            }
        } catch (error) {
            console.error(`Error initializing Select2 for ${fieldName}:`, error);
        }
    });
}

function loadInitialData($element, url, initialData, fieldName, isMultiple) {


    // Handle different data types for initialData
    let ids = [];

    if (initialData === null || initialData === undefined || initialData === '') {
        return;
    }

    // Convert initialData to array of IDs
    if (typeof initialData === 'string') {
        ids = isMultiple ? initialData.split(',').filter(id => id.trim()) : [initialData.trim()];
    } else if (typeof initialData === 'number') {
        ids = [initialData.toString()];
    } else if (Array.isArray(initialData)) {
        ids = initialData.map(id => id.toString()).filter(id => id.trim());
    } else if (typeof initialData === 'object') {
        // Handle case where initialData might be an object with id property
        if (initialData.id) {
            ids = [initialData.id.toString()];
        } else {
            return;
        }
    } else {
        return;
    }

    // Filter out empty IDs
    ids = ids.filter(id => id && id.trim() !== '');

    if (ids.length === 0) {
        return;
    }


    $.ajax({
        url: url,
        dataType: 'json',
        data: {
            ids: ids.join(','),
            field_name: fieldName
        },
        success: function (data) {

            if (!data.results || data.results.length === 0) {
                return;
            }

            // Clear existing options (except empty option for single select)
            if (!isMultiple) {
                $element.find('option:not([value=""])').remove();
            } else {
                $element.empty();
            }

            // Add options and set values
            data.results.forEach(function (item) {
                const option = new Option(item.text, item.id, true, true);
                $element.append(option);
            });

            // Trigger change to update Select2
            $element.trigger('change');

        },

    });
}

// Function to safely initialize Select2 with retries
function safeInitializeSelect2() {
    const elementsToInitialize = $('.select2-pagination:not(.select2-hidden-accessible)');

    if (elementsToInitialize.length > 0) {
        initializeSelect2Pagination();

        // Check if any elements still need initialization after a short delay
        setTimeout(function () {
            const stillNeedInit = $('.select2-pagination:not(.select2-hidden-accessible)');
            if (stillNeedInit.length > 0) {
                initializeSelect2Pagination();
            }
        }, 500);
    }
}

// Initialize when DOM is ready

// Initialize after window load (in case some elements load later)
$(window).on('load', function () {
    safeInitializeSelect2();
});

// Manual trigger function for external use
window.reinitializeSelect2 = function () {
    safeInitializeSelect2();
};


function isElementChecked(element) {
    let message = element.getAttribute('data-message');
    if (element.checked)
        Swal.fire({
            html: message,
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: horillaMessages.confirm,
            cancelButtonText: horillaMessages.cancel,
            reverseButtons: true,
            showClass: {
                popup: `
    animate__animated
    animate__fadeInUp
    animate__faster
    `
            },
            hideClass: {
                popup: `
    animate__animated
    animate__fadeOutDown
    animate__faster
    `
            }
        }).then((result) => {
            if (result.isConfirmed) {
                return true
            }
            element.checked = false
            return false
        });
}

$(document).ready(function () {
    $("select").on("select2:select", function (e) {
        $(this).closest("select")[0].dispatchEvent(new Event("change"));
    });
});

// $(document).on("htmx:afterSettle", function () {
//     initializeSelect2Pagination();
//     alert();
//     $("select").on("select2:select", function (e) {
//         $(this).closest("select")[0].dispatchEvent(new Event("change"));
//     });
// });

$(document).on("htmx:afterSettle", function (e) {
    let elt = e.detail.elt;
    $(elt).find("select")
        .off("select2:select")
        .on("select2:select", function () {
            this.dispatchEvent(new Event("change"));
        });
    if ($(elt).find("select").length) {
        initializeSelect2Pagination();
    }
});


$(document).on('keydown', function (e) {
    if (e.key === "Escape" || e.keyCode === 27) {
        // Find all visible modals and hide them
        $('.fixed.inset-0.flex').each(function () {
            if (!$(this).hasClass('hidden')) {
                $(this).addClass('hidden'); // Hide modal
                $(this).find('.opacity-0').removeClass('opacity-100 scale-100').addClass('opacity-0 scale-95'); // Optional: reset animation
            }
        });
    }
});
