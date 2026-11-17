# Stored lessons

Every lesson the Prompt Lab has judged, kept so a new or reworded check judges the same
lessons again instead of making new ones (RELAY.md, "Stored lessons", on the
`feature/prompt-eval-harness` branch).

- `index.json`: each lesson id with its address, test case and the fixed scores and tries that use it.
- `<lesson id>/result.json.gz`: the lesson as the runner read it.
- `<lesson id>/answer.json`: the judge's latest answer.
- `<lesson id>/side.json`: that answer, checked and scored.

Save and get lessons with `python -m runner.lesson_store` (see its docstring). Images are
not kept: the judge downloads them again from the links in the lesson.
