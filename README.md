# CollageAI prompt optimization

Try prompt changes for the lesson wizard on the **real** CollageAI app, and compare the lessons
they produce. Over a week we keep the changes that make lessons better, then merge the winners
into CollageAI.

## How it works

1. **An experiment is a draft pull request (PR) on CollageAI** that changes one or two prompt
   files under `server/agents/`. Add the `render-preview` label, and Render deploys the PR to its
   own address, `https://collageai-dev-pr-<number>.onrender.com`, with CollageAI's own keys.
   No Monday ticket is needed for a draft.
2. **The baseline is the dev site.** Keep each experiment branch up to date with dev
   ("Update branch" on the PR), so the prompt is the only difference.
3. **The runner logs in as a test teacher** and goes through the lesson wizard with the same
   calls and fields as the website: upload, objectives, concepts, exercise plan, create lesson,
   and generate content.
4. **It reads the finished lesson back** the way the lesson page does: every concept with its
   blocks, and every exercise with its questions. It saves the result to
   `outputs/<target>-<time>/<case>/result.json`, with a link to the lesson page in the app.

The runner plays the teacher: it keeps the first N objectives and concepts (set in each test
case) and accepts the exercise plan as the AI wrote it. Editor AI actions are not covered yet.

The runner only sends the test teacher's password to a CollageAI preview address or the dev
address you set. Any other address is refused.

## Folders

```
test-set/<case>/
  case.yaml     Subject, level, language, custom instructions, what the teacher keeps.
  source.md     The material, sent as pasted text.
runner/         The script that does the run.
outputs/        Results (not saved in git).
```

Each test case gets its own course, named "Prompt eval: <course title>", in the test teacher's
account. It is created on the first run and reused after that. Generated lessons stay in the
course, so you can open them in the app.

## Try a prompt change (for teammates)

1. In CollageAI, start a branch from `dev` and change the prompt. The prompt map shows each
   step's file, for example `server/agents/prompts/user/los_user.py` for learning objectives.
2. Open a **draft** PR into `dev` and add the `render-preview` label. Put "Prompt experiment:" at
   the start of the title, and say what you changed and why.
3. When the preview is up, go to this repo's Actions tab, choose "Run experiment", then
   "Run workflow", and enter `pr-<number>`.
4. Open the run's results, or click the lesson page link it prints.

Rules:
- Change one or two prompts per experiment, so we know what made the difference.
- Never merge an experiment PR. Winners get a clean PR at the end.
- Use made-up or openly licensed material in test cases. Never real student or customer data.

## Run it on your machine

```bash
pip install -r requirements.txt
export RUNNER_TEACHER_EMAIL=...      # the test teacher's login
export RUNNER_TEACHER_PASSWORD=...
export RUNNER_DEV_URL=https://...    # only needed for --target dev
python -m runner --target pr-2101
```

Add `--case test-set/biology-photosynthesis` to run one case.

## Settings the GitHub Action needs

- Secrets: `RUNNER_TEACHER_EMAIL` and `RUNNER_TEACHER_PASSWORD`, the login of a test teacher
  account on dev. Previews use the dev database, so the same login works on every preview.
- Variable: `RUNNER_DEV_URL`, the dev site's address.

## Status

- Done: test case format, the runner for the full lesson pipeline, a manual GitHub Action, and
  one sample case (Biology, photosynthesis).
- Not run end to end yet: it needs the test teacher login above.
- Next: the first baseline run on dev, more subjects and file uploads, assessment and import
  wizards, the judge, a readable report, and the leaderboard.
