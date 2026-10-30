.PHONY: check check-branch check-issues validate-templates validate-profiles check-profile-patterns check-no-merge terminal-state

# Aggregate lightweight checks (no test suite — standalone stdlib script).
check: check-branch validate-templates validate-profiles check-profile-patterns check-no-merge

# Guard against reintroduced hard-coded default-branch literals (#18).
check-branch:
	@bash scripts/check-branch-literals.sh

# Validate state-file template structure (v0.3.0).
validate-templates:
	@bash scripts/validate-templates.sh

# Validate every profile against generic.json's keys (profiles/README.md rule).
# Usage: make validate-profiles DIRS="profiles ~/.config/pipeline-skills/profiles"
validate-profiles:
	@bash scripts/validate-profiles.sh $(DIRS)

# A profile's own security patterns / auto-reject triggers all reach the state
# file, ahead of generic's (end to end through pipeline.py ship --init-only).
check-profile-patterns:
	@bash scripts/check-profile-patterns.sh

# --no-merge skips the merge only; the Retrospective still runs and posts.
check-no-merge:
	@bash scripts/check-no-merge.sh

# Pre-drain staleness check: verify cited symbols still exist (#7).
# Usage: make check-issues ISSUES="7 6"
check-issues:
	@bash scripts/check-issue-symbols.sh $(ISSUES)

# Substitute PR-number placeholders after the PR exists (#6).
# Usage: make sub-pr PR=42 FILES="ROADMAP.md CHANGELOG.md"
sub-pr:
	@bash scripts/substitute-pr-number.sh $(PR) $(FILES)

# Report the clean terminal state — the /pipeline-cycle stop condition (v0.7.0).
terminal-state:
	@bash scripts/terminal-state.sh
