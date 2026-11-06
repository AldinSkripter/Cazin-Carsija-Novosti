import { useEffect, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import Youtube from "@tiptap/extension-youtube";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import {
  Bold, Italic, Strikethrough, Heading2, Heading3, List, ListOrdered, Quote, Link2, ImagePlus, Youtube as YtIcon, Table2, Undo2, Redo2, Minus,
} from "lucide-react";
import { mediaUrl } from "../../lib/api";
import { MediaPicker } from "./Media";

function Btn({ on, active, children, label }) {
  return (
    <button type="button" onClick={on} title={label} aria-label={label} data-testid={`editor-${label.toLowerCase().replace(/\s+/g, "-")}`}
      className={`p-2 rounded-sm hover:bg-slate-100 ${active ? "bg-ccn-mist text-ccn-tealdark" : ""}`}>{children}</button>
  );
}

export function RichEditor({ value, onChange }) {
  const [pick, setPick] = useState(false);
  const editor = useEditor({
    extensions: [
      StarterKit, Link.configure({ openOnClick: false }), Image, Youtube.configure({ nocookie: true, width: 640, height: 360 }),
      Table.configure({ resizable: false }), TableRow, TableHeader, TableCell,
    ],
    content: value || "",
    onUpdate: ({ editor: e }) => onChange(e.getHTML()),
  });
  useEffect(() => {
    if (editor && value !== editor.getHTML() && !editor.isFocused) editor.commands.setContent(value || "", false);
  }, [value, editor]);
  if (!editor) return null;
  const c = () => editor.chain().focus();
  const link = () => {
    const url = window.prompt("URL linka (https://…)", editor.getAttributes("link").href || "https://");
    if (url === null) return;
    if (!url) c().unsetLink().run(); else c().extendMarkRange("link").setLink({ href: url }).run();
  };
  const yt = () => { const url = window.prompt("YouTube URL"); if (url) c().setYoutubeVideo({ src: url }).run(); };
  return (
    <div className="border rounded-md bg-white" data-testid="rich-editor">
      <div className="flex flex-wrap gap-0.5 border-b p-1 sticky top-14 bg-white z-10">
        <Btn label="Podebljano" on={() => c().toggleBold().run()} active={editor.isActive("bold")}><Bold className="w-4 h-4" /></Btn>
        <Btn label="Kurziv" on={() => c().toggleItalic().run()} active={editor.isActive("italic")}><Italic className="w-4 h-4" /></Btn>
        <Btn label="Precrtano" on={() => c().toggleStrike().run()} active={editor.isActive("strike")}><Strikethrough className="w-4 h-4" /></Btn>
        <Btn label="Naslov H2" on={() => c().toggleHeading({ level: 2 }).run()} active={editor.isActive("heading", { level: 2 })}><Heading2 className="w-4 h-4" /></Btn>
        <Btn label="Naslov H3" on={() => c().toggleHeading({ level: 3 }).run()} active={editor.isActive("heading", { level: 3 })}><Heading3 className="w-4 h-4" /></Btn>
        <Btn label="Lista" on={() => c().toggleBulletList().run()} active={editor.isActive("bulletList")}><List className="w-4 h-4" /></Btn>
        <Btn label="Numerisana lista" on={() => c().toggleOrderedList().run()} active={editor.isActive("orderedList")}><ListOrdered className="w-4 h-4" /></Btn>
        <Btn label="Citat" on={() => c().toggleBlockquote().run()} active={editor.isActive("blockquote")}><Quote className="w-4 h-4" /></Btn>
        <Btn label="Link" on={link} active={editor.isActive("link")}><Link2 className="w-4 h-4" /></Btn>
        <Btn label="Slika" on={() => setPick(true)}><ImagePlus className="w-4 h-4" /></Btn>
        <Btn label="YouTube" on={yt}><YtIcon className="w-4 h-4" /></Btn>
        <Btn label="Tabela" on={() => c().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}><Table2 className="w-4 h-4" /></Btn>
        <Btn label="Linija" on={() => c().setHorizontalRule().run()}><Minus className="w-4 h-4" /></Btn>
        <Btn label="Poništi" on={() => c().undo().run()}><Undo2 className="w-4 h-4" /></Btn>
        <Btn label="Ponovi" on={() => c().redo().run()}><Redo2 className="w-4 h-4" /></Btn>
        {editor.isActive("table") && (
          <span className="flex gap-1 text-xs items-center ml-2">
            <button type="button" className="px-2 py-1 border rounded-sm" onClick={() => c().addRowAfter().run()}>+ red</button>
            <button type="button" className="px-2 py-1 border rounded-sm" onClick={() => c().addColumnAfter().run()}>+ kolona</button>
            <button type="button" className="px-2 py-1 border rounded-sm" onClick={() => c().deleteTable().run()}>obriši tabelu</button>
          </span>
        )}
      </div>
      <EditorContent editor={editor} className="article-body !text-base" />
      <MediaPicker open={pick} onClose={() => setPick(false)} onPick={(m) => c().setImage({ src: mediaUrl(m.large), alt: m.alt || "", title: m.credit ? `Foto: ${m.credit}` : "" }).run()} />
    </div>
  );
}
