#!/usr/bin/env python3
"""
Generate review prompts and run droid exec for benchmark reviews.

Produces the same two-pass (candidates + validator) prompts as droid-action,
then runs droid exec for each pass. No GitHub posting.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def generate_candidates_prompt(
    repo: str, pr_number: int, head_sha: str, head_ref: str, base_ref: str,
    diff_path: str, comments_path: str, description_path: str,
    candidates_path: str,
) -> str:
    return f"""You are a senior staff software engineer and expert code reviewer.

Your task: Review PR #{pr_number} in {repo} and generate a JSON file with **high-confidence, actionable** review comments that pinpoint genuine issues.

<context>
Repo: {repo}
PR Number: {pr_number}
PR Head Ref: {head_ref}
PR Head SHA: {head_sha}
PR Base Ref: {base_ref}

Precomputed data files:
- PR Description: `{description_path}`
- Full PR Diff: `{diff_path}`
- Existing Comments: `{comments_path}`
</context>

<understanding_phase>
**Step 0: Understand the PR intent**

1. Read the PR description from `{description_path}` to understand the purpose and scope of the changes.
2. If the PR description contains a ticket URL (e.g., Jira, Linear, GitHub issue link) or a ticket ID, **always fetch it** using FetchUrl or the appropriate tool to understand the full requirements and acceptance criteria. This context is critical for evaluating whether the implementation is correct and complete.
</understanding_phase>

<review_guidelines>
- You are currently checked out to the PR branch.
- Review ALL modified files in the PR branch.
- Do NOT duplicate comments already in `{comments_path}`.
</review_guidelines>

<triage_phase>
**Step 1: Analyze and group the modified files**

Before reviewing, you must triage the PR to enable parallel review:

1. Read the diff file (`{diff_path}`) to identify ALL modified files
2. Group the files into logical clusters based on:
   - **Related functionality**: Files in the same module or feature area
   - **File relationships**: A component and its tests, a class and its interface
   - **Risk profile**: Security-sensitive files together, database/migration files together
   - **Dependencies**: Files that import each other or share types

3. Document your grouping briefly, for example:
   - Group 1 (Auth): src/auth/login.ts, src/auth/session.ts, tests/auth.test.ts
   - Group 2 (API handlers): src/api/users.ts, src/api/orders.ts
   - Group 3 (Database): src/db/migrations/001.ts, src/db/schema.ts

Guidelines for grouping:
- Aim for 3-6 groups to balance parallelism with context coherence
- Keep related files together so reviewers have full context
- Each group should be reviewable independently
</triage_phase>

<parallel_review_phase>
**Step 2: Spawn parallel subagents to review each group**

After grouping, use the Task tool to spawn parallel `file-group-reviewer` subagents. Each subagent will review one group of files independently.

**IMPORTANT**: Spawn ALL subagents in a single response to enable parallel execution.

For each group, invoke the Task tool with:
- `subagent_type`: "file-group-reviewer"
- `description`: Brief label (e.g., "Review auth module")
- `prompt`: Must include:
  1. The PR context (repo, PR number, base/head refs)
  2. The list of assigned files for this group
  3. The relevant diff sections for those files (extract from `{diff_path}`)
  4. Instructions to return a JSON array of findings

Example Task invocation for one group:
```
Task(
  subagent_type: "file-group-reviewer",
  description: "Review auth module",
  prompt: \"\"\"
    Review the following files from PR #{pr_number} in {repo}.

    PR Context:
    - Head SHA: {head_sha}
    - Base Ref: {base_ref}

    Assigned files:
    - src/auth/login.ts
    - src/auth/session.ts
    - tests/auth.test.ts

    Diff for these files:
    <paste relevant diff sections here>

    Return a JSON array of issues found. If no issues, return [].
  \"\"\"
)
```

Spawn all group reviewers in parallel by including multiple Task calls in one response.
</parallel_review_phase>

<aggregation_phase>
**Step 3: Aggregate subagent results**

After all subagents complete, collect and merge their findings:

1. **Collect results**: Each subagent returns a JSON array of comment objects
2. **Merge arrays**: Combine all arrays into a single comments array
3. **Add commit_id**: Add `"commit_id": "{head_sha}"` to each comment object
4. **Deduplicate**: If multiple subagents flagged the same location (same path + line), keep only one comment (prefer higher priority: P0 > P1 > P2)
5. **Filter existing**: Remove any comments that duplicate issues already in `{comments_path}`
6. **Write reviewSummary**: Synthesize a 1-3 sentence overall assessment based on all findings

Write the final aggregated result to `{candidates_path}` using the schema in `<output_spec>`.
</aggregation_phase>

<output_spec>
Write output to `{candidates_path}` using this exact schema:

```json
{{
  "version": 1,
  "meta": {{
    "repo": "owner/repo",
    "prNumber": 123,
    "headSha": "<head sha>",
    "baseRef": "main",
    "generatedAt": "<ISO timestamp>"
  }},
  "comments": [
    {{
      "path": "src/index.ts",
      "body": "[P1] Title\\n\\n1 paragraph.",
      "line": 42,
      "startLine": null,
      "side": "RIGHT",
      "commit_id": "<head sha>"
    }}
  ],
  "reviewSummary": {{
    "body": "1-3 sentence overall assessment"
  }}
}}
```

<schema_details>
- **version**: Always `1`

- **meta**: Metadata object
  - `repo`: "{repo}"
  - `prNumber`: {pr_number}
  - `headSha`: "{head_sha}"
  - `baseRef`: "{base_ref}"
  - `generatedAt`: ISO 8601 timestamp (e.g., "2024-01-15T10:30:00Z")

- **comments**: Array of comment objects
  - `path`: Relative file path (e.g., "src/index.ts")
  - `body`: Comment text starting with priority tag [P0|P1|P2], then title, then 1 paragraph explanation
  - `line`: Target line number (single-line) or end line number (multi-line). Must be >= 0.
  - `startLine`: `null` for single-line comments, or start line number for multi-line comments
  - `side`: "RIGHT" for new/modified code (default), "LEFT" only for removed code
  - `commit_id`: "{head_sha}"

- **reviewSummary**:
  - `body`: 1-3 sentence overall assessment
</schema_details>
</output_spec>

<critical_constraints>
**DO NOT** post to GitHub.
**DO NOT** invoke any PR mutation tools (inline comments, submit review, delete/minimize/reply/resolve, etc.).
**DO NOT** modify any files other than writing to `{candidates_path}`.
Output ONLY the JSON file—no additional commentary.
</critical_constraints>
"""


def generate_validator_prompt(
    repo: str, pr_number: int, head_sha: str, head_ref: str, base_ref: str,
    diff_path: str, comments_path: str, description_path: str,
    candidates_path: str, validated_path: str,
) -> str:
    return f"""You are validating candidate review comments for PR #{pr_number} in {repo}.

IMPORTANT: This is Phase 2 (validator) of a two-pass review pipeline.

### Context

* Repo: {repo}
* PR Number: {pr_number}
* PR Head Ref: {head_ref}
* PR Head SHA: {head_sha}
* PR Base Ref: {base_ref}

### Inputs

Read:
* PR Description: `{description_path}`
* Candidates: `{candidates_path}`
* Full PR Diff: `{diff_path}`
* Existing Comments: `{comments_path}`

### Output

Write validated results to: `{validated_path}`

=======================

## CRITICAL REQUIREMENTS

1. You MUST read and validate **every** candidate before writing the output.
2. For each candidate, confirm:
   * It is a real, actionable bug (not speculative)
   * There is a realistic trigger path and observable wrong behavior
   * The anchor is valid (path + side + line/startLine correspond to the diff)
3. Preserve ordering: keep results in the same order as candidates.
4. **When in doubt, reject.** A false positive is worse than a missed bug.

=======================

## Phase 1: Load context (REQUIRED)

1. Read the PR description: `{description_path}`
2. Read existing comments: `{comments_path}`
3. Read the COMPLETE diff: `{diff_path}` (if large, read in chunks — do not proceed until you have read the ENTIRE diff)
4. Read candidates: `{candidates_path}`

=======================

## Phase 2: Validate candidates

### Approve ONLY if at least one is true
* Definite runtime failure
* Incorrect logic with a concrete trigger path and wrong outcome
* Security vulnerability with realistic exploit
* Data corruption/loss
* Breaking contract change (discoverable in code/tests)

### Reject if ANY of these are true
* It's stylistic / naming / formatting / dead code
* It's about test quality or test code (unless masking a production bug)
* It's a pre-existing issue not introduced by this PR
* It's not anchored to a valid changed line
* It's already reported (dedupe against existing comments)

### Deduplication (STRICT)

If two or more candidates describe the same underlying bug (same root cause, even if anchored to different lines or worded differently), approve only the ONE with the best anchor and clearest explanation. Reject the rest with reason "duplicate of candidate N".

When rejecting, write a concise reason.

=======================

## Phase 3: Write {validated_path}

Write the file with this schema:

```json
{{
  "version": 1,
  "meta": {{
    "repo": "owner/repo",
    "prNumber": 123,
    "headSha": "<head sha>",
    "baseRef": "main",
    "validatedAt": "<ISO timestamp>"
  }},
  "results": [
    {{
      "status": "approved",
      "comment": {{
        "path": "src/index.ts",
        "body": "[P1] Title\\n\\n1 paragraph.",
        "line": 42,
        "startLine": null,
        "side": "RIGHT",
        "commit_id": "{head_sha}"
      }}
    }},
    {{
      "status": "rejected",
      "candidate": {{
        "path": "src/other.ts",
        "body": "[P2] ...",
        "line": 10,
        "startLine": null,
        "side": "RIGHT",
        "commit_id": "{head_sha}"
      }},
      "reason": "Not a real bug because ..."
    }}
  ],
  "reviewSummary": {{
    "status": "approved",
    "body": "1-3 sentence overall assessment"
  }}
}}
```

Notes:
* Use `commit_id` = `{head_sha}`.
* `results` MUST have exactly one entry per candidate, in the same order.

Then write the file using the local file tool.

**DO NOT** post to GitHub.
**DO NOT** invoke any PR mutation tools (inline comments, submit review, delete/minimize/reply/resolve, etc.).
**DO NOT** modify any files other than writing to `{validated_path}`.
Output ONLY the JSON file—no additional commentary.
"""


def run_droid_exec(prompt_path: str, model: str, reasoning: str, tools: list[str], tag: str = "code-review") -> int:
    cmd = [
        "droid", "exec",
        "--skip-permissions-unsafe",
        "--enabled-tools", ",".join(tools),
        "--tag", tag,
        "--reasoning-effort", reasoning,
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(["-f", prompt_path])

    print(f"  Running: {' '.join(cmd[:6])}... ({Path(prompt_path).name})")
    result = subprocess.run(cmd, timeout=600)
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--model", default="gpt-5.2")
    parser.add_argument("--reasoning", default="high")
    parser.add_argument("--prompts-dir", required=True)
    args = parser.parse_args()

    prompts_dir = Path(args.prompts_dir)
    diff_path = str(prompts_dir / "pr.diff")
    comments_path = str(prompts_dir / "existing_comments.json")
    description_path = str(prompts_dir / "pr_description.txt")
    candidates_path = str(prompts_dir / "review_candidates.json")
    validated_path = str(prompts_dir / "review_validated.json")

    # --- Pass 1: Candidates ---
    print(f"Pass 1: Generating candidates for PR #{args.pr_number}...")
    candidate_prompt = generate_candidates_prompt(
        args.repo, args.pr_number, args.head_sha, args.head_ref, args.base_ref,
        diff_path, comments_path, description_path, candidates_path,
    )
    candidate_prompt_file = prompts_dir / "candidate_prompt.txt"
    candidate_prompt_file.write_text(candidate_prompt)

    candidate_tools = ["Read", "Grep", "Glob", "LS", "Execute", "Task", "FetchUrl", "Skill"]
    rc = run_droid_exec(str(candidate_prompt_file), args.model, args.reasoning, candidate_tools)
    if rc != 0:
        print(f"  Candidate pass failed with exit code {rc}")

    if not Path(candidates_path).exists():
        print("  ERROR: No candidates output produced")
        sys.exit(1)

    # --- Pass 2: Validator ---
    print(f"Pass 2: Validating candidates for PR #{args.pr_number}...")
    validator_prompt = generate_validator_prompt(
        args.repo, args.pr_number, args.head_sha, args.head_ref, args.base_ref,
        diff_path, comments_path, description_path, candidates_path, validated_path,
    )
    validator_prompt_file = prompts_dir / "validator_prompt.txt"
    validator_prompt_file.write_text(validator_prompt)

    validator_tools = ["Read", "Grep", "Glob", "LS", "Execute", "Create", "Edit", "ApplyPatch"]
    rc = run_droid_exec(str(validator_prompt_file), args.model, args.reasoning, validator_tools)
    if rc != 0:
        print(f"  Validator pass failed with exit code {rc}")

    # Summary
    if Path(validated_path).exists():
        with open(validated_path) as f:
            data = json.load(f)
        approved = sum(1 for r in data.get("results", []) if r.get("status") == "approved")
        rejected = sum(1 for r in data.get("results", []) if r.get("status") == "rejected")
        print(f"  Done: {approved} approved, {rejected} rejected")
    elif Path(candidates_path).exists():
        with open(candidates_path) as f:
            data = json.load(f)
        print(f"  Done (no validator output): {len(data.get('comments', []))} candidates")
    else:
        print("  Done: no output")


if __name__ == "__main__":
    main()
