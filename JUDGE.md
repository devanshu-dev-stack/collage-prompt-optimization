# Judge checklist

The judge reads one generated lesson next to its source material and custom instructions,
and lists every problem it finds. It never changes prompts: these rules are only for
checking output. Every lesson is judged the same way: a try's lesson, and the lessons behind
the fixed scores of Current dev and Megan's PR (RELAY.md, "Fixed scores").

## What the judge reads

- The source material, with each source's name when there is more than one.
- The custom instructions.
- Every concept block and every exercise block (text, quiz questions, answers, feedback).

## Checks

| Check | A problem when… | Not a problem when… |
|---|---|---|
| **Invented quote** | Text in quotation marks, or presented as a person's or work's words, is not in the source at all. | It is in the source word for word (small punctuation changes are fine). A quote that is in the source with some words changed is an inexact quote instead. |
| **Inexact quote** | A quote that is in the source, but with words changed, added or dropped (beyond punctuation). | It matches word for word, or the lesson paraphrases without quotation marks. |
| **Misattributed quote** | A quote that is in the source is credited to a different person or work than the source says. | The source gives no author and the lesson gives none either. |
| **Factual error** | A claim contradicts the source. For a claim the source does not cover, it contradicts well-established knowledge. When sources disagree, the lesson picks one side without saying so. | The lesson presents several viewpoints or arguments as such, or names which source says what. |
| **Wrong viewpoint** | The lesson states a different stance, emphasis or conclusion than the source. | The custom instructions ask for it. |
| **Off-source content** | A topic or fact that is not in the source. | The custom instructions ask for it, it is a short definition needed to read the source, or it is an example (examples follow the rule below). |
| **Custom instructions not followed** | A part, step, activity or focus the custom instructions ask for is left out, put in a different order, or replaced with something else; or the lesson is built mainly on a different source than the one they name. Each one counts once. | There are no custom instructions, or the request cannot apply to one lesson (for example, a task across several weeks). Missing coverage of the source is not a problem under this check. |

**Extra checks.** Anyone can suggest a check on the page's Checks tab. Once Claude accepts
it, it reaches the judge inside `<extra_checks>`: an id, a name and what counts as a problem.
The judge lists problems for it like any other check, and its points count the same way. A
lesson judged before a check existed shows "-" for it (`checked` lists what it was judged on).

**Examples.** The judge lists every example in the lesson and marks whether it comes from
the source. An example is a specific case that shows the concept in use: a scenario, a
worked problem with numbers, an experiment or a case study. General explanation is not an
example. A story counts only when the lesson uses it to show a concept.

The source comes first. An example counts as from the source when it keeps the source's own
case (its people, facts, numbers and findings), even if the lesson reframes it for the audience
the custom instructions ask for, such as saying how an education leader would meet it. It is
made up when the lesson replaces the source's case with a new one. An example from outside the
source is fine when the source has no example that fits the same concept. It is a problem (a **made-up example**) when the source
already has an example that fits that concept and the lesson made one up instead. For each
example not from the source, the judge says whether the source had one that fits.

## What the judge reports, per lesson

- **Problems:** for each one, the check, where it is (concept or exercise title, block
  number), the lesson's words, the source's words or "not in source", and one sentence on why.
- **Examples:** each example with where it is, whether it comes from the source, and for
  one that does not, whether the source had one that fits.
- **Totals:** problems per check, the share of examples taken from the source, and the
  number of made-up examples.

## Score

Each lesson gets a score from 0 to 100, worked out by the code from the judge's list, never
by the judge itself. Each problem costs points:

| Problem | Points off |
|---|---|
| Invented quote | 10 |
| Inexact quote | 3 |
| Misattributed quote | 10 |
| Factual error | 10 |
| Wrong viewpoint | 5 |
| Off-source content | 3 |
| Custom instructions not followed | 5 |
| Made-up example (the source had one) | 3 |

Each lesson gets two scores:

- **Source accuracy:** 100 minus the points lost per concept, so a long lesson is not punished
  for its length: a lesson with 6 concepts that loses 129 points scores 100 - 129 / 6 = 78.
  It counts every check above except "Custom instructions not followed", plus made-up examples.
- **Follows instructions:** 100 minus 5 points for each "Custom instructions not followed"
  problem, for the whole lesson. It is kept apart so a long list of missing steps does not hide
  differences in accuracy.

Neither goes below 0. The weights live in `runner/judge.py` (`SCORE_POINTS`). The leaderboard
ranks by source accuracy.

## Comparing a try with the fixed scores

Per test case, a try is compared with the average of the lessons behind each fixed score:
fewer problems and fewer made-up examples is better, and a higher share of examples from the
source is better. AI output changes from run to run, so a difference counts only when it holds across
repeated runs of the same try.
