import json
import logging
from django.conf import settings
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

logger = logging.getLogger(__name__)


# Load JSON guide data from file specified in settings
def load_json_data():
    """
    Loads structured guide data from a JSON file specified in Django settings.
    Returns the parsed dictionary or an empty 'guides' structure on error.
    """
    try:
        with open(settings.JSON_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"JSON load error: {str(e)}")
        return {"guides": []}


def process_json_data(json_data):
    """
    Converts structured JSON guide data into LangChain-compatible Document objects.

    Each section of each guide becomes a Document with associated metadata (titles, links).
    The section text includes:
      - Guide and section title/description
      - Ordered steps with title, description, and images

    Returns:
        List of Document objects (each with page_content and metadata).
    """
    processed_docs = []

    for guide in json_data.get("guides", []):
        guide_title = guide.get("title", "Untitled Guide")
        guide_description = guide.get("description", "").strip()

        for section in guide.get("sections", []):
            section_title = section.get("title", "Untitled Section").strip()
            section_description = section.get("description", "").strip()
            section_youtube = section.get("youtube_link", "").strip()

            # Build metadata dictionary
            metadata = {
                "guide_title": guide_title,
                "section_title": section_title
            }
            if guide_description:
                metadata["guide_description"] = guide_description
            if section_youtube:
                metadata["youtube_link"] = section_youtube

            # Construct full text content for this section
            parts = []
            parts.append(guide_title)
            parts.append("")
            if guide_description:
                parts.append(guide_description)
                parts.append("")

            parts.append(section_title)
            parts.append("")
            if section_description:
                parts.append(section_description)
                parts.append("")

            # Iterate through each step
            steps_list = section.get("steps", [])
            if not isinstance(steps_list, list):
                print(
                    f"[Warning] In section '{section_title}', 'steps' is not a list (got {type(steps_list)}). Skipping steps.")
                steps_list = []

            for idx, step in enumerate(steps_list, start=1):
                if not isinstance(step, dict):
                    print(
                        f"[Warning] In section '{section_title}', step index {idx} is not an object (got {type(step)}). Skipping.")
                    continue

                # Handle 'step' field if present, else use index
                if "step" not in step:
                    print(f"[Error] Missing 'step' key in section '{section_title}', Step data: {step!r}")
                    step_num = idx
                else:
                    raw = step["step"]
                    if not isinstance(raw, int):
                        print(
                            f"[Warning] In section '{section_title}', 'step' is not int ({raw!r}). Using index {idx}.")
                        step_num = idx
                    else:
                        step_num = raw

                # Build step line (number + title + optional description)
                title = step.get("title", "").strip()
                if title:
                    step_line = f"{step_num}. {title}"
                else:
                    step_line = f"{step_num}."

                desc = step.get("description", "")
                if desc:
                    if isinstance(desc, list):
                        bullets = "\n   - ".join(item for item in desc if item is not None)
                        step_line += "\n   - " + bullets
                    else:
                        step_line += f": {desc}"

                parts.append(step_line)

                # Include image URLs if provided
                img_field = step.get("imageURL", "")
                if img_field:
                    urls = [u.strip() for u in img_field.split(",") if u.strip()]
                    for u in urls:
                        parts.append(f"   Image URL: {u}")

                parts.append("")  # Blank line after each step

            # Final section content
            section_text = "\n".join(parts).strip()
            processed_docs.append(Document(page_content=section_text, metadata=metadata.copy()))

    return processed_docs


# Load and parse PDF file as Document objects
def load_pdf_data():
    """
    Loads data from a PDF file defined in Django settings.
    Uses LangChain's PyPDFLoader.
    Returns a list of Document objects or an empty list on failure.
    """
    try:
        return PyPDFLoader(settings.PDF_DATA_PATH).load()
    except Exception as e:
        logger.error(f"PDF load error: {str(e)}")
        return []


def setup_vector_db():
    """
    Sets up the vector database and ensemble retriever:
    1. Loads both JSON and PDF documents.
    2. Splits PDF content using RecursiveCharacterTextSplitter.
    3. Creates:
       - FAISS vector retriever with HuggingFace embeddings.
       - BM25 keyword-based retriever.
       - Ensemble retriever combining both with weighted logic.
    Returns:
        (ensemble_retriever, faiss_vector_store, bm25_retriever, combined_documents)
    """
    try:
        # Load and process data
        json_docs = process_json_data(load_json_data())
        pdf_docs = load_pdf_data()

        if not json_docs and not pdf_docs:
            logger.warning("Using dummy document")
            combined_docs = [Document(page_content="dummy", metadata={})]
        else:
            combined_docs = json_docs

            # Chunk PDF documents if available
            if pdf_docs:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=100,
                    separators=[
                        "\n- ",  # bullet points
                        "\n• ",
                        "\n\n",  # paragraph
                        "\n",  # line
                        " ",  # word
                        ""  # fallback
                    ],
                    length_function=len
                )
                pdf_chunks = text_splitter.split_documents(pdf_docs)
                combined_docs += pdf_chunks

        # 1. Create FAISS retriever
        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vector_store = FAISS.from_documents(combined_docs, embedding_model)
        faiss_retriever = vector_store.as_retriever()

        # Create BM25 keyword retriever
        bm25_retriever = BM25Retriever.from_documents(combined_docs)

        # Combine both using EnsembleRetriever
        retriever = EnsembleRetriever(
            retrievers=[faiss_retriever, bm25_retriever],
            weights=[0.7, 0.3]  # Tunable based on testing
        )

        return retriever, vector_store, bm25_retriever, combined_docs

    except Exception as e:
        logger.error(f"Vector DB setup failed: {str(e)}")
        return None, None, None, None
