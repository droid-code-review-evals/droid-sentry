## Review Focus
- Focus on correctness bugs, logic errors, and security issues
- DO NOT flag performance concerns, style issues, or minor improvements  
- Only flag issues at P0 (crash/data loss) or P1 (incorrect behavior) severity
- Skip P2 and P3 entirely

## Confidence Gate
- Only flag an issue if you can trace a SPECIFIC input or code path that triggers the bug
- Vague concerns ("this might cause issues") are not findings — skip them
- If the bug requires an extremely unlikely precondition, skip it

## Before You Flag: False Positive Checklist
Before reporting any issue, verify:
- [ ] The issue is NOT handled elsewhere in the same PR (check other files in the diff)
- [ ] The issue is NOT guarded by a caller or upstream validation
- [ ] The issue affects actual runtime behavior, not just theoretical edge cases
- [ ] You are NOT flagging a deliberate design choice or existing pattern in the codebase

## Depth Over Breadth
- If a PR has complex logic changes, spend your budget going deep on those files
- Prefer finding 2-3 high-confidence bugs over 5+ low-confidence ones
- Maximum 3 comments per file — only your highest-confidence findings

## What Counts as a Real Bug
- Null/undefined dereferences with a reachable code path
- Logic errors that produce wrong results (wrong condition, off-by-one, missing case)
- Security vulnerabilities (injection, auth bypass, CSRF, XSS)
- Resource leaks or missing cleanup
- Race conditions or concurrency bugs with a concrete trigger scenario
- API contract violations (wrong return type, missing error handling)

## What to SKIP
- Performance suggestions
- Code style or readability improvements
- Missing tests or test improvements
- Documentation issues
- Suggestions that start with "consider" or "you might want to"
- Issues that require 3+ unlikely conditions to trigger
