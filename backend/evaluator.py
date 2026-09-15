import json
import re

from ollama import chat


EVALUATOR_MODEL = "qwen2.5:7b"


def evaluate_rag(
    question: str,
    retrieved_context: str,
    generated_answer: str,
):
    prompt = f"""
You are an objective evaluator for a Retrieval-Augmented Generation system.

Evaluate the generated answer using ONLY:

1. The user's question
2. The retrieved context
3. The generated answer

Do not use outside knowledge.
Do not assume that a statement is correct merely because it sounds reasonable.
Do not penalize the answer for information that is absent from the retrieved context.

Your task is to evaluate the quality of the generated answer relative to the retrieved context.

QUESTION:
{question}

RETRIEVED CONTEXT:
{retrieved_context}

GENERATED ANSWER:
{generated_answer}

Evaluate the following criteria.

1. CONTEXT RELEVANCE

Determine whether the retrieved context contains information relevant to answering
the question.

- Score 0 if the context is empty or completely irrelevant.
- Give a higher score when the context contains information directly useful for answering
  the question.
- Evaluate only the context provided above.

2. FAITHFULNESS

Determine whether the claims in the generated answer are supported by the retrieved
context.

- Penalize unsupported claims, hallucinations, contradictions, and invented details.
- A claim is supported only if it can be reasonably verified from the retrieved context.
- Do not use outside knowledge.
- If the answer correctly states that the context does not contain enough information,
  do not penalize it for refusing to speculate.

3. ANSWER RELEVANCE

Determine whether the generated answer directly addresses the user's question.

- Penalize irrelevant information, unnecessary digressions, and failure to answer the question.
- Give a high score when the answer is focused and directly useful.

4. ANSWER COMPLETENESS

Determine whether the generated answer covers the important information available
in the retrieved context that is necessary to answer the question.

- Evaluate completeness only against the retrieved context.
- Do not assume that information missing from the retrieved context should have been included.
- Penalize the omission of important information that is present in the retrieved context.

5. UNSUPPORTED CLAIMS

Identify every meaningful claim in the generated answer that is not supported by
the retrieved context.

For each unsupported claim, briefly explain why it is unsupported.

If there are no unsupported claims, return an empty list.

SCORING SCALE:

0 = Completely absent, incorrect, or unsupported
1 = Very poor
2 = Poor
3 = Partially acceptable
4 = Good
5 = Excellent

The following four criteria must receive integer scores from 0 to 5:

- context_relevance
- faithfulness
- answer_relevance
- answer_completeness

Calculate the overall answer quality using this exact formula:

overall_score =
(
    context_relevance.score
    + faithfulness.score
    + answer_relevance.score
    + answer_completeness.score
) / 4

Round overall_score to two decimal places.

Important rules:

- If the retrieved context is empty, context_relevance.score must be 0.
- If the answer contains unsupported claims, list them explicitly.
- If there are no unsupported claims, return an empty list.
- Do not use outside knowledge.
- Return only valid JSON.
- Do not include Markdown code fences.
- Do not include text outside the JSON object.
- Follow the exact JSON structure below.

Return JSON in exactly this structure:

{{
    "answer_quality": {{
        "overall_score": 0.0,
        "reason": ""
    }},
    "context_relevance": {{
        "score": 0,
        "reason": ""
    }},
    "faithfulness": {{
        "score": 0,
        "reason": ""
    }},
    "answer_relevance": {{
        "score": 0,
        "reason": ""
    }},
    "answer_completeness": {{
        "score": 0,
        "reason": ""
    }},
    "unsupported_claims": []
}}
"""

    try:
        response = chat(
            model=EVALUATOR_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            format="json",
        )

        raw_output = response["message"]["content"]

        try:
            return json.loads(raw_output)

        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)

            if match:
                return json.loads(match.group(0))

            return {
                "error": "Evaluator returned invalid JSON",
                "raw_output": raw_output,
            }

    except Exception as error:
        return {
            "error": "Evaluator execution failed",
            "details": str(error),
        }