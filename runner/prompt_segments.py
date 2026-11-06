"""Pull the written prompt text out of a CollageAI prompt file, and put edited text back.

People edit only the text. Values the app fills in at run time (f-string parts such as
{subject_safe}) show as «subject_safe» markers. When text goes back, every brace typed by a
person is escaped, so only the original markers become code again: an edit cannot add code.

Usage:
    python -m runner.prompt_segments export --file <path> --repo-path <path in repo> --dev-commit <sha> --out seg.json
    python -m runner.prompt_segments apply --file <path> --edits edits.json
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from runner.errors import RunnerInputError
from runner.segment_models import FileEdits, FileSegments, PromptSegment

MARKER_PATTERN = re.compile(r"«([^«»\n]+)»")
MIN_TEXT_CHARS = 25
MIN_SPACES = 3
LOG_METHODS = frozenset({"debug", "info", "warning", "error", "exception", "critical"})


@dataclass(frozen=True)
class FoundString:
    node: ast.Constant | ast.JoinedStr
    label: str


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _is_docstring(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    expr = parents.get(node)
    owner = parents.get(expr) if isinstance(expr, ast.Expr) else None
    body = getattr(owner, "body", None)
    return isinstance(body, list) and bool(body) and body[0] is expr


def _in_log_or_raise(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, ast.Raise):
            return True
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute) and current.func.attr in LOG_METHODS:
            return True
        current = parents.get(current)
    return False


def _label(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    """Where the text is used: its function, constant, and dict key when there is one."""
    parts: list[str] = []
    current: ast.AST | None = node
    while current is not None:
        parent = parents.get(current)
        if isinstance(parent, ast.Dict) and isinstance(current, ast.expr) and current in parent.values:
            key = parent.keys[parent.values.index(current)]
            if key is not None:
                parts.append(ast.unparse(key).strip("'\""))
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parts.append(current.name)
            break
        if isinstance(current, (ast.Assign, ast.AnnAssign)) and isinstance(parents.get(current), ast.Module):
            target = current.targets[0] if isinstance(current, ast.Assign) else current.target
            parts.append(ast.unparse(target))
            break
        current = parent
    return " › ".join(reversed(parts)) or "module"


def _marker_source(value: ast.FormattedValue) -> str:
    """The "{...}" source of one f-string part, exactly as Python will rebuild it."""
    return ast.unparse(ast.JoinedStr(values=[value]))[2:-1]


def _display(node: ast.Constant | ast.JoinedStr) -> tuple[str, dict[str, str]]:
    if isinstance(node, ast.Constant):
        return str(node.value), {}
    text: list[str] = []
    markers: dict[str, str] = {}
    for part in node.values:
        if isinstance(part, ast.Constant):
            text.append(str(part.value))
        elif isinstance(part, ast.FormattedValue):
            source = _marker_source(part)
            name = source[1:-1]
            markers[name] = source
            text.append(f"«{name}»")
    return "".join(text), markers


def _is_prompt_text(text: str) -> bool:
    plain = MARKER_PATTERN.sub("", text)
    return len(plain.strip()) >= MIN_TEXT_CHARS and plain.count(" ") >= MIN_SPACES


def find_strings(source: str) -> list[FoundString]:
    tree = ast.parse(source)
    parents = _parents(tree)
    found: list[FoundString] = []
    for node in ast.walk(tree):
        is_text = isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str))
        if not is_text or isinstance(parents.get(node), (ast.JoinedStr, ast.FormattedValue)):
            continue
        if _is_docstring(node, parents) or _in_log_or_raise(node, parents):
            continue
        parent = parents.get(node)
        if isinstance(parent, ast.Dict) and node in parent.keys:
            continue
        assert isinstance(node, (ast.Constant, ast.JoinedStr))
        if _is_prompt_text(_display(node)[0]):
            found.append(FoundString(node, _label(node, parents)))
    return sorted(found, key=lambda f: (f.node.lineno, f.node.col_offset))


def _segment_ids(found: list[FoundString]) -> list[str]:
    seen: dict[str, int] = {}
    ids = []
    for item in found:
        seen[item.label] = seen.get(item.label, 0) + 1
        ids.append(f"{item.label}#{seen[item.label]}")
    return ids


def export_segments(source: str, repo_path: str, dev_commit: str) -> FileSegments:
    found = find_strings(source)
    segments = []
    for segment_id, item in zip(_segment_ids(found), found):
        text, markers = _display(item.node)
        segments.append(PromptSegment(id=segment_id, label=item.label, text=text, placeholders=sorted(markers)))
    return FileSegments(path=repo_path, devCommit=dev_commit, segments=segments)


def _escape(text: str, is_fstring: bool) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return escaped.replace("{", "{{").replace("}", "}}") if is_fstring else escaped


def encode(text: str, node: ast.Constant | ast.JoinedStr) -> str:
    """Python source for `text`, keeping only this string's own «markers» as code."""
    _, markers = _display(node)
    is_fstring = isinstance(node, ast.JoinedStr)
    pieces: list[str] = []
    position = 0
    for match in MARKER_PATTERN.finditer(text):
        name = match.group(1)
        if name not in markers:
            raise RunnerInputError(f"«{name}» is not a value this prompt fills in. Keep only the original «…» markers.")
        pieces.append(_escape(text[position:match.start()], is_fstring))
        pieces.append(markers[name])
        position = match.end()
    pieces.append(_escape(text[position:], is_fstring))
    return ("f" if is_fstring else "") + '"""' + "".join(pieces) + '"""'


def _offset(lines: list[str], line: int, col_bytes: int) -> int:
    """Character offset in the file of an ast (1-based line, UTF-8 byte column) position."""
    before = sum(len(text) for text in lines[: line - 1])
    return before + len(lines[line - 1].encode("utf-8")[:col_bytes].decode("utf-8"))


def apply_edits(source: str, edits: FileEdits) -> str:
    found = find_strings(source)
    by_id = dict(zip(_segment_ids(found), found))
    unknown = [edit.id for edit in edits.segments if edit.id not in by_id]
    if unknown:
        raise RunnerInputError(f"These prompt parts no longer exist on dev: {', '.join(unknown)}. Start the edit again from dev.")
    lines = source.splitlines(keepends=True)
    replacements = []
    for edit in edits.segments:
        node = by_id[edit.id].node
        if edit.text == _display(node)[0]:
            continue
        assert node.end_lineno is not None and node.end_col_offset is not None
        start = _offset(lines, node.lineno, node.col_offset)
        end = _offset(lines, node.end_lineno, node.end_col_offset)
        replacements.append((start, end, encode(edit.text, node)))
    for start, end, new_source in sorted(replacements, reverse=True):
        source = source[:start] + new_source + source[end:]
    ast.parse(source)
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or apply prompt text segments.")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("--file", type=Path, required=True)
    export.add_argument("--repo-path", required=True)
    export.add_argument("--dev-commit", required=True)
    export.add_argument("--out", type=Path, required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("--file", type=Path, required=True)
    apply.add_argument("--edits", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "export":
            segments = export_segments(args.file.read_text(encoding="utf-8"), args.repo_path, args.dev_commit)
            args.out.write_text(segments.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
            print(f"{len(segments.segments)} prompt part(s) from {args.repo_path}")
        else:
            edits = FileEdits.model_validate_json(args.edits.read_text(encoding="utf-8"))
            args.file.write_text(apply_edits(args.file.read_text(encoding="utf-8"), edits), encoding="utf-8")
            print(f"Applied {len(edits.segments)} edited part(s) to {args.file}")
    except (RunnerInputError, SyntaxError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
