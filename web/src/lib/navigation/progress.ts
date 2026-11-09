/**
 * The thin bar at the top of the screen while the next page is prepared: the screen answers the
 * very moment a link is touched, instead of looking frozen. Written into the page (no JavaScript
 * file, ADR-004); it works with the server pages as they are (real 404s, feed without scripts).
 * It starts on a click on a link to another page of the site and stops when the address changes.
 */
export const progressScript = `(function(){var b=document.getElementById("sg-progress"),h=document.documentElement;if(!b)return;
var on=false,t;function done(){if(!on)return;on=false;clearTimeout(t);b.setAttribute("data-state","done");delete h.dataset.navigating;
t=setTimeout(function(){b.removeAttribute("data-state")},450)}
function start(){on=true;clearTimeout(t);b.removeAttribute("data-state");void b.offsetWidth;b.setAttribute("data-state","run");h.dataset.navigating="";t=setTimeout(done,20000)}
document.addEventListener("click",function(e){if(e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
var a=e.target&&e.target.closest&&e.target.closest("a[href]");if(!a||(a.target&&a.target!=="_self")||a.hasAttribute("download"))return;
var u=new URL(a.href,location.href);if(u.origin!==location.origin||(u.pathname===location.pathname&&u.search===location.search))return;start()},true);
var p=history.pushState;history.pushState=function(){var r=p.apply(this,arguments);done();return r};
addEventListener("popstate",done);addEventListener("pageshow",done)})()`;
