#!/bin/bash

WORKSPACE="/home/admin/0code/00koder"

fix_project() {
    local project=$1
    cd "$WORKSPACE/$project" || return

    # For projects with package.json but missing dependencies (like poolAmazono3)
    if [[ -f "package.json" ]]; then
        echo "Installing dependencies for $project"
        npm install
    fi

    # For projects without package.json and without index.html
    if [[ ! -f "package.json" && ! -f "index.html" ]]; then
        echo "Creating minimal index.html for $project"
        echo "<!DOCTYPE html><html><head><title>${project}</title></head><body><h1>${project}</h1></body></html>" > index.html
    fi
}

# Process all project directories
while IFS= read -r -d '' dir; do
    project=$(basename "$dir")
    fix_project "$project"
done < <(find "$WORKSPACE" -maxdepth 1 -type d ! -name "$(basename "$WORKSPACE")" -print0)