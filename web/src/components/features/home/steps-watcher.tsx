/**
 * Sets the state of the pinned piece of product from the sentence being read. Written into the page
 * after the sentences: no JavaScript file on the public home (ADR-004). Without it, the first state.
 */
export function StepsWatcher({ target }: { target: string }) {
  const script = `(function(){var r=document.getElementById(${JSON.stringify(target)});if(!r||!("IntersectionObserver"in window))return;
var o=new IntersectionObserver(function(e){e.forEach(function(x){if(x.isIntersecting)r.dataset.active=x.target.dataset.step})},{rootMargin:"-45% 0px -45% 0px"});
r.querySelectorAll("[data-step]").forEach(function(s){o.observe(s)})})()`;
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
