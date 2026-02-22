from nicegui import ui


def frame(title: str = "PaperMind"):
    ui.colors(primary="#6366f1", secondary="#a855f7", accent="#06b6d4")
    with ui.header().classes("items-center justify-between bg-primary"):
        with ui.row().classes("items-center gap-4"):
            ui.link("PaperMind", "/").classes("text-xl font-bold text-white no-underline")
            ui.link("Dashboard", "/").classes("text-white no-underline")
            ui.link("Upload", "/upload").classes("text-white no-underline")
            ui.link("Graph", "/graph").classes("text-white no-underline")
        ui.label(title).classes("text-white text-sm opacity-70")
