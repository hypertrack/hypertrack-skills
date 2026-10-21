default:
    @just --list

# Keep the skill small: SKILL.md <= 200 lines, all skill Markdown <= 300 lines
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

# Size budget, formatting, script syntax, regression tests, links, and API endpoints vs the live OpenAPI spec
check: budget fmt-check scripts test refs

# Format Markdown with dprint
fmt:
    dprint fmt

# Check Markdown formatting
fmt-check:
    dprint check

# Check every URL resolves and every API endpoint mentioned exists in the OpenAPI spec
refs:
    python3 tools/check_refs.py

# Syntax-check the bundled and maintenance scripts
scripts:
    python3 -m py_compile skills/hypertrack-integration/scripts/*.py tools/*.py

# Compile Swift/Kotlin/TS/Dart/C# snippets against the latest SDK releases (needs Xcode, a JDK, an Android SDK, node; downloads Dart and .NET)
snippets *args:
    python3 tools/check_snippets.py {{args}}

# Regression tests for the scripts, tools, and snippets with logic (stdlib; node/npx for the JS ones)
test:
    python3 -m unittest discover -s tests
