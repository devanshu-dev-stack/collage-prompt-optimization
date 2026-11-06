# CollageAI prompt optimization

Try prompt changes for the lesson wizard, run them through the **real** CollageAI code, and
compare the lessons they produce. Over a week we keep the changes that make lessons better and
then move the winners into CollageAI as normal pull requests.

## How a run works

1. Download CollageAI at one fixed commit (`collage_ref.txt`), so every run uses the same code.
2. Make a private copy of its server folder and drop in the experiment's prompt files.
   Your CollageAI checkout is never changed.
3. Start the real app (`server/app.py`) against an empty, throwaway database.
4. Create a teacher and one course per test case, using CollageAI's own seed helpers.
5. Click through the lesson wizard through the same routes the website calls, with the same
   fields: upload, objectives, concepts, exercise plan, create lesson, generate content.
6. Read the finished lesson back (every concept and exercise, with all their blocks) and save
   it, with each step's reply and the AI token counts, to `outputs/<experiment>/<case>/result.json`.

The script stands in for the teacher: it keeps the first N objectives and concepts (set per test
case) and accepts the exercise plan as the AI wrote it. Editor AI actions (regenerate or improve a
block) are not covered yet.

## Folders

```
collage_ref.txt          The CollageAI commit every run uses. Change it on purpose, then re-run baseline.
experiments/<name>/
  experiment.yaml        Who made it, what it changes and why.
  files/server/agents/   Only the prompt files you changed, at their CollageAI path.
test-set/<case>/
  case.yaml              Subject, level, language, custom instructions, what the teacher keeps.
  source.md              The material, sent as pasted text.
runner/                  The script that does the run.
outputs/                 Results (not saved in git).
```

## Try a prompt change (for teammates)

You can do all of this on the GitHub website.

1. Find the prompt in CollageAI. The prompt map shows each step's file, for example
   `server/agents/prompts/user/los_user.py` for learning objectives.
2. In this repo, create `experiments/<short-name>/experiment.yaml`, copying `experiments/baseline/experiment.yaml`
   and filling in your name and what you changed.
3. Create `experiments/<short-name>/files/<same CollageAI path>`, for example
   `experiments/<short-name>/files/server/agents/prompts/user/los_user.py`, and paste in the whole
   file with your change. Start from the file at the commit in `collage_ref.txt`.
4. Choose "Create a new branch and start a pull request".

Rules:
- Change one or two prompts per experiment, so we know what made the difference.
- Only files that already exist under `server/agents/` can be replaced. A wrong path stops the run.
- Use made-up or openly licensed material in test cases. Never real student or customer data.

Pull requests run automatically in the next step. For now, run an experiment by hand:
Actions tab, "Run experiment", "Run workflow", then type the experiment folder name.

## Run it on your machine

You need a CollageAI checkout, its server packages installed, MongoDB on `localhost:27017`
(the runner refuses any other address), and the Azure OpenAI settings in your environment.

```bash
python -m runner --collage-dir ../CollageAI --experiment experiments/baseline
```

Add `--case test-set/biology-photosynthesis` to run one case. Each run uses a new database
named `prompt_eval_<date>_<time>`.

## Settings the GitHub Action needs

Secrets (Settings, Secrets and variables, Actions):
- `COLLAGE_REPO_TOKEN`: a read-only token that can read CollageAI-Org/CollageAI.
- `AZURE_OPENAI_<REGION>_ENDPOINT` and `AZURE_OPENAI_<REGION>_KEY1` for at least one region
  (US, US2, FRANCE or SWEDEN).
- `GEMINI_API_KEY`, needed once test cases upload files.

Variables, set to match production: `DEFAULT_MODEL`, `GEMINI_ENABLED`, `WIZARD_GEMINI_MODEL`,
`MULTIMODAL_PROVIDER`.

## Status

- Done: experiment and test case formats, the runner for the full lesson pipeline, a manual
  GitHub Action, and one sample case (Biology, photosynthesis).
- Checked locally without AI keys: the app starts, login, course setup and upload work. The AI
  steps have not run yet; they need the secrets above.
- Next: the first real baseline run, more subjects and file uploads, assessment and import
  wizards, the judge, pull request comments with a readable report, and the leaderboard.
