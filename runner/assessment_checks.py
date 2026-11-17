"""The summative checks (the team's "Criteria for Evaluating Summative Assessments"), with their points.

The two feedback checks are left out for now: feedback gets its own pipeline later. Serious mistakes
(wrong science, a wrong key, no single right answer, a question that cannot be answered, an answer
given away, content never taught or never tested) cost 5 points; the rest cost 3.
"""

from typing import Final

from runner.assessment_judge_models import AssessmentCheck, CheckLevel

SERIOUS_POINTS: Final[int] = 5
OTHER_POINTS: Final[int] = 3

_A, _Q = CheckLevel.ASSESSMENT, CheckLevel.QUESTION

ASSESSMENT_CHECKS: Final[tuple[AssessmentCheck, ...]] = (
    AssessmentCheck(id="a1", level=_A, points=SERIOUS_POINTS, name="Important content missing",
                    look_for="A major concept or learning objective from the corresponding lesson is not assessed, leaving the student and instructor without evidence of understanding in that area."),
    AssessmentCheck(id="a2", level=_A, points=OTHER_POINTS, name="Unbalanced content coverage",
                    look_for="Several questions assess the same narrow topic or skill while other important topics receive little or no attention."),
    AssessmentCheck(id="a3", level=_A, points=SERIOUS_POINTS, name="Questions outside the taught scope",
                    look_for="A question requires a concept, method, convention, or level of mathematical skill that was not taught in the lesson and is not an established prerequisite."),
    AssessmentCheck(id="a4", level=_A, points=OTHER_POINTS, name="Recall dominates the assessment",
                    look_for="Most questions can be answered by remembering a definition or equation, even though the lesson expects students to interpret, apply, compare, or reason with the ideas."),
    AssessmentCheck(id="a5", level=_A, points=OTHER_POINTS, name="Too much routine calculation",
                    look_for="Most quantitative questions require only substitution into a familiar equation and provide little evidence that students understand when or why the equation applies."),
    AssessmentCheck(id="a6", level=_A, points=OTHER_POINTS, name="Insufficient range of reasoning",
                    look_for="The assessment repeatedly asks students to perform the same kind of reasoning and does not include other important skills from the lesson, such as interpreting, predicting, comparing, or evaluating a claim."),
    AssessmentCheck(id="a7", level=_A, points=OTHER_POINTS, name="Repetitive questions",
                    look_for="Multiple questions test essentially the same idea in the same way, without adding meaningful coverage or revealing a different aspect of understanding."),
    AssessmentCheck(id="a8", level=_A, points=OTHER_POINTS, name="Difficulty poorly matched to the lesson",
                    look_for="Questions are so straightforward that they do not distinguish understanding from memorization, or so difficult and complex that students are unlikely to demonstrate the intended learning."),
    AssessmentCheck(id="a9", level=_A, points=OTHER_POINTS, name="Excessive dependence on one question",
                    look_for="A broad or central learning objective is represented only by an item whose result could be dominated by an unrelated difficulty, such as unfamiliar wording or a complex calculation."),
    AssessmentCheck(id="a10", level=_A, points=SERIOUS_POINTS, name="Answer revealed elsewhere",
                    look_for="One question, answer choice, diagram, or piece of feedback provides the answer or a decisive clue to another question on the same assessment."),
    AssessmentCheck(id="q1", level=_Q, points=OTHER_POINTS, name="Question does not test an important idea",
                    look_for="A question focuses on a minor detail or isolated fact rather than an important concept, relationship, or skill from the lesson."),
    AssessmentCheck(id="q2", level=_Q, points=OTHER_POINTS, name="Conceptual reasoning not required",
                    look_for="A student can answer correctly by recognizing a familiar phrase or formula without understanding the underlying concept the question is intended to assess."),
    AssessmentCheck(id="q3", level=_Q, points=OTHER_POINTS, name="Application without interpretation",
                    look_for="A question asks students to compute a quantity but does not require them to interpret the result, choose an appropriate principle, or understand what the result means when those skills are part of the learning goal."),
    AssessmentCheck(id="q4", level=_Q, points=OTHER_POINTS, name="Unclear question or task",
                    look_for="Students cannot readily tell what they are being asked to determine, compare, predict, or explain."),
    AssessmentCheck(id="q5", level=_Q, points=SERIOUS_POINTS, name="Missing information or assumptions",
                    look_for="A question cannot be answered uniquely because it omits a necessary detail, such as the system, initial conditions, reference frame, direction, or whether friction is negligible."),
    AssessmentCheck(id="q6", level=_Q, points=SERIOUS_POINTS, name="Incorrect science or mathematics",
                    look_for="The question contains a conceptual, mathematical, or scientific error."),
    AssessmentCheck(id="q7", level=_Q, points=OTHER_POINTS, name="Ambiguous wording",
                    look_for="A phrase can reasonably be interpreted in more than one way, and those interpretations lead to different answers."),
    AssessmentCheck(id="q8", level=_Q, points=OTHER_POINTS, name="Question relies on an irrelevant trick",
                    look_for="Getting the question right depends mainly on noticing a subtle wording trap or incidental detail rather than understanding the intended concept."),
    AssessmentCheck(id="q9", level=_Q, points=OTHER_POINTS, name="Too many ideas bundled together",
                    look_for="A question combines so many concepts or steps that an incorrect response does not reveal which idea the student misunderstood."),
    AssessmentCheck(id="q10", level=_Q, points=OTHER_POINTS, name="Extraneous complexity",
                    look_for="A scenario includes details, calculations, or technical language that add reading or processing burden without contributing to the concept being assessed."),
    AssessmentCheck(id="q11", level=_Q, points=OTHER_POINTS, name="Misleading or missing representation",
                    look_for="A question refers to a diagram, graph, table, or image that is missing, incorrect, insufficiently labeled, or inconsistent with the text."),
    AssessmentCheck(id="q12", level=_Q, points=OTHER_POINTS, name="Notation or units unclear",
                    look_for="Symbols, subscripts, signs, axes, or units are undefined, inconsistent, or ambiguous in a way that affects the answer."),
    AssessmentCheck(id="q13", level=_Q, points=SERIOUS_POINTS, name="Incorrect answer key",
                    look_for="A correct answer is not marked as correct, or an incorrect answer is marked as correct."),
    AssessmentCheck(id="q14", level=_Q, points=SERIOUS_POINTS, name="No uniquely correct answer",
                    look_for="A single-answer question has more than one defensible answer, no defensible answer, or overlapping choices that make the intended answer unclear."),
    AssessmentCheck(id="q15", level=_Q, points=OTHER_POINTS, name="Distractors are implausible",
                    look_for="Incorrect options are so obviously wrong that students can eliminate them without understanding the concept."),
    AssessmentCheck(id="q16", level=_Q, points=OTHER_POINTS, name="Distractors do not reveal thinking",
                    look_for="Incorrect options do not reflect plausible misconceptions, reasoning errors, or calculation mistakes, making responses less useful for diagnosing understanding."),
    AssessmentCheck(id="q17", level=_Q, points=OTHER_POINTS, name="Too few plausible distractors",
                    look_for="Only one incorrect option reflects a reasonable misunderstanding; the remaining distractors are filler or easy to dismiss."),
    AssessmentCheck(id="q18", level=_Q, points=OTHER_POINTS, name="Answer choices are not parallel",
                    look_for="Choices differ unnecessarily in scope, precision, grammatical form, or level of detail, making them harder to compare or giving away the answer."),
    AssessmentCheck(id="q19", level=_Q, points=OTHER_POINTS, name="Unintended answer cues",
                    look_for="The correct answer can be identified from its length, wording, grammar, specificity, position, or overlap with the question rather than from subject knowledge."),
    AssessmentCheck(id="q20", level=_Q, points=OTHER_POINTS, name="Answer with flawed reasoning",
                    look_for="An option reaches the correct conclusion for an incorrect reason, or combines multiple claims such that its truth is unclear."),
    AssessmentCheck(id="q21", level=_Q, points=OTHER_POINTS, name="Ambiguous or overlapping options",
                    look_for="Two options express substantially the same answer, or an option is true only under assumptions not stated in the question."),
)
