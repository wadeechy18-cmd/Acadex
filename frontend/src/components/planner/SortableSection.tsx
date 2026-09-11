"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/Button";
import type { ContentBlock, LessonSection } from "@/types";

interface Props {
  section: LessonSection;
  onChange: (section: LessonSection) => void;
  onDelete: () => void;
  onDuplicate: () => void;
}

export function SortableSection({ section, onChange, onDelete, onDuplicate }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: section.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  function updateBlock(index: number, block: ContentBlock) {
    const body = [...section.body];
    body[index] = block;
    onChange({ ...section, body });
  }

  function addBlock() {
    onChange({ ...section, body: [...section.body, { type: "paragraph", text: "" }] });
  }

  function removeBlock(index: number) {
    onChange({ ...section, body: section.body.filter((_, i) => i !== index) });
  }

  return (
    <div ref={setNodeRef} style={style} className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-3">
        <button
          type="button"
          {...attributes}
          {...listeners}
          aria-label="Drag to reorder"
          className="mt-2 cursor-grab select-none text-slate-400 hover:text-slate-600"
        >
          ⋮⋮
        </button>
        <div className="flex-1 flex flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            <input
              value={section.title}
              onChange={(e) => onChange({ ...section, title: e.target.value })}
              placeholder="Section title"
              className="flex-1 min-w-[160px] rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            />
            <input
              value={section.type}
              onChange={(e) => onChange({ ...section, type: e.target.value })}
              placeholder="type (e.g. starter)"
              className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            />
            <input
              type="number"
              min={0}
              max={300}
              value={section.duration_minutes}
              onChange={(e) => onChange({ ...section, duration_minutes: Number(e.target.value) })}
              className="w-24 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            />
            <span className="self-center text-sm text-slate-500">min</span>
          </div>

          <div className="flex flex-col gap-2">
            {section.body.map((block, i) => (
              <div key={i} className="flex gap-2">
                <select
                  value={block.type}
                  onChange={(e) => updateBlock(i, { ...block, type: e.target.value as ContentBlock["type"] })}
                  className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <option value="paragraph">Paragraph</option>
                  <option value="activity_instruction">Activity instruction</option>
                </select>
                <textarea
                  value={block.text}
                  onChange={(e) => updateBlock(i, { ...block, text: e.target.value })}
                  rows={2}
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                />
                <button
                  type="button"
                  onClick={() => removeBlock(i)}
                  className="text-xs text-slate-400 hover:text-red-600"
                  aria-label="Remove block"
                >
                  ✕
                </button>
              </div>
            ))}
            <button type="button" onClick={addBlock} className="self-start text-xs font-medium text-brand-700 hover:underline">
              + Add content
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <Button variant="secondary" className="px-2 py-1 text-xs" onClick={onDuplicate}>
            Duplicate
          </Button>
          <Button variant="secondary" className="px-2 py-1 text-xs" onClick={onDelete}>
            Remove
          </Button>
        </div>
      </div>
    </div>
  );
}
