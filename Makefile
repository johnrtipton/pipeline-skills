.PHONY: check check-branch

# Aggregate lightweight checks (no test suite — standalone stdlib script).
check: check-branch

# Guard against reintroduced hard-coded default-branch literals (#18).
check-branch:
	@bash scripts/check-branch-literals.sh
