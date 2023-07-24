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

    const Sweat = {

        replaceElement: function(sourceId, targetId, event) {
            var sourceEl = document.getElementById(sourceId);
            var targetEl = document.getElementById(targetId);
            var sourceEl_ = sourceEl.content.firstElementChild.cloneNode(true);
            targetEl.replaceChildren(...[sourceEl_]);
            event.preventDefault();
        },
        
        loadFolder: function(url){
            fetch(url)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`Server returned error ${response.status} while handling request ${url}`);
                    }
                    response.text().then((text) => {
                        var entryListEl = document.getElementById('entry-list');
                        entryListEl.innerHTML = text;
                    });
                });              
        },

        closeDialog: function(event, dialogId) {
            var dialog = document.querySelector(dialogId);                        
            dialog.classList.remove("in"); 
            dialog.close();        
            event.preventDefault(); 
        },

        openDialog: function(event, dialogId) {
            var dialog = document.querySelector(dialogId);                        
            dialog.showModal();         
            dialog.classList.add("in"); 
            return dialog;
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

    window.Sweat = Sweat;
})