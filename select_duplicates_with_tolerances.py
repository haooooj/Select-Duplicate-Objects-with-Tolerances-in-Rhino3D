# coding: utf-8
import rhinoscriptsyntax as rs
import Rhino
import math
import System

def select_duplicates_with_tolerances():
    # Prompt user to select objects
    objs = rs.GetObjects("Select objects to check for duplicates", preselect=True)
    if not objs:
        print("No objects selected.")
        return

    # Prompt for distance tolerance
    distance_tol = rs.GetReal(
        "Enter distance tolerance (model units)", 
        number=rs.UnitAbsoluteTolerance(), 
        minimum=0.0)
    if distance_tol is None:
        print("No distance tolerance provided.")
        return

    # Prompt for angle tolerance (degrees)
    angle_tol_deg = rs.GetReal(
        "Enter angle tolerance (degrees)", 
        number=1.0, 
        minimum=0.0, 
        maximum=180.0)
    if angle_tol_deg is None:
        print("No angle tolerance provided.")
        return
    angle_tol_rad = math.radians(angle_tol_deg)

    # Store geometries and spatial index for efficient search
    geometries = {}
    bboxes = {}
    rtree = Rhino.Geometry.RTree()

    for i, obj_id in enumerate(objs):
        if rs.IsBlockInstance(obj_id):
            block_name = rs.BlockInstanceName(obj_id)
            xform = rs.BlockInstanceXform(obj_id)
            geo = rs.coercegeometry(obj_id)
            bbox = geo.GetBoundingBox(True)
            geometries[i] = (obj_id, ("block", block_name, xform))
            bboxes[i] = bbox
            rtree.Insert(bbox, i)
            continue
        geom = rs.coercegeometry(obj_id)
        if isinstance(geom, Rhino.Geometry.Extrusion):
            geom = geom.ToBrep()
        bbox = geom.GetBoundingBox(True)
        geometries[i] = (obj_id, geom)
        bboxes[i] = bbox
        rtree.Insert(bbox, i)

    def expand_bbox(bbox, tol):
        minpt = Rhino.Geometry.Point3d(bbox.Min.X-tol, bbox.Min.Y-tol, bbox.Min.Z-tol)
        maxpt = Rhino.Geometry.Point3d(bbox.Max.X+tol, bbox.Max.Y+tol, bbox.Max.Z+tol)
        return Rhino.Geometry.BoundingBox(minpt, maxpt)

    pairs = set()
    def make_callback(index_a):
        def rtree_callback(sender, e):
            if e.Id != index_a:
                pair = (min(index_a, e.Id), max(index_a, e.Id))
                pairs.add(pair)
        return rtree_callback

    for idx in geometries:
        search_bbox = expand_bbox(bboxes[idx], distance_tol)
        rtree.Search(search_bbox, System.EventHandler[Rhino.Geometry.RTreeEventArgs](make_callback(idx)))

    # Functions for geometry deviation calculation
    def curve_deviation(c1, c2):
        domain1, domain2 = c1.Domain, c2.Domain
        sample_count = 20
        max_dist, max_angle = 0.0, 0.0
        for i in range(sample_count + 1):
            t_norm = i / float(sample_count)
            t1 = domain1.ParameterAt(t_norm)
            t2 = domain2.ParameterAt(t_norm)
            p1 = c1.PointAt(t1)
            p2 = c2.PointAt(t2)
            dist = p1.DistanceTo(p2)
            tan1 = c1.TangentAt(t1)
            tan2 = c2.TangentAt(t2)
            angle = Rhino.Geometry.Vector3d.VectorAngle(tan1, tan2)
            if dist > max_dist:
                max_dist = dist
            if angle > max_angle:
                max_angle = angle
        return max_dist, max_angle

    def brep_deviation(b1, b2):
        bbox1, bbox2 = b1.GetBoundingBox(True), b2.GetBoundingBox(True)
        if (
            bbox1.Min.X > bbox2.Max.X + distance_tol or bbox1.Max.X < bbox2.Min.X - distance_tol or
            bbox1.Min.Y > bbox2.Max.Y + distance_tol or bbox1.Max.Y < bbox2.Min.Y - distance_tol or
            bbox1.Min.Z > bbox2.Max.Z + distance_tol or bbox1.Max.Z < bbox2.Min.Z - distance_tol
        ):
            return float("inf"), float("inf")
        faces1, faces2 = b1.Faces, b2.Faces
        count = min(faces1.Count, faces2.Count)
        u_count = v_count = 5
        max_dist, max_angle = 0.0, 0.0
        for f in range(count):
            fa, fb = faces1[f], faces2[f]
            dom_u_a, dom_v_a = fa.Domain(0), fa.Domain(1)
            dom_u_b, dom_v_b = fb.Domain(0), fb.Domain(1)
            for i in range(u_count+1):
                for j in range(v_count+1):
                    ur = i / float(u_count)
                    vr = j / float(v_count)
                    ua = dom_u_a.ParameterAt(ur)
                    va = dom_v_a.ParameterAt(vr)
                    ub = dom_u_b.ParameterAt(ur)
                    vb = dom_v_b.ParameterAt(vr)
                    pa, pb = fa.PointAt(ua, va), fb.PointAt(ub, vb)
                    na, nb = fa.NormalAt(ua, va), fb.NormalAt(ub, vb)
                    dist = pa.DistanceTo(pb)
                    angle = Rhino.Geometry.Vector3d.VectorAngle(na, nb)
                    if dist > max_dist:
                        max_dist = dist
                    if angle > max_angle:
                        max_angle = angle
        return max_dist, max_angle

    def is_same_block(name_a, xform_a, name_b, xform_b, pos_tol, angle_tol_rad):
        if name_a != name_b:
            return False
        # Compare origins (insertion point)
        origin_a = Rhino.Geometry.Point3d(xform_a.M03, xform_a.M13, xform_a.M23)
        origin_b = Rhino.Geometry.Point3d(xform_b.M03, xform_b.M13, xform_b.M23)
        if origin_a.DistanceTo(origin_b) > pos_tol:
            return False
        # Compare orientation (main axis, simplified)
        vec_a = Rhino.Geometry.Vector3d(xform_a.M00, xform_a.M10, xform_a.M20)
        vec_b = Rhino.Geometry.Vector3d(xform_b.M00, xform_b.M10, xform_b.M20)
        angle = Rhino.Geometry.Vector3d.VectorAngle(vec_a, vec_b)
        if angle > angle_tol_rad:
            return False
        return True

    # Evaluate potential duplicate pairs
    duplicate_ids = set()
    for idx1, idx2 in pairs:
        id1, geom1 = geometries[idx1]
        id2, geom2 = geometries[idx2]
        if id1 in duplicate_ids or id2 in duplicate_ids:
            continue
        # Block to Block comparison
        if (
            isinstance(geom1, tuple) and geom1[0] == "block" and
            isinstance(geom2, tuple) and geom2[0] == "block"
        ):
            name_a, xform_a = geom1[1], geom1[2]
            name_b, xform_b = geom2[1], geom2[2]
            if is_same_block(name_a, xform_a, name_b, xform_b, distance_tol, angle_tol_rad):
                duplicate_ids.add(id2)
            continue
        # Regular geometry comparison
        if (
            not isinstance(geom1, tuple) and not isinstance(geom2, tuple) and
            (type(geom1) == type(geom2) or (isinstance(geom1, Rhino.Geometry.Brep) and isinstance(geom2, Rhino.Geometry.Brep)))
        ):
            if isinstance(geom1, Rhino.Geometry.Point):
                if geom1.Location.DistanceTo(geom2.Location) <= distance_tol:
                    duplicate_ids.add(id2)
            elif isinstance(geom1, Rhino.Geometry.Curve):
                d, a = curve_deviation(geom1, geom2)
                if d <= distance_tol and a <= angle_tol_rad:
                    duplicate_ids.add(id2)
            elif isinstance(geom1, Rhino.Geometry.Brep):
                d, a = brep_deviation(geom1, geom2)
                if d <= distance_tol and a <= angle_tol_rad:
                    duplicate_ids.add(id2)
            else:
                continue
        else:
            continue

    # Select duplicates
    if duplicate_ids:
        rs.UnselectAllObjects()
        rs.SelectObjects(list(duplicate_ids))
        print("Selected {} duplicate object(s) within the specified tolerances.".format(len(duplicate_ids)))
    else:
        print("No duplicates found within the specified tolerances.")

if __name__ == "__main__":
    select_duplicates_with_tolerances()
