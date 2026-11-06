import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, mediaUrl } from "../../lib/api";
import { useSeo, trackView } from "../../lib/seo";
import { useSite } from "../../lib/auth";
import { ArticleView } from "../../components/public/ArticleView";
import { MostRead } from "../../components/public/HomeBlocks";
import { AdSlot } from "../../components/public/AdSlot";
import { Skeleton } from "../../components/ui/skeleton";
import NotFound from "./NotFound";

export default function ArticlePage() {
  const { slug } = useParams();
  const nav = useNavigate();
  const { site } = useSite();
  const [a, setA] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    setA(null);
    setErr(null);
    api.get(`/public/articles/${slug}`).then((r) => {
      if (r.data.redirect) { nav(r.data.redirect, { replace: true }); return; }
      setA(r.data);
      trackView(r.data.id);
    }).catch((e) => setErr(e.response?.status || 500));
  }, [slug, nav]);
  const img = a && (a.social_image || a.featured_image?.large);
  useSeo({
    siteName: site.site_name, title: a ? a.seo_title || a.title : undefined, description: a ? a.seo_description || a.summary : undefined,
    image: img ? mediaUrl(img) : undefined, type: "article", canonical: a?.canonical_url || undefined,
    jsonLd: a ? {
      "@context": "https://schema.org", "@type": "NewsArticle", headline: a.title, description: a.summary, image: img ? [mediaUrl(img)] : [],
      datePublished: a.published_at, dateModified: a.updated_at || a.published_at,
      author: (a.authors || []).map((u) => ({ "@type": "Person", name: u.name, url: `${window.location.origin}/autor/${u.slug}` })),
      publisher: { "@type": "NewsMediaOrganization", name: site.publisher_name || site.site_name, logo: { "@type": "ImageObject", url: window.location.origin + "/icon-512.png" } },
      mainEntityOfPage: window.location.href, articleSection: a.category?.name, keywords: (a.tags || []).join(", "),
    } : undefined,
  });
  if (err === 410) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-24 text-center" data-testid="article-gone">
        <h1 className="font-serif-news text-3xl font-black">Članak je uklonjen</h1>
        <p className="mt-3 text-slate-600">Ovaj članak više nije dostupan na portalu.</p>
      </div>
    );
  }
  if (err) return <NotFound />;
  if (!a) return <div className="max-w-7xl mx-auto px-4 py-8"><Skeleton className="h-12 w-2/3" /><Skeleton className="h-96 mt-6 max-w-3xl" /></div>;
  return (
    <div className="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-12 gap-10">
      <div className="lg:col-span-8"><ArticleView a={a} /></div>
      <aside className="lg:col-span-4 space-y-6 lg:sticky lg:top-32 self-start">
        <AdSlot position="sidebar" />
        <MostRead />
      </aside>
    </div>
  );
}
