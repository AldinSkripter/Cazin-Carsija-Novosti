import { useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { Button } from "../ui/button";

export function DeleteArticleButton({ article, onDeleted, beforeDelete, onBusyChange, testId }) {
  const [busy, setBusy] = useState(false);
  const remove = async () => {
    if (busy || !window.confirm(`Obrisati članak „${article.title || "Bez naslova"}“? Članak će biti uklonjen s portala.`)) return;
    setBusy(true);
    onBusyChange?.(true);
    try {
      await beforeDelete?.();
      await api.delete(`/admin/articles/${article.id}`);
      toast.success("Članak je obrisan");
      onDeleted();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  };
  return <Button type="button" variant="outline" size="sm" className="text-ccn-red" disabled={busy} onClick={remove} aria-label={`Obriši članak: ${article.title || "Bez naslova"}`} data-testid={testId || `article-delete-${article.id}`}><Trash2 className="w-4 h-4 mr-1" />{busy ? "Brisanje…" : "Obriši"}</Button>;
}
