#!/usr/bin/env python3
"""Cross-verify a proof using GPT via OpenRouter when available."""
import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from settings import OPENAI_API_KEY, OPENROUTER_API_KEY
from _common.openrouter import extract_response_text, normalize_model, openrouter_client

VERIFY_PROMPT = """\
Your task is to evaluate the quality of a proof. The proof should be a rigorous \
mathematical argument with every step explicitly justified.

Please evaluate the proof and score it according to the following criteria:

- If the proof is completely correct, with all steps executed properly and clearly \
demonstrated, then the score is 1

- If the proof is generally correct, but with some details omitted or minor errors, \
then the score is 0.5

- If the proof does not actually prove the stated lemma, contains fatal errors, or \
has severe omissions, then the score is 0

- Additionally, referencing anything from any paper or external result does not save \
the need to prove the reference. It's okay IF AND ONLY IF the proof also presents a \
valid justification of the referenced argument(s); otherwise, if the proof omits the \
justification or if the justification is not completely correct, score accordingly

Please carefully reason out and analyze the quality of the proof below, and in your \
final response present a detailed evaluation followed by your score.

Your response format:

Here is my evaluation of the proof:

[Present in detail the key steps of the proof or the steps for which you had doubts \
regarding their correctness. For each step, explicitly analyze whether it is accurate: \
for correct steps, explain why you initially doubted them and why they are indeed correct; \
for erroneous steps, explain the reason for the error and its impact on the overall proof.]

Based on my evaluation, the final overall score should be: \\boxed{{...}}

[where ... is 0, 0.5, or 1]

---

## Problem
{problem}

## Lemma
{lemma}

## Proof
{proof}"""


def verify(proof_file: str, problem_file: str | None = None, lemma_file: str | None = None,
           model: str = "gpt-5.5-pro", temperature: float = 0.3) -> None:
    logger.info("cross_verify.verify called: proof=%s model=%s", proof_file, model)
    proof = Path(proof_file).read_text(encoding="utf-8")
    problem = Path(problem_file).read_text(encoding="utf-8") if problem_file else "(not provided)"
    lemma = Path(lemma_file).read_text(encoding="utf-8") if lemma_file else "(not provided)"

    prompt = VERIFY_PROMPT.format(problem=problem, lemma=lemma, proof=proof)

    if OPENROUTER_API_KEY:
        try:
            client = openrouter_client(OPENROUTER_API_KEY)
            response = client.responses.create(
                model=normalize_model(model, "openai"),
                input=prompt,
                reasoning={"effort": "high"},
            )
            text = extract_response_text(response)
        except Exception as e:
            logger.exception("cross_verify.verify failed via OpenRouter: %s", e)
            print(json.dumps({"ok": False, "error": str(e)}))
            sys.exit(1)
    else:
        api_key = OPENAI_API_KEY
        if not api_key:
            print(json.dumps({"ok": False, "error": "OPENROUTER_API_KEY or OPENAI_API_KEY not set"}))
            sys.exit(1)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.responses.create(
                model=model,
                input=prompt,
                reasoning={"effort": "high"},
            )
            text = response.output[-1].content[0].text if response.output else ""
        except Exception as e:
            logger.exception("cross_verify.verify failed: %s", e)
            print(json.dumps({"ok": False, "error": str(e)}))
            sys.exit(1)

    match = re.search(r"\\boxed\{(.*?)\}", text)
    score = float(match.group(1).strip()) if match else -1

    logger.info("cross_verify.verify succeeded: score=%s", score)
    print(json.dumps({"ok": True, "score": score, "analysis": text}, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cross-verify a proof using GPT")
    parser.add_argument("proof_file", help="Path to proof file")
    parser.add_argument("--problem", default=None, help="Path to problem statement file")
    parser.add_argument("--lemma", default=None, help="Path to lemma statement file")
    parser.add_argument("--model", default="gpt-5.5-pro", help="GPT model")
    parser.add_argument("--temperature", type=float, default=0.3)
    args = parser.parse_args(argv)
    verify(args.proof_file, args.problem, args.lemma, args.model, args.temperature)


if __name__ == "__main__":
    main()
