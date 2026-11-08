import { useEffect, useRef, useState } from "react";

const BANNER_HTML = `<!doctype html><html><head><meta name="referrer" content="strict-origin-when-cross-origin"><style>html,body{margin:0;padding:0;width:160px;height:600px;overflow:hidden}</style></head><body>
<script>var atOptions = {'key':'a6ab0fdb24758def841905fb9b323b35','format':'iframe','height':600,'width':160,'params':{}};</script>
<script src="https://bicea.org/22/a6ab0fdb24758def841905fb9b323b35"></script>
</body></html>`;

const NATIVE_HTML = `<!doctype html><html><head><style>html,body{margin:0;padding:0;overflow:hidden}*{box-sizing:border-box;max-width:100%}</style></head><body>
<div id="container-519742b55f0077a1c7d9fdb720f55ed7"></div>
<script async="async" data-cfasync="false" src="https://bicea.org/21/519742b55f0077a1c7d9fdb720f55ed7"></script>
<script>new ResizeObserver(function(){parent.postMessage({type:'ccn-native-ad-height',height:document.body.scrollHeight},'*')}).observe(document.body);</script>
</body></html>`;

const RECTANGLE_HTML = `<!doctype html><html><head><meta name="referrer" content="strict-origin-when-cross-origin"><style>html,body{margin:0;padding:0;width:300px;height:250px;overflow:hidden}</style></head><body>
<script>var atOptions = {'key':'3b29f279dd8912216e84eb9172023930','format':'iframe','height':250,'width':300,'params':{}};</script>
<script src="https://bicea.org/22/3b29f279dd8912216e84eb9172023930"></script>
</body></html>`;

const COMPACT_HTML = `<!doctype html><html><head><meta name="referrer" content="strict-origin-when-cross-origin"><style>html,body{margin:0;padding:0;width:160px;height:300px;overflow:hidden}</style></head><body>
<script>var atOptions = {'key':'b5dc973d9146f24207625e6510801dfc','format':'iframe','height':300,'width':160,'params':{}};</script>
<script src="https://bicea.org/22/b5dc973d9146f24207625e6510801dfc"></script>
</body></html>`;

export function AdsterraBanner({ variant = "sidebar" }) {
  const [enabled, setEnabled] = useState(false);
  const [height, setHeight] = useState(250);
  const frame = useRef(null);
  const native = variant === "native";
  const rectangle = variant === "rectangle";
  const compact = variant === "compact";
  const width = rectangle ? 300 : 160;
  const fixedHeight = rectangle ? 250 : compact ? 300 : 600;
  useEffect(() => {
    const desktop = window.matchMedia(rectangle ? "(min-width: 316px)" : "(min-width: 1024px)");
    const update = () => {
      try {
        setEnabled((native || compact || desktop.matches) && JSON.parse(localStorage.getItem("ccn_consent") || "null")?.marketing === true);
      } catch {
        setEnabled(false);
      }
    };
    update();
    desktop.addEventListener("change", update);
    window.addEventListener("ccn-consent-change", update);
    window.addEventListener("storage", update);
    return () => {
      desktop.removeEventListener("change", update);
      window.removeEventListener("ccn-consent-change", update);
      window.removeEventListener("storage", update);
    };
  }, [native, rectangle, compact]);
  useEffect(() => {
    if (!native || !enabled) return;
    const resize = (event) => {
      if (event.source !== frame.current?.contentWindow || event.data?.type !== "ccn-native-ad-height") return;
      const next = event.data.height;
      if (Number.isFinite(next) && next >= 0) setHeight(Math.min(Math.ceil(next), 2000));
    };
    window.addEventListener("message", resize);
    return () => window.removeEventListener("message", resize);
  }, [native, enabled]);
  if (!enabled) return null;
  return (
    <aside className="w-full min-w-0 overflow-hidden" aria-label="Reklama" data-testid={`adsterra-${variant}`}>
      <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400 mb-1 text-center">Oglas</div>
      <iframe ref={frame} title={native ? "Adsterra preporučeni sadržaj" : `Adsterra oglas ${width} × ${fixedHeight}`} srcDoc={native ? NATIVE_HTML : rectangle ? RECTANGLE_HTML : compact ? COMPACT_HTML : BANNER_HTML} width={native ? "100%" : width} height={native ? height : fixedHeight} loading="lazy"
        className="block mx-auto border-0" style={{ width: native ? "100%" : width, height: native ? height : fixedHeight }} />
    </aside>
  );
}
