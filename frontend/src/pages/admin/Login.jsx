import { useEffect, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useSeo } from "../../lib/seo";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";

function Shell({ children }) {
  useSeo({ title: "Prijava – CMS", noindex: true });
  return (
    <div className="min-h-screen bg-ccn-navy flex items-center justify-center p-4 relative overflow-hidden grain">
      <div className="w-full max-w-sm bg-white rounded-2xl p-8 shadow-2xl fade-up">
        <img src="/logo-web.webp" alt="Cazin Čaršija Novosti" className="h-20 mx-auto mb-2 bg-ccn-navy rounded-xl p-2" />
        <p className="text-center text-[11px] uppercase tracking-[0.2em] text-slate-400 mb-6">Redakcijski CMS</p>
        {children}
      </div>
    </div>
  );
}

export default function Login() {
  const { user, setUser, reload } = useAuth();
  useEffect(() => { if (user === undefined) reload(); }, [user, reload]);
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "", totp: "" });
  const [need2fa, setNeed2fa] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/admin" replace />;
  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (forgot) {
        const { data } = await api.post("/auth/forgot-password", { email: f.email });
        toast.success(data.message);
        setForgot(false);
      } else {
        const { data } = await api.post("/auth/login", f);
        if (data.requires_2fa) setNeed2fa(true);
        else { setUser(data); nav("/admin"); }
      }
    } catch (e2) { setErr(errMsg(e2)); } finally { setBusy(false); }
  };
  return (
    <Shell>
      <h1 className="text-xl font-bold text-center mb-5">{forgot ? "Zaboravljena lozinka" : "Prijava u redakciju"}</h1>
      <form onSubmit={submit} className="grid gap-3" data-testid="login-form">
        <Input type="email" required placeholder="E-mail" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="login-email" />
        {!forgot && <Input type="password" required placeholder="Lozinka" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="login-password" />}
        {need2fa && <Input inputMode="numeric" placeholder="2FA kod iz aplikacije" value={f.totp} onChange={(e) => setF({ ...f, totp: e.target.value })} data-testid="login-totp" autoFocus />}
        {err && <p className="text-sm text-ccn-red" data-testid="login-error">{err}</p>}
        <Button disabled={busy} className="bg-ccn-navy hover:bg-ccn-tealdark" data-testid="login-submit">{busy ? "…" : forgot ? "Pošalji link" : "Prijava"}</Button>
        <button type="button" onClick={() => setForgot(!forgot)} className="text-xs text-slate-500 hover:text-ccn-navy" data-testid="login-forgot-toggle">{forgot ? "Nazad na prijavu" : "Zaboravili ste lozinku?"}</button>
      </form>
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [pw, setPw] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    try { await api.post("/auth/reset-password", { token: params.get("token"), password: pw }); toast.success("Lozinka promijenjena"); nav("/admin/prijava"); }
    catch (err) { toast.error(errMsg(err)); }
  };
  return (
    <Shell>
      <form onSubmit={submit} className="grid gap-3" data-testid="reset-form">
        <h1 className="text-xl font-bold text-center">Nova lozinka</h1>
        <Input type="password" required placeholder="Min. 10 znakova, veliko slovo i broj" value={pw} onChange={(e) => setPw(e.target.value)} data-testid="reset-password" />
        <Button className="bg-ccn-navy" data-testid="reset-submit">Sačuvaj</Button>
      </form>
    </Shell>
  );
}
