#!/bin/bash

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Log start of execution
echo "$(date) - Launching project at $1" >> launch.log

# Get project path from argument
PROJECT_PATH="$1"

# Validate project path
if [ ! -d "$PROJECT_PATH" ]; then
    echo "ERROR: Project path $PROJECT_PATH is not a directory" >> launch.log
    exit 1
fi

# Determine project type and start command
if [ -f "$PROJECT_PATH/package.json" ]; then
    # Advanced project type detection (with additional frameworks)
    if grep -q '"next"' "$PROJECT_PATH/package.json"; then
        type="nextjs"
    elif grep -q '"react"' "$PROJECT_PATH/package.json"; then
        type="react"
    elif grep -q '"vue"' "$PROJECT_PATH/package.json"; then
        type="vue"
    elif grep -q '"@sveltejs/kit"' "$PROJECT_PATH/package.json"; then
        type="sveltekit"
    elif grep -q '"express"' "$PROJECT_PATH/package.json"; then
        type="express"
    elif grep -q '"nestjs/core"' "$PROJECT_PATH/package.json"; then
        type="nestjs"
    elif grep -q '"@angular/core"' "$PROJECT_PATH/package.json"; then
        type="angular"
    elif grep -q '"nuxt"' "$PROJECT_PATH/package.json"; then
        type="nuxt"
    elif grep -q '"gatsby"' "$PROJECT_PATH/package.json"; then
        type="gatsby"
    elif grep -q '"@remix-run"' "$PROJECT_PATH/package.json"; then
        type="remix"
    elif grep -q '"vite"' "$PROJECT_PATH/package.json"; then
        type="vite"
    elif grep -q '"astro"' "$PROJECT_PATH/package.json"; then
        type="astro"
    else
        type="node"
    fi
    echo "Starting $type project at $PROJECT_PATH" >> launch.log
    
    # Allocate port from port registry
    response=$(curl -s -X POST http://localhost:4110/allocate -H "Content-Type: application/json" -d "{\"project_path\":\"$PROJECT_PATH\"}")
    if ! PORT=$(python -c "import json, sys; data=json.loads(sys.argv[1]); print(data.get('port', ''))" "$response" 2>/dev/null); then
        echo "ERROR: Failed to parse port allocation response for project $PROJECT_PATH. Response: $response" >> launch.log
        exit 1
    fi
    if [ -z "$PORT" ]; then
        echo "ERROR: Failed to allocate port for project $PROJECT_PATH. Response: $response" >> launch.log
        exit 1
    fi
    echo "Allocated port $PORT for project $PROJECT_PATH" >> launch.log
    
    # Check if port is already in use
    if lsof -i :$PORT; then
        echo "Port $PORT is already in use. Cannot launch project." >> launch.log
        exit 1
    fi
    
    # Determine package manager: use yarn if available, else npm
    PM="npm"
    if command -v yarn &> /dev/null && [ -f "$PROJECT_PATH/yarn.lock" ]; then
        PM="yarn"
    fi

    # Check for Docker configuration
    if [ -f "$PROJECT_PATH/Dockerfile" ] || [ -f "$PROJECT_PATH/docker-compose.yml" ]; then
        type="docker"
        echo "Starting Docker project at $PROJECT_PATH" >> launch.log
    
        # Build and run the Docker container
        if [ -f "$PROJECT_PATH/docker-compose.yml" ]; then
            (cd "$PROJECT_PATH" && timeout 300 docker-compose up --build) >> launch.log 2>&1 &
        else
            (cd "$PROJECT_PATH" && timeout 300 docker build -t "${PROJECT_PATH##*/}" . && timeout 300 docker run -p $PORT:$PORT "${PROJECT_PATH##*/}") >> launch.log 2>&1 &
        fi
        pid=$!
        echo $pid > "$PROJECT_PATH/.pid"
        echo "PORT:$PORT"
    else
        # Check if dependencies need to be installed
        if [ ! -d "$PROJECT_PATH/node_modules" ]; then
            echo "Installing dependencies in background for project $PROJECT_PATH" >> launch.log
            (cd "$PROJECT_PATH" && $PM install > "$PROJECT_PATH/.install.log" 2>&1 &)
        fi

        # Framework-specific port handling with explicit host binding for local only
        if [ "$type" = "nextjs" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOSTNAME=127.0.0.1 $PM run dev -- -p $PORT) >> launch.log 2>&1 &
        elif [ "$type" = "react" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOST=127.0.0.1 $PM run start) >> launch.log 2>&1 &
        elif [ "$type" = "sveltekit" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT $PM run dev --host 127.0.0.1) >> launch.log 2>&1 &
        elif [ "$type" = "express" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOST=127.0.0.1 node app.js) >> launch.log 2>&1 &
        elif [ "$type" = "nestjs" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOST=127.0.0.1 $PM run start:dev) >> launch.log 2>&1 &
        elif [ "$type" = "angular" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT ng serve --host 127.0.0.1 --port $PORT) >> launch.log 2>&1 &
        elif [ "$type" = "nuxt" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOST=127.0.0.1 $PM run dev) >> launch.log 2>&1 &
        elif [ "$type" = "gatsby" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOST=127.0.0.1 $PM run develop) >> launch.log 2>&1 &
        elif [ "$type" = "remix" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT HOST=127.0.0.1 $PM run dev) >> launch.log 2>&1 &
        elif [ "$type" = "vite" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT $PM run dev --host 127.0.0.1 --port $PORT) >> launch.log 2>&1 &
        elif [ "$type" = "astro" ]; then
            (cd "$PROJECT_PATH" && timeout 300 PORT=$PORT $PM run dev --host 127.0.0.1) >> launch.log 2>&1 &
        else
            # If no specific script, try to start with node
            if [ -f "$PROJECT_PATH/server.js" ]; then
                (cd "$PROJECT_PATH" && timeout 300 HOST=127.0.0.1 node server.js --port $PORT) >> launch.log 2>&1 &
            elif [ -f "$PROJECT_PATH/index.js" ]; then
                (cd "$PROJECT_PATH" && timeout 300 HOST=127.0.0.1 node index.js --port $PORT) >> launch.log 2>&1 &
            else
                (cd "$PROJECT_PATH" && timeout 300 $PM run dev -- --host 127.0.0.1 --port $PORT) >> launch.log 2>&1 &
            fi
        fi
        pid=$!
        echo $pid > "$PROJECT_PATH/.pid"
        echo "PORT:$PORT"
    fi

elif [ -f "$PROJECT_PATH/requirements.txt" ] || [ -f "$PROJECT_PATH/app.py" ]; then
    # Determine Python project type
    if grep -iq "flask" "$PROJECT_PATH/requirements.txt" || ( [ -f "$PROJECT_PATH/app.py" ] && grep -iq "flask" "$PROJECT_PATH/app.py" ); then
        type="flask"
        echo "Starting Flask project at $PROJECT_PATH" >> launch.log
    else
        type="python"
        echo "Starting Python project at $PROJECT_PATH" >> launch.log
    fi
     
    # Allocate port from port registry
    response=$(curl -s -X POST http://localhost:4110/allocate -H "Content-Type: application/json" -d "{\"project_path\":\"$PROJECT_PATH\"}")
    if ! PORT=$(python -c "import json, sys; print(json.loads(sys.argv[1])['port'])" "$response" 2>/dev/null); then
        echo "ERROR: Failed to allocate port for project $PROJECT_PATH. Response: $response" >> launch.log
        exit 1
    fi
     
    if [ "$type" = "flask" ]; then
        (cd "$PROJECT_PATH" && timeout 300 flask run --host 127.0.0.1 --port $PORT) >> launch.log 2>&1 &
    else
        (cd "$PROJECT_PATH" && timeout 300 HOST=127.0.0.1 python app.py --port $PORT) >> launch.log 2>&1 &
    fi
    pid=$!
    echo $pid > "$PROJECT_PATH/.pid"
    echo "PORT:$PORT"
else
    # Try to start as a simple static server
    echo "Starting static server for $PROJECT_PATH" >> launch.log
    
    # Allocate port from port registry
    response=$(curl -s -X POST http://localhost:4110/allocate -H "Content-Type: application/json" -d "{\"project_path\":\"$PROJECT_PATH\"}")
    if ! PORT=$(python -c "import json, sys; print(json.loads(sys.argv[1])['port'])" "$response" 2>/dev/null); then
        echo "ERROR: Failed to allocate port for project $PROJECT_PATH. Response: $response" >> launch.log
        exit 1
    fi
    
    (cd "$PROJECT_PATH" && timeout 300 python -m http.server $PORT) >> launch.log 2>&1 &
    pid=$!
    echo $pid > "$PROJECT_PATH/.pid"
    echo "PORT:$PORT"
fi

echo "$(date) - Project launch completed" >> launch.log

# Add cleanup handler
trap "pkill -P $pid; exit" SIGINT SIGTERM