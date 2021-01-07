function ab2str(buf) {
    return btoa(String.fromCharCode.apply(null, new Uint8Array(buf))).replace(/\//g, '_').replace(/\+/g, '-').replace(/=*$/, '');
}

function str2ab(enc) {
    var str = atob(enc.replace(/_/g, '/').replace(/-/g, '+'));
    var buf = new ArrayBuffer(str.length);
    var bufView = new Uint8Array(buf);
    for (var i = 0, strLen = str.length; i < strLen; i++) {
        bufView[i] = str.charCodeAt(i);
    }
    return buf;
}
