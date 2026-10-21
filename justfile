default:
    @just --list

# Skill size: SKILL.md <= 200 lines, all skill Markdown <= 300 lines
budget:
    #!/usr/bin/env bash
    set -euo pipefail
    skill=$(wc -l < skills/hypertrack-integration/SKILL.md | tr -d ' ')
    total=$(find skills -name '*.md' -exec cat {} + | wc -l | tr -d ' ')
    echo "SKILL.md: $skill/200 lines, all skill Markdown: $total/300 lines"
    if [ "$skill" -gt 200 ] || [ "$total" -gt 300 ]; then
        echo "over budget: link to the docs instead of restating them (see VISION.md)"
        exit 1
    fi

# Size budget, formatting, and links/API endpoints vs the live OpenAPI spec
check: budget fmt-check refs

# Format Markdown with dprint
fmt:
    dprint fmt

# Check Markdown formatting
fmt-check:
    dprint check

# Check every URL resolves and every API endpoint mentioned exists in the OpenAPI spec
refs:
    python3 tools/check_refs.py
