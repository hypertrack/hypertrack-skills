default:
    @just --list

# Formatting, script syntax, regression tests, links, and API endpoints vs the live OpenAPI spec
check: fmt-check scripts test refs

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
