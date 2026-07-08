import pytesseract
from vision_model import (generate_image_description)

def serialize_text(item):
    return item.text.strip()

def serialize_formula(item):
    try:
        if item.orig:
            return f"FORMULA: {item.orig.strip()}"
    except Exception:
        pass

    try:
        if item.text:
            return f"FORMULA: {item.text.strip()}"
    except Exception:
        pass

    return ""

def serialize_table(table_item, text_lookup):
    title = get_table_title(table_item,text_lookup)
    if not table_item.data:
        return (
            "EMPTY TABLE",
            {
                "title": title,
                "headers": [],
                "row_count": 0
            }
        )

    table_data = table_item.data
    if not getattr(table_data, "grid", None):
        return (
            "EMPTY TABLE",
            {
                "title": title,
                "headers": [],
                "row_count": 0
            }
        )
    headers = [cell.text.strip() for cell in table_data.grid[0]]
    rows = []

    for row in table_data.grid[1:]:
        row_pairs = []
        for header, cell in zip(headers, row):
            row_pairs.append(f"{header}: {cell.text.strip()}")

        rows.append(" | ".join(row_pairs))

    content = "\n".join(rows)
    metadata = {"title": title,"headers": headers,"row_count": len(rows)}
    return content, metadata


def serialize_picture(picture_item,document,text_lookup):
    caption = get_picture_caption(picture_item,text_lookup)
    image = picture_item.get_image(document)
    ocr_text = ""
    vision_description = ""

    if image:
        ocr_text = extract_ocr_text(image)
        vision_description = (generate_image_description(image))

    content = f""" IMAGE CAPTION: {caption} 
                   OCR TEXT: {ocr_text}
                   VISION DESCRIPTION: {vision_description}"""
    return content, image

def get_picture_caption(picture_item,text_lookup):
    try:
        if picture_item.captions:
            return resolve_ref(text_lookup,picture_item.captions[0])

    except Exception:
        pass

    return ""

def get_table_title(table_item,text_lookup):
    print("\nLOOKUP CHECK")
    print("Caption refs:", table_item.captions)

    for caption in table_item.captions:
        print(
            "Resolved:",
            resolve_ref(text_lookup, caption)
        )
    try:
        if table_item.captions:
            return resolve_ref(text_lookup,table_item.captions[0])

    except Exception:
        pass

    return ""

def resolve_ref(text_lookup, ref_item):
    try:
        ref_id = str(ref_item.cref)
        return text_lookup.get(ref_id,"")

    except Exception:
        return ""
    
def extract_ocr_text(image):
    try:
        image = image.convert("L")
        text = pytesseract.image_to_string(image)
        return text.strip()

    except Exception as e:
        print("OCR ERROR:", e)
        return ""
