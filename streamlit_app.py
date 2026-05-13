import streamlit as st

from src.engine.loader import DataValidationError, load_gamedata
from src.runner.runner_utils import (
    execute_campaign_run,
    execute_scene_run,
    load_preset,
)
from src.runner.streamlit_utils import (
    build_scene_result_rows,
    discover_local_models,
    normalize_single_scene_run,
    rewrite_run_config_for_model,
)


st.set_page_config(page_title="AgentQuest Run Viewer", layout="wide")


def _render_scene_result(row: dict) -> None:
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown(f"### {row['scene_id']}")
        st.caption(row["scene_title"])
        st.markdown(f"**Monster:** {row['monster_name']}")
        st.code(row["monster_id"])

    with right_col:
        st.markdown(f"### {row['character_name']}")
        st.code(row["character_id"])

    st.markdown("**Model Tool Call**")
    st.code(row["raw_model_output"] or "No model output returned.", language="json")

    if row["status"] == "success":
        st.success(row["status_label"])
    else:
        reason = row["reason"] or row["verdict"].get("outcome", "failure")
        st.error(f"{row['status_label']}: {reason}")

    if row["reason"]:
        st.caption(row["reason"])

    with st.expander("Validator Details"):
        st.json(row["verdict"])


def main() -> None:
    st.title("AgentQuest Run Viewer")
    st.caption("Install Streamlit if needed: `pip install streamlit`")

    try:
        gamedata = load_gamedata("data")
    except DataValidationError as error:
        st.error(f"Data validation error: {error}")
        return
    except Exception as error:
        st.error(f"Unexpected error while loading game data: {error}")
        return

    model_options = discover_local_models()
    if not model_options:
        st.error("No GGUF models were found under local_models/.")
        return

    characters = gamedata["raw"]["characters"]
    campaigns = gamedata["raw"]["campaigns"]
    scenes = gamedata["raw"]["scenes"]

    character_options = {f"{item['name']} ({item['character_id']})": item["character_id"] for item in characters}
    campaign_options = {f"{item['name']} ({item['campaign_id']})": item["campaign_id"] for item in campaigns}
    scene_options = {
        f"{item['title']} ({item['scene_id']})": item["scene_id"]
        for item in scenes
    }

    with st.form("run_form"):
        top_left, top_mid, top_right = st.columns(3)

        with top_left:
            selected_model = st.selectbox("Model", model_options, index=0)

        with top_mid:
            selected_character_label = st.selectbox("Character", list(character_options.keys()), index=0)
            selected_character_id = character_options[selected_character_label]

        with top_right:
            run_mode = st.selectbox("Run Type", ["campaign", "scene"], index=0)

        if run_mode == "campaign":
            selected_campaign_label = st.selectbox("Campaign", list(campaign_options.keys()), index=0)
            selected_campaign_id = campaign_options[selected_campaign_label]
            selected_scene_id = None
        else:
            selected_scene_label = st.selectbox("Scene", list(scene_options.keys()), index=0)
            selected_scene_id = scene_options[selected_scene_label]
            selected_campaign_id = None

        submitted = st.form_submit_button("Run")

    if not submitted:
        return

    try:
        rewrite_run_config_for_model(selected_model)
        cfg = load_preset("default")

        if run_mode == "campaign":
            run_result = execute_campaign_run(
                gamedata=gamedata,
                campaign_id=selected_campaign_id,
                character_id=selected_character_id,
                prompt_format="json_only",
                cfg=cfg,
                model_key="",
                max_tokens=128,
                temperature=0.0,
            )
        else:
            scene_run = execute_scene_run(
                gamedata=gamedata,
                character_id=selected_character_id,
                scene_id=selected_scene_id,
                prompt_format="json_only",
                cfg=cfg,
                model_key="",
                max_tokens=128,
                temperature=0.0,
            )
            run_result = normalize_single_scene_run(scene_run)

        scene_rows = build_scene_result_rows(run_result["scene_runs"], gamedata)

        st.subheader("Run Summary")
        summary_payload = {
            "model": selected_model,
            "character_id": selected_character_id,
            "run_type": run_mode,
            "campaign_id": selected_campaign_id,
            "scene_id": selected_scene_id,
            "total_scenes_rendered": len(scene_rows),
            "final_outcome": run_result["final_outcome"],
            "stop_scene_id": run_result["stop_scene_id"],
        }
        st.json(summary_payload)

        for index, row in enumerate(scene_rows):
            if index:
                st.divider()
            _render_scene_result(row)

    except Exception as error:
        st.error(f"Run failed: {error}")


if __name__ == "__main__":
    main()
