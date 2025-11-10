#!/usr/bin/env python3
"""
Comprehensive Framework Detection and Support System
"""

import os
import json
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Tuple, Optional

class FrameworkDetector:
    def __init__(self):
        self.frameworks = self._load_frameworks()
    
    def _load_frameworks(self) -> Dict:
        """Load framework detection rules from configuration"""
        return {
            # JavaScript/TypeScript Frameworks
            'react': {
                'name': 'React',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'"react"'],
                'commands': {
                    'start': 'npm start',
                    'build': 'npm run build',
                    'dev': 'npm start'
                },
                'ports': [3000, 3001, 3002],
                'icon': 'react.png'
            },
            'vue': {
                'name': 'Vue.js',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'"vue"'],
                'commands': {
                    'start': 'npm run serve',
                    'build': 'npm run build',
                    'dev': 'npm run serve'
                },
                'ports': [8080, 8081],
                'icon': 'vue.png'
            },
            'angular': {
                'name': 'Angular',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'@angular/core'],
                'commands': {
                    'start': 'ng serve',
                    'build': 'ng build',
                    'dev': 'ng serve'
                },
                'ports': [4200, 4201],
                'icon': 'angular.png'
            },
            'nextjs': {
                'name': 'Next.js',
                'type': 'fullstack',
                'files': ['package.json'],
                'content_patterns': [r'"next"'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [3000, 3001],
                'icon': 'nextjs.png'
            },
            'nuxt': {
                'name': 'Nuxt.js',
                'type': 'fullstack',
                'files': ['package.json'],
                'content_patterns': [r'"nuxt"'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [3000, 3001],
                'icon': 'nuxt.png'
            },
            'svelte': {
                'name': 'Svelte',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'"svelte"'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [5000, 5001],
                'icon': 'svelte.png'
            },
            'sveltekit': {
                'name': 'SvelteKit',
                'type': 'fullstack',
                'files': ['package.json'],
                'content_patterns': [r'@sveltejs/kit'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [5173, 5174],
                'icon': 'sveltekit.png'
            },
            'express': {
                'name': 'Express.js',
                'type': 'backend',
                'files': ['package.json'],
                'content_patterns': [r'"express"'],
                'commands': {
                    'start': 'node server.js',
                    'build': 'npm run build',
                    'dev': 'nodemon server.js'
                },
                'ports': [3000, 4000, 5000],
                'icon': 'express.png'
            },
            'nestjs': {
                'name': 'NestJS',
                'type': 'backend',
                'files': ['package.json'],
                'content_patterns': [r'@nestjs/core'],
                'commands': {
                    'start': 'npm run start:dev',
                    'build': 'npm run build',
                    'dev': 'npm run start:dev'
                },
                'ports': [3000, 4000],
                'icon': 'nestjs.png'
            },
            'gatsby': {
                'name': 'Gatsby',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'"gatsby"'],
                'commands': {
                    'start': 'npm run develop',
                    'build': 'npm run build',
                    'dev': 'npm run develop'
                },
                'ports': [8000, 8001],
                'icon': 'gatsby.png'
            },
            'remix': {
                'name': 'Remix',
                'type': 'fullstack',
                'files': ['package.json'],
                'content_patterns': [r'@remix-run'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [3000, 3001],
                'icon': 'remix.png'
            },
            'vite': {
                'name': 'Vite',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'"vite"'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [5173, 5174],
                'icon': 'vite.png'
            },
            'astro': {
                'name': 'Astro',
                'type': 'frontend',
                'files': ['package.json'],
                'content_patterns': [r'"astro"'],
                'commands': {
                    'start': 'npm run dev',
                    'build': 'npm run build',
                    'dev': 'npm run dev'
                },
                'ports': [3000, 4321],
                'icon': 'astro.png'
            },
            
            # Python Frameworks
            'flask': {
                'name': 'Flask',
                'type': 'backend',
                'files': ['requirements.txt', 'app.py'],
                'content_patterns': [r'flask'],
                'commands': {
                    'start': 'flask run',
                    'build': 'echo "No build needed"',
                    'dev': 'flask run'
                },
                'ports': [5000, 5001],
                'icon': 'flask.png'
            },
            'django': {
                'name': 'Django',
                'type': 'fullstack',
                'files': ['requirements.txt', 'manage.py'],
                'content_patterns': [r'django'],
                'commands': {
                    'start': 'python manage.py runserver 0.0.0.0:8000',
                    'build': 'python manage.py collectstatic --noinput',
                    'dev': 'python manage.py runserver 0.0.0.0:8000'
                },
                'ports': [8000, 8001],
                'icon': 'django.png'
            },
            'fastapi': {
                'name': 'FastAPI',
                'type': 'backend',
                'files': ['requirements.txt', 'main.py'],
                'content_patterns': [r'fastapi'],
                'commands': {
                    'start': 'uvicorn main:app --reload',
                    'build': 'echo "No build needed"',
                    'dev': 'uvicorn main:app --reload'
                },
                'ports': [8000, 8001],
                'icon': 'fastapi.png'
            },
            
            # Other Languages
            'go': {
                'name': 'Go',
                'type': 'backend',
                'files': ['main.go', 'go.mod'],
                'content_patterns': [],
                'commands': {
                    'start': 'go run main.go',
                    'build': 'go build -o app',
                    'dev': 'go run main.go'
                },
                'ports': [8080, 3000, 5000],
                'icon': 'go.png'
            },
            'rust': {
                'name': 'Rust',
                'type': 'backend',
                'files': ['Cargo.toml', 'src/main.rs'],
                'content_patterns': [],
                'commands': {
                    'start': 'cargo run',
                    'build': 'cargo build --release',
                    'dev': 'cargo run'
                },
                'ports': [8080, 3000],
                'icon': 'rust.png'
            },
            'ruby': {
                'name': 'Ruby on Rails',
                'type': 'fullstack',
                'files': ['Gemfile', 'config.ru'],
                'content_patterns': [r'rails'],
                'commands': {
                    'start': 'bundle exec rails server -b 0.0.0.0 -p 3000',
                    'build': 'bundle install',
                    'dev': 'bundle exec rails server -b 0.0.0.0 -p 3000'
                },
                'ports': [3000, 3001],
                'icon': 'ruby.png'
            },
            'php': {
                'name': 'PHP',
                'type': 'backend',
                'files': ['composer.json', 'index.php'],
                'content_patterns': [],
                'commands': {
                    'start': 'php -S 0.0.0.0:8000',
                    'build': 'composer install',
                    'dev': 'php -S 0.0.0.0:8000'
                },
                'ports': [8000, 8080],
                'icon': 'php.png'
            },
            
            # Static
            'static': {
                'name': 'Static HTML',
                'type': 'frontend',
                'files': ['index.html'],
                'content_patterns': [],
                'commands': {
                    'start': 'python -m http.server 8000',
                    'build': 'echo "No build needed"',
                    'dev': 'python -m http.server 8000'
                },
                'ports': [8000, 8080],
                'icon': 'html.png'
            }
        }
    
    def detect_framework(self, project_path: str) -> Optional[Dict]:
        """Detect the framework used in a project"""
        project_path = Path(project_path)
        
        # Check each framework
        for framework, config in self.frameworks.items():
            # Check if required files exist
            has_files = all((project_path / file).exists() for file in config['files'])
            
            if has_files:
                # If files exist, check content patterns (if any)
                match = True
                for file in config['files']:
                    file_path = project_path / file
                    if file_path.exists() and config.get('content_patterns'):
                        try:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                            for pattern in config['content_patterns']:
                                if not re.search(pattern, content, re.IGNORECASE):
                                    match = False
                                    break
                        except Exception:
                            # If we can't read the file, skip content check
                            pass
                
                if match:
                    return {**config, 'id': framework}
        
        # If no specific framework detected, check if it's a static site
        if (project_path / 'index.html').exists():
            return {**self.frameworks['static'], 'id': 'static'}
        
        return None
    
    def get_launch_command(self, framework_config: Dict, port: int) -> str:
        """Get the appropriate launch command for a framework with a specific port"""
        framework_id = framework_config['id']
        base_command = framework_config['commands']['dev']
        
        # Customize command based on framework
        if framework_id in ['react', 'nextjs', 'nuxt', 'svelte', 'sveltekit', 'vite', 'astro', 'remix']:
            # These frameworks can take PORT environment variable
            return f"PORT={port} {base_command}"
        elif framework_id == 'angular':
            # Angular uses --port flag
            return f"{base_command} --host 0.0.0.0 --port {port}"
        elif framework_id == 'express':
            # Express can use PORT environment variable
            return f"PORT={port} {base_command}"
        elif framework_id == 'nestjs':
            return f"PORT={port} {base_command}"
        elif framework_id == 'flask':
            # Flask can use --port flag or environment variable
            return f"FLASK_RUN_PORT={port} FLASK_RUN_HOST=0.0.0.0 {base_command.replace('flask run', 'flask run --host 0.0.0.0 --port ' + str(port))}"
        elif framework_id == 'django':
            # Django uses specific command format
            return f"python manage.py runserver 0.0.0.0:{port}"
        elif framework_id == 'fastapi':
            return f"PORT={port} {base_command}"
        elif framework_id == 'go':
            return f"PORT={port} {base_command}"
        elif framework_id == 'static':
            return f"cd {framework_config['project_path']} && python -m http.server {port}"
        elif framework_id == 'gatsby':
            return f"PORT={port} HOST=0.0.0.0 {base_command}"
        else:
            # Default: try with PORT environment variable
            return f"PORT={port} {base_command}"
    
    def get_framework_icon(self, framework_id: str) -> str:
        """Get the icon for a framework"""
        framework_config = self.frameworks.get(framework_id)
        if framework_config:
            return framework_config['icon']
        return 'default.png'

def main():
    """Example usage of the framework detector"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python framework_detector.py <project_path>")
        return
    
    project_path = sys.argv[1]
    detector = FrameworkDetector()
    
    framework = detector.detect_framework(project_path)
    if framework:
        print(f"Detected framework: {framework['name']}")
        print(f"Type: {framework['type']}")
        print(f"ID: {framework['id']}")
        print(f"Icon: {framework['icon']}")
        print(f"Commands: {framework['commands']}")
    else:
        print("No known framework detected")

if __name__ == "__main__":
    main()