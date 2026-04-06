## Review Focus
- Focus EXCLUSIVELY on correctness bugs, logic errors, and security issues
- DO NOT flag performance concerns, style issues, or minor improvements
- Only flag issues at P0 (crash/data loss) or P1 (incorrect behavior) severity
- Skip P2 and P3 entirely

## Depth Over Breadth
- If a PR has complex logic changes, spend your budget going deep on those files
- Prefer finding 3-4 high-confidence bugs on one PR over 1 comment each on 5 PRs
- Every finding must have a concrete, specific trigger path -- no "might" or "could"

## What Counts as a Real Bug
- Null/undefined dereferences with a reachable code path
- Logic errors that produce wrong results (wrong condition, off-by-one, missing case)
- Security vulnerabilities (injection, auth bypass, CSRF, XSS)
- Resource leaks or missing cleanup
- Race conditions or concurrency bugs
- API contract violations (wrong return type, missing error handling)
- Data corruption or loss scenarios

## What to SKIP
- Performance suggestions (caching, query optimization, etc.)
- Code style or readability improvements
- Missing tests or test improvements
- Documentation issues
- Suggestions that start with "consider" or "you might want to"
