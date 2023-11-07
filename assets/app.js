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

        onEntryLoad: function (id, title, event) {
            var entryEl = document.getElementById(`entry-${id}`);
            entryEl.classList.add('status-read')
            Sweat.loadEntry(id, title, event)
        },

        morph: function (sourceEl, fragment, options) {
            Idiomorph.morph(sourceEl, fragment)
            // morphdom(sourceEl, fragment, {
            //     childrenOnly: true,
            //     onBeforeElUpdated: (fromEl, toEl) => {
            //         if (fromEl.tagName == "DETAILS") {
            //             console.log(`Skipped ${fromEl.getAttribute('id')}`)
            //             return false;
            //         }
            //         // console.log(`Matched ${fromEl.getAttribute('id')} <- ${toEl.getAttribute('id')}`);
            //         return true;
            //     },
            //     onBeforeElChildrenUpdated: (fromEl, toEl) => {
            //         if (fromEl.tagName == "DETAILS") {
            //             console.log(`Skipped ${fromEl.getAttribute('id')}`)
            //             return false;
            //         }

            //         console.log(`Updated ${fromEl.getAttribute('id')}`)
            //         return true;
            //     }     
            // })
        },

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

            // Update UI timer 
            // var timerId = setInterval(() => {
            //     if (dirty) {
            //         var newUrl = new URL(location.href);
            //         newUrl.pathname = '/nav'
            //         fetch(newUrl)
            //             .then((response) => {
            //                 if (!response.ok) {
            //                     throw new Error(`Server returned error ${response.status} while handling GET request`);
            //                 }
            //                 response.text().then((text) => {
            //                     // navViewEl.innerHTML = text;
            //                     Sweat.morph(navViewEl, text)
            //                 });
            //             });
            //         dirty = false;
            //     }
            // }, 1500)
        },

        submitRemoteForm: function (url, event) {
            var dialogEl = document.getElementById('dialog');

            // @@TODO Add spinner
            var button = dialogEl.querySelector('button[type=submit]');
            if (button) {
                button.disabled = true;
            }

            event.preventDefault();
            var formData = new FormData(event.target);
            fetch(makeEndpointURL(url), { method: 'POST', body: formData })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handing POST request`);
                    }
                    response.text().then((text) => {
                        const contentType = response.headers.get("content-type");
                        if (contentType.startsWith('text/html')) {
                            dialogEl.querySelector('.dialog-content').innerHTML = text;
                        } else if (contentType.startsWith('text/javascript')) {
                            Sweat.closeDialog();
                            // Finished, update UI
                            eval(text);
                        }
                    });
                });
        },

        openRemoteDialog: function (url, event) {
            var dialogEl = document.getElementById('dialog');

            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handling request ${url}`);
                    }
                    response.text().then((text) => {
                        dialogEl.querySelector('.dialog-content').innerHTML = text;
                        Sweat.openDialog(dialogEl, event)
                    });
                });
        },

        // loadEntry: function (id, title, event) {
        //     var mainEl = document.getElementById('main');
        //     fetch(makeEndpointURL(`/entries/${id}`))
        //         .then((response) => {
        //             if (!response.ok) {
        //                 throw new Error(`Server returned error ${response.status} while handling GET request`);
        //             }
        //             response.text().then((text) => {
        //                 // mainEl.innerHTML = text;
        //                 // Remove any previous animation triggers
        //                 //mainEl.classList.remove('in')
        //                 eval(text)
        //                 window.requestAnimationFrame((timeStamp) => {
        //                     // Add on next frame to trigger entering animation
        //                     mainEl.classList.add('in')
        //                 })
        //             });
        //         });

        //     // @@TODO
        //     //document.title = `${title} • Coldsweat`;
        //     event.preventDefault();
        // },

        // loadFolder: function (url, title, event, updateNav=false) {
        //     if (event) {
        //         event.preventDefault();
        //         var inputEl = event.currentTarget.previousElementSibling
        //         if (inputEl) {
        //             inputEl.checked = true;
        //         }
        //     }            
        //     var newUrl = new URL(url);
        //     newUrl.searchParams.delete('xhr');
        //     if(newUrl == location.href) {
        //         // Do not reload the same folder
        //         return;
        //     }
        //     fetch(url)
        //         .then((response) => {
        //             if (!response.ok) {
        //                 throw new Error(`Server returned error ${response.status} while handling request ${url}`);
        //             }
        //             response.text().then((text) => {
        //                 var panelEl = document.getElementById('panel');
        //                 panelEl.innerHTML = text;
        //                 var listEl = panelEl.querySelector('.list-view')
        //                 window.requestAnimationFrame((timeStamp) => {
        //                     // Add on next frame to trigger entering animation 
        //                     listEl.classList.add('in')
        //                 }
        //                 )
        //                 var newUrl = new URL(url);
        //                 // We want to restore the whole page
        //                 newUrl.searchParams.delete('xhr');
        //                 history.pushState({}, '', newUrl.href)
        //                 if (title) {
        //                     document.title = `${title} • Coldsweat`;
        //                 }                        
        //             });
        //         });
        // },

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

        markSaved: function (id, event) {
            var toggle = event.target;
            var new_value = toggle.checked ? 'saved' : 'unsaved'
            Sweat.mark(id, new_value)
        },

        mark: function (id, status) {
            var formData = new FormData();
            formData.append('mark', '')
            formData.append('as', status)
            fetch(makeEndpointURL(`/entries/${id}`), { method: 'POST', body: formData })
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handling POST request`);
                    }
                    response.text().then((text) => {
                    });
                });
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