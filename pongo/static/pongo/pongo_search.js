var pongoSearchIndex = 0;
var pongoSearchResult = []; 

function pongoToggleSearch(){
    pongoClearSearch();
    var searchEntry = document.getElementById('search_entry');
    searchEntry.value = '';
    var topBar = document.getElementById('top_bar');
    var topBarRect = topBar.getBoundingClientRect();
    var topBarHeight = topBarRect.bottom - topBarRect.top;
    var control = document.getElementById('player_control');
    if (control) {
	var controlTop = control.getBoundingClientRect().top;
    } 
    var searchBar = document.getElementById('search_bar');
    var searchBarRect = searchBar.getBoundingClientRect();
    var searchBarHeight = searchBarRect.bottom - searchBarRect.top;

    var topSpace = document.getElementById('top_space');
    var topSpaceRect = topSpace.getBoundingClientRect();
    if (topBarRect.top == 0) {
	var searchBottom = searchBar.getBoundingClientRect().bottom;
	topBar.style.top = searchBarRect.bottom + "px";
	if (control) {
	    control.style.top = (controlTop + searchBarRect.bottom) + "px";
	}
	topSpace.style.height = topBarHeight + searchBarHeight + "px"; 
	searchEntry.focus();
    } else {
	topBar.style.top = "0px";
	topSpace.style.height = topBarHeight + "px";
	if (control) {
	    control.style.top = controlTop - topBarRect.top + "px";
	}
    }
}

function pongoSearchAlbums(){
    pongoSearch('album_item', ['album_name', 'album_artists']);
}

function pongoNextAlbum() {
    if (pongoSearchResult.length == 0) {
	pongoSearchAlbums();
    } else {
	pongoNext();
    }
}

function pongoPreviousAlbum() {
    if (pongoSearchResult.length == 0) {
	pongoSearchAlbums();
    } else {
	pongoPrevious();
    }
}

function pongoSearchTracks(){
    pongoSearch('track_item', ['track_name', 'track_artists']);
}

function pongoNextTrack() {
    if (pongoSearchResult.length == 0) {
	pongoSearchTracks();
    } else {
	pongoNext();
    }
}

function pongoPreviousTrack() {
    if (pongoSearchResult.length == 0) {
	pongoSearchTracks();
    } else {
	pongoPrevious();
    }
}

function pongoSearch(container, children) {
    var searchEntry = document.getElementById('search_entry');
    var text = searchEntry.value;
    // Close the keyboard on Android phones.
    searchEntry.readOnly = true;
    setTimeout(function(){ searchEntry.blur();
			   searchEntry.readOnly = false;}, 100);
    if (text == '') {
	pongoClearSearch();
	return;
    }
    var albums = document.getElementsByClassName(container);
    var pattern = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    var re = new RegExp(pattern, 'im')
    pongoClearSearch();
    for (var i = 0; i < albums.length; i++){
	item = albums[i]
	if (item.style.display == "none") {
	    continue;
	}
	for (var j = 0; j < children.length; j++) {
	    elements = item.getElementsByClassName(children[j]);
	    if (elements.length > 0) {
		text = elements[0].textContent;
		if (re.test(text)) {
		    item.classList.add('pongo_highlight');
		    pongoSearchResult.push(item);
		    break;
		}
	    }
	}
    }
    pongoScroll(pongoSearchResult[0]);
}

function pongoClearSearch() {
    for (var i = 0; i < pongoSearchResult.length; i++){
	pongoSearchResult[i].classList.remove('pongo_highlight')
    }
    pongoSearchIndex = 0;
    pongoSearchResult = [];
}

function pongoNext() {
    if (pongoSearchResult.length > 0) {
	pongoSearchIndex += 1;
	if (pongoSearchIndex >= pongoSearchResult.length ){
	    pongoSearchIndex = 0;
	}
	var item = pongoSearchResult[pongoSearchIndex];
	pongoScroll(item);
    }
}

function pongoPrevious() {
    if (pongoSearchResult.length > 0) {
	pongoSearchIndex -= 1;
	if (pongoSearchIndex < 0 ){
	    pongoSearchIndex = pongoSearchResult.length - 1;
	}
	var album = pongoSearchResult[pongoSearchIndex];
	pongoScroll(album);
    }
}

function pongoScroll(element) {
    if (element) {
	var rect = element.getBoundingClientRect();
	var top = window.pageYOffset + rect.top;
	var tabControl = document.getElementById("tab_control");
	var playerControl = document.getElementById("player_control");
	if (playerControl) {
	    var correction = playerControl.getBoundingClientRect().bottom;
	} else {
	    var correction = tabControl.getBoundingClientRect().bottom;
	}
	window.scroll(0, top - correction);
    }
}

function pongoAlbumSearchKey(event) {
    var searchEntry = document.getElementById('search_entry');
    if (searchEntry.value == '') {
	pongoClearSearch();
    } else if (event.keyCode == 13) {
	pongoNextAlbum();
    }
}

function pongoTrackSearchKey(event) {
    var searchEntry = document.getElementById('search_entry');
    if (searchEntry.value == '') {
	pongoClearSearch();
    } else if (event.keyCode == 13) {
	pongoNextTrack();
    }
}

function pongoIOSScrollHack() {
    // iOS insists on scrolling the text input down 
    var searchBar = document.getElementById('search_bar')
    searchBar.top = "0px";
}
