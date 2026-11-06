import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDate } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHead } from "./AdminLayout";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Switch } from "../../components/ui/switch";
import { Dialog, DialogContent, DialogTitle } from "../../components/ui/dialog";

function UserDialog({ u, roles, perms, cats, onClose, onSaved }) {
  const [f, setF] = useState({ ...u, password: "" });
  const save = async () => {
    try {
      if (u.id) await api.put(`/admin/users/${u.id}`, f); else await api.post("/admin/users", f);
      toast.success("Sačuvano"); onSaved();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const toggle = (k, v) => setF({ ...f, [k]: (f[k] || []).includes(v) ? f[k].filter((x) => x !== v) : [...(f[k] || []), v] });
  const rolePerms = roles.find((r) => r.key === f.role)?.permissions || [];
  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="user-dialog">
        <DialogTitle>{u.id ? "Uredi korisnika" : "Novi korisnik"}</DialogTitle>
        <div className="grid sm:grid-cols-2 gap-3">
          <Input placeholder="Ime i prezime" value={f.name || ""} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="user-name" />
          <Input placeholder="E-mail" value={f.email || ""} disabled={!!u.id} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="user-email" />
          <Input type="password" placeholder={u.id ? "Nova lozinka (opcionalno)" : "Lozinka (min 10, veliko slovo, broj)"} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="user-password" />
          <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} className="border rounded-sm px-3 py-2 text-sm" data-testid="user-role">{roles.map((r) => <option key={r.key} value={r.key}>{r.name}</option>)}</select>
        </div>
        <Input placeholder="Kratka biografija (javno)" value={f.bio || ""} onChange={(e) => setF({ ...f, bio: e.target.value })} />
        <div className="flex gap-6 text-sm"><label className="flex gap-2 items-center"><Switch checked={f.active !== false} onCheckedChange={(v) => setF({ ...f, active: v })} data-testid="user-active" />Aktivan</label>
          <label className="flex gap-2 items-center"><Switch checked={f.show_public !== false} onCheckedChange={(v) => setF({ ...f, show_public: v })} />Prikaži na stranici Autori</label></div>
        <div><p className="text-xs font-bold uppercase text-slate-500 mb-2">Dodatne pojedinačne dozvole (pored uloge)</p>
          <div className="grid sm:grid-cols-2 gap-1">{Object.entries(perms).map(([k, l]) => (
            <label key={k} className="flex gap-2 text-xs items-center"><input type="checkbox" checked={rolePerms.includes(k) || (f.extra_permissions || []).includes(k)} disabled={rolePerms.includes(k)} onChange={() => toggle("extra_permissions", k)} data-testid={`user-perm-${k}`} />{l} <code className="text-[10px] text-slate-400">{k}</code></label>))}</div>
        </div>
        <div><p className="text-xs font-bold uppercase text-slate-500 mb-2">Dodijeljene kategorije (za urednike; prazno = sve)</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1 max-h-32 overflow-y-auto">{cats.map((c) => <label key={c.id} className="flex gap-2 text-xs"><input type="checkbox" checked={(f.assigned_categories || []).includes(c.id)} onChange={() => toggle("assigned_categories", c.id)} />{c.name}</label>)}</div>
        </div>
        <Button className="bg-ccn-navy" onClick={save} data-testid="user-save">Sačuvaj</Button>
      </DialogContent>
    </Dialog>
  );
}

function RolesEditor({ roles, perms, reload }) {
  const save = async (r, list) => { try { await api.put(`/admin/roles/${r.key}`, { permissions: list }); toast.success("Uloga ažurirana"); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className="bg-white border rounded-md overflow-x-auto mt-8" data-testid="roles-matrix">
      <h2 className="font-bold p-4 pb-0">Uloge i dozvole (RBAC)</h2>
      <table className="text-xs w-full mt-3">
        <thead><tr className="bg-slate-50"><th className="p-2 text-left">Dozvola</th>{roles.map((r) => <th key={r.key} className="p-2">{r.name}</th>)}</tr></thead>
        <tbody>{Object.entries(perms).map(([k, l]) => (
          <tr key={k} className="border-t"><td className="p-2">{l} <code className="text-slate-400">{k}</code></td>
            {roles.map((r) => <td key={r.key} className="p-2 text-center"><input type="checkbox" checked={r.permissions.includes(k)} disabled={r.key === "super_admin"} data-testid={`role-${r.key}-${k}`}
              onChange={(e) => save(r, e.target.checked ? [...r.permissions, k] : r.permissions.filter((x) => x !== k))} /></td>)}</tr>
        ))}</tbody>
      </table>
    </div>
  );
}

export default function Users() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState({ roles: [], permissions: {} });
  const [cats, setCats] = useState([]);
  const [edit, setEdit] = useState(null);
  const load = () => { api.get("/admin/users").then((r) => setUsers(r.data)); api.get("/admin/roles").then((r) => setRoles(r.data)); };
  useEffect(() => { load(); api.get("/public/categories").then((r) => setCats(r.data)); }, []);
  const roleName = (k) => roles.roles.find((r) => r.key === k)?.name || k;
  const del = async (u) => { if (window.confirm(`Obrisati ${u.email}?`)) { try { await api.delete(`/admin/users/${u.id}`); load(); } catch (e) { toast.error(errMsg(e)); } } };
  return (
    <div data-testid="admin-users">
      <PageHead title="Korisnici i uloge"><Button className="bg-ccn-navy" onClick={() => setEdit({ role: "journalist", active: true })} data-testid="add-user-button"><Plus className="w-4 h-4 mr-1" />Novi korisnik</Button></PageHead>
      <div className="bg-white border rounded-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="p-3">Ime</th><th className="p-3">E-mail</th><th className="p-3">Uloga</th><th className="p-3">2FA</th><th className="p-3">Status</th><th className="p-3">Zadnja prijava</th><th /></tr></thead>
          <tbody>{users.map((u) => (
            <tr key={u.id} className="border-t" data-testid={`user-row-${u.email}`}>
              <td className="p-3 font-semibold">{u.name}</td><td className="p-3">{u.email}</td><td className="p-3">{roleName(u.role)}{u.extra_permissions?.length > 0 && <span className="text-xs text-ccn-tealdark"> +{u.extra_permissions.length}</span>}</td>
              <td className="p-3">{u.totp_enabled ? "✓" : "—"}</td><td className="p-3">{u.active ? "Aktivan" : "Neaktivan"}</td><td className="p-3 text-slate-500">{fmtDate(u.last_login)}</td>
              <td className="p-3 whitespace-nowrap"><Button size="sm" variant="outline" onClick={() => setEdit(u)} data-testid={`user-edit-${u.email}`}>Uredi</Button> <Button size="sm" variant="ghost" className="text-ccn-red" onClick={() => del(u)} data-testid={`user-delete-${u.email}`}>Obriši</Button></td>
            </tr>))}</tbody>
        </table>
      </div>
      <RolesEditor roles={roles.roles} perms={roles.permissions} reload={load} />
      {edit && <UserDialog u={edit} roles={roles.roles} perms={roles.permissions} cats={cats} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); }} />}
    </div>
  );
}

export function Profile() {
  const { user, reload } = useAuth();
  const [setup, setSetup] = useState(null);
  const [code, setCode] = useState("");
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [sessions, setSessions] = useState([]);
  const loadS = () => api.get("/auth/sessions").then((r) => setSessions(r.data));
  useEffect(() => { loadS(); }, []);
  const run = async (fn, msg) => { try { await fn(); toast.success(msg); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div className="grid lg:grid-cols-2 gap-5 max-w-5xl" data-testid="admin-profile">
      <div className="bg-white border rounded-md p-5">
        <h2 className="font-bold mb-3">Dvofaktorska autentifikacija (2FA)</h2>
        {user.totp_enabled ? (
          <div className="grid gap-2"><p className="text-sm text-emerald-700" data-testid="2fa-enabled">2FA je uključena.</p>
            <Input placeholder="Kod za isključivanje" value={code} onChange={(e) => setCode(e.target.value)} data-testid="2fa-disable-code" />
            <Button variant="outline" onClick={() => run(async () => { await api.post("/auth/2fa/disable", { code }); reload(); }, "2FA isključena")} data-testid="2fa-disable">Isključi 2FA</Button></div>
        ) : setup ? (
          <div className="grid gap-2"><img src={setup.qr} alt="QR kod" className="w-44" data-testid="2fa-qr" /><p className="text-xs text-slate-500">Skenirajte u Google Authenticator / Authy. Ključ: <code>{setup.secret}</code></p>
            <Input placeholder="6-cifreni kod" value={code} onChange={(e) => setCode(e.target.value)} data-testid="2fa-code" />
            <Button className="bg-ccn-navy" onClick={() => run(async () => { await api.post("/auth/2fa/enable", { code }); setSetup(null); reload(); }, "2FA uključena")} data-testid="2fa-enable">Potvrdi i uključi</Button></div>
        ) : <Button className="bg-ccn-navy" onClick={() => api.post("/auth/2fa/setup").then((r) => setSetup(r.data))} data-testid="2fa-setup">Uključi 2FA</Button>}
      </div>
      <div className="bg-white border rounded-md p-5 grid gap-2 content-start">
        <h2 className="font-bold mb-1">Promjena lozinke</h2>
        <Input type="password" placeholder="Trenutna lozinka" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} data-testid="pw-current" />
        <Input type="password" placeholder="Nova lozinka" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} data-testid="pw-new" />
        <Button variant="outline" onClick={() => run(() => api.post("/auth/change-password", pw), "Lozinka promijenjena")} data-testid="pw-save">Promijeni</Button>
      </div>
      <div className="bg-white border rounded-md p-5 lg:col-span-2">
        <div className="flex justify-between mb-3"><h2 className="font-bold">Aktivne sesije</h2>
          <Button variant="outline" className="text-ccn-red" onClick={() => run(async () => { await api.post("/auth/logout-all"); window.location.href = "/admin/prijava"; }, "Odjavljeni sa svih uređaja")} data-testid="logout-all">Odjava sa svih uređaja</Button></div>
        {sessions.map((s) => (
          <p key={s.id} className="text-sm py-2 border-b flex justify-between gap-2"><span className="truncate">{s.current && <strong>(ova) </strong>}{s.user_agent} · {s.ip} · {fmtDate(s.created_at)}</span>
            {!s.current && <button className="text-xs text-ccn-red" onClick={() => api.delete(`/auth/sessions/${s.id}`).then(loadS)}>Prekini</button>}</p>
        ))}
      </div>
    </div>
  );
}
