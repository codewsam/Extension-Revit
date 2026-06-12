# -*- coding: utf-8 -*-
__title__ = "Cotas Automaticas de Familias(em construção)"
__version__ = "2.9"
__doc__ = (
  
)

# ============================================================
# IMPORTS
# ============================================================
from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, Options,
    LocationCurve, Solid, PlanarFace, ReferenceArray, Line, XYZ,
    Transaction, DimensionType, UnitUtils, FamilyInstanceReferenceType,
)

try:
    from Autodesk.Revit.DB import UnitTypeId
    def to_ft(cm):
        return UnitUtils.ConvertToInternalUnits(cm, UnitTypeId.Centimeters)
    def to_cm(ft):
        return UnitUtils.ConvertFromInternalUnits(ft, UnitTypeId.Centimeters)
except ImportError:
    from Autodesk.Revit.DB import DisplayUnitType
    def to_ft(cm):
        return UnitUtils.ConvertToInternalUnits(cm, DisplayUnitType.DUT_CENTIMETERS)
    def to_cm(ft):
        return UnitUtils.ConvertFromInternalUnits(ft, DisplayUnitType.DUT_CENTIMETERS)

from pyrevit import revit, forms, script
import math

# ============================================================
# Globals
# ============================================================
doc    = revit.doc
uidoc  = revit.uidoc
output = script.get_output()

TOL_DIM_ZERO = to_ft(1.0)   # 1 cm

# ============================================================
# ETAPA 1 - Vista ativa
# ============================================================
view = doc.ActiveView
output.print_md("## Cotas Automaticas v2.9 - **{}**".format(view.Name))

if view.ViewType.ToString() not in ("Elevation", "Section"):
    forms.alert(
        "Esta ferramenta funciona em vistas de Elevacao ou Corte.\n"
        "Vista atual: {} ({})".format(view.Name, view.ViewType),
        exitscript=True,
    )

right    = view.RightDirection
up       = view.UpDirection
view_dir = view.ViewDirection

# ============================================================
# ETAPA 2 - Elementos na vista
# ============================================================
def collect_category(cat_id):
    return list(
        FilteredElementCollector(doc, view.Id)
        .OfCategory(cat_id)
        .WhereElementIsNotElementType()
        .ToElements()
    )

walls    = collect_category(BuiltInCategory.OST_Walls)
doors    = collect_category(BuiltInCategory.OST_Doors)
windows  = collect_category(BuiltInCategory.OST_Windows)
openings = doors + windows

output.print_md("**Paredes:** {} | **Portas:** {} | **Janelas:** {}".format(
    len(walls), len(doors), len(windows)
))

if not walls:
    forms.alert("Nenhuma parede encontrada na vista ativa.", exitscript=True)

# ============================================================
# HELPERS
# ============================================================
def dot(a, b):
    return a.X * b.X + a.Y * b.Y + a.Z * b.Z

def pts_close(p1, p2, tol_ft=None):
    tol_ft = tol_ft or to_ft(2.0)
    dx = p1.X - p2.X; dy = p1.Y - p2.Y; dz = p1.Z - p2.Z
    return math.sqrt(dx*dx + dy*dy + dz*dz) < tol_ft

def get_wall_dir(wall):
    loc = wall.Location
    if not isinstance(loc, LocationCurve):
        return None, None, None
    c = loc.Curve
    p0 = c.GetEndPoint(0)
    p1 = c.GetEndPoint(1)
    raw = p1 - p0
    if raw.GetLength() < 1e-9:
        return None, None, None
    return raw.Normalize(), p0, p1

def classify_wall(wall):
    d, p0, p1 = get_wall_dir(wall)
    if d is None:
        return None, None, None, None
    d_right = abs(dot(d, right))
    d_up    = abs(dot(d, up))
    d_depth = abs(dot(d, view_dir))
    if d_right >= d_up and d_right >= d_depth:
        return "H", d, p0, p1
    elif d_up >= d_right and d_up >= d_depth:
        return "V", d, p0, p1
    return "D", d, p0, p1

def faces_by_axis(element, axis_dir, threshold=0.8):
    opt = Options()
    opt.ComputeReferences = True
    result = []
    for g in element.get_Geometry(opt):
        if not isinstance(g, Solid) or g.Volume <= 0:
            continue
        for face in g.Faces:
            if face.Reference is None or not isinstance(face, PlanarFace):
                continue
            d = dot(face.FaceNormal, axis_dir)
            if abs(d) > threshold:
                pos = dot(face.Origin, axis_dir)
                result.append((d, pos, face.Reference))
    return result

def filter_zero_segments(pairs):
    if not pairs:
        return []
    accepted = [pairs[0]]
    for val, ref in pairs[1:]:
        diff = abs(val - accepted[-1][0])
        if diff > TOL_DIM_ZERO:
            accepted.append((val, ref))
        else:
            output.print_md("  [FILTRO] dist={:.2f}cm descartada".format(to_cm(diff)))
    return accepted

# ============================================================
# HELPERS DE ABERTURA
# ============================================================
def get_opening_refs_lr(opening):
    """Retorna (ref_left, r_left, ref_right, r_right) via GetReferences."""
    try:
        rl = opening.GetReferences(FamilyInstanceReferenceType.Left)
        rr = opening.GetReferences(FamilyInstanceReferenceType.Right)
        if not rl or not rr:
            return None
        bb = opening.get_BoundingBox(view) or opening.get_BoundingBox(None)
        if bb is None:
            return None
        r_l = dot(bb.Min, right)
        r_r = dot(bb.Max, right)
        if r_l > r_r:
            r_l, r_r = r_r, r_l
        return (rl[0], r_l, rr[0], r_r)
    except Exception as e:
        output.print_md("  [WARN] refs_lr [{}]: {}".format(opening.Id.IntegerValue, e))
        return None

def get_opening_ref_top(opening):
    """Retorna (ref_top, u_top) via GetReferences."""
    try:
        rt = opening.GetReferences(FamilyInstanceReferenceType.Top)
        if not rt:
            return None
        bb = opening.get_BoundingBox(view) or opening.get_BoundingBox(None)
        u_top = dot(bb.Max, up) if bb else None
        return (rt[0], u_top)
    except Exception as e:
        output.print_md("  [WARN] ref_top [{}]: {}".format(opening.Id.IntegerValue, e))
        return None

def get_host_bottom_ref(opening):
    """Face inferior da parede hospedeira — usada como base do vao na cota de altura."""
    try:
        host = opening.Host
        if host is None:
            return None
        opt = Options()
        opt.ComputeReferences = True
        best = None
        for g in host.get_Geometry(opt):
            if not isinstance(g, Solid) or g.Volume <= 0:
                continue
            for face in g.Faces:
                if not isinstance(face, PlanarFace) or face.Reference is None:
                    continue
                if dot(face.FaceNormal, up) < -0.8:
                    pos = dot(face.Origin, up)
                    if best is None or pos < best[0]:
                        best = (pos, face.Reference)
        return best
    except Exception as e:
        output.print_md("  [WARN] host_bottom [{}]: {}".format(opening.Id.IntegerValue, e))
        return None

# ============================================================
# COLETA refs_h — SO faces de parede (sem mistura com aberturas)
# ============================================================
refs_h_pairs = []
pts_h        = []

for wall in walls:
    orient, _, p0, p1 = classify_wall(wall)
    if orient is None:
        continue
    faces = faces_by_axis(wall, right)
    pos_faces = [(pos, ref) for (d, pos, ref) in faces if d > 0]
    neg_faces = [(pos, ref) for (d, pos, ref) in faces if d < 0]
    pt_left   = p0 if dot(p0, right) <= dot(p1, right) else p1
    pt_right  = p1 if pt_left is p0 else p0

    if neg_faces:
        ref_neg = min(neg_faces, key=lambda x: x[0])
        if not any(pts_close(pt_left, ep) for ep in pts_h):
            refs_h_pairs.append((ref_neg[0], ref_neg[1]))
            pts_h.append(pt_left)

    if pos_faces:
        ref_pos = max(pos_faces, key=lambda x: x[0])
        if not any(pts_close(pt_right, ep) for ep in pts_h):
            refs_h_pairs.append((ref_pos[0], ref_pos[1]))
            pts_h.append(pt_right)

refs_h_pairs.sort(key=lambda x: x[0])
refs_h_pairs = filter_zero_segments(refs_h_pairs)
refs_h = [r for _, r in refs_h_pairs]
output.print_md("**Refs horiz. (paredes):** {}".format(len(refs_h)))

# ============================================================
# COLETA refs_v — faces topo e base das paredes
# ============================================================
refs_v_pairs = []
z_vals_seen  = []
TOL_Z = to_ft(0.5)

def z_already(z_val):
    return any(abs(z_val - zv) < TOL_Z for zv in z_vals_seen)

for wall in walls:
    orient, _, p0, p1 = classify_wall(wall)
    if orient is None:
        continue
    faces = faces_by_axis(wall, up)
    pos_faces = [(pos, ref) for (d, pos, ref) in faces if d > 0]
    neg_faces = [(pos, ref) for (d, pos, ref) in faces if d < 0]

    if pos_faces:
        z_top, ref_top = max(pos_faces, key=lambda x: x[0])
        if not z_already(z_top):
            refs_v_pairs.append((z_top, ref_top))
            z_vals_seen.append(z_top)

    if neg_faces:
        z_bot, ref_bot = min(neg_faces, key=lambda x: x[0])
        if not z_already(z_bot):
            refs_v_pairs.append((z_bot, ref_bot))
            z_vals_seen.append(z_bot)

refs_v_pairs.sort(key=lambda x: x[0])
refs_v_pairs = filter_zero_segments(refs_v_pairs)
refs_v = [r for _, r in refs_v_pairs]
output.print_md("**Refs vert. (paredes):** {}".format(len(refs_v)))

# ============================================================
# BUILDERS DE LINHA DE COTA
# ============================================================
def _wall_center():
    pts = []
    for w in walls:
        bb = w.get_BoundingBox(None)
        if bb:
            pts.append(XYZ((bb.Min.X+bb.Max.X)/2, (bb.Min.Y+bb.Max.Y)/2, (bb.Min.Z+bb.Max.Z)/2))
    if not pts:
        return 0.0, 0.0
    return (sum(p.Y for p in pts)/len(pts), sum(p.Z for p in pts)/len(pts))

def build_dim_line_h(r_vals, offset_cm=60.0):
    if not r_vals:
        return None
    y_avg, z_avg = _wall_center()
    offset_ft = to_ft(offset_cm)
    r_min = min(r_vals) - to_ft(30)
    r_max = max(r_vals) + to_ft(30)
    def mpt(r):
        return XYZ(
            right.X*r + up.X*(z_avg+offset_ft),
            right.Y*r + up.Y*(z_avg+offset_ft) + y_avg*(1-abs(right.Y)),
            right.Z*r + up.Z*(z_avg+offset_ft),
        )
    pt1, pt2 = mpt(r_min), mpt(r_max)
    return Line.CreateBound(pt1, pt2) if pt1.DistanceTo(pt2) > 1e-6 else None

def build_dim_line_v(z_vals, offset_cm=60.0):
    if not z_vals:
        return None
    offset_ft = to_ft(offset_cm)
    all_bb = [w.get_BoundingBox(None) for w in walls if w.get_BoundingBox(None)]
    if not all_bb:
        return None
    cx = sum((b.Min.X+b.Max.X)/2 for b in all_bb) / len(all_bb)
    cy = sum((b.Min.Y+b.Max.Y)/2 for b in all_bb) / len(all_bb)
    base_r = dot(XYZ(cx, cy, 0), right) + offset_ft
    def mpt(u):
        return XYZ(right.X*base_r+up.X*u, right.Y*base_r+up.Y*u, right.Z*base_r+up.Z*u)
    pt1 = mpt(min(z_vals)-to_ft(30))
    pt2 = mpt(max(z_vals)+to_ft(30))
    return Line.CreateBound(pt1, pt2) if pt1.DistanceTo(pt2) > 1e-6 else None

def build_opening_line_h(opening, offset_cm=35.0):
    """Linha horizontal acima do vao para cota de largura."""
    bb = opening.get_BoundingBox(view) or opening.get_BoundingBox(None)
    if not bb:
        return None
    offset_ft = to_ft(offset_cm)
    r_min = dot(bb.Min, right)
    r_max = dot(bb.Max, right)
    u_top = dot(bb.Max, up)
    y_mid = (bb.Min.Y+bb.Max.Y)/2.0
    def mpt(r):
        u = u_top + offset_ft
        return XYZ(right.X*r+up.X*u, right.Y*r+up.Y*u+y_mid*(1-abs(right.Y)), right.Z*r+up.Z*u)
    pt1 = mpt(r_min - to_ft(5))
    pt2 = mpt(r_max + to_ft(5))
    return Line.CreateBound(pt1, pt2) if pt1.DistanceTo(pt2) > 1e-6 else None

def build_opening_line_v(opening, offset_cm=35.0):
    """Linha vertical lateral ao vao para cota de altura."""
    bb = opening.get_BoundingBox(view) or opening.get_BoundingBox(None)
    if not bb:
        return None
    offset_ft = to_ft(offset_cm)
    u_min = dot(bb.Min, up)
    u_max = dot(bb.Max, up)
    r_pos = dot(bb.Max, right) + offset_ft
    def mpt(u):
        return XYZ(right.X*r_pos+up.X*u, right.Y*r_pos+up.Y*u, right.Z*r_pos+up.Z*u)
    pt1 = mpt(u_min - to_ft(5))
    pt2 = mpt(u_max + to_ft(5))
    return Line.CreateBound(pt1, pt2) if pt1.DistanceTo(pt2) > 1e-6 else None

# ============================================================
# Tipo de cota
# ============================================================
dim_type = None
try:
    dtypes = list(FilteredElementCollector(doc).OfClass(DimensionType).ToElements())
    if dtypes:
        dim_type = dtypes[0]
except Exception:
    pass

def apply_dim_type(dim):
    if dim_type:
        try:
            dim.DimensionType = dim_type
        except Exception:
            pass

# ============================================================
# CRIAR COTAS
# ============================================================
dims_created = 0
errors       = 0

with Transaction(doc, "Cotas Automaticas v2.9") as t:
    t.Start()
    try:

        # ── Cota horizontal principal: SO faces de parede ──
        if len(refs_h) >= 2:
            r_vals = [v for v, _ in refs_h_pairs]
            dim_line = build_dim_line_h(r_vals, offset_cm=60.0)
            if dim_line:
                ra = ReferenceArray()
                for r in refs_h:
                    ra.Append(r)
                try:
                    new_dim = doc.Create.NewDimension(view, dim_line, ra)
                    apply_dim_type(new_dim)
                    dims_created += 1
                    output.print_md("Cota horizontal principal: **{}** refs".format(ra.Size))
                except Exception as e:
                    errors += 1
                    output.print_md("Erro cota horizontal: `{}`".format(e))
        else:
            output.print_md("Menos de 2 refs horizontais.")

        # ── Cota vertical principal: SO faces de parede ──
        if len(refs_v) >= 2:
            z_vals = [v for v, _ in refs_v_pairs]
            dim_line = build_dim_line_v(z_vals, offset_cm=60.0)
            if dim_line:
                ra = ReferenceArray()
                for r in refs_v:
                    ra.Append(r)
                try:
                    new_dim = doc.Create.NewDimension(view, dim_line, ra)
                    apply_dim_type(new_dim)
                    dims_created += 1
                    output.print_md("Cota vertical principal: **{}** refs".format(ra.Size))
                except Exception as e:
                    errors += 1
                    output.print_md("Erro cota vertical: `{}`".format(e))
        else:
            output.print_md("Menos de 2 refs verticais.")

        # ── Cotas individuais de vao ──
        created_op = 0
        for op in openings:
            op_id = op.Id.IntegerValue
            try:
                # Largura: GetReferences(Left) + GetReferences(Right) — isolados
                lr = get_opening_refs_lr(op)
                if lr:
                    ref_l, r_l, ref_r, r_r = lr
                    if abs(r_r - r_l) > TOL_DIM_ZERO:
                        dim_line = build_opening_line_h(op, offset_cm=35.0)
                        if dim_line:
                            ra = ReferenceArray()
                            ra.Append(ref_l)
                            ra.Append(ref_r)
                            try:
                                new_dim = doc.Create.NewDimension(view, dim_line, ra)
                                apply_dim_type(new_dim)
                                created_op += 1
                                output.print_md("  Largura [{}]: {:.1f}cm".format(
                                    op_id, to_cm(abs(r_r - r_l))))
                            except Exception as e:
                                errors += 1
                                output.print_md("  Erro largura [{}]: `{}`".format(op_id, e))

                # Altura: face base parede hospedeira + GetReferences(Top)
                # (face do host + ref da familia filha — combinacao aceita pelo Revit)
                top    = get_opening_ref_top(op)
                bot    = get_host_bottom_ref(op)
                if top and bot:
                    ref_top, u_top = top
                    u_bot, ref_bot = bot
                    if u_top is not None and abs(u_top - u_bot) > TOL_DIM_ZERO:
                        dim_line = build_opening_line_v(op, offset_cm=35.0)
                        if dim_line:
                            ra = ReferenceArray()
                            ra.Append(ref_bot)
                            ra.Append(ref_top)
                            try:
                                new_dim = doc.Create.NewDimension(view, dim_line, ra)
                                apply_dim_type(new_dim)
                                created_op += 1
                                output.print_md("  Altura [{}]: {:.1f}cm".format(
                                    op_id, to_cm(abs(u_top - u_bot))))
                            except Exception as e:
                                errors += 1
                                output.print_md("  Erro altura [{}]: `{}`".format(op_id, e))
                else:
                    if not top:
                        output.print_md("  [{}] sem ref Top".format(op_id))
                    if not bot:
                        output.print_md("  [{}] sem face base da parede hospedeira".format(op_id))

            except Exception as e:
                errors += 1
                output.print_md("Erro abertura [{}]: `{}`".format(op_id, e))

        if created_op:
            dims_created += created_op
            output.print_md("Cotas de vaos: **{}**".format(created_op))
        else:
            output.print_md("Nenhuma cota de vao criada.")

        t.Commit()

    except Exception as e:
        t.RollBack()
        forms.alert("Erro na transacao:\n{}".format(str(e)))

# ============================================================
# RESUMO
# ============================================================
output.print_md("---")
output.print_md("## Concluido! (v2.9)")
output.print_md("- **Cotas criadas:** {}".format(dims_created))
output.print_md("- **Erros:** {}".format(errors))
output.print_md("- **Paredes:** {} | **Aberturas:** {}".format(len(walls), len(openings)))