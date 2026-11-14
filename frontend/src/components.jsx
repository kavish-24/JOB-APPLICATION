import { useState } from "react";

export function Chips({ items, tone = "", empty = "none" }) {
  if (!items?.length) return <span className="faint">{empty}</span>;
  return (
    <div className="chips">
      {items.map((s) => (
        <span key={s} className={`chip ${tone}`}>{s}</span>
      ))}
    </div>
  );
}

/** Type a skill, press Enter or comma to add it; Backspace on empty removes the last. */
export function TagInput({ value, onChange, placeholder = "Add a skill, press Enter" }) {
  const [draft, setDraft] = useState("");
  const add = (raw) => {
    const parts = raw.split(",").map((s) => s.trim()).filter(Boolean);
    const next = [...value];
    for (const p of parts)
      if (!next.some((v) => v.toLowerCase() === p.toLowerCase())) next.push(p);
    onChange(next);
    setDraft("");
  };
  return (
    <div className="taginput" onClick={(e) => e.currentTarget.querySelector("input")?.focus()}>
      {value.map((s) => (
        <span key={s} className="chip tag">
          {s}
          <button type="button" aria-label={`Remove ${s}`}
                  onClick={() => onChange(value.filter((v) => v !== s))}>×</button>
        </span>
      ))}
      <input
        value={draft}
        placeholder={value.length ? "" : placeholder}
        onChange={(e) => (e.target.value.endsWith(",") ? add(e.target.value) : setDraft(e.target.value))}
        onKeyDown={(e) => {
          if (e.key === "Enter") { e.preventDefault(); if (draft.trim()) add(draft); }
          if (e.key === "Backspace" && !draft && value.length) onChange(value.slice(0, -1));
        }}
        onBlur={() => draft.trim() && add(draft)}
      />
    </div>
  );
}

export function Segmented({ options, value, onChange, name }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={name}>
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value}
                className={`${value === o.value ? "on" : ""} ${o.tone || ""}`}
                onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Stat({ value, label, tone = "", active, onClick }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag type={onClick ? "button" : undefined}
         className={`stat ${tone} ${active ? "active" : ""}`} onClick={onClick}>
      <span className="stat-num">{value ?? "–"}</span>
      <span className="stat-label">{label}</span>
    </Tag>
  );
}
