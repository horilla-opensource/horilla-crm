function closeShortcutModal() {
    $('#shortcutKeysModal').addClass('hidden');
}

function initShortcutKeys() {
    if (window.shortcutKeysInitialized) {
        return;
    }
    window.shortcutKeysInitialized = true;

    let activeModifier = null;
    let modalShown = false;
    let modifierHoldTimer = null;
    const MODIFIER_HOLD_DURATION = 200;
    const shortKeyDataUrl = "/shortkeys/short-key-data/";
    window.shortcutKeysCache = [];

    function createShortcutModal() {
        if ($('#shortcutKeysModal').length) return;

        const modalHTML = `
        <div id="shortcutKeysModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50 bg-[#00000030] flex">
            <div class="bg-white w-full max-w-md rounded-lg shadow-lg p-0 transition-all duration-300 md:min-w-[650px] opacity-100 scale-100">
                <div class="relative p-4 w-full max-w-2xl max-h-full">
                    <div class="relative bg-white rounded-lg shadow-sm">
                        <div class="p-5 pt-3 flex justify-between items-center">
                            <h2 class="text-md font-semibold">Available Shortcut Keys</h2>
                            <button type="button" class="text-gray-500 hover:text-red-500 text-xl" onclick="closeShortcutModal()">
                            <img src="/static/assets/icons/close.svg" alt="icon">
                            </button>
                        </div>
                        <div id="shortcut-content" class="overflow-hidden p-4 grid gap-2" style="max-height: 400px; overflow-y: auto;"></div>
                    </div>
                </div>
            </div>
        </div>
        `;
        $('body').append(modalHTML);
    }

    function fetchShortcutKeys(callback) {
        $.ajax({
            url: shortKeyDataUrl,
            method: 'GET',
            success: function(data) {
                const isMac = /mac|darwin/i.test(navigator.userAgent);
                window.shortcutKeysCache = data.shortcuts.map(sk => ({
                    key: sk.key.toUpperCase(),
                    command: sk.command.toLowerCase(),
                    displayCommand: (sk.command.toLowerCase() === 'alt' && isMac) ? 'OPTION' : sk.command.toUpperCase(),
                    displaySymbol: (sk.command.toLowerCase() === 'alt' && isMac) ? '⌥' : sk.command.toUpperCase(),
                    title: sk.title,
                    section: sk.section,
                    description: sk.description || '',
                    page: sk.page
                }));
                callback(window.shortcutKeysCache);
            },
            error: function(error) {
                console.error('Failed to fetch shortcut keys:', error);
                callback([]);
            }
        });
    }

    function showShortcutModal(keys) {
        createShortcutModal();
        $('#shortcutKeysModal').removeClass('hidden');

        let contentHTML = keys.map(sk => `
            <div class="flex items-center p-2 mb-1 border-[2px] border-primary-300 rounded-[5px] shadow-sm">
                <div class="min-w-[80px] flex gap-1">
                    <span class="bg-primary-300 text-primary-600 border border-primary-600 px-2 py-1 rounded text-xs font-semibold">${sk.displayCommand}</span>
                    <span>+</span>
                    <span class="bg-[#e1850d23] text-[#e1850d] border border-[#e1850d] px-2 py-1 rounded text-xs font-semibold">${sk.key}</span>
                </div>
                <div class="ml-4 flex-1">
                    <div class="font-medium">${sk.title}</div>
                    ${sk.description ? `<div class="text-xs text-gray-600">${sk.description}</div>` : ''}
                </div>
            </div>
        `).join('');

        $('#shortcut-content').html(contentHTML);
    }

    $(document).off("keydown.shortcutKeys keyup.shortcutKeys keydown.shortcutKeysEscape");

    fetchShortcutKeys(function(keys) {
        window.shortcutKeysCache = keys;

        $(document).on("keydown.shortcutKeys", function(e) {
            if (e.altKey && !activeModifier) {
                activeModifier = 'alt';

                if ($("input:focus, textarea:focus, select:focus").length) {
                    return;
                }

                if (!modalShown && !modifierHoldTimer) {
                    modifierHoldTimer = setTimeout(function() {
                        showShortcutModal(window.shortcutKeysCache);
                        modalShown = true;
                    }, MODIFIER_HOLD_DURATION);
                }
                return;
            }

            if (activeModifier && e.altKey) {
                const pressedKey = e.key.toUpperCase();

                if (modifierHoldTimer) {
                    clearTimeout(modifierHoldTimer);
                    modifierHoldTimer = null;
                }

                const match = window.shortcutKeysCache.find(
                    sk => sk.key === pressedKey && sk.command.toLowerCase() === 'alt'
                );

                if (match) {
                    e.preventDefault();

                    if ($("input:focus, textarea:focus, select:focus").length) {
                        return;
                    }

                    closeShortcutModal();
                    modalShown = false;
                    activeModifier = null;

                    const url = new URL(match.page, window.location.origin);
                    if (match.section) {
                        url.searchParams.set("section", match.section);
                    }
                    window.location.href = url.toString();
                }
            }
        });

        $(document).on("keyup.shortcutKeys", function(e) {
            if (!e.altKey && activeModifier === 'alt') {
                activeModifier = null;

                if (modifierHoldTimer) {
                    clearTimeout(modifierHoldTimer);
                    modifierHoldTimer = null;
                }
            }
        });

        $(document).on("keydown.shortcutKeysEscape", function(e) {
            if (e.key === "Escape") {
                closeShortcutModal();
                modalShown = false;
                activeModifier = null;

                if (modifierHoldTimer) {
                    clearTimeout(modifierHoldTimer);
                    modifierHoldTimer = null;
                }
            }
        });
    });
}

function refreshShortcutKeys() {
    const shortKeyDataUrl = "/shortkeys/short-key-data/";
    $.ajax({
        url: shortKeyDataUrl,
        method: 'GET',
        success: function(data) {
            const isMac = /mac|darwin/i.test(navigator.userAgent);
            window.shortcutKeysCache = data.shortcuts.map(sk => ({
                key: sk.key.toUpperCase(),
                command: sk.command.toLowerCase(),
                displayCommand: (sk.command.toLowerCase() === 'alt' && isMac) ? 'OPTION' : sk.command.toUpperCase(),
                displaySymbol: (sk.command.toLowerCase() === 'alt' && isMac) ? '⌥' : sk.command.toUpperCase(),
                title: sk.title,
                section: sk.section,
                description: sk.description || '',
                page: sk.page
            }));
        },
        error: function(error) {
            console.error('Failed to refresh shortcut keys:', error);
        }
    });
}

$(document).ready(initShortcutKeys);

$(document).on("htmx:afterSwap htmx:afterSettle", function(event) {
    const target = event.target;
    const triggeringElement = event.detail?.elt;

    if (
        (triggeringElement && (
            triggeringElement.id === 'short-key-create' ||
            triggeringElement.closest('[hx-get*="short_key"]') ||
            triggeringElement.closest('[hx-post*="short_key"]')
        )) ||
        (target && (
            target.id === 'short_key_list' ||
            target.closest('#short_key_list')
        ))
    ) {
        refreshShortcutKeys();
    }
});



// function closeShortcutModal() {
//     $('#shortcutKeysModal').addClass('hidden');
// }

// function initShortcutKeys() {
//     let activeModifier = null;
//     let modalShown = false;
//     let modifierHoldTimer = null;
//     const MODIFIER_HOLD_DURATION = 200;
//     const shortKeyDataUrl = "/shortkeys/short-key-data/";

//     function createShortcutModal() {
//         if ($('#shortcutKeysModal').length) return;

//         const modalHTML = `
//         <div id="shortcutKeysModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50 bg-[#00000030] flex">
//             <div class="bg-white w-full max-w-md rounded-lg shadow-lg p-0 transition-all duration-300 md:min-w-[650px] opacity-100 scale-100">
//                 <div class="relative p-4 w-full max-w-2xl max-h-full">
//                     <div class="relative bg-white rounded-lg shadow-sm">
//                         <div class="p-5 pt-3 flex justify-between items-center">
//                             <h2 class="text-md font-semibold">Available Shortcut Keys</h2>
//                             <button type="button" class="text-gray-500 hover:text-red-500 text-xl" onclick="closeShortcutModal()">
//                             <img src="/static/assets/icons/close.svg" alt="icon">
//                             </button>
//                         </div>
//                         <div id="shortcut-content" class="overflow-hidden p-4 grid gap-2" style="max-height: 400px; overflow-y: auto;"></div>
//                     </div>
//                 </div>
//             </div>
//         </div>
//         `;
//         $('body').append(modalHTML);
//     }

//     function fetchShortcutKeys(callback) {
//         $.ajax({
//             url: shortKeyDataUrl,
//             method: 'GET',
//             success: function(data) {
//                 const isMac = /mac|darwin/i.test(navigator.userAgent);
//                 const shortcutKeys = data.shortcuts.map(sk => ({
//                     key: sk.key.toUpperCase(),
//                     command: sk.command.toLowerCase(),
//                     displayCommand: (sk.command.toLowerCase() === 'alt' && isMac) ? 'OPTION' : sk.command.toUpperCase(),
//                     displaySymbol: (sk.command.toLowerCase() === 'alt' && isMac) ? '⌥' : sk.command.toUpperCase(),
//                     title: sk.title,
//                     section: sk.section,
//                     description: sk.description || '',
//                     page: sk.page
//                 }));
//                 callback(shortcutKeys);
//             },
//             error: function() {
//                 callback([]);
//             }
//         });
//     }

//     function showShortcutModal(shortcutKeys) {
//         createShortcutModal();
//         $('#shortcutKeysModal').removeClass('hidden');

//         let contentHTML = shortcutKeys.map(sk => `
//             <div class="flex items-center p-2 mb-1 border-[2px] border-primary-300 rounded-[5px] shadow-sm">
//                 <div class="min-w-[80px] flex gap-1">
//                     <span class="bg-primary-300 text-primary-600 border border-primary-600 px-2 py-1 rounded text-xs font-semibold">${sk.displayCommand}</span>
//                     <span>+</span>
//                     <span class="bg-[#e1850d23] text-[#e1850d] border border-[#e1850d] px-2 py-1 rounded text-xs font-semibold">${sk.key}</span>
//                 </div>
//                 <div class="ml-4 flex-1">
//                     <div class="font-medium">${sk.title}</div>
//                     ${sk.description ? `<div class="text-xs text-gray-600">${sk.description}</div>` : ''}
//                 </div>
//             </div>
//         `).join('');

//         $('#shortcut-content').html(contentHTML);
//     }

//     $(document).off("keydown.shortcutKeys keyup.shortcutKeys keydown.shortcutKeysEscape");

//     fetchShortcutKeys(function(shortcutKeys) {
//         $(document).on("keydown.shortcutKeys", function(e) {
//             if (e.altKey && !activeModifier) {
//                 activeModifier = 'alt';

//                 if ($("input:focus, textarea:focus, select:focus").length) {
//                     return;
//                 }

//                 if (!modalShown && !modifierHoldTimer) {
//                     modifierHoldTimer = setTimeout(function() {
//                         showShortcutModal(shortcutKeys);
//                         modalShown = true;
//                     }, MODIFIER_HOLD_DURATION);
//                 }
//                 return;
//             }

//             if (activeModifier && e.altKey) {
//                 const pressedKey = e.key.toUpperCase();

//                 if (modifierHoldTimer) {
//                     clearTimeout(modifierHoldTimer);
//                     modifierHoldTimer = null;
//                 }

//                 const match = shortcutKeys.find(
//                     sk => sk.key === pressedKey && sk.command.toLowerCase() === 'alt'
//                 );

//                 if (match) {
//                     e.preventDefault();

//                     if ($("input:focus, textarea:focus, select:focus").length) {
//                         return;
//                     }

//                     closeShortcutModal();
//                     modalShown = false;
//                     activeModifier = null;

//                     const url = new URL(match.page, window.location.origin);
//                     if (match.section) {
//                         url.searchParams.set("section", match.section);
//                     }
//                     window.location.href = url.toString();
//                 }
//             }
//         });

//         $(document).on("keyup.shortcutKeys", function(e) {
//             if (!e.altKey && activeModifier === 'alt') {
//                 activeModifier = null;

//                 if (modifierHoldTimer) {
//                     clearTimeout(modifierHoldTimer);
//                     modifierHoldTimer = null;
//                 }
//             }
//         });

//         $(document).on("keydown.shortcutKeysEscape", function(e) {
//             if (e.key === "Escape") {
//                 closeShortcutModal();
//                 modalShown = false;
//                 activeModifier = null;

//                 if (modifierHoldTimer) {
//                     clearTimeout(modifierHoldTimer);
//                     modifierHoldTimer = null;
//                 }
//             }
//         });
//     });
// }

// $(document).ready(initShortcutKeys);
// $(document).on("htmx:afterSwap htmx:afterSettle", initShortcutKeys);
