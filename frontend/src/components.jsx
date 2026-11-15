import { useState } from "react";

/** Material Symbols icon. */
export function Icon({ name, className = "" }) {
  return <span className={`ms ${className}`} aria-hidden="true">{name}</span>;
}

/** Page header: eyebrow, big title with the lime period, lede, actions. */
export function PageHead({ eyebrow, title, lede, children }) {
  return (
    <section className="page-head">
      <div>
        {eyebrow && <p className="eyebrow"><span className="led" />{eyebrow}</p>}
        <h1>{title}<span className="dot-accent">.</span></h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {children && <div className="row">{children}</div>}
    </section>
  );
}

/** Card header: "01 / TARGET ROLE" eyebrow + title (+ right-hand slot). */
export function CardHead({ step, eyebrow, title, sub, children }) {
  return (
    <div className="card-head">
      <div>
        {(step || eyebrow) && (
          <p className="eyebrow">{step ? `${step} / ` : ""}{eyebrow}</p>
        )}
        <h2>{title}</h2>
        {sub && <p className="muted small" style={{ margin: "2px 0 0" }}>{sub}</p>}
      </div>
      {children && <div className="row">{children}</div>}
    </div>
  );
}

export function Chips({ items, tone = "", empty = "none", icon }) {
  if (!items?.length) return <span className="faint small">{empty}</span>;
  return (
    <div className="chips">
      {items.map((s) => (
        <span key={s} className={`chip ${tone}`}>{icon && <Icon name={icon} />}{s}</span>
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
          <Icon name="lightbulb" />{s}
          <button type="button" aria-label={`Remove ${s}`}
                  onClick={() => onChange(value.filter((v) => v !== s))}>×</button>
        </span>
      ))}
      <input
        value={draft}
        placeholder={value.length ? "+ Add skill" : placeholder}
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

/** Stat tile: coloured mono label (+ icon), big number, unit word, optional sub line. */
export function Stat({ label, value, unit, sub, icon, tone = "", active, onClick, corner }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag type={onClick ? "button" : undefined}
         className={`stat ${tone} ${active ? "active" : ""}`} onClick={onClick}
         aria-pressed={onClick ? !!active : undefined}>
      <span className="stat-top">
        <span className="stat-label">{label}</span>
        {corner}{icon && <Icon name={icon} className="sm" />}
      </span>
      <span>
        <span className="stat-num">{value ?? "–"}</span>
        {unit && <span className="stat-unit">{unit}</span>}
      </span>
      {sub && <span className="stat-sub">{sub}</span>}
    </Tag>
  );
}

export function Alert({ tone = "amber", icon = "warning", title, children }) {
  return (
    <div className={`alert ${tone}`} role={tone === "coral" ? "alert" : "status"}>
      <Icon name={icon} />
      <div>{title && <b>{title}</b>}{children}</div>
    </div>
  );
}

export function EmptyState({ icon, title, children, actions }) {
  return (
    <div className="empty-state">
      <div className="icon-box"><Icon name={icon} className="lg" /></div>
      <h2>{title}</h2>
      <p>{children}</p>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}
