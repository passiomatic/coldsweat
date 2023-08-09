window.addEventListener("DOMContentLoaded", (event) => {

    function findParent(currentNode, parentClass) {
        while (currentNode.tagName != 'BODY') {
            if (currentNode.classList.contains(parentClass)) {
                return currentNode;
            }
            currentNode = currentNode.parentNode;
        }
        return null;
    }
    
    function makeEndpointURL(pathname) {
        var segments = [
            window.applicationURL,
            pathname
        ]                          
        return segments.join('')
    }    

    // Find innermost element that does not get replaced
    var listViewEl = document.getElementById("panel-content");

    const Sweat = {


        setup: function() { 
            // Prev
            hotkeys('j', function(event, handler){
                var currentCardInput = listViewEl.querySelector(".entry .entry-card input:checked");
                var prevCard = null;
                var prevCardInput = null;
                if(currentCardInput) {
                    var li = currentCardInput.parentNode.parentNode;
                    // @@TODO Skip headings
                    prevCard = li.previousElementSibling;
                    prevCardInput = prevCard.querySelector(".entry-card input");
                } else {
                    // Select first
                    prevCardInput = listViewEl.querySelector(".entry .entry-card input");
                } 
                if(prevCardInput) {
                    prevCardInput.checked = true;
                    Sweat.mark(prevCardInput.value, 'read');
                    Sweat.loadEntry(prevCardInput.value, event);
                }                
            });
            // Next
            hotkeys('k', function(event, handler){
                var currentCardInput = listViewEl.querySelector(".entry .entry-card input:checked");
                var nextCard = null;
                var nextCardInput = null;
                if(currentCardInput) {
                    var li = currentCardInput.parentNode.parentNode;
                    // @@TODO Skip headings
                    nextCard = li.nextElementSibling;
                    nextCardInput = nextCard.querySelector(".entry-card input");
                } else {
                    // Select first
                    nextCardInput = listViewEl.querySelector(".entry .entry-card input");
                } 
                if(nextCardInput) {
                    nextCardInput.checked = true;       
                    Sweat.mark(nextCardInput.value, 'read')
                    Sweat.loadEntry(nextCardInput.value, event)
                }
            });            
        },

        submitRemoteForm: function(url, event) {
            // @@TODO Do async request 
            event.preventDefault();            
        },

        openRemoteDialog: function(url, event) {
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

        loadEntry: function(id, event) {
            Sweat.replaceElement(`template-${id}`, 'main', event);
            Sweat.mark(id, 'read');
        },

        replaceElement: function(sourceId, targetId, event) {
            var sourceEl = document.getElementById(sourceId);
            var targetEl = document.getElementById(targetId);
            var sourceEl_ = sourceEl.content.firstElementChild.cloneNode(true);
            targetEl.replaceChildren(...[sourceEl_]);
            event.preventDefault();
        },
        
        loadFolder: function(url, event){
            if(event) {
                event.preventDefault();
            }
            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handling request ${url}`);
                    }
                    response.text().then((text) => {
                        var entryListEl = document.getElementById('panel-content');
                        entryListEl.innerHTML = text;
                    });
                });              
        },

        closeDialog: function(event) {
            var dialog = document.getElementById('dialog');                        
            //dialog.classList.remove("in"); 
            dialog.close();  
        },

        openDialog: function(dialogEl, event) {
            dialogEl.showModal();         
            //dialogEl.classList.add("in"); 
            return dialogEl;
        },

        mark: function(id, status) {
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

        loadMore: function(url) {
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
        }
    }

    Sweat.setup();
    window.Sweat = Sweat;

})