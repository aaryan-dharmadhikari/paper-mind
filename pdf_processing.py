import base64
import shutil
from pathlib import Path
import db
import llm
from config import UPLOAD_DIR


class DuplicatePaperError(Exception):
    def __init__(self, paper_id: int):
        self.paper_id = paper_id
        super().__init__(f"Paper already exists (id={paper_id})")


async def process_pdf(file_path: Path, original_name: str) -> int:
    # Check for duplicate
    existing = db.get_paper_by_filename(original_name)
    if existing:
        raise DuplicatePaperError(existing["id"])

    # Save to uploads directory
    dest = UPLOAD_DIR / original_name
    if dest != file_path:
        shutil.copy2(file_path, dest)

    # Base64-encode PDF for LLM document understanding
    pdf_base64 = base64.standard_b64encode(dest.read_bytes()).decode("utf-8")

    # LLM parse — sends PDF directly, no local text extraction needed
    parsed = await llm.parse_paper_with_llm(pdf_base64)

    # Store paper
    paper_id = db.insert_paper(
        title=parsed.get("title", original_name),
        authors=parsed.get("authors", []),
        abstract=parsed.get("abstract", ""),
        summary=parsed.get("summary", ""),
        source_url=original_name,
        raw_text="",
    )

    # Store concepts and link to paper
    concept_name_to_id = {}
    for concept_data in parsed.get("concepts", []):
        name = concept_data.get("name", "").strip()
        if not name:
            continue
        concept_id = db.upsert_concept(name, concept_data.get("description", ""))
        concept_name_to_id[name.lower()] = concept_id
        db.link_paper_concept(paper_id, concept_id)

    # Store concept links
    for link in parsed.get("concept_links", []):
        a_name = link.get("from", "").strip().lower()
        b_name = link.get("to", "").strip().lower()
        if a_name in concept_name_to_id and b_name in concept_name_to_id:
            db.upsert_concept_link(
                concept_name_to_id[a_name],
                concept_name_to_id[b_name],
                link.get("relationship", ""),
            )

    return paper_id
