from nicegui import ui
from pages.layout import frame
import db


@ui.page("/graph")
def graph_page():
    frame("Knowledge Graph")

    concepts = db.list_concepts()
    links = db.get_all_concept_links()
    knowledge = {k["concept_id"]: k["confidence"] for k in db.get_user_knowledge()}

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
        ui.label("Knowledge Graph").classes("text-2xl font-bold")

        if not concepts:
            ui.label("No concepts yet. Upload a paper to build your graph.").classes("text-gray-500")
            return

        # Build ECharts graph data
        nodes = []
        for c in concepts:
            conf = knowledge.get(c["id"], 0.0)
            nodes.append({
                "name": c["name"],
                "symbolSize": 15 + conf * 35,
                "value": c["description"],
                "itemStyle": {"color": _confidence_color(conf)},
            })

        concept_names = {c["id"]: c["name"] for c in concepts}
        edges = []
        for link in links:
            if link["concept_a"] in concept_names and link["concept_b"] in concept_names:
                edges.append({
                    "source": concept_names[link["concept_a"]],
                    "target": concept_names[link["concept_b"]],
                    "value": link["relationship"],
                })

        chart_options = {
            "tooltip": {"formatter": "{b}: {c}"},
            "legend": {"show": False},
            "series": [{
                "type": "graph",
                "layout": "force",
                "roam": True,
                "draggable": True,
                "label": {"show": True, "position": "right", "fontSize": 11},
                "force": {
                    "repulsion": 200,
                    "gravity": 0.1,
                    "edgeLength": [80, 200],
                },
                "emphasis": {"focus": "adjacency", "lineStyle": {"width": 4}},
                "edgeSymbol": ["none", "arrow"],
                "edgeLabel": {"show": True, "formatter": "{c}", "fontSize": 9},
                "data": nodes,
                "links": edges,
                "lineStyle": {"color": "source", "curveness": 0.1},
            }],
        }

        ui.echart(chart_options).classes("w-full").style("height: 600px")

        # Legend
        with ui.row().classes("gap-4 items-center"):
            ui.label("Confidence:").classes("text-sm font-medium")
            for label, color in [("Low", "#ef4444"), ("Medium", "#eab308"), ("High", "#22c55e"), ("Untested", "#94a3b8")]:
                with ui.row().classes("items-center gap-1"):
                    ui.html(f'<div style="width:12px;height:12px;border-radius:50%;background:{color}"></div>')
                    ui.label(label).classes("text-xs")


def _confidence_color(conf: float) -> str:
    if conf == 0.0:
        return "#94a3b8"  # gray for untested
    if conf < 0.33:
        return "#ef4444"
    elif conf < 0.66:
        return "#eab308"
    return "#22c55e"
