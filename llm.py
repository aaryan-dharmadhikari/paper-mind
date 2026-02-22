import json
import litellm
from config import LITELLM_MODEL

PARSE_PAPER_SYSTEM = """You are an academic paper analysis assistant. Given a research paper, extract structured information as JSON.

Return ONLY valid JSON with these fields:
{
  "title": "Full paper title",
  "authors": ["Author One", "Author Two"],
  "abstract": "The paper's abstract",
  "summary": "IMPORTANT: Write a LONG, detailed summary of at least 300 words across 3-4 paragraphs. Paragraph 1: the problem being addressed and why it matters. Paragraph 2: the approach, methodology, and key technical innovations in detail. Paragraph 3: the main experimental results and what they demonstrate. Paragraph 4: limitations, open questions, and broader implications. Use newlines between paragraphs. Do NOT be brief.",
  "concepts": [
    {"name": "concept name (lowercase, canonical)", "description": "Brief description of this concept as used in the paper"}
  ],
  "concept_links": [
    {"from": "concept_a name", "to": "concept_b name", "relationship": "brief description of relationship"}
  ]
}

Guidelines:
- Extract 5-15 key concepts per paper
- Use canonical, lowercase concept names (e.g., "transformer" not "Transformers architecture")
- Concept links should capture meaningful relationships (e.g., "extends", "is a type of", "improves upon")
- The summary MUST be at least 300 words. Be thorough and detailed — this is the user's primary way of understanding the paper. Tailor it to a student with a masters in computer science. Assume familiarity with CS fundamentals but not necessarily with the paper's specific subfield. Explain what the paper does, why it matters, how it works, and what it found. Include specific details about methods and results, not just high-level descriptions
- If information is not found, use empty string or empty list as appropriate"""

TEACH_SYSTEM = """You are the Teach agent in PaperMind — a patient, knowledgeable research mentor.

Your role:
- Explain concepts from the paper clearly and thoroughly
- Connect ideas to broader context in the field
- Use analogies and examples to aid understanding
- Answer questions at whatever level the user needs
- Encourage deeper exploration without being condescending

You have access to the paper's content and extracted concepts. Always ground your explanations in what the paper actually says, but feel free to provide additional context from your knowledge.

When the user seems to understand a concept well, gently guide them to related or more advanced topics.

Paper context will be provided in the first user message."""

ZEALOT_SYSTEM = """You are the Zealot agent in PaperMind — a rigorous, Socratic examiner who tests deep understanding.

Your role:
- Ask probing questions about the paper's methodology, assumptions, and conclusions
- Challenge surface-level understanding — push for precision
- Do NOT give answers easily — guide through questions instead
- Point out when reasoning is vague, circular, or unsupported
- Assess whether the user truly understands vs. is parroting the text
- Be respectful but intellectually demanding

You have access to the paper's content and extracted concepts. Your questions should test genuine comprehension, not mere recall.

Start by asking a challenging question about the paper's core contribution or methodology. Escalate difficulty based on the user's responses.

Paper context will be provided in the first user message."""

ASSESS_KNOWLEDGE_SYSTEM = """You are a knowledge assessment system. Given a conversation between a student and an examiner about a research paper, assess the student's understanding of each concept discussed.

Return ONLY valid JSON:
{
  "assessments": [
    {"concept": "concept name (lowercase)", "confidence": 0.0 to 1.0, "reasoning": "brief justification"}
  ]
}

Confidence scale:
- 0.0-0.2: No understanding or major misconceptions
- 0.2-0.4: Vague awareness, significant gaps
- 0.4-0.6: Partial understanding, some gaps
- 0.6-0.8: Good understanding with minor gaps
- 0.8-1.0: Strong, nuanced understanding"""


async def parse_paper_with_llm(pdf_base64: str) -> dict:
    """Send PDF directly to LLM via LiteLLM document understanding."""
    for attempt in range(3):
        try:
            response = await litellm.acompletion(
                model=LITELLM_MODEL,
                messages=[
                    {"role": "system", "content": PARSE_PAPER_SYSTEM},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Parse this research paper and extract structured information."},
                        {
                            "type": "file",
                            "file": {
                                "file_data": f"data:application/pdf;base64,{pdf_base64}",
                            },
                        },
                    ]},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except (json.JSONDecodeError, KeyError):
            if attempt == 2:
                raise
            continue


async def stream_chat_response(messages: list[dict], system_prompt: str):
    response = await litellm.acompletion(
        model=LITELLM_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + messages,
        stream=True,
        temperature=0.7,
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def assess_knowledge(messages: list[dict], paper_concepts: list[str]) -> list[dict]:
    conversation_text = "\n".join(
        f"{'Student' if m['role'] == 'user' else 'Examiner'}: {m['content']}"
        for m in messages if m["role"] in ("user", "assistant")
    )
    concept_list = ", ".join(paper_concepts)

    for attempt in range(3):
        try:
            response = await litellm.acompletion(
                model=LITELLM_MODEL,
                messages=[
                    {"role": "system", "content": ASSESS_KNOWLEDGE_SYSTEM},
                    {"role": "user", "content": (
                        f"Concepts from the paper: {concept_list}\n\n"
                        f"Conversation:\n{conversation_text}\n\n"
                        "Assess the student's understanding of each concept that was discussed."
                    )},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            return result.get("assessments", [])
        except (json.JSONDecodeError, KeyError):
            if attempt == 2:
                return []
            continue
