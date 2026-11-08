import { Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Header, HeaderAds } from "./Header";
import { Footer, CookieBanner } from "./Footer";
import { useSite } from "../../lib/auth";
import { trackView } from "../../lib/seo";
import { AdsterraSocialBar } from "./AdsterraSocialBar";

export default function PublicLayout() {
  const { pathname } = useLocation();
  const { site, theme } = useSite();
  useEffect(() => {
    window.scrollTo(0, 0);
    if (!pathname.startsWith("/vijesti/")) trackView(null);
  }, [pathname]);
  if (site.maintenance_mode) {
    return (
      <div className="min-h-screen bg-ccn-navy flex flex-col items-center justify-center text-white p-6 text-center" data-testid="maintenance-page">
        <img src="/logo-web.webp" alt={site.site_name} className="h-28" />
        <p className="mt-6 text-lg">{site.maintenance_message}</p>
      </div>
    );
  }
  return (
    <div className={`min-h-screen flex flex-col transition-colors duration-300 ${theme === "dark" ? "theme-dark" : ""}`} data-testid="public-root" data-theme={theme}>
      <Header />
      <HeaderAds />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <CookieBanner />
      <AdsterraSocialBar />
    </div>
  );
}
