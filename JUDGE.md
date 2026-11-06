# Judge checklist

The judge reads one generated lesson next to its source material and custom instructions,
and lists every problem it finds. It never changes prompts: these rules are only for
checking output. Dev's lesson and the try's lesson are judged the same way, then compared.

## What the judge reads

- The source material, with each source's name when there is more than one.
- The custom instructions.
- Every concept block and every exercise block (text, quiz questions, answers, feedback).

## Checks

| Check | A problem when… | Not a problem when… |
|---|---|---|
| **Invented quote** | Text in quotation marks, or presented as a person's or work's words, does not appear in the source. | It is in the source word for word (small punctuation changes are fine). |
| **Misattributed quote** | A quote that is in the source is credited to a different person or work than the source says. | The source gives no author and the lesson gives none either. |
| **Factual error** | A claim contradicts the source. For a claim the source does not cover, it contradicts well-established knowledge. When sources disagree, the lesson picks one side without saying so. | The lesson presents several viewpoints or arguments as such, or names which source says what. |
| **Wrong viewpoint** | The lesson states a different stance, emphasis or conclusion than the source. | The custom instructions ask for it. |
| **Off-source content** | A topic or fact that is not in the source. | The custom instructions ask for it, it is a short definition needed to read the source, or it is an example (examples follow the rule below). |

**Examples.** The judge lists every example in the lesson and marks whether it comes from
the source. An example is a specific case that shows the concept in use: a scenario, a
worked problem with numbers, an experiment or a case study. General explanation is not an
example. A story counts only when the lesson uses it to show a concept.

The source comes first. An example from outside the source is fine when the source has no
example that fits the same concept. It is a problem (a **made-up example**) when the source
already has an example that fits that concept and the lesson made one up instead. For each
example not from the source, the judge says whether the source had one that fits.

## What the judge reports, per lesson

- **Problems:** for each one, the check, where it is (concept or exercise title, block
  number), the lesson's words, the source's words or "not in source", and one sentence on why.
- **Examples:** each example with where it is, whether it comes from the source, and for
  one that does not, whether the source had one that fits.
- **Totals:** problems per check, the share of examples taken from the source, and the
  number of made-up examples.

## Comparing a try with dev

Per test case: fewer problems and fewer made-up examples is better, and a higher share of
examples from the source is better. AI output changes from run to run, so a difference counts only when it holds across
repeated runs of the same try.
