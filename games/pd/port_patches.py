"""Web (Emscripten) patches for the Perfect Dark PC port.

The patch is stored as a unified diff (port_patches.diff, made with
`git -C pcport diff`) and applied with `git apply`; applying twice is a no-op.

usage: python -m games.pd.port_patches <pcport_dir> [--check]
"""
import os, subprocess, sys

DIFF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'port_patches.diff')


def git(tree, *args):
    return subprocess.run(['git', '-C', tree, *args], capture_output=True, text=True)


def main():
    tree = sys.argv[1]
    if git(tree, 'apply', '--check', '--reverse', DIFF).returncode == 0:
        print('port patches: already applied')
        return 0
    r = git(tree, 'apply', '--whitespace=nowarn', DIFF)
    if r.returncode:
        print('port patches: FAILED\n' + r.stderr[-2000:])
        return 1
    print('port patches: applied')
    return 0


if __name__ == '__main__':
    sys.exit(main())
