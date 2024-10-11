import re
import subprocess
import sys

def get_system_python_version():
    """Get the full Python version of the system (e.g., 3.13.0)."""
    return sys.version.split()[0]

def parse_pipfile(pipfile_path="Pipfile"):
    """Parse the Pipfile and extract the python_version and python_full_version."""
    with open(pipfile_path, "r") as file:
        pipfile_content = file.read()

    python_version_match = re.search(r'python_version\s*=\s*"([\d\.]+)"', pipfile_content)
    python_full_version_match = re.search(r'python_full_version\s*=\s*"([\d\.]+)"', pipfile_content)

    python_version = python_version_match.group(1) if python_version_match else None
    python_full_version = python_full_version_match.group(1) if python_full_version_match else None

    return pipfile_content, python_version, python_full_version

def update_pipfile(pipfile_content, python_version, new_python_full_version, pipfile_path="Pipfile"):
    """Update the Pipfile with the new python_full_version."""
    # Update the python_full_version in the Pipfile content
    updated_content = re.sub(
        r'python_full_version\s*=\s*"[\d\.]+"',
        f'python_full_version = "{new_python_full_version}"',
        pipfile_content,
    )
    
    # If python_full_version isn't present, add it to the [requires] section
    if not re.search(r'python_full_version', updated_content):
        updated_content = re.sub(
            r'(\[requires\])',
            f'\\1\npython_full_version = "{new_python_full_version}"',
            updated_content
        )

    # Write the updated content back to the Pipfile
    with open(pipfile_path, "w") as file:
        file.write(updated_content)

    print(f"Pipfile updated with python_full_version = {new_python_full_version}.")

def version_compare(v1, v2):
    """Compare two version strings v1 and v2."""
    return tuple(map(int, v1.split('.'))) >= tuple(map(int, v2.split('.')))

def main():
    system_python_version = get_system_python_version()
    print(f"System Python version: {system_python_version}")

    pipfile_content, python_version, python_full_version = parse_pipfile()

    if python_version and version_compare(system_python_version, python_version):
        print(f"Updating Pipfile: system Python version ({system_python_version}) >= required Python version ({python_version})")
        update_pipfile(pipfile_content, python_version, system_python_version)
    else:
        print(f"System Python version ({system_python_version}) is less than required Python version ({python_version}). No update needed.")

if __name__ == "__main__":
    main()
