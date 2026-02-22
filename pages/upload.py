from pathlib import Path
from nicegui import ui, events
from pages.layout import frame
import pdf_processing


@ui.page("/upload")
def upload_page():
    frame("Upload Paper")

    with ui.column().classes("w-full max-w-2xl mx-auto p-4 gap-4"):
        ui.label("Upload a Research Paper").classes("text-2xl font-bold")
        ui.label("Upload a PDF to extract concepts and build your knowledge graph.").classes("text-gray-500")

        status = ui.label("").classes("text-sm")
        spinner = ui.spinner(size="lg")
        spinner.visible = False

        async def handle_upload(e: events.UploadEventArguments):
            spinner.visible = True
            status.text = "Processing PDF..."
            status.classes(remove="text-red-500 text-green-500")

            try:
                # Save uploaded file to temp location
                temp_path = Path("/tmp") / e.file.name
                temp_path.write_bytes(await e.file.read())

                paper_id = await pdf_processing.process_pdf(temp_path, e.file.name)

                status.text = "Paper processed successfully!"
                status.classes(add="text-green-500", remove="text-red-500")
                spinner.visible = False

                ui.navigate.to(f"/paper/{paper_id}")

            except pdf_processing.DuplicatePaperError as dup:
                status.text = "Paper already uploaded — redirecting..."
                status.classes(add="text-green-500", remove="text-red-500")
                spinner.visible = False
                ui.navigate.to(f"/paper/{dup.paper_id}")

            except Exception as ex:
                status.text = f"Error: {ex}"
                status.classes(add="text-red-500", remove="text-green-500")
                spinner.visible = False

        ui.upload(
            label="Drop PDF here or click to browse",
            on_upload=handle_upload,
            auto_upload=True,
            max_file_size=50_000_000,
        ).props('accept=".pdf"').classes("w-full")
