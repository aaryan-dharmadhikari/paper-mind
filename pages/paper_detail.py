import base64
from pathlib import Path
from nicegui import ui
from pages.layout import frame
from config import UPLOAD_DIR
import db
import llm


@ui.page("/paper/{paper_id}")
def paper_detail_page(paper_id: int):
    frame("Paper Detail")

    paper = db.get_paper(paper_id)
    if paper is None:
        with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
            ui.label("Paper not found.").classes("text-red-500 text-xl")
        return

    concepts = db.get_concepts_for_paper(paper_id)
    notes = db.get_notes_for_paper(paper_id)

    with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        # Title + authors
        if paper["source_url"]:
            ui.link(paper["title"], f"/uploads/{paper['source_url']}", new_tab=True).classes("text-2xl font-bold")
        else:
            ui.label(paper["title"]).classes("text-2xl font-bold")
        authors_str = ", ".join(paper["authors"])
        if authors_str:
            ui.label(authors_str).classes("text-gray-600")
        ui.label(f"Added {paper['added_at'][:10]}").classes("text-sm text-gray-400")

        # Self-rating + chat button
        with ui.row().classes("w-full items-center gap-4"):
            ui.button("Open Chat", icon="chat",
                      on_click=lambda: ui.navigate.to(f"/chat/new?paper_id={paper_id}&agent=teach")
                      ).props("color=primary")

            ui.label("My understanding:").classes("text-sm text-gray-500 ml-auto")
            current_rating = paper.get("self_rating") or 0.0
            rating_labels = {0: "Not rated", 1: "Lost", 2: "Shaky", 3: "Getting there", 4: "Solid", 5: "Nailed it"}
            rating_label = ui.label(rating_labels[round(current_rating * 5)]).classes("text-sm font-medium")

            def on_rating_change(e):
                val = e.value / 5.0
                db.update_paper_self_rating(paper_id, val)
                rating_label.text = rating_labels[e.value]

            ui.slider(min=0, max=5, step=1, value=round(current_rating * 5),
                      on_change=on_rating_change).props("label-always").classes("w-48")

        # Abstract
        if paper["abstract"]:
            with ui.card().classes("w-full"):
                ui.label("Abstract").classes("text-lg font-semibold mb-1")
                ui.label(paper["abstract"]).classes("text-sm text-gray-700")

        # Summary
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Summary").classes("text-lg font-semibold")

                regen_btn = ui.button("Regenerate", icon="refresh").props("flat dense size=sm")
                regen_spinner = ui.spinner(size="sm")
                regen_spinner.visible = False

                async def regenerate_summary():
                    pdf_path = UPLOAD_DIR / paper["source_url"] if paper["source_url"] else None
                    if not pdf_path or not pdf_path.exists():
                        ui.notify("PDF not found in uploads", type="negative")
                        return

                    regen_btn.visible = False
                    regen_spinner.visible = True
                    summary_label.text = "Regenerating summary..."

                    try:
                        pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("utf-8")
                        parsed = await llm.parse_paper_with_llm(pdf_b64)
                        new_summary = parsed.get("summary", "")
                        if new_summary:
                            db.update_paper_summary(paper_id, new_summary)
                            summary_label.text = new_summary
                            ui.notify("Summary regenerated!", type="positive")
                        else:
                            summary_label.text = paper["summary"] or "No summary."
                            ui.notify("LLM returned empty summary", type="warning")
                    except Exception as e:
                        summary_label.text = paper["summary"] or "No summary."
                        ui.notify(f"Error: {e}", type="negative")
                    finally:
                        regen_btn.visible = True
                        regen_spinner.visible = False

                regen_btn.on_click(regenerate_summary)

            summary_label = ui.label(paper["summary"] or "No summary yet.").classes("text-gray-700")

        # Concepts
        if concepts:
            with ui.card().classes("w-full"):
                ui.label("Key Concepts").classes("text-lg font-semibold mb-2")
                with ui.row().classes("flex-wrap gap-2"):
                    for c in concepts:
                        with ui.badge(c["name"]).props("color=secondary outline"):
                            ui.tooltip(c["description"] or "No description")

        # Previous chats for this paper
        chats = db.list_chats(paper_id=paper_id)
        if chats:
            with ui.card().classes("w-full"):
                ui.label("Chat History").classes("text-lg font-semibold mb-2")
                for ch in chats:
                    agent_label = "Teach" if ch["agent_type"] == "teach" else "Zealot"
                    with ui.row().classes("items-center gap-2 py-1 border-b"):
                        ui.badge(agent_label, color="primary" if ch["agent_type"] == "teach" else "negative")
                        ui.link(f"Session {ch['id']} — {ch['created_at'][:10]}", f"/chat/{ch['id']}").classes("text-sm")

        # User notes / takeaways
        with ui.card().classes("w-full"):
            ui.label("My Takeaways").classes("text-lg font-semibold mb-2")

            notes_container = ui.column().classes("w-full gap-2")

            def render_notes():
                notes_container.clear()
                current_notes = db.get_notes_for_paper(paper_id)
                with notes_container:
                    if not current_notes:
                        ui.label("No takeaways yet.").classes("text-gray-400 text-sm")
                    for n in current_notes:
                        with ui.row().classes("w-full items-start gap-2 py-1 border-b"):
                            ui.label(n["takeaway"]).classes("flex-1 text-sm")
                            ui.label(n["created_at"][:10]).classes("text-xs text-gray-400")

            render_notes()

            with ui.row().classes("w-full gap-2 mt-2"):
                note_input = ui.textarea(placeholder="Write a takeaway...").classes("flex-1").props("rows=2")

                def save_note():
                    text = note_input.value.strip()
                    if text:
                        db.add_note(paper_id, text)
                        note_input.value = ""
                        render_notes()

                ui.button("Save", on_click=save_note).props("color=primary")
