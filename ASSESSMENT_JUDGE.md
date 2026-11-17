# Assessment judge checklist

The judge reads one generated summative assessment next to the source material it was made
from, and lists every problem it finds. It never changes prompts: these rules are only for
checking output. Every summative is judged the same way: a try's, and those behind Current
dev's fixed assessment score (RELAY.md, "Assessments").

## What the judge reads

- The source material, with each source's name when there is more than one.
- The learning objectives the teacher asked the assessment to cover, and the question mix
  they asked for (question types and thinking levels).
- The assessment: its instructions, then every question in order with its type, points,
  options, answer key, grading criteria or blanks. Each question's feedback is shown too,
  because a check such as "Answer revealed elsewhere" can depend on it.

A summative is made from source material, not from a lesson. Wherever a check says "the
lesson", read it as the source material and the learning objectives the assessment was asked
to cover: what was taught is what the source teaches toward those objectives.

## Checks

The checks are listed in the prompt, in two groups: checks on the assessment as a whole, and
checks on single questions. Feedback quality is not judged yet (it gets its own pipeline), so
there is no check for wrong or unhelpful feedback.

- List one problem for each distinct place the assessment breaks a check. A question-level
  problem names its question ("Question 4"). An assessment-level problem names the questions
  it is about ("Questions 3 and 7") or "Whole assessment", and is listed once.
- Do not list the same problem twice under different checks: pick the check that fits best.
- Quote the assessment's words exactly in `assessment_text`. For `source_text`, quote the
  source when it matters, write "not in source" when the source does not have it, or "not
  about the source" when the problem is about how the question is built.
- A long source is given as a text file to search: search it (Grep) before saying something
  was not taught.

## Score

The code, never the judge, works out one score from the judge's list: **Assessment quality**,
from 0 to 100. Each problem costs points (5 for serious checks, 3 for the rest; the list
lives in `runner/assessment_checks.py`). The score is 100 minus the points lost per 10
questions, so a longer assessment is not punished for its length: a 15-question assessment
that loses 30 points scores 100 - 30 x 10 / 15 = 80. It never goes below 0.
