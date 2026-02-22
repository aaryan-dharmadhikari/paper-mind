from nicegui import ui
from starlette.requests import Request
from pages.layout import frame
import db
import llm

AGENT_STYLES = {
    "teach": {"label": "Teach", "color": "#6366f1", "bg": "#eef2ff", "border": "#c7d2fe"},
    "zealot": {"label": "Zealot", "color": "#dc2626", "bg": "#fef2f2", "border": "#fecaca"},
}


def _build_paper_context(paper: dict, concepts: list[dict], notes: list[dict]) -> str:
    concept_list = ", ".join(c["name"] for c in concepts)
    ctx = (
        f"Paper: {paper['title']}\n"
        f"Authors: {', '.join(paper['authors'])}\n"
        f"Abstract: {paper['abstract']}\n\n"
        f"Summary: {paper['summary']}\n\n"
        f"Key concepts: {concept_list}"
    )
    if notes:
        takeaways = "\n".join(f"- {n['takeaway']}" for n in notes)
        ctx += f"\n\nUser's takeaways:\n{takeaways}"
    return ctx


def _render_msg(container, msg: dict):
    """Render a single message into the chat container."""
    with container:
        if msg["role"] == "user":
            with ui.element("div").classes("flex justify-end w-full"):
                ui.html(msg["content"]).classes(
                    "rounded-xl px-4 py-2 max-w-[75%] bg-gray-100 text-gray-800"
                )
        elif msg["role"] == "assistant":
            agent = msg.get("agent", "teach")
            style = AGENT_STYLES[agent]
            with ui.element("div").classes("flex justify-start w-full gap-2 items-start"):
                ui.badge(style["label"]).style(
                    f"background-color: {style['color']}; color: white; flex-shrink: 0; margin-top: 4px"
                )
                ui.html(msg["content"]).style(
                    f"background-color: {style['bg']}; border: 1px solid {style['border']}; "
                    f"color: #1f2937"
                ).classes("rounded-xl px-4 py-2 max-w-[75%]")


@ui.page("/chat/new")
def new_chat_page(request: Request):
    paper_id = int(request.query_params.get("paper_id", 0))
    agent = request.query_params.get("agent", "teach")

    if not paper_id:
        frame("Chat")
        with ui.column().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label("Missing paper_id.").classes("text-red-500")
        return

    chat_id = db.get_or_create_chat_for_paper(paper_id)
    ui.navigate.to(f"/chat/{chat_id}?agent={agent}")


@ui.page("/chat/{chat_id}")
def chat_page(chat_id: int, request: Request):
    frame("Chat")

    chat = db.get_chat(chat_id)
    if chat is None:
        with ui.column().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label("Chat not found.").classes("text-red-500")
        return

    paper = db.get_paper(chat["paper_id"])
    if paper is None:
        with ui.column().classes("w-full max-w-3xl mx-auto p-4"):
            ui.label("Paper not found.").classes("text-red-500")
        return

    concepts = db.get_concepts_for_paper(chat["paper_id"])
    notes = db.get_notes_for_paper(chat["paper_id"])
    paper_context = _build_paper_context(paper, concepts, notes)

    messages: list[dict] = chat["messages_json"]
    initial_agent = request.query_params.get("agent", "teach")
    state = {"agent": initial_agent, "sending": False}

    with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-2"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.link(paper["title"], f"/paper/{paper['id']}").classes("font-medium text-lg")

            def start_fresh():
                new_id = db.create_chat(chat["paper_id"])
                ui.navigate.to(f"/chat/{new_id}?agent={state['agent']}")
            ui.button("New Session", icon="add", on_click=start_fresh).props("flat dense size=sm")

        # Agent toggle
        with ui.row().classes("w-full items-center gap-2"):
            teach_btn = ui.button("Teach", icon="school").props("dense")
            zealot_btn = ui.button("Zealot", icon="quiz").props("dense")

            def set_agent(agent: str):
                state["agent"] = agent
                _update_toggle_styles()

            def _update_toggle_styles():
                if state["agent"] == "teach":
                    teach_btn.props("color=primary")
                    zealot_btn.props(remove="color=red", add="color=grey outline")
                else:
                    zealot_btn.props("color=red")
                    teach_btn.props(remove="color=primary", add="color=grey outline")

            teach_btn.on_click(lambda: set_agent("teach"))
            zealot_btn.on_click(lambda: set_agent("zealot"))
            _update_toggle_styles()

        # Summary & takeaways
        with ui.expansion("Paper Summary & Takeaways", icon="description").classes("w-full").props(
            "default-opened" if not messages else ""
        ):
            ui.label(paper["summary"]).classes("text-sm text-gray-700")
            if notes:
                ui.separator()
                ui.label("Your Takeaways").classes("text-sm font-semibold mt-1")
                for n in notes:
                    ui.label(f"- {n['takeaway']}").classes("text-sm text-gray-600")

        # Chat area
        chat_container = ui.column().classes("w-full gap-3 flex-1 overflow-y-auto p-2").style("max-height: 55vh")

        with chat_container:
            for msg in messages:
                _render_msg(chat_container, msg)

        # Input
        with ui.row().classes("w-full gap-2 items-end"):
            msg_input = ui.textarea(placeholder="Type your message...").classes("flex-1").props("rows=2 autofocus")

            async def send_message():
                if state["sending"]:
                    return
                text = msg_input.value.strip()
                if not text:
                    return

                state["sending"] = True
                msg_input.value = ""
                agent = state["agent"]
                style = AGENT_STYLES[agent]
                system_prompt = llm.TEACH_SYSTEM if agent == "teach" else llm.ZEALOT_SYSTEM

                messages.append({"role": "user", "content": text})

                with chat_container:
                    # User bubble
                    with ui.element("div").classes("flex justify-end w-full"):
                        ui.html(text).classes("rounded-xl px-4 py-2 max-w-[75%] bg-gray-100 text-gray-800")

                    # Agent bubble (streaming)
                    with ui.element("div").classes("flex justify-start w-full gap-2 items-start"):
                        ui.badge(style["label"]).style(
                            f"background-color: {style['color']}; color: white; flex-shrink: 0; margin-top: 4px"
                        )
                        response_html = ui.html("...").style(
                            f"background-color: {style['bg']}; border: 1px solid {style['border']}; color: #1f2937"
                        ).classes("rounded-xl px-4 py-2 max-w-[75%]")

                # Build LLM messages with paper context on first user msg
                llm_messages = []
                for i, m in enumerate(messages):
                    if m["role"] == "assistant":
                        llm_messages.append({"role": "assistant", "content": m["content"]})
                    elif i == 0 and m["role"] == "user":
                        llm_messages.append({
                            "role": "user",
                            "content": f"[Paper Context]\n{paper_context}\n\n[User]\n{m['content']}",
                        })
                    else:
                        llm_messages.append({"role": m["role"], "content": m["content"]})

                full_response = ""
                try:
                    async for chunk in llm.stream_chat_response(llm_messages, system_prompt):
                        full_response += chunk
                        response_html.content = full_response.replace("\n", "<br>")
                except Exception as e:
                    full_response = f"Error: {e}"
                    response_html.content = full_response

                messages.append({"role": "assistant", "content": full_response, "agent": agent})
                db.update_chat_messages(chat_id, messages)

                if agent == "zealot":
                    zealot_msgs = [m for m in messages if m.get("agent") == "zealot" or m["role"] == "user"]
                    if len(zealot_msgs) >= 8:
                        await _run_assessment(chat["paper_id"], zealot_msgs, concepts)

                state["sending"] = False

            ui.button("Send", on_click=send_message).props("color=primary")

            async def end_and_assess():
                zealot_msgs = [m for m in messages if m.get("agent") == "zealot" or m["role"] == "user"]
                if len(zealot_msgs) >= 2:
                    await _run_assessment(chat["paper_id"], zealot_msgs, concepts)
                    ui.notify("Knowledge assessment updated!", type="positive")
            ui.button("Assess", icon="grading", on_click=end_and_assess).props("color=red outline dense")


async def _run_assessment(paper_id: int, messages: list[dict], concepts: list[dict]):
    concept_names = [c["name"] for c in concepts]
    assessments = await llm.assess_knowledge(messages, concept_names)
    for a in assessments:
        name = a.get("concept", "").strip().lower()
        confidence = a.get("confidence", 0.0)
        for c in concepts:
            if c["name"] == name:
                db.upsert_user_knowledge(c["id"], confidence)
                break
