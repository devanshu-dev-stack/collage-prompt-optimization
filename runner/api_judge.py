"""Judge one lesson or summative through the Claude API, on the team's key, instead of a judge agent.

It sends the prompt that `runner.judge prompt` or `runner.assessment_judge prompt` built, unchanged,
and writes the answer file that `runner.judge check` or `runner.assessment_judge check` reads.
Agent judging stays as it is; this is an extra option (JUDGE.md, "API mode").

The prompt asks the judge to open images with Read and search long sources with Grep. The API has
neither, so the judge gets two small tools that do the same, limited to this judge's own files.

Usage:
    python -m runner.api_judge --kind lesson --prompt <prompt.md> --out <answer.json> [--checks <lab checks.json>] [--case-dir <test case folder>]
    python -m runner.api_judge --kind assessment --prompt <prompt.md> --out <answer.json> --case-dir <test case folder>
Options: --model (opus or sonnet, default opus), --effort (default high).
"""

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import anthropic
from anthropic.types import Message, MessageParam, ToolParam, ToolResultBlockParam
from pydantic import BaseModel, JsonValue

from runner import assessment_judge, judge
from runner.constants import (
    API_JUDGE_IMAGE_MAX_BYTES, API_JUDGE_KEY_ENV, API_JUDGE_MAX_IMAGES, API_JUDGE_MAX_TOKENS, API_JUDGE_MAX_TURNS,
    API_JUDGE_SEARCH_CONTEXT_LINES, API_JUDGE_SEARCH_MAX_HITS, IMAGE_FILE_SUFFIXES,
)


class JudgeKind(str, Enum):
    LESSON = "lesson"
    ASSESSMENT = "assessment"


class JudgeModel(str, Enum):
    """The models a judge may run on. Opus is the default: a smaller model missed most factual errors (RELAY.md)."""
    OPUS = "opus"
    SONNET = "sonnet"


class Effort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


@dataclass(frozen=True)
class ModelPrice:
    """Dollars per million tokens, for the cost line in the usage file."""
    model_id: str
    input: float
    output: float
    cache_write: float
    cache_read: float


MODELS: dict[JudgeModel, ModelPrice] = {
    JudgeModel.OPUS: ModelPrice("claude-opus-5-5", input=4.0, output=20.0, cache_write=5.0, cache_read=0.20),
    JudgeModel.SONNET: ModelPrice("claude-sonnet-5-5", input=2.0, output=10.0, cache_write=2.5, cache_read=0.10),
}
TOKENS_PER_MILLION = 1_000_000
STOP_END_TURN = "end_turn"
STOP_TOOL_USE = "tool_use"
VIEW_IMAGE_TOOL = "view_image"
SEARCH_SOURCE_TOOL = "search_source"
SEARCHABLE_SUFFIX = ".txt"
MEDIA_TYPES: dict[str, str] = {suffix: media for media, suffix in IMAGE_FILE_SUFFIXES.items()} | {".jpeg": "image/jpeg"}

SYSTEM_PROMPT = (
    "You are a careful judge. In this run you have no Read or Grep tools. Where the prompt says to open an "
    f"image file with Read, call {VIEW_IMAGE_TOOL} with that exact path (at most {API_JUDGE_MAX_IMAGES} images). "
    f"Where it says to search a source text file (Grep), call {SEARCH_SOURCE_TOOL} with that exact path and "
    "the words to look for. When you are done, answer with the JSON object only."
)
TOOLS: list[ToolParam] = [
    {
        "name": VIEW_IMAGE_TOOL,
        "description": "Show one image file named in the prompt, so you can judge what it shows.",
        "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "The image path exactly as the prompt gives it."}},
                         "required": ["path"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": SEARCH_SOURCE_TOOL,
        "description": "Search a long source's text file named in the prompt. Returns the matching lines with a little context. "
                       "The query is plain words, matched without case; a line matches when it holds all of them.",
        "input_schema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "The source text path exactly as the prompt gives it."},
            "query": {"type": "string", "description": "One to five words to look for."}},
            "required": ["path", "query"], "additionalProperties": False},
        "strict": True,
    },
]


class ViewImageInput(BaseModel):
    path: str


class SearchSourceInput(BaseModel):
    path: str
    query: str


class Usage(BaseModel):
    model: str
    effort: str
    turns: int = 0
    images_opened: int = 0
    searches: int = 0
    input_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class JudgeFiles:
    """The only files the judge's tools may open: this prompt's image folder and the test case folder."""
    roots: list[Path]
    images_opened: int = 0
    searches: int = 0
    opened: set[Path] = field(default_factory=set)

    def _allowed(self, raw: str) -> Path | None:
        path = Path(raw).resolve()
        if any(path.is_relative_to(root) for root in self.roots) and path.is_file():
            return path
        return None

    def view_image(self, raw: str) -> ToolResultBlockParam | str:
        path = self._allowed(raw)
        media = MEDIA_TYPES.get(path.suffix.lower()) if path else None
        if not path or not media:
            return "That path is not an image named in the prompt."
        if path not in self.opened and self.images_opened >= API_JUDGE_MAX_IMAGES:
            return f"You already opened {API_JUDGE_MAX_IMAGES} images. Judge the rest from the words around them."
        data = path.read_bytes()
        if len(data) > API_JUDGE_IMAGE_MAX_BYTES:
            return "This image is too large to show. Judge it from the words around it."
        if path not in self.opened:
            self.opened.add(path)
            self.images_opened += 1
        return {"type": "tool_result", "tool_use_id": "", "content": [{"type": "image", "source": {
            "type": "base64", "media_type": media, "data": base64.standard_b64encode(data).decode("ascii")}}]}  # type: ignore[typeddict-item]

    def search(self, raw: str, query: str) -> str:
        path = self._allowed(raw)
        if not path or path.suffix.lower() != SEARCHABLE_SUFFIX:
            return "That path is not a source text file named in the prompt."
        words = [word.lower() for word in re.findall(r"\w+", query)]
        if not words:
            return "Give one or more words to look for."
        self.searches += 1
        lines = path.read_text(encoding="utf-8").splitlines()
        hits = [index for index, line in enumerate(lines) if all(word in line.lower() for word in words)]
        if not hits:
            return f"No line holds all of: {' '.join(words)}."
        parts = []
        for index in hits[:API_JUDGE_SEARCH_MAX_HITS]:
            start, end = max(0, index - API_JUDGE_SEARCH_CONTEXT_LINES), index + API_JUDGE_SEARCH_CONTEXT_LINES + 1
            parts.append(f"[line {index + 1}]\n" + "\n".join(lines[start:end]))
        more = f"\n({len(hits) - API_JUDGE_SEARCH_MAX_HITS} more matches not shown; use more words.)" if len(hits) > API_JUDGE_SEARCH_MAX_HITS else ""
        return "\n---\n".join(parts) + more


def strict_schema(value: JsonValue) -> JsonValue:
    """Structured output needs every object to forbid fields it does not list."""
    if isinstance(value, dict):
        out = {key: strict_schema(inner) for key, inner in value.items()}
        if out.get("type") == "object":
            out["additionalProperties"] = False
        return out
    if isinstance(value, list):
        return [strict_schema(inner) for inner in value]
    return value


def _answer_schema(kind: JudgeKind, checks: Path | None) -> JsonValue:
    schema = judge.answer_schema(judge.load_config(checks)) if kind is JudgeKind.LESSON else assessment_judge.answer_schema()
    return strict_schema(schema)


def _tool_results(message: Message, files: JudgeFiles) -> list[ToolResultBlockParam]:
    results: list[ToolResultBlockParam] = []
    for block in message.content:
        if block.type != "tool_use":
            continue
        if block.name == VIEW_IMAGE_TOOL:
            shown = files.view_image(ViewImageInput.model_validate(block.input).path)
        elif block.name == SEARCH_SOURCE_TOOL:
            asked = SearchSourceInput.model_validate(block.input)
            shown = files.search(asked.path, asked.query)
        else:
            shown = "There is no such tool."
        if isinstance(shown, str):
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": shown})
        else:
            shown["tool_use_id"] = block.id
            results.append(shown)
    return results


def _add_usage(usage: Usage, message: Message, price: ModelPrice) -> None:
    used = message.usage
    usage.turns += 1
    usage.input_tokens += used.input_tokens
    usage.cache_write_tokens += used.cache_creation_input_tokens or 0
    usage.cache_read_tokens += used.cache_read_input_tokens or 0
    usage.output_tokens += used.output_tokens
    usage.cost_usd = round((usage.input_tokens * price.input + usage.cache_write_tokens * price.cache_write
                            + usage.cache_read_tokens * price.cache_read + usage.output_tokens * price.output)
                           / TOKENS_PER_MILLION, 4)


def run_judge(prompt: str, schema: JsonValue, files: JudgeFiles, model: JudgeModel, effort: Effort,
              client: anthropic.Anthropic) -> tuple[str, Usage]:
    """Ask the model, answer its image and search calls, and return its final JSON text and the tokens used."""
    price = MODELS[model]
    usage = Usage(model=price.model_id, effort=effort.value)
    messages: list[MessageParam] = [{"role": "user", "content": prompt}]
    for _ in range(API_JUDGE_MAX_TURNS):
        # Streamed so a long answer never hits the request timeout. The whole conversation is cached,
        # so each new round pays full price only for what was added.
        with client.messages.stream(
            model=price.model_id, max_tokens=API_JUDGE_MAX_TOKENS, system=SYSTEM_PROMPT, messages=messages,
            tools=TOOLS, cache_control={"type": "ephemeral"},
            output_config={"effort": effort.value, "format": {"type": "json_schema", "schema": schema}},
        ) as stream:
            message = stream.get_final_message()
        _add_usage(usage, message, price)
        usage.images_opened, usage.searches = files.images_opened, files.searches
        if message.stop_reason == STOP_TOOL_USE:
            # The whole reply goes back, thinking included, so the model keeps its reasoning.
            messages.append({"role": "assistant", "content": message.content})
            messages.append({"role": "user", "content": _tool_results(message, files)})
            continue
        if message.stop_reason != STOP_END_TURN:
            raise RuntimeError(f"The judge stopped early ({message.stop_reason}).")
        text = "".join(block.text for block in message.content if block.type == "text")
        return text, usage
    raise RuntimeError(f"The judge did not answer within {API_JUDGE_MAX_TURNS} rounds.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Judge a lesson or summative through the Claude API.")
    parser.add_argument("--kind", type=JudgeKind, choices=list(JudgeKind), required=True)
    parser.add_argument("--prompt", type=Path, required=True, help="The prompt built by runner.judge prompt or runner.assessment_judge prompt.")
    parser.add_argument("--out", type=Path, required=True, help="Where to write the judge's JSON answer.")
    parser.add_argument("--checks", type=Path, help="The page's lab/checks, as JSON (lessons only; the same file the prompt used).")
    parser.add_argument("--case-dir", type=Path, help="The test case folder, so the judge can open its source files.")
    parser.add_argument("--model", type=JudgeModel, choices=list(JudgeModel), default=JudgeModel.OPUS)
    parser.add_argument("--effort", type=Effort, choices=list(Effort), default=Effort.HIGH)
    args = parser.parse_args()

    key = os.environ.get(API_JUDGE_KEY_ENV, "").strip()
    if not key:
        print(f"{API_JUDGE_KEY_ENV} is not set.", file=sys.stderr)
        return 2
    roots = [(args.prompt.parent / f"{args.prompt.stem}-images").resolve()]
    if args.case_dir:
        roots.append(args.case_dir.resolve())
    files = JudgeFiles(roots=roots)
    usage_path = args.out.with_name(f"{args.out.stem}-usage.json")
    try:
        text, usage = run_judge(args.prompt.read_text(encoding="utf-8"), _answer_schema(args.kind, args.checks),
                                files, args.model, args.effort, anthropic.Anthropic(api_key=key))
    except anthropic.APIStatusError as error:
        # Status and type only: the response body is not needed and never holds the key.
        print(f"The Claude API refused the call (HTTP {error.status_code}, {type(error).__name__}).", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("Could not reach the Claude API.", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    # Fail here, not later in `check`, when the answer is not JSON at all.
    json.loads(text)
    args.out.write_text(text, encoding="utf-8")
    usage_path.write_text(usage.model_dump_json(indent=2), encoding="utf-8")
    print(f"Wrote {args.out} ({usage.turns} rounds, {usage.images_opened} images, {usage.searches} searches, "
          f"{usage.input_tokens + usage.cache_write_tokens + usage.cache_read_tokens} input and {usage.output_tokens} "
          f"output tokens, about ${usage.cost_usd:.2f}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
