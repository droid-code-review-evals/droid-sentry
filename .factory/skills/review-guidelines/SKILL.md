# Review Guidelines

## Do NOT report these patterns (they are almost always false positives):

1. Missing null checks on values that are guaranteed by the framework or type system
2. Error handling suggestions for code that intentionally lets exceptions propagate
3. Performance concerns without evidence of actual bottleneck
4. Thread safety issues in single-threaded contexts
5. Input validation that is handled at a different layer (e.g., API gateway, ORM)
6. Missing try/catch around operations that are expected to succeed in normal flow
7. Style, naming, or formatting suggestions
8. Concerns about code that existed before this PR and was not modified

## DO report these patterns:

1. Logic errors where the code does something different from what the PR description intends
2. Off-by-one errors in loops, pagination, or array indexing
3. Wrong variable used (copy-paste errors, shadowing)
4. Missing return statements or unreachable code
5. SQL injection, XSS, or command injection in user-facing code
6. Race conditions that can cause data corruption
7. Breaking API contract changes (wrong type, missing field)
