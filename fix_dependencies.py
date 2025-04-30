# save as fix_dependencies.py
import subprocess
import sys
import pkg_resources

def get_version(package_name):
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None

# Print current versions
print("Current package versions:")
for pkg in ['starlette', 'fastapi', 'uvicorn', 'otree', 'botex']:
    version = get_version(pkg)
    print(f"{pkg}: {version}")

# Install specific versions known to work with oTree
print("\nInstalling compatible versions...")
subprocess.check_call([
    sys.executable, "-m", "pip", "install",
    "starlette==0.27.0",  # This specific version works with oTree
    "fastapi==0.95.2",    # Compatible with this starlette version
    "uvicorn==0.22.0",    # Compatible with this fastapi version
])

print("\nUpdated package versions:")
for pkg in ['starlette', 'fastapi', 'uvicorn']:
    version = get_version(pkg)
    print(f"{pkg}: {version}")

print("\nNow try running the oTree server again.")