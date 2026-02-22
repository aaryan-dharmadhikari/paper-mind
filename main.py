from nicegui import ui, app
import db
import config

# Import pages to register routes
import pages.dashboard  # noqa: F401
import pages.upload  # noqa: F401
import pages.paper_detail  # noqa: F401
import pages.chat  # noqa: F401
import pages.graph  # noqa: F401


app.add_static_files("/uploads", config.UPLOAD_DIR)
app.on_startup(db.init_db)


def main():
    ui.run(
        title="PaperMind",
        host=config.NICEGUI_HOST,
        port=config.NICEGUI_PORT,
        reload=True,
        show=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
