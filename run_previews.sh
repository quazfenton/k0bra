#!/bin/bash

# Define the workspace directory
WORKSPACE="/home/admin/0code/00koder"

# Create a report file
REPORT="$WORKSPACE/preview_report.md"
echo "# Project Preview Status Report" > $REPORT
echo "| Project | Status | Output Snippet |" >> $REPORT
echo "|---------|--------|----------------|" >> $REPORT

# List of project directories
cd $WORKSPACE
for dir in */; do
    # Remove the trailing slash
    project=${dir%/}
    echo "Processing $project"

    cd "$WORKSPACE/$project"

    # Check for project type and run command
    if [[ -f "package.json" ]]; then
        # Check for dev script
        if grep -q '"dev"' package.json; then
            CMD="npm run dev"
        elif grep -q '"start"' package.json; then
            CMD="npm run start"
        else
            CMD="echo 'NOT_RUNNABLE: No dev or start script in package.json'"
        fi
    elif [[ -f "index.html" ]]; then
        # For static site, use Python HTTP server on a random port (port 0) but we don't care about the port
        CMD="python3 -m http.server 0"
    else
        CMD="echo 'NOT_RUNNABLE: No index.html or package.json'"
    fi

    # Run the command with a timeout of 5 seconds and capture output
    OUTPUT=$(timeout 5 $CMD 2>&1)
    EXIT_CODE=$?

    # Analyze the output
    if [[ $EXIT_CODE -eq 124 ]]; then
        # Timeout occurred, but that's expected. Check if the output indicates success.
        if echo "$OUTPUT" | grep -q -i "Serving HTTP\|Listening\|started"; then
            STATUS="✅ Success"
        elif echo "$OUTPUT" | grep -q -i "error\|not found\|command not found\|EACCES"; then
            STATUS="❌ Failure"
        else
            STATUS="⚠️ Unknown (timed out)"
        fi
    else
        # The command exited before timeout. Check the exit code and output.
        if [[ $EXIT_CODE -eq 0 ]]; then
            if echo "$OUTPUT" | grep -q -i "Serving HTTP\|Listening\|started"; then
                STATUS="✅ Success"
            else
                STATUS="⚠️ Exited early without success indicator"
            fi
        else
            STATUS="❌ Failed with exit code $EXIT_CODE"
        fi
    fi

    # If the output is long, take the first 100 characters for the snippet
    SNIPPET=$(echo "$OUTPUT" | head -c 100)
    # Escape any pipes in the snippet to not break the markdown table
    SNIPPET=${SNIPPET//|/\\|}

    # Append to report
    echo "| $project | $STATUS | $SNIPPET |" >> $REPORT

    # Go back to workspace
    cd $WORKSPACE
done < <(find "$WORKSPACE" -maxdepth 1 -type d ! -name "$(basename "$WORKSPACE")" -print0)