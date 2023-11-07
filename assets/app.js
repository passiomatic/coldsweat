import hotkeys from 'hotkeys-js';
import 'idiomorph';
import 'htmx.org';
window.htmx = require('htmx.org');

htmx.on("htmx:afterSwap", (e) => {
    if (e.detail.target.id == "dialog") {
        var dialogEl = e.detail.target;
        dialogEl.showModal();
    }
})

htmx.on("htmx:beforeSwap", (e) => {
    if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
        var dialogEl = e.detail.target;
        dialogEl.close();
        e.detail.shouldSwap = false;
    }
})

document.body.addEventListener("navChanged", function (evt) {
    // console.log("navChanged:",  evt.detail.url)
    htmx.ajax('GET', evt.detail.url, '#nav')
})

document.body.addEventListener("articleListChanged", function (evt) {
    // console.log("articleListChanged:",  evt.detail.url)    
    htmx.ajax('GET', evt.detail.url, '#panel')
})

window.addEventListener("DOMContentLoaded", (event) => {

    function makeEndpointURL(pathname) {
        var segments = [
            window.applicationURL,
            pathname
        ]
        return segments.join('')
    }

    // Innermost element that does not get replaced
    var listViewEl = document.getElementById("panel");
    // var navViewEl = document.getElementById("nav");
    // var dirty = false;

    const Sweat = {

        // onEntryLoad: function (id, title, event) {
        //     var entryEl = document.getElementById(`entry-${id}`);
        //     entryEl.classList.add('status-read')
        //     Sweat.loadEntry(id, title, event)
        // },

        setup: function () {
            window.addEventListener("popstate", (event) => {
                //console.log('popstate', event.state)
            });

            // Prev
            hotkeys('j', function (event, handler) {
                var currentCardInput = listViewEl.querySelector(".entry .entry-card input:checked");
                var prevCard = null;
                var prevCardInput = null;
                if (currentCardInput) {
                    var li = currentCardInput.parentNode.parentNode;
                    // @@TODO Skip headings
                    prevCard = li.previousElementSibling;
                    prevCardInput = prevCard.querySelector(".entry-card input");
                } else {
                    // Select first
                    prevCardInput = listViewEl.querySelector(".entry .entry-card input");
                }
                if (prevCardInput) {
                    prevCardInput.checked = true;
                    var entryEl = document.getElementById(`entry-${prevCardInput.value}`);
                    entryEl.classList.add('status-read');
                    // Sweat.mark(prevCardInput.value, 'read');
                    Sweat.loadEntry(prevCardInput.value, event);
                }
            });
            // Next
            hotkeys('k', function (event, handler) {
                var currentCardInput = listViewEl.querySelector(".entry .entry-card input:checked");
                var nextCard = null;
                var nextCardInput = null;
                if (currentCardInput) {
                    var li = currentCardInput.parentNode.parentNode;
                    // @@TODO Skip headings
                    nextCard = li.nextElementSibling;
                    nextCardInput = nextCard.querySelector(".entry-card input");
                } else {
                    // Select first
                    nextCardInput = listViewEl.querySelector(".entry .entry-card input");
                }
                if (nextCardInput) {
                    nextCardInput.checked = true;
                    var entryEl = document.getElementById(`entry-${nextCardInput.value}`);
                    entryEl.classList.add('status-read');
                    // Sweat.mark(nextCardInput.value, 'read')
                    Sweat.loadEntry(nextCardInput.value, event)
                }
            });
        },

        closeDialog: function (event) {
            var dialog = document.getElementById('dialog');
            //dialog.classList.remove("in"); 
            dialog.close();
        },

        openDialog: function (dialogEl, event) {
            dialogEl.showModal();
            //dialogEl.classList.add("in"); 
            return dialogEl;
        },

        shareEntry: async function (shareData) {
            if (navigator.share) {
                try {
                    await navigator.share(shareData);
                } catch (err) {
                    console.log('Error while sharing entry: ', err)
                }
            } else {
                // @@TODO Copy URL to clipboard as fallback 
            }
        }
    }

    Sweat.setup();
    window.Sweat = Sweat;

})