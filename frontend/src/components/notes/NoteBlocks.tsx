import katex from "katex";
import type { NoteBlock } from "@/types";

function Formula({ latex }: { latex: string }) {
  let html: string;
  try {
    html = katex.renderToString(latex, { throwOnError: false, displayMode: true });
  } catch {
    html = latex;
  }
  return <div className="overflow-x-auto py-2" dangerouslySetInnerHTML={{ __html: html }} />;
}

const CALLOUT_STYLES: Record<string, { label: string; className: string }> = {
  key_point: { label: "Key point", className: "border-brand-300 bg-brand-50 text-brand-900" },
  example: { label: "Example", className: "border-slate-300 bg-slate-50 text-slate-800" },
  exam_tip: { label: "Exam tip", className: "border-amber-300 bg-amber-50 text-amber-900" },
};

function Callout({ kind, text }: { kind: string; text: string }) {
  const style = CALLOUT_STYLES[kind];
  return (
    <div className={`rounded-lg border-l-4 px-4 py-3 text-sm ${style.className}`}>
      <p className="font-semibold uppercase tracking-wide text-xs">{style.label}</p>
      <p className="mt-1">{text}</p>
    </div>
  );
}

export function NoteBlocks({ blocks }: { blocks: NoteBlock[] }) {
  return (
    <div className="flex flex-col gap-4">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "heading":
            return (
              <h3 key={i} className="text-lg font-semibold text-slate-900">
                {String(block.text)}
              </h3>
            );
          case "paragraph":
            return (
              <p key={i} className="text-sm leading-relaxed text-slate-700">
                {String(block.text)}
              </p>
            );
          case "formula":
            return <Formula key={i} latex={String(block.latex)} />;
          case "key_point":
          case "example":
          case "exam_tip":
            return <Callout key={i} kind={block.type} text={String(block.text)} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
