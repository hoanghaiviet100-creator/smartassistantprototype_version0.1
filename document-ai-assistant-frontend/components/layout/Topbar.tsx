import { ChevronDown, CircleHelp, ShieldCheck } from "lucide-react";

export function Topbar() {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <span>Workspace</span><span className="slash">/</span><strong>Ask documents</strong><ChevronDown size={14} />
      </div>
      <div className="topbar-actions">
        <span className="privacy-note"><ShieldCheck size={14} /> Private workspace</span>
        <button type="button" className="help-button" aria-label="Help"><CircleHelp size={17} /></button>
      </div>
    </header>
  );
}
