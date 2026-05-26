import streamlit as st


def inject_app_chrome() -> None:
    st.markdown(
        """
        <style>
        :root {
            --aq-bg: #10151d;
            --aq-panel: rgba(22, 29, 39, 0.92);
            --aq-panel-strong: rgba(27, 36, 48, 0.98);
            --aq-ink: #edf2f7;
            --aq-muted: #a8b3c2;
            --aq-line: rgba(140, 167, 196, 0.18);
            --aq-accent: #c68b3c;
            --aq-accent-deep: #8d5a1f;
            --aq-success: #74c69d;
            --aq-danger: #f28482;
            --aq-info: #89c2d9;
        }
        .stApp {
            background:
                radial-gradient(circle at top, rgba(198, 139, 60, 0.16), transparent 30%),
                linear-gradient(180deg, #0d1218 0%, #111823 42%, #151f2d 100%);
            color: var(--aq-ink);
        }
        .aq-hero, .aq-panel, .aq-summary {
            background: var(--aq-panel);
            border: 1px solid var(--aq-line);
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(61, 39, 24, 0.08);
        }
        .aq-hero {
            padding: 1.4rem 1.6rem;
            margin-bottom: 1rem;
            background:
                linear-gradient(135deg, rgba(24, 32, 44, 0.98), rgba(55, 38, 24, 0.94)),
                var(--aq-panel);
            color: #f7fafc;
        }
        .aq-hero h1 {
            margin: 0;
            font-size: 2.2rem;
            letter-spacing: 0.04em;
        }
        .aq-hero p {
            margin: 0.35rem 0 0;
            color: rgba(237, 242, 247, 0.86);
        }
        .aq-panel, .aq-summary {
            padding: 1rem 1.1rem;
            margin-bottom: 0.85rem;
        }
        .aq-kicker {
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.72rem;
            color: #f6c177;
            margin-bottom: 0.35rem;
        }
        .aq-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--aq-muted);
            margin-bottom: 0.2rem;
        }
        .aq-value {
            font-size: 1rem;
            font-weight: 600;
            color: var(--aq-ink);
        }
        .aq-scene-card {
            background: var(--aq-panel-strong);
            border: 1px solid var(--aq-line);
            border-radius: 16px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.65rem;
        }
        .aq-progress-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }
        .aq-scene-card.current {
            border-color: rgba(159, 91, 45, 0.65);
            box-shadow: 0 0 0 1px rgba(159, 91, 45, 0.12);
        }
        .aq-scene-title {
            font-weight: 700;
            color: var(--aq-ink);
        }
        .aq-scene-meta {
            color: var(--aq-muted);
            font-size: 0.92rem;
        }
        .aq-status-pill {
            display: inline-block;
            margin-top: 0.35rem;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            background: rgba(53, 92, 125, 0.12);
            color: var(--aq-info);
        }
        .aq-status-pass { background: rgba(116, 198, 157, 0.14); color: var(--aq-success); }
        .aq-status-fail { background: rgba(242, 132, 130, 0.14); color: var(--aq-danger); }
        .aq-status-not_run { background: rgba(137, 194, 217, 0.12); color: var(--aq-info); }
        .aq-status-running { background: rgba(198, 139, 60, 0.14); color: #f6c177; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(14, 20, 28, 0.98), rgba(20, 29, 40, 0.98));
            border-right: 1px solid var(--aq-line);
        }
        [data-testid="stSidebar"] * {
            color: var(--aq-ink);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_status_label(status: str) -> str:
    return status.replace("_", " ").strip().upper()


def render_page_hero(*, run_mode: str, selected_preset: str, actor_label: str) -> None:
    mission = "Campaign operations" if run_mode == "campaign" else "Single scene skirmish"
    st.markdown(
        (
            "<section class='aq-hero'>"
            "<div class='aq-kicker'>AgentQuest Tactical Console</div>"
            "<h1>Run Viewer</h1>"
            f"<p>{mission} with <strong>{actor_label}</strong> under the "
            f"<strong>{selected_preset}</strong> preset.</p>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_info_panel(title: str, items: list[tuple[str, str]]) -> None:
    body = "".join(
        f"<div class='aq-label'>{label}</div><div class='aq-value'>{value}</div>"
        for label, value in items
    )
    st.markdown(
        f"<section class='aq-panel'><div class='aq-scene-title'>{title}</div>{body}</section>",
        unsafe_allow_html=True,
    )


def status_css_class(status: str) -> str:
    normalized = status.lower()
    if normalized == "pass":
        return "aq-status-pass"
    if normalized in {"fail", "hard_fail", "soft_fail", "ast_fail"}:
        return "aq-status-fail"
    if normalized == "running":
        return "aq-status-running"
    return "aq-status-not_run"
