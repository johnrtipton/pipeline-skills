.PHONY: check check-branch check-issues

# Aggregate lightweight checks (no test suite — standalone stdlib script).
check: check-branch

# Guard against reintroduced hard-coded default-branch literals (#18).
check-branch:
	@bash scripts/check-branch-literals.sh

# Pre-drain staleness check: verify cited symbols still exist (#7).
# Usage: make check-issues ISSUES="7 6"
check-issues:
	@bash scripts/check-issue-symbols.sh $(ISSUES)

# Substitute PR-number placeholders after the PR exists (#6).
# Usage: make sub-pr PR=42 FILES="ROADMAP.md CHANGELOG.md"
sub-pr:
	@bash scripts/substitute-pr-number.sh $(PR) $(FILES)
