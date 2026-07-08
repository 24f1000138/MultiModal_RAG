from transformers import AutoProcessor
from transformers import AutoModelForCausalLM
from PIL import Image
import torch

MODEL_ID = "microsoft/Florence-2-base"

processor = AutoProcessor.from_pretrained(MODEL_ID,trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_ID,trust_remote_code=True)
model.eval()

def generate_image_description(image):
    prompt = "<MORE_DETAILED_CAPTION>" #later make this dynamic by asking user what kind of description they want using UI
    inputs = processor(text=prompt,images=image,return_tensors="pt")
    with torch.no_grad():
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=256,
            do_sample=False
        )

    generated_text = processor.batch_decode(generated_ids,skip_special_tokens=True)[0]
    return generated_text