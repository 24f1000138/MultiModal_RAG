from importlib.metadata import metadata
import os
import faiss
import numpy as np
import fitz
import gc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UPLOAD_DIR = PROJECT_ROOT / "uploads"
EXTRACTED_IMAGES_DIR = PROJECT_ROOT / "extracted_images"
TEMP_BATCH_DIR = PROJECT_ROOT / "temp_batches"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_BATCH_DIR.mkdir(parents=True, exist_ok=True)

from sentence_transformers import SentenceTransformer
from backend.models import Chunk, SessionLocal
from docling.datamodel.pipeline_options import (PdfPipelineOptions)
from docling.document_converter import (DocumentConverter,PdfFormatOption)
from docling.datamodel.base_models import (InputFormat)
from backend.serializers import (serialize_text,serialize_table,serialize_picture,serialize_formula)
from collections import defaultdict

EMBEDDING_DIMENSION = 768
FAISS_INDEX_PATH = PROJECT_ROOT / "rag2_faiss_index.bin"
MAPPING_PATH = PROJECT_ROOT / "rag2_chunk_mapping.npy"

embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")

if os.path.exists(FAISS_INDEX_PATH):
    faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))
    chunk_id_mapping = np.load(str(MAPPING_PATH), allow_pickle=True).tolist()
    print("Loaded existing FAISS index.")

else:
    faiss_index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
    chunk_id_mapping = []
    print("Created new FAISS index.")

session = SessionLocal()

def split_pdf_into_batches(pdf_path, batch_size=25):
    pdf = fitz.open(pdf_path)
    batch_files = []
    total_pages = len(pdf)
    TEMP_BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for start in range(0, total_pages, batch_size):
        end = min(start + batch_size, total_pages)
        batch_pdf = fitz.open()
        batch_pdf.insert_pdf(pdf,from_page=start,to_page=end - 1)
        batch_path =  TEMP_BATCH_DIR / f"batch_{start}_to_{end}.pdf"
        batch_pdf.save(str(batch_path))
        batch_pdf.close()
        batch_files.append((batch_path, start))

    pdf.close()
    return batch_files

def get_processed_pages(document):
    pages = set()
    for element, _ in document.iterate_items():
        if hasattr(element, "prov"):
            try:
                if element.prov:
                    pages.add(element.prov[0].page_no)

            except Exception:
                pass

    return pages

def create_single_page_pdf(original_pdf, page_number):
    pdf = fitz.open(original_pdf)
    mini = fitz.open()
    mini.insert_pdf(pdf,from_page=page_number,to_page=page_number)
    TEMP_BATCH_DIR.mkdir(parents=True, exist_ok=True)

    output = TEMP_BATCH_DIR / f"page_{page_number + 1}.pdf"
    mini.save(str(output))

    mini.close()
    pdf.close()
    return str(output)

def detect_scanned_pdf(pdf_path):
    temp_pdf = fitz.open()
    original = fitz.open(pdf_path)

    temp_pdf.insert_pdf(
        original,
        from_page=0,
        to_page=min(9, len(original)-1)
    )

    sample_pdf = TEMP_BATCH_DIR / "sample.pdf"
    temp_pdf.save(str(sample_pdf))

    temp_pdf.close()
    original.close()
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    converter = DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=pipeline_options)})

    result = converter.convert(str(sample_pdf))
    document = result.document
    total_text = 0

    for element, _ in document.iterate_items():
        if hasattr(element, "text"):
            total_text += len(element.text or "")

        if total_text > 1000:
            break

    del result
    gc.collect()
    if sample_pdf.exists():
        sample_pdf.unlink()
    return total_text < 1000

def convert_batch(pdf_path, pipeline_options):
    converter = DocumentConverter(format_options={
            InputFormat.PDF:
            PdfFormatOption(
                pipeline_options=pipeline_options
            )})
    
    return converter.convert(pdf_path)

def ingest_document(pdf_path, ocr_mode="Auto Detect"):
    pdf = fitz.open(pdf_path)
    total_pages = len(pdf)
    pdf.close()
    use_batching = total_pages >= 100
    pipeline_options = PdfPipelineOptions()

    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = False
    pipeline_options.images_scale = 1

    if ocr_mode == "Force OCR":
        pipeline_options.do_ocr = True

    elif ocr_mode == "Disable OCR":
        pipeline_options.do_ocr = False

    else:
        pipeline_options.do_ocr = detect_scanned_pdf(pdf_path)
        if pipeline_options.do_ocr:
            print("Scanned PDF detected. OCR enabled.")

    if not use_batching:
        converter = DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=pipeline_options)})
        result = converter.convert(pdf_path)
        process_document(result.document,pdf_path,page_offset=0)
        try:
            session.commit()
            faiss.write_index(faiss_index,str(FAISS_INDEX_PATH))
            np.save(str(MAPPING_PATH),np.array(chunk_id_mapping))

        except Exception:
            session.rollback()
            raise

        del result
        gc.collect()
        return

    print(
        f"Large PDF detected "
        f"({total_pages} pages). "
        f"Using batch ingestion."
    )

    batch_files = split_pdf_into_batches(pdf_path,batch_size=25)
    global_chunk_index = 0
    failed_pages = []

    for batch_path, page_offset in batch_files:
        try:
            result = convert_batch(batch_path, pipeline_options)
            processed_pages = get_processed_pages(result.document)
            global_chunk_index = process_document(result.document,pdf_path,page_offset,global_chunk_index)

            batch_page_count = min(25, total_pages - page_offset)
            expected_pages = set(range(1, batch_page_count + 1))
            missing_pages = expected_pages - processed_pages

            if missing_pages:
                print(f"\nMissing pages in batch starting at {page_offset + 1}: "
                    f"{sorted(missing_pages)}")

                for page in sorted(missing_pages):
                    absolute_page = page_offset + page - 1
                    retry_pdf = create_single_page_pdf(pdf_path,absolute_page)

                    try:
                        retry_result = convert_batch(retry_pdf,pipeline_options)
                        retry_processed = get_processed_pages(retry_result.document)

                        if len(retry_processed) > 0:
                            print(f"Recovered page "
                                f"{absolute_page + 1}")
                            retry_offset = absolute_page
                            global_chunk_index = process_document(retry_result.document,pdf_path,retry_offset,global_chunk_index)

                        else:
                            print(f"Still failed page "f"{absolute_page + 1}")
                            failed_pages.append(absolute_page + 1)

                        del retry_result
                        gc.collect()

                    except Exception as e:
                        print(f"Retry failed page "f"{absolute_page + 1}: {e}")
                        failed_pages.append(absolute_page + 1)

                    finally:
                        if os.path.exists(retry_pdf):
                            os.remove(retry_pdf)

            try:
                session.commit()
                faiss.write_index(faiss_index, str(FAISS_INDEX_PATH))
                np.save(str(MAPPING_PATH), np.array(chunk_id_mapping))

            except Exception:
                session.rollback()
                raise   
                
            del result
            gc.collect()

        except Exception as e:
            print(f"Batch starting at page {page_offset+1} failed: {e}")
            session.rollback()

        finally:
            if os.path.exists(batch_path):
                os.remove(batch_path)

    print("\nAll batches completed.")
    if failed_pages:
        print("\nPages that could not be recovered:")
        print(sorted(failed_pages))

def process_document(document,pdf_path,page_offset=0,chunk_index_start=0):
    list_groups = defaultdict(list)
    text_lookup = {}
    caption_refs = set()
    chunk_index = chunk_index_start
    for element, level in document.iterate_items():
        if hasattr(element, "self_ref"):
            ref_id = str(element.self_ref)
            try:
                content = element.text.strip()

            except Exception:
                content = str(element)
            text_lookup[ref_id] = content
        
        if type(element).__name__ == "PictureItem":
            for caption in element.captions:
                caption_refs.add(str(caption.cref))

        elif type(element).__name__ == "TableItem":
            for caption in element.captions:
                caption_refs.add(str(caption.cref))
        elif type(element).__name__ == "ListItem":
            parent_id = str(element.parent.cref)
            list_groups[parent_id].append(element)

    current_section = ""
    processed_lists = set()
    for element, level in document.iterate_items():
        chunk_type = type(element).__name__
        title = None
        if hasattr(element, "label"):
            title = str(element.label)

        document_name = os.path.basename(pdf_path)
        page_number = None
        if hasattr(element, "prov"):
            try:
                if element.prov:
                    page_number = (element.prov[0].page_no + page_offset)

            except Exception:
                pass
        
        img = None
        image_path = None
        if chunk_type == "SectionHeaderItem":
            current_section = serialize_text(element)
            continue
        
        metadata = {"docling_type": chunk_type,"document_name": document_name, "section": current_section}

        if chunk_type == "TextItem":
            if (hasattr(element, "self_ref") and str(element.self_ref) in caption_refs):
                continue
            content = serialize_text(element)

        elif chunk_type == "TableItem":
            content, table_metadata = (serialize_table(element,text_lookup))
            metadata.update(table_metadata)

        elif chunk_type == "PictureItem":
            content, img = serialize_picture(element, document, text_lookup)
            if img:
                image_filename = (
                    f"{Path(document_name).stem}_"
                    f"page_{page_number}_"
                    f"picture_{chunk_index}.png"
                )

                absolute_image_path = EXTRACTED_IMAGES_DIR / image_filename

                img.save(str(absolute_image_path))
                image_path = str(
                    absolute_image_path.relative_to(PROJECT_ROOT)
                ).replace("\\", "/")

        elif chunk_type == "FormulaItem":
            print("\nFOUND FORMULA ITEM")
            content = serialize_formula(element)

        elif chunk_type == "ListItem":
            parent_id = str(element.parent.cref)
            if parent_id in processed_lists:
                continue

            processed_lists.add(parent_id)
            items = list_groups[parent_id]
            list_text = "\n".join(f"• {item.text.strip()}" for item in items)
            content = (
                f"SECTION: {current_section}\n\n"
                f"{list_text}")
            metadata["list_group"] = parent_id
            metadata["list_size"] = len(items)

        else:
            try:
                content = element.text.strip()

            except Exception:
                content = str(element).strip()

        if not content:
            continue

        chunk_id = (f"{document_name}_chunk_{chunk_index}")
        existing_chunk = (session.query(Chunk).filter(Chunk.chunk_id == chunk_id).first())

        if existing_chunk:
            print(f"Skipping: {chunk_id}")
            chunk_index += 1
            continue

        embedding = embedding_model.encode(
            f"Represent this sentence "
            f"for retrieval: {content}"
        )
        embedding_array = np.array([embedding]).astype("float32")
        faiss_index.add(embedding_array)
        chunk_id_mapping.append(chunk_id)

        chunk = Chunk(chunk_id=chunk_id,source_file=pdf_path,page_number=page_number,chunk_index=chunk_index,chunk_type=chunk_type,content=content,title=title,metadata_json=metadata, image_path=image_path)
        session.add(chunk)

        print(
            f"[{chunk_index}] "
            f"{chunk_type} "
            f"(Page {page_number})"
        )
        print(
            "DOCLING PAGE:",
            element.prov[0].page_no,
            "OFFSET:",
            page_offset,
            "FINAL:",
            page_number
        )
            
        chunk_index += 1
    return chunk_index