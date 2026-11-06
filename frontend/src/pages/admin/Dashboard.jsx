import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, FileText, CalendarClock, Clock3, PenLine, Users, Eye } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { api, fmtDate } from "../../lib/api";
import { PageHead } from "./AdminLayout";

function Stat({ label, value, icon: I, to, tid, accent = "text-ccn-tealdark" }) {
  const body = (
    <div className="bg-white border rounded-md p-4 hover:shadow-md transition-shadow h-full" data-testid={tid}>
      <I className={`w-5 h-5 ${accent}`} />
      <p className="text-3xl font-bold mt-2">{value ?? "–"}</p>
      <p className="text-xs text-slate-500 uppercase tracking-wider mt-1">{label}</p>
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [days, setDays] = useState(7);
  useEffect(() => { api.get("/admin/dashboard", { params: { days } }).then((r) => setD(r.data)); }, [days]);
  if (!d) return <p>Učitavanje…</p>;
  return (
    <div data-testid="admin-dashboard">
      <PageHead title="Dashboard" sub="Pregled rada redakcije">
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="border rounded-sm px-3 py-2 text-sm bg-white" data-testid="dashboard-days">
          <option value={1}>Danas</option><option value={7}>7 dana</option><option value={30}>30 dana</option><option value={90}>90 dana</option>
        </select>
      </PageHead>
      {d.warnings.length > 0 && (
        <div className="mb-6 space-y-2" data-testid="dashboard-warnings">
          {d.warnings.map((w) => <p key={w} className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-900 text-sm px-4 py-2 rounded-sm"><AlertTriangle className="w-4 h-4" />{w}</p>)}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        <Stat label="Objavljeno ukupno" value={d.published} icon={FileText} to="/admin/clanci?status=published" tid="stat-published" />
        <Stat label="Objavljeno danas" value={d.published_today} icon={Clock3} tid="stat-today" />
        <Stat label="Nacrti" value={d.drafts} icon={PenLine} to="/admin/clanci?status=draft" tid="stat-drafts" />
        <Stat label="Na pregledu" value={d.review} icon={Eye} to="/admin/clanci?status=review" tid="stat-review" accent="text-amber-600" />
        <Stat label="Zakazano" value={d.scheduled} icon={CalendarClock} to="/admin/clanci?status=scheduled" tid="stat-scheduled" />
        <Stat label="Aktivni novinari" value={d.active_journalists} icon={Users} tid="stat-journalists" />
        <Stat label="Prikazi stranica" value={d.totals.pageviews} icon={Eye} tid="stat-pageviews" accent="text-ccn-gold" />
      </div>
      <div className="grid lg:grid-cols-3 gap-5 mt-6">
        <div className="lg:col-span-2 bg-white border rounded-md p-5">
          <h2 className="font-bold mb-1">Posjete</h2>
          <p className="text-xs text-slate-500 mb-4">Prikazi: {d.totals.pageviews} · Sesije: {d.totals.sessions} · Korisnici (anonimni ID preglednika): {d.totals.users}</p>
          <div className="h-64" data-testid="dashboard-chart">
            <ResponsiveContainer>
              <AreaChart data={d.traffic}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6E9EF" />
                <XAxis dataKey="day" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Legend />
                <Area type="monotone" dataKey="pageviews" name="Prikazi" stroke="#0B1F3B" fill="#0B1F3B22" />
                <Area type="monotone" dataKey="sessions" name="Sesije" stroke="#00C2B8" fill="#00C2B822" />
                <Area type="monotone" dataKey="users" name="Korisnici" stroke="#D4A52C" fill="#D4A52C22" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-white border rounded-md p-5" data-testid="dashboard-top-articles">
          <h2 className="font-bold mb-3">Najčitanije</h2>
          {d.top_articles.map((a, i) => (
            <Link key={a.id} to={`/admin/clanci/${a.id}`} className="flex gap-3 py-2 border-b last:border-0 text-sm hover:text-ccn-tealdark">
              <span className="font-bold text-ccn-gold w-5">{i + 1}</span><span className="flex-1 line-clamp-2">{a.title}</span><span className="text-slate-400">{a.views}</span>
            </Link>
          ))}
        </div>
        <div className="bg-white border rounded-md p-5" data-testid="dashboard-campaigns">
          <h2 className="font-bold mb-3">Aktivne reklamne kampanje</h2>
          {d.active_campaigns.length === 0 && <p className="text-sm text-slate-500">Nema aktivnih kampanja.</p>}
          {d.active_campaigns.map((c) => <p key={c.name} className="text-sm py-1.5 border-b last:border-0 flex justify-between"><span>{c.name}</span><span className="text-slate-400">{c.impressions || 0} / {c.clicks || 0} klik</span></p>)}
        </div>
        <div className="lg:col-span-2 bg-white border rounded-md p-5" data-testid="dashboard-activity">
          <h2 className="font-bold mb-3">Posljednje aktivnosti</h2>
          {d.recent_activity.map((l) => (
            <p key={l.id} className="text-sm py-1.5 border-b last:border-0 flex gap-3"><span className="text-slate-400 w-36 shrink-0">{fmtDate(l.created_at)}</span><span className="font-semibold">{l.user_name}</span><span className="text-slate-600 truncate">{l.action} {l.details}</span></p>
          ))}
        </div>
      </div>
    </div>
  );
}
