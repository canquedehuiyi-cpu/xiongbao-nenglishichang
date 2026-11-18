"""Prepare an isolated runtime, or smoke-check the selected interpreter."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def check():
    if not (3, 12) <= sys.version_info[:2] < (3, 15):
        raise RuntimeError('Use Python 3.12–3.14 for the pinned dependencies.')
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.TopLoc import TopLoc_Location
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy

    shape = BRepPrimAPI_MakeBox(1, 2, 3).Shape()
    BRepMesh_IncrementalMesh(shape, 0.1)
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    mesh = BRep_Tool.Triangulation_s(TopoDS.Face(explorer.Current()), TopLoc_Location())
    if not mesh or not mesh.NbTriangles():
        raise RuntimeError('OpenCascade mesh smoke check failed.')
    with tempfile.TemporaryDirectory(prefix='cad-render-check-') as directory:
        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')
        ax.plot([0, 1], [0, 2], [0, 3])
        ax.view_init(25, -55, vertical_axis='y')
        destination = Path(directory) / 'smoke.png'
        fig.savefig(destination)
        plt.close(fig)
        if destination.stat().st_size == 0:
            raise RuntimeError('Plot smoke check failed.')
    versions = {name: importlib.metadata.version(name)
                for name in ['cadquery-ocp', 'matplotlib', 'numpy']}
    print(json.dumps({'python': sys.version.split()[0], 'executable': sys.executable,
                      'packages': versions, 'meshAndPlot': 'passed'}, indent=2))


def setup(args):
    if not (3, 12) <= sys.version_info[:2] < (3, 15):
        raise RuntimeError('Use Python 3.12–3.14 to create this environment.')
    destination = args.venv.resolve()
    config = destination / 'pyvenv.cfg'
    if destination.exists():
        if not config.is_file():
            if any(destination.iterdir()):
                raise RuntimeError('Refusing a nonempty directory without pyvenv.cfg.')
        else:
            values = dict(line.split(' = ', 1) for line in config.read_text().splitlines()
                          if ' = ' in line)
            expected_home = Path(sys.base_prefix).resolve()
            if Path(values.get('home', '')).resolve() != expected_home:
                raise RuntimeError('Existing environment uses another Python installation.')
    venv.EnvBuilder(with_pip=True).create(destination)
    interpreter = destination / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    requirements = Path(__file__).resolve().parents[1] / 'requirements.txt'
    command = [str(interpreter), '-m', 'pip', 'install', '--only-binary=:all:',
               '-r', str(requirements)]
    if args.wheelhouse:
        wheelhouse = args.wheelhouse.resolve()
        if not wheelhouse.is_dir():
            raise RuntimeError('Wheelhouse directory does not exist.')
        command += ['--no-index', '--find-links', str(wheelhouse)]
    subprocess.run(command, check=True)
    subprocess.run([str(interpreter), str(Path(__file__).resolve()), 'check'], check=True)
    freeze = subprocess.run([str(interpreter), '-m', 'pip', 'freeze'],
                            check=True, capture_output=True, text=True)
    (destination / 'installed-requirements.txt').write_text(freeze.stdout, encoding='utf-8')
    print('Runtime ready:', interpreter)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    modes.add_parser('check')
    prepare = modes.add_parser('setup')
    prepare.add_argument('--venv', type=Path, required=True)
    prepare.add_argument('--wheelhouse', type=Path)
    args = parser.parse_args()
    try:
        check() if args.mode == 'check' else setup(args)
    except (ImportError, RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
