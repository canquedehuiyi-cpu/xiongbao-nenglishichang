"""Render actual STEP face meshes with explicit camera-up and provenance."""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys


def view_pair(value):
    try:
        pair = tuple(float(part) for part in value.split(','))
        if len(pair) != 2 or not all(math.isfinite(part) for part in pair):
            raise ValueError()
        return pair
    except ValueError:
        raise argparse.ArgumentTypeError('Use finite elevation,azimuth, e.g. 25,-55.')


def render(args):
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    source = args.input.resolve(strict=True)
    if not math.isfinite(args.deflection) or args.deflection <= 0:
        raise ValueError('Deflection must be positive and finite.')
    reader = STEPControl_Reader()
    if reader.ReadFile(str(source)) != IFSelect_RetDone:
        raise RuntimeError('STEP reader rejected the file.')
    if not reader.TransferRoots():
        raise RuntimeError('No STEP roots could be transferred.')
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError('STEP contains no transferred shape.')
    mesher = BRepMesh_IncrementalMesh(shape, args.deflection)
    if not mesher.IsDone():
        raise RuntimeError('STEP meshing failed.')
    triangles, faces, unmeshed = [], [], []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face(explorer.Current())
        surface = BRepAdaptor_Surface(face)
        info = {'index': len(faces) + 1, 'type': str(surface.GetType())}
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, properties)
        info['area'] = properties.Mass()
        info['centroid'] = list(properties.CentreOfMass().Coord())
        if 'Plane' in info['type']:
            plane = surface.Plane()
            info.update(origin=list(plane.Location().Coord()),
                        normal=list(plane.Axis().Direction().Coord()))
        elif 'Cylinder' in info['type']:
            cylinder = surface.Cylinder()
            info.update(origin=list(cylinder.Location().Coord()),
                        axis=list(cylinder.Axis().Direction().Coord()), radius=cylinder.Radius())
        location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh and mesh.NbTriangles():
            points = [list(mesh.Node(i).Transformed(location.Transformation()).Coord())
                      for i in range(1, mesh.NbNodes() + 1)]
            info['meshBounds'] = [[min(point[k] for point in points),
                                   max(point[k] for point in points)] for k in range(3)]
            for i in range(1, mesh.NbTriangles() + 1):
                triangles.append([points[j - 1] for j in mesh.Triangle(i).Get()])
        else:
            unmeshed.append(info['index'])
        faces.append(info)
        explorer.Next()
    if unmeshed or not triangles:
        raise RuntimeError(f'Incomplete mesh; unmeshed faces: {unmeshed}.')
    solid_count = 0
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solid_count += 1
        explorer.Next()
    bounds = [[min(face['meshBounds'][k][0] for face in faces),
               max(face['meshBounds'][k][1] for face in faces)] for k in range(3)]
    if args.bounds:
        limits = args.bounds
        if not all(math.isfinite(v) for v in limits) or any(
                limits[2 * k] >= limits[2 * k + 1] for k in range(3)):
            raise ValueError('Bounds must be finite, with min < max for each axis.')
        bounds = [[limits[2 * k], limits[2 * k + 1]] for k in range(3)]
        triangles = [triangle for triangle in triangles if all(
            max(point[k] for point in triangle) >= bounds[k][0]
            and min(point[k] for point in triangle) <= bounds[k][1] for k in range(3))]
        if not triangles:
            raise ValueError('No mesh triangles intersect the requested bounds.')
    views = args.view or [(25, -55), (25, 125), (90, -90), (0, -90)]
    if len(views) > 12:
        raise ValueError('Use at most 12 views per image.')
    columns = min(2, len(views))
    rows = math.ceil(len(views) / columns)
    fig = plt.figure(figsize=(8 * columns, 5 * rows))
    spans = [max(hi - lo, 1e-6) for lo, hi in bounds]
    for i, (elevation, azimuth) in enumerate(views, 1):
        ax = fig.add_subplot(rows, columns, i, projection='3d')
        ax.add_collection3d(Poly3DCollection(
            triangles, facecolors=['#b4cedb'] * len(triangles), shade=True,
            edgecolors=['#455766' if args.mesh_edges else (0, 0, 0, 0)] * len(triangles),
            linewidth=0.08 if args.mesh_edges else 0,
            axlim_clip=bool(args.bounds)))
        for axis, limits in zip('xyz', bounds):
            getattr(ax, f'set_{axis}lim')(limits)
            getattr(ax, f'{axis}axis').set_major_locator(MaxNLocator(nbins=4))
        ax.set_box_aspect(spans)
        ax.set_proj_type('ortho')
        ax.view_init(elevation, azimuth, vertical_axis=args.up_axis)
        ax.set_xlabel('X (' + args.length_unit + ')')
        ax.set_ylabel('Y (' + args.length_unit + ')')
        ax.set_zlabel('Z (' + args.length_unit + ')')
        # A collapsed viewing axis has overlapping ticks in orthogonal views.
        hidden_axis = None
        if abs(abs(elevation) % 180 - 90) < 1e-8:
            hidden_axis = args.up_axis
        elif abs(elevation % 180) < 1e-8:
            horizontal_axes = {'x': ['y', 'z'], 'y': ['z', 'x'],
                               'z': ['x', 'y']}[args.up_axis]
            if abs(azimuth % 180) < 1e-8:
                hidden_axis = horizontal_axes[0]
            elif abs(abs(azimuth) % 180 - 90) < 1e-8:
                hidden_axis = horizontal_axes[1]
        if hidden_axis:
            getattr(ax, f'set_{hidden_axis}ticks')([])
            getattr(ax, f'set_{hidden_axis}label')('')
        ax.set_title(f'View {i}: elev={elevation:g}, azim={azimuth:g}, up=+{args.up_axis.upper()}')
    fig.tight_layout()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / 'views.png', dpi=150)
    plt.close(fig)
    summary = {'solidCount': solid_count, 'faceCount': len(faces),
               'faceTypes': dict(Counter(face['type'] for face in faces)),
               'surfaceArea': sum(face['area'] for face in faces), 'faces': faces}
    manifest = {'input': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'python': sys.version.split()[0], 'packages': {
                    name: importlib.metadata.version(name)
                    for name in ['cadquery-ocp', 'matplotlib', 'numpy']},
                'lengthUnitLabel': args.length_unit, 'unitVerifiedByScript': False,
                'coordinateTransform': 'identity; original STEP coordinates after reader transfer',
                'upAxis': args.up_axis, 'projection': 'orthographic', 'views': views,
                'meshEdgesShown': args.mesh_edges,
                'deflection': args.deflection, 'displayBoundsApproximate': bounds,
                'cropMode': 'triangle AABB intersection' if args.bounds else 'none',
                'displayTriangleCount': len(triangles), 'unmeshedFaces': unmeshed}
    for name, data in [('geometry.json', summary), ('render_manifest.json', manifest)]:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'solids': solid_count,
                      'faces': len(faces), 'triangles': len(triangles)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--up-axis', choices=['x', 'y', 'z'], required=True)
    parser.add_argument('--length-unit', required=True, help='Confirmed label; does not convert units.')
    parser.add_argument('--deflection', type=float, default=0.3)
    parser.add_argument('--view', type=view_pair, action='append')
    parser.add_argument('--bounds', type=float, nargs=6)
    parser.add_argument('--mesh-edges', action='store_true', help='Show triangulation edges.')
    args = parser.parse_args()
    try:
        render(args)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
