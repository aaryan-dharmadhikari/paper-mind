from nicegui import ui
from pages.layout import frame
import db


@ui.page("/")
def dashboard_page():
    frame("Dashboard")

    stats = db.get_stats()
    papers = db.list_papers()
    knowledge = db.get_user_knowledge()
    recent_chats = db.list_chats(limit=10)

    with ui.column().classes("w-full max-w-5xl mx-auto p-4 gap-4"):
        # Stats cards
        with ui.row().classes("w-full gap-4"):
            with ui.card().classes("flex-1"):
                ui.label("Papers").classes("text-sm text-gray-500")
                ui.label(str(stats["paper_count"])).classes("text-3xl font-bold")
            with ui.card().classes("flex-1"):
                ui.label("Concepts").classes("text-sm text-gray-500")
                ui.label(str(stats["concept_count"])).classes("text-3xl font-bold")
            with ui.card().classes("flex-1"):
                ui.label("Chat Sessions").classes("text-sm text-gray-500")
                ui.label(str(stats["chat_count"])).classes("text-3xl font-bold")
            with ui.card().classes("flex-1"):
                ui.label("Avg. Confidence").classes("text-sm text-gray-500")
                ui.label(f"{stats['avg_confidence']:.0%}").classes("text-3xl font-bold")

        # Knowledge confidence chart
        if knowledge:
            with ui.card().classes("w-full"):
                ui.label("Knowledge Confidence").classes("text-lg font-semibold mb-2")
                chart_data = {
                    "tooltip": {},
                    "xAxis": {
                        "type": "category",
                        "data": [k["name"] for k in knowledge],
                        "axisLabel": {"rotate": 45, "fontSize": 10},
                    },
                    "yAxis": {"type": "value", "min": 0, "max": 1},
                    "series": [{
                        "type": "bar",
                        "data": [
                            {
                                "value": k["confidence"],
                                "itemStyle": {
                                    "color": _confidence_color(k["confidence"])
                                },
                            }
                            for k in knowledge
                        ],
                    }],
                }
                ui.echart(chart_data).classes("w-full h-64")

        # Papers list
        with ui.card().classes("w-full"):
            ui.label("Papers").classes("text-lg font-semibold mb-2")
            if not papers:
                ui.label("No papers yet. Upload one to get started!").classes("text-gray-500")
            else:
                for p in papers:
                    with ui.row().classes("w-full items-center justify-between py-2 border-b"):
                        with ui.column().classes("gap-0"):
                            ui.link(p["title"], f"/paper/{p['id']}").classes("font-medium")
                            authors_str = ", ".join(p["authors"][:3])
                            if len(p["authors"]) > 3:
                                authors_str += " et al."
                            ui.label(authors_str).classes("text-sm text-gray-500")
                        ui.label(p["added_at"][:10]).classes("text-sm text-gray-400")

        # Recent chats
        if recent_chats:
            with ui.card().classes("w-full"):
                ui.label("Recent Chats").classes("text-lg font-semibold mb-2")
                for ch in recent_chats:
                    with ui.row().classes("w-full items-center justify-between py-2 border-b"):
                        agent_label = "Teach" if ch["agent_type"] == "teach" else "Zealot"
                        with ui.row().classes("items-center gap-2"):
                            ui.badge(agent_label, color="primary" if ch["agent_type"] == "teach" else "negative")
                            ui.link(ch["paper_title"], f"/chat/{ch['id']}").classes("text-sm")
                        ui.label(ch["created_at"][:10]).classes("text-sm text-gray-400")


def _confidence_color(conf: float) -> str:
    if conf < 0.33:
        return "#ef4444"
    elif conf < 0.66:
        return "#eab308"
    return "#22c55e"
