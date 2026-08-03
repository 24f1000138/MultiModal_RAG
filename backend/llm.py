from ollama import chat
import time

def generate_answer(question, contexts):

    prompt = f"""
You are a document question answering assistant.
Use ONLY the supplied context.

Rules:
1. Do not make up information.
2. If the answer is not present or if the question is irrelevant to the context, point it out.
3. Give precise answers.
4. If multiple contexts mention the answer, combine them.
5. If the question is ambiguous, ask for clarification.
6. For table data, extract the relevant information and present it in a clear format. for example, if the context contains a table with sales data, and the question is about total sales for a specific product, extract the relevant rows and sum the sales figures to provide a clear answer.
7. For image data, caption, ocr text and visual description will be provided in the context. OCR and visual description might not be in the same context or might be incorrect understanding of the image. Use all the information provided to give the best answer you can while also bringing up any inconsistencies in the data.
8. This step is very important: We have to build answer based on references, so while answering, please also mention the source of the information you are using. For example, if you are using information from a chunk with source file "report.pdf" and page number 5 and section "Introduction", please mention that in your answer like this: "According to report.pdf page 5, in the "Introduction" section ...". If you are using information from multiple sources, please mention all of them in your answer.Bonus: Also mention chunk type if it is a table or image. For example, "According to report.pdf page 5, which contains a table about sales data, ...".
QUESTION:
{question}

CONTEXT:
{contexts}

ANSWER:
"""
    print("len(prompt):", len(prompt))
    print("len(contexts):", len(contexts))

    start = time.time()
    response = chat(
        model="qwen2.5:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    print(
    "LLM:",
    time.time() - start
    )
    return response["message"]["content"]