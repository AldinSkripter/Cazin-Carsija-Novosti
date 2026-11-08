import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { api, fmtDate, STATUS_LABELS, STATUS_COLORS } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHead } from "./AdminLayout";
import { Button } from "../../components/ui/button";
import { FacebookImport } from "../../components/admin/FacebookImport";

export default function Articles() {
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], total: 0 });
  const [cats, setCats] = useState([]);
  const [q, setQ] = useState("");
  const status = params.get("status") || "";
  const page = Number(params.get("page") || 1);
  const qs = params.toString();
  useEffect(() => { api.get("/public/categories").then((r) => setCats(r.data)); }, []);
  const load = () => { api.get("/admin/articles", { params: Object.fromEntries(new URLSearchParams(qs)) }).then((r) => setData(r.data)); };
  useEffect(() => { load(); }, [qs]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (k, v) => { v ? params.set(k, v) : params.delete(k); if (k !== "page") params.delete("page"); setParams(params); };
  const catName = (id) => cats.find((c) => c.id === id)?.name || "–";
  return (
    <div data-testid="admin-articles">
      <PageHead title="Članci" sub={`${data.total} članaka`}>
        {can("articles.publish") && <FacebookImport onDone={load} />}
        {can("articles.create") && <Link to="/admin/clanci/novi"><Button className="bg-ccn-navy" data-testid="new-article-button"><Plus className="w-4 h-4 mr-1" />Novi članak</Button></Link>}
      </PageHead>
      <div className="flex flex-wrap gap-2 mb-4">
        {["", ...Object.keys(STATUS_LABELS)].map((s) => (
          <button key={s} onClick={() => set("status", s)} data-testid={`filter-status-${s || "all"}`}
            className={`px-3 py-1.5 rounded-full text-sm border ${status === s ? "bg-ccn-navy text-white border-ccn-navy" : "bg-white"}`}>{s ? STATUS_LABELS[s] : "Svi"}</button>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        <form onSubmit={(e) => { e.preventDefault(); set("q", q); }} className="flex gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Pretraži članke…" className="border rounded-sm px-3 py-2 text-sm w-64" data-testid="articles-search" />
        </form>
        <select value={params.get("category_id") || ""} onChange={(e) => set("category_id", e.target.value)} className="border rounded-sm px-3 py-2 text-sm bg-white" data-testid="articles-category-filter">
          <option value="">Sve kategorije</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={params.get("mine") === "true"} onChange={(e) => set("mine", e.target.checked ? "true" : "")} data-testid="articles-mine" />Samo moji</label>
      </div>
      <div className="bg-white border rounded-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr><th className="p-3">Naslov</th><th className="p-3">Status</th><th className="p-3">Kategorija</th><th className="p-3">Pregledi</th><th className="p-3">Ažurirano</th></tr>
          </thead>
          <tbody>
            {data.items.map((a) => (
              <tr key={a.id} className="border-t hover:bg-slate-50" data-testid={`article-row-${a.id}`}>
                <td className="p-3 max-w-md">
                  <Link to={`/admin/clanci/${a.id}`} className="font-semibold hover:text-ccn-tealdark">{a.title || "(bez naslova)"}</Link>
                  <div className="flex gap-1 mt-1">
                    {a.is_breaking && <span className="text-[10px] bg-ccn-red text-white px-1.5 rounded-sm">BREAKING</span>}
                    {a.is_pinned && <span className="text-[10px] bg-ccn-navy text-white px-1.5 rounded-sm">FIKSIRANO</span>}
                    {a.is_exclusive && <span className="text-[10px] bg-ccn-gold px-1.5 rounded-sm">EKSKLUZIVNO</span>}
                  </div>
                </td>
                <td className="p-3"><span className={`text-xs px-2 py-1 rounded-full font-semibold ${STATUS_COLORS[a.status]}`} data-testid={`article-status-${a.id}`}>{STATUS_LABELS[a.status]}</span></td>
                <td className="p-3">{catName(a.category_id)}</td>
                <td className="p-3">{a.views || 0}</td>
                <td className="p-3 text-slate-500 whitespace-nowrap">{fmtDate(a.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.items.length && <p className="p-8 text-center text-slate-500">Nema članaka.</p>}
      </div>
      {data.total > 25 && (
        <div className="flex gap-2 mt-4">
          <Button variant="outline" disabled={page <= 1} onClick={() => set("page", page - 1)}>‹</Button>
          <span className="px-3 py-2 text-sm">{page} / {Math.ceil(data.total / 25)}</span>
          <Button variant="outline" disabled={page * 25 >= data.total} onClick={() => set("page", page + 1)} data-testid="articles-next-page">›</Button>
        </div>
      )}
    </div>
  );
}
