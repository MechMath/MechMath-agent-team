#!/usr/bin/env python3
"""Free-form mathematical discussion with Gemini/GPT via OpenRouter when available."""
import argparse
import logging
import os
import sys
from pathlib import Path

from _common.paths import configure_cli_logging

configure_cli_logging()
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from settings import GEMINI_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY
from _common.openrouter import extract_response_text, normalize_model, openrouter_client


def discuss(question: str, backend: str = "gemini", model: str | None = None,
            context_file: str | None = None) -> None:
    logger.info("discussion_partner.discuss called: backend=%s model=%s", backend, model)
    if context_file:
        ctx = Path(context_file).read_text(encoding="utf-8")
        full_prompt = f"## Context\n\n{ctx}\n\n## Question\n\n{question}"
    else:
        full_prompt = question

    if OPENROUTER_API_KEY:
        try:
            if backend == "gemini":
                model = normalize_model(model or "gemini-2.5-pro", "google")
                client = openrouter_client(OPENROUTER_API_KEY)
                response = client.responses.create(
                    model=model,
                    input=full_prompt,
                    temperature=0.7,
                )
            elif backend == "gpt":
                model = normalize_model(model or "gpt-5.5-pro", "openai")
                client = openrouter_client(OPENROUTER_API_KEY)
                response = client.responses.create(
                    model=model,
                    input=full_prompt,
                    reasoning={"effort": "high"},
                )
            else:
                print(f"Error: backend must be 'gemini' or 'gpt', got '{backend}'", file=sys.stderr)
                sys.exit(1)

            logger.info("discussion_partner.discuss succeeded via OpenRouter: backend=%s model=%s", backend, model)
            print(extract_response_text(response) or "(empty response)")
            return
        except Exception as e:
            logger.exception("discussion_partner.discuss failed via OpenRouter: %s", e)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if backend == "gemini":
        model = model or "gemini-2.5-pro"
        api_key = GEMINI_API_KEY
        if not api_key:
            print("Error: OPENROUTER_API_KEY or GEMINI_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(temperature=0.7),
            )
            logger.info("discussion_partner.discuss succeeded: backend=gemini model=%s", model)
            print(response.text or "(empty response)")
        except Exception as e:
            logger.exception("discussion_partner.discuss failed (gemini): %s", e)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif backend == "gpt":
        model = model or "gpt-5.5-pro"
        api_key = OPENAI_API_KEY
        if not api_key:
            print("Error: OPENROUTER_API_KEY or OPENAI_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.responses.create(
                model=model,
                input=full_prompt,
                reasoning={"effort": "high"},
            )
            logger.info("discussion_partner.discuss succeeded: backend=gpt model=%s", model)
            if response.output:
                print(response.output[-1].content[0].text)
            else:
                print("(empty response)")
        except Exception as e:
            logger.exception("discussion_partner.discuss failed (gpt): %s", e)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: backend must be 'gemini' or 'gpt', got '{backend}'", file=sys.stderr)
        sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Discuss math with Gemini/GPT")
    parser.add_argument("question", help="Question text (or - for stdin)")
    parser.add_argument("--backend", choices=["gemini", "gpt"], default="gemini")
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--context", default=None, help="File with additional context")
    args = parser.parse_args(argv)

    question = sys.stdin.read() if args.question == "-" else args.question
    discuss(question, args.backend, args.model, args.context)


if __name__ == "__main__":
    main()
