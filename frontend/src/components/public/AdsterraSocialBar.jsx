import { useEffect } from "react";

export function AdsterraSocialBar() {
  useEffect(() => {
    let script;
    const update = () => {
      let consent = false;
      try {
        consent = JSON.parse(localStorage.getItem("ccn_consent") || "null")?.marketing === true;
      } catch { /* Invalid stored consent does not enable ads. */ }
      if (!consent || script) return;
      script = document.createElement("script");
      script.src = "https://bicea.org/14/4014436d892242bd3d2318525df11081";
      script.async = true;
      script.setAttribute("data-cfasync", "false");
      script.id = "ccn-adsterra-socialbar";
      document.body.appendChild(script);
    };
    const timer = setTimeout(update, 0);
    window.addEventListener("ccn-consent-change", update);
    window.addEventListener("storage", update);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("ccn-consent-change", update);
      window.removeEventListener("storage", update);
      script?.remove();
    };
  }, []);
  return null;
}
