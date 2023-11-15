// import hotkeys from 'hotkeys-js';
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

    // Innermost element that does not get replaced
    var listViewEl = document.getElementById("panel");
    // var navViewEl = document.getElementById("nav");

    const Sweat = {

        toggleNode: function (id, event) {
            console.log('toggleNode ', id)
            var nodeEl = document.getElementById(id);
            nodeEl.classList.toggle('open')
        },

        setup: function () {

            // // Prev
            // hotkeys('j', function (event, handler) {
            //     var currentCardInput = listViewEl.querySelector(".entry .entry-card input:checked");
            //     var prevCard = null;
            //     var prevCardInput = null;
            //     if (currentCardInput) {
            //         var li = currentCardInput.parentNode.parentNode;
            //         prevCard = li.previousElementSibling;
            //         prevCardInput = prevCard.querySelector(".entry-card input");
            //     } else {
            //         // Select first
            //         prevCardInput = listViewEl.querySelector(".entry .entry-card input");
            //     }
            //     if (prevCardInput) {
            //         prevCardInput.checked = true;
            //         htmx.trigger(`#${prevCardInput.id}`, "change");                    
            //         var entryEl = document.getElementById(`entry-${prevCardInput.value}`);
            //         entryEl.classList.add('status-read');
            //     }
            // });
            // // Next
            // hotkeys('k', function (event, handler) {
            //     var currentCardInput = listViewEl.querySelector(".entry .entry-card input:checked");
            //     var nextCard = null;
            //     var nextCardInput = null;
            //     if (currentCardInput) {
            //         var li = currentCardInput.parentNode.parentNode;
            //         nextCard = li.nextElementSibling;
            //         nextCardInput = nextCard.querySelector(".entry-card input");
            //     } else {
            //         // Select first
            //         nextCardInput = listViewEl.querySelector(".entry .entry-card input");
            //     }
            //     if (nextCardInput) {
            //         nextCardInput.checked = true;
            //         htmx.trigger(`#${nextCardInput.id}`, "change");
            //         var entryEl = document.getElementById(`entry-${nextCardInput.value}`);
            //         entryEl.classList.add('status-read');
            //     }
            // });
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

    // Sweat.setup();
    window.Sweat = Sweat;

})