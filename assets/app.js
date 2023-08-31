import hotkeys from 'hotkeys-js';
import morphdom from 'morphdom';

window.addEventListener("DOMContentLoaded", (event) => {

    // function findParent(currentNode, parentClass) {
    //     while (currentNode.tagName != 'BODY') {
    //         if (currentNode.classList.contains(parentClass)) {
    //             return currentNode;
    //         }
    //         currentNode = currentNode.parentNode;
    //     }
    //     return null;
    // }

    function makeEndpointURL(pathname) {
        var segments = [
            window.applicationURL,
            pathname
        ]
        return segments.join('')
    }

    // Innermost element that does not get replaced
    var listViewEl = document.getElementById("panel");

    const Sweat = {

        morph: function (sourceEl, fragment, options) {
            morphdom(sourceEl, fragment, options)
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
                    Sweat.mark(prevCardInput.value, 'read');
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
                    Sweat.mark(nextCardInput.value, 'read')
                    Sweat.loadEntry(nextCardInput.value, event)
                }
            });
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

        loadEntry: function (id, title, event) {
            var mainEl = document.getElementById('main');
            // Remove any previous animation triggers
            //mainEl.classList.remove('in')
            Sweat.replaceElementWithTemplate(`template-${id}`, mainEl, event);
            window.requestAnimationFrame((timeStamp) => {
                // Add on next frame to trigger entering animation
                mainEl.classList.add('in')
            })

            Sweat.mark(id, 'read');
            //document.title = `${title} • Coldsweat`;
            event.preventDefault();
        },

        replaceElementWithTemplate: function (templateId, targetEl, event) {
            var templateEl = document.getElementById(templateId);
            //var targetEl = document.getElementById(targetId);
            var sourceElCopy = templateEl.content.firstElementChild.cloneNode(true);
            targetEl.replaceChildren(...[sourceElCopy]);
        },

        loadFolder: function (url, title, event) {
            if (event) {
                event.preventDefault();
            }
            var inputEl = event.currentTarget.previousElementSibling
            if (inputEl) {
                inputEl.checked = true;
            }
            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handling request ${url}`);
                    }
                    response.text().then((text) => {
                        var panelEl = document.getElementById('panel');
                        panelEl.innerHTML = text;
                        var listEl = panelEl.querySelector('.list-view')
                        window.requestAnimationFrame((timeStamp) => {
                            // Add on next frame to trigger entering animation 
                            listEl.classList.add('in')
                        }
                        )
                        var newUrl = new URL(url);
                        // We want to restore the whole page
                        newUrl.searchParams.delete('xhr');
                        history.pushState({}, '', newUrl.href)
                        if (title) {
                            document.title = `${title} • Coldsweat`;
                        }
                    });
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
                        throw new Error(`Server returned error ${response.status} while handing POST request`);
                    }
                    response.text().then((text) => {
                    });
                });
        },

        loadMore: function (url) {
            var wrapper = document.getElementById("entry-list");
            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handling pagination`);
                    }
                    response.text().then((text) => {
                        var button = wrapper.querySelector(".more");
                        button.remove();
                        var template = document.createElement('template');
                        template.innerHTML = text;
                        template.content.childNodes.forEach((child) => {
                            wrapper.appendChild(child.cloneNode(true));
                        })
                        //child.scrollIntoView({ behavior: "smooth", block: "start" })
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