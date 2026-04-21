# Review Guidelines - Enhanced Thoroughness

## Critical Instructions

1. **Review EVERY file individually.** Do not skip files even if they appear to be simple renames, test-only changes, or boilerplate. Bugs hide in seemingly innocent changes.

2. **Check each function/method modified in the diff.** For each one:
   - What are the implicit assumptions about input types and values?
   - What happens on edge cases (null, empty, zero, negative, boundary values)?
   - Does the function correctly handle all error paths?
   - Are return values used correctly by callers?

3. **Cross-reference related changes.** When a type, interface, or function signature changes in one file, check ALL callers/implementers in the diff for mismatches.

4. **Be especially vigilant for:**
   - Variables evaluated at definition time vs runtime (class-level defaults, module-level expressions)
   - Wrong variable names used (copy-paste errors, similar variable names)
   - Boolean logic errors (AND vs OR, negation errors, always-true/false conditions)
   - Off-by-one errors in loops, slices, and comparisons
   - Missing null/undefined checks on optional values
   - Cache key construction that could collide

5. **Err on the side of reporting.** If you see something that looks like it could be a bug with a plausible trigger path, report it. The validator will filter out false positives. Your job is to catch bugs, not to pre-filter.
