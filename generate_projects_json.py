import os
import json
import re
from pathlib import Path
import time
import requests
import subprocess
import shutil
from datetime import datetime

# Import our framework detection module
try:
    from framework_detector import FrameworkDetector
except ImportError:
    # Fallback to basic detection if the module isn't available
    class FrameworkDetector:
        def detect_framework(self, project_path):
            # Basic fallback detection
            project_path = Path(project_path)
            
            # Check for package.json frameworks
            if (project_path / 'package.json').exists():
                try:
                    with open(project_path / 'package.json', 'r') as f:
                        content = f.read().lower()
                        if 'react' in content:
                            return {'name': 'React', 'id': 'react', 'icon': 'react.png', 'type': 'frontend'}
                        elif 'vue' in content:
                            return {'name': 'Vue.js', 'id': 'vue', 'icon': 'vue.png', 'type': 'frontend'}
                        elif 'angular' in content:
                            return {'name': 'Angular', 'id': 'angular', 'icon': 'angular.png', 'type': 'frontend'}
                        elif 'next' in content:
                            return {'name': 'Next.js', 'id': 'nextjs', 'icon': 'nextjs.png', 'type': 'fullstack'}
                        elif 'nuxt' in content:
                            return {'name': 'Nuxt.js', 'id': 'nuxt', 'icon': 'nuxt.png', 'type': 'fullstack'}
                    return {'name': 'Node.js', 'id': 'node', 'icon': 'node.png', 'type': 'backend'}
                except:
                    pass
            
            # Check for Python files
            if (project_path / 'requirements.txt').exists() or (project_path / 'app.py').exists():
                try:
                    if (project_path / 'requirements.txt').exists():
                        with open(project_path / 'requirements.txt', 'r') as f:
                            content = f.read().lower()
                            if 'flask' in content:
                                return {'name': 'Flask', 'id': 'flask', 'icon': 'flask.png', 'type': 'backend'}
                            elif 'django' in content:
                                return {'name': 'Django', 'id': 'django', 'icon': 'django.png', 'type': 'fullstack'}
                    return {'name': 'Python', 'id': 'python', 'icon': 'python.png', 'type': 'backend'}
                except:
                    pass
            
            # Default to static if index.html exists
            if (project_path / 'index.html').exists():
                return {'name': 'Static HTML', 'id': 'html', 'icon': 'html.png', 'type': 'frontend'}
            
            return {'name': 'Unknown', 'id': 'unknown', 'icon': 'default.png', 'type': 'unknown'}

# Load project type configuration
def load_project_config():
    config = []
    try:
        with open('project_types.conf', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        config.append({
                            'pattern': parts[0],
                            'type': parts[1],
                            'icon': parts[2],
                            'framework': parts[1] if len(parts) > 3 else parts[1]  # Additional framework info
                        })
    except FileNotFoundError:
        # Default configuration if file doesn't exist
        config = [
            {'pattern': 'package.json:.*react', 'type': 'react', 'icon': 'react.png', 'framework': 'react'},
            {'pattern': 'package.json:.*vue', 'type': 'vue', 'icon': 'vue.png', 'framework': 'vue'}, 
            {'pattern': 'package.json:.*angular', 'type': 'angular', 'icon': 'angular.png', 'framework': 'angular'},
            {'pattern': 'package.json:.*next', 'type': 'nextjs', 'icon': 'nextjs.png', 'framework': 'nextjs'},
            {'pattern': 'package.json:.*nuxt', 'type': 'nuxt', 'icon': 'nuxt.png', 'framework': 'nuxt'},
            {'pattern': 'package.json:.*svelte', 'type': 'svelte', 'icon': 'svelte.png', 'framework': 'svelte'},
            {'pattern': 'package.json:.*gatsby', 'type': 'gatsby', 'icon': 'gatsby.png', 'framework': 'gatsby'},
            {'pattern': 'package.json:.*express', 'type': 'express', 'icon': 'express.png', 'framework': 'express'},
            {'pattern': 'package.json:.*nestjs', 'type': 'nestjs', 'icon': 'nestjs.png', 'framework': 'nestjs'},
            {'pattern': 'requirements.txt', 'type': 'python', 'icon': 'python.png', 'framework': 'python'},
            {'pattern': 'app.py', 'type': 'flask', 'icon': 'flask.png', 'framework': 'flask'},
            {'pattern': 'Dockerfile', 'type': 'docker', 'icon': 'docker.png', 'framework': 'docker'},
            {'pattern': 'docker-compose.yml', 'type': 'docker-compose', 'icon': 'docker.png', 'framework': 'docker'},
            {'pattern': 'main.py', 'type': 'python', 'icon': 'python.png', 'framework': 'python'},
            {'pattern': 'index.html', 'type': 'html', 'icon': 'html.png', 'framework': 'html'},
            {'pattern': 'main.go', 'type': 'go', 'icon': 'go.png', 'framework': 'go'},
            {'pattern': 'Cargo.toml', 'type': 'rust', 'icon': 'rust.png', 'framework': 'rust'},
            {'pattern': 'go.mod', 'type': 'go', 'icon': 'go.png', 'framework': 'go'},
            {'pattern': 'Gemfile', 'type': 'ruby', 'icon': 'ruby.png', 'framework': 'ruby'},
            {'pattern': 'composer.json', 'type': 'php', 'icon': 'php.png', 'framework': 'php'},
        ]
    return config

def get_project_metadata(project_path):
    """Get additional project metadata like dependencies, size, etc."""
    metadata = {
        'dependencies': [],
        'size': 0,
        'last_build_time': None,
        'preview_image': None,
        'framework_details': None
    }
    
    try:
        # Calculate directory size
        for dirpath, dirnames, filenames in os.walk(project_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    metadata['size'] += os.path.getsize(filepath)
                except OSError:
                    pass  # Skip files that can't be accessed
        
        # Get dependencies based on project type
        if (project_path / 'package.json').exists():
            try:
                with open(project_path / 'package.json', 'r') as f:
                    package_data = json.load(f)
                    deps = package_data.get('dependencies', {})
                    dev_deps = package_data.get('devDependencies', {})
                    all_deps = {**deps, **dev_deps}
                    metadata['dependencies'] = list(all_deps.keys())[:10]  # Limit to first 10
            except Exception:
                pass
        elif (project_path / 'requirements.txt').exists():
            try:
                with open(project_path / 'requirements.txt', 'r') as f:
                    lines = f.readlines()
                    deps = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dep = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0]
                            deps.append(dep)
                    metadata['dependencies'] = deps[:10]  # Limit to first 10
            except Exception:
                pass
                
        # Check for preview image
        for img_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            for img_name in ['preview', 'screenshot', 'thumbnail', 'image', 'logo', 'demo']:
                img_path = project_path / f"{img_name}{img_ext}"
                if img_path.exists():
                    metadata['preview_image'] = f"previews/{project_path.name}_{img_name}{img_ext}"
                    break
            if metadata['preview_image']:
                break
                
    except Exception as e:
        print(f"Error getting metadata for {project_path}: {e}")
    
    return metadata

def main():
    workspace = Path('.')
    projects = []
    
    # Initialize framework detector
    detector = FrameworkDetector()

    # Fetch running projects status from launch server
    running_projects = {}
    try:
        response = requests.get('http://localhost:6110/status')
        if response.status_code == 200:
            running_projects = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching running projects status: {e}")
        # Continue without running project info if fetch fails

    for entry in workspace.iterdir():
        if entry.is_dir() and not entry.name.startswith('.'):
            # Use advanced framework detection
            framework_info = detector.detect_framework(str(entry))
            
            # Get project metadata
            metadata = get_project_metadata(entry)
            
            # Get last modified time
            last_modified = entry.stat().st_mtime
            # Get creation time (on systems that support it)
            try:
                creation_time = entry.stat().st_ctime
            except AttributeError:
                creation_time = last_modified  # Fallback on systems that don't have creation time

            # Determine icon based on detected framework
            if framework_info and 'icon' in framework_info:
                icon = framework_info['icon']
            else:
                icon = 'default.png'
            
            project_info = {
                'name': entry.name,
                'path': str(entry),
                'type': framework_info['id'] if framework_info else 'unknown',
                'framework': framework_info['name'] if framework_info else 'Unknown',
                'framework_details': framework_info,
                'icon': icon,
                'description': get_description(entry),
                'last_modified': last_modified,
                'created': creation_time,
                'size': metadata['size'],
                'dependencies': metadata['dependencies'],
                'preview_image': metadata['preview_image'],
                'status': 'stopped'  # Default status
            }

            # Add port and url if the project is running
            str_entry = str(entry)
            if str_entry in running_projects:
                project_info['port'] = running_projects[str_entry].get('port')
                project_info['url'] = running_projects[str_entry].get('url')
                project_info['status'] = 'running'

            projects.append(project_info)

    # Sort projects by last modified time (newest first)
    projects.sort(key=lambda x: x['last_modified'], reverse=True)

    with open('projects.json', 'w') as f:
        json.dump(projects, f, indent=2)

def get_description(project_path):
    """Get project description from README or other documentation files."""
    # Check for README.md
    readme = project_path / 'README.md'
    if readme.exists():
        try:
            with open(readme, 'r', encoding='utf-8') as f:
                content = f.read(500)  # First 500 characters
                # Remove markdown formatting and URLs
                content = re.sub(r'<[^>]*>', '', content)  # Remove HTML tags
                content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)  # Remove markdown links
                content = re.sub(r'#+\s*', '', content)  # Remove markdown headers
                content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)  # Remove code blocks
                content = re.sub(r'`.*?`', '', content)  # Remove inline code
                content = re.sub(r'https?://\S+', '', content)  # Remove URLs
                content = re.sub(r'\n\s*\n', '\n', content)  # Remove extra newlines
                return content.strip()[:250]  # Limit to 250 chars
        except Exception:
            pass
    
    # Check for other documentation files
    for doc_file in ['DESCRIPTION', 'README.txt', 'info.txt', 'about.txt']:
        doc_path = project_path / doc_file
        if doc_path.exists():
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    return f.read(250).strip()  # First 250 characters
            except Exception:
                pass
    
    # Check for package.json description
    if (project_path / 'package.json').exists():
        try:
            with open(project_path / 'package.json', 'r') as f:
                package_data = json.load(f)
                desc = package_data.get('description')
                if desc:
                    return desc[:250]  # Limit to 250 chars
        except Exception:
            pass
    
    # Check for Python __init__.py docstring
    if (project_path / '__init__.py').exists():
        try:
            with open(project_path / '__init__.py', 'r', encoding='utf-8') as f:
                content = f.read(1000)
                # Look for module docstring
                match = re.search(r'("""|\'\'\')(.*?)(\1)', content, re.DOTALL)
                if match:
                    docstring = match.group(2).strip()
                    return docstring[:250]  # Limit to 250 chars
        except Exception:
            pass
    
    return None

if __name__ == '__main__':
    main()