# -*- coding: utf-8 -*-
"""
Monoposto Formula 1 Moderna ad Altissimo Dettaglio (Esterni Aerodinamici Curvilinei + Interni Cockpit Completi)
Progettato da zero per Blender 5.2 LTS.
Genera:
  - File progetto: f1_macchina_bella.blend
  - Video 10 secondi (300 frame a 30 fps): f1_showcase_10s.mp4
  - Render di anteprima ad alta risoluzione
"""

import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Euler, Matrix

CARTELLA = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ARG = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SOLO_PREVIEW = "--preview" in ARG

# ============================ 1. PULIZIA E IMPOSTAZIONE SCENA ============================
bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
S.frame_start = 1
S.frame_end = 300
S.render.fps = 30

COL_MAIN = bpy.data.collections.new("F1_Monoposto_Completa")
S.collection.children.link(COL_MAIN)

SUB_COLS = {}
for cname in ("Carrozzeria_Aero", "Interni_Cockpit", "Ali_Fondo_Diffusore", "Ruote_Freni_Sospensioni", "Studio_Pista_Luci"):
    c = bpy.data.collections.new(cname)
    COL_MAIN.children.link(c)
    SUB_COLS[cname] = c


def link_obj(o, col_name="Carrozzeria_Aero"):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    SUB_COLS[col_name].objects.link(o)
    return o


def set_in(node, name, val):
    if name in node.inputs:
        node.inputs[name].default_value = val


def applica_smooth(o, angolo=38.0):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angolo))
    except Exception:
        try:
            bpy.ops.object.shade_auto_smooth(angle=math.radians(angolo))
        except Exception:
            bpy.ops.object.shade_smooth()
    o.select_set(False)


# ============================ 2. MATERIALI PBR AVANZATI ============================
MATS = {}


def mat_vernice_f1(nome, colore_base, metal=0.32, rough=0.12, coat=1.0, coat_rough=0.02):
    if nome in MATS:
        return MATS[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    set_in(bsdf, "Base Color", colore_base)
    set_in(bsdf, "Metallic", metal)
    set_in(bsdf, "Roughness", rough)
    set_in(bsdf, "Specular IOR Level", 0.72)
    set_in(bsdf, "Coat Weight", coat)
    set_in(bsdf, "Coat Roughness", coat_rough)
    set_in(bsdf, "Coat IOR", 1.58)

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 380.0
    noise.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.012
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    MATS[nome] = m
    return m


def mat_carbonio(nome="Fibra_Carbonio_3K", scala=150.0, rough=0.22, coat=0.65):
    if nome in MATS:
        return MATS[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    set_in(bsdf, "Metallic", 0.52)
    set_in(bsdf, "Roughness", rough)
    set_in(bsdf, "Specular IOR Level", 0.65)
    set_in(bsdf, "Coat Weight", coat)
    set_in(bsdf, "Coat Roughness", 0.06)

    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scala, scala, scala)
    mp.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(45))

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'DIAGONAL'
    wave.inputs["Scale"].default_value = 4.0
    wave.inputs["Distortion"].default_value = 0.25

    checker = nt.nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 8.0
    checker.inputs["Color1"].default_value = (0.012, 0.014, 0.018, 1.0)
    checker.inputs["Color2"].default_value = (0.042, 0.046, 0.054, 1.0)

    mix_c = nt.nodes.new("ShaderNodeMix")
    mix_c.data_type = 'RGBA'
    mix_c.inputs["Factor"].default_value = 0.35
    mix_c.inputs["B"].default_value = (0.022, 0.025, 0.030, 1.0)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.07
    bump.inputs["Distance"].default_value = 0.002

    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], checker.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(checker.outputs["Color"], mix_c.inputs["A"])
    nt.links.new(mix_c.outputs["Result"], bsdf.inputs["Base Color"])
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    MATS[nome] = m
    return m


def mat_pbr(nome, colore, metal=0.0, rough=0.35, emit_col=None, emit_str=0.0, bump_str=0.0, bump_scale=50.0, coat=0.0, spec=0.6):
    if nome in MATS:
        return MATS[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    set_in(bsdf, "Base Color", colore)
    set_in(bsdf, "Metallic", metal)
    set_in(bsdf, "Roughness", rough)
    set_in(bsdf, "Specular IOR Level", spec)
    if coat > 0:
        set_in(bsdf, "Coat Weight", coat)
        set_in(bsdf, "Coat Roughness", 0.04)
    if emit_col is not None and emit_str > 0:
        set_in(bsdf, "Emission Color", emit_col)
        set_in(bsdf, "Emission Strength", emit_str)
    if bump_str > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        noise.inputs["Detail"].default_value = 6.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_str
        bump.inputs["Distance"].default_value = 0.008
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    MATS[nome] = m
    return m


# Palette Materiali Calibrata (Rosso Corsa Ferrari Profondo + Carbonio + Metalli CNC + Alcantara + OLED)
M_ROSSO       = mat_vernice_f1("Vernice_Rosso_Corsa", (0.58, 0.006, 0.009, 1.0), metal=0.28, rough=0.11, coat=1.0, coat_rough=0.02)
M_BIANCO      = mat_vernice_f1("Vernice_Bianco_Racing", (0.92, 0.93, 0.95, 1.0), metal=0.10, rough=0.14, coat=0.85)
M_GIALLO      = mat_vernice_f1("Vernice_Giallo_Modena", (0.95, 0.72, 0.01, 1.0), metal=0.15, rough=0.14, coat=0.85)
M_CARBON      = mat_carbonio("Fibra_Carbonio_3K", scala=150.0, rough=0.20, coat=0.70)
M_CARBON_OP   = mat_carbonio("Fibra_Carbonio_Opaco", scala=170.0, rough=0.45, coat=0.08)
M_CAVITA_NERA = mat_pbr("Cavita_Condotto_Nero", (0.002, 0.002, 0.003, 1.0), metal=0.0, rough=0.98, spec=0.0)
M_GOMMA       = mat_pbr("Gomma_Pirelli_Slick", (0.018, 0.019, 0.022, 1.0), metal=0.0, rough=0.58, bump_str=0.06, bump_scale=95.0)
M_CERCHIO     = mat_pbr("Cerchio_Forgiato_BBS", (0.11, 0.12, 0.14, 1.0), metal=0.92, rough=0.18, coat=0.5)
M_ALLUMINIO   = mat_pbr("Alluminio_CNC", (0.80, 0.83, 0.88, 1.0), metal=0.96, rough=0.14)
M_TITANIO     = mat_pbr("Titanio_Aerospaziale", (0.42, 0.45, 0.50, 1.0), metal=0.94, rough=0.20)
M_INCONEL     = mat_pbr("Inconel_Scarico", (0.48, 0.33, 0.20, 1.0), metal=0.95, rough=0.20, bump_str=0.04)
M_ORO         = mat_pbr("Oro_Termico_CNC", (0.90, 0.66, 0.12, 1.0), metal=0.96, rough=0.15)
M_ALCANTARA   = mat_pbr("Alcantara_Cockpit", (0.028, 0.030, 0.035, 1.0), metal=0.0, rough=0.92, bump_str=0.18, bump_scale=240.0)
M_CINTURA_R   = mat_pbr("Cintura_Sabelt_Rossa", (0.75, 0.015, 0.02, 1.0), metal=0.05, rough=0.62, bump_str=0.12, bump_scale=180.0)
M_SPECCHIO    = mat_pbr("Specchio_Cromo", (0.96, 0.97, 0.99, 1.0), metal=1.0, rough=0.01)
M_DISCO_CARB  = mat_pbr("Disco_Freno_Carbonio", (0.06, 0.055, 0.055, 1.0), metal=0.68, rough=0.38, bump_str=0.16, bump_scale=85.0)
M_PINZA_BREMBO= mat_vernice_f1("Pinza_Brembo_Rossa", (0.82, 0.01, 0.015, 1.0), metal=0.55, rough=0.14, coat=0.9)

# Materiali Emissivi (LED, Display OLED, Freni, Luci Showroom)
M_LED_ROSSO   = mat_pbr("LED_Rosso_FIA", (1.0, 0.03, 0.01, 1.0), rough=0.1, emit_col=(1.0, 0.03, 0.01, 1.0), emit_str=16.0)
M_LED_VERDE   = mat_pbr("LED_Verde_RPM", (0.05, 1.0, 0.32, 1.0), rough=0.1, emit_col=(0.05, 1.0, 0.32, 1.0), emit_str=11.0)
M_LED_BLU     = mat_pbr("LED_Blu_RPM", (0.08, 0.45, 1.0, 1.0), rough=0.1, emit_col=(0.08, 0.45, 1.0, 1.0), emit_str=13.0)
M_LED_GIALLO  = mat_pbr("LED_Giallo_Tele", (1.0, 0.78, 0.04, 1.0), rough=0.1, emit_col=(1.0, 0.78, 0.04, 1.0), emit_str=10.0)
M_LED_CIANO   = mat_pbr("LED_Ciano_Tele", (0.05, 0.88, 1.0, 1.0), rough=0.1, emit_col=(0.05, 0.88, 1.0, 1.0), emit_str=9.0)
M_OLED_BG     = mat_pbr("OLED_Schermo_Nero", (0.003, 0.005, 0.010, 1.0), rough=0.04, coat=1.0)
M_FRENO_GLOW  = mat_pbr("Freno_Glow_Caldo", (1.0, 0.22, 0.02, 1.0), rough=0.2, emit_col=(1.0, 0.18, 0.01, 1.0), emit_str=5.5)
M_LUCE_STUDIO = mat_pbr("Barra_LED_Showroom", (1.0, 0.98, 0.95, 1.0), rough=0.1, emit_col=(0.96, 0.98, 1.0, 1.0), emit_str=6.5)
M_ASFALTO     = mat_pbr("Pavimento_Showroom_Asfalto", (0.020, 0.022, 0.027, 1.0), metal=0.15, rough=0.24, bump_str=0.05, bump_scale=60.0, coat=0.22)


# ============================ 3. MOTORI GEOMETRICI PROCEDURALI (LOFT & PROFILI) ============================
def crea_mesh_loft(nome, sezioni_punti, mat, col="Carrozzeria_Aero", chiudi_capi=True, ciclico_profilo=True, subsurf=2, bevel_w=0.0, parent=None):
    me = bpy.data.meshes.new(nome)
    bm = bmesh.new()

    anelli_v = []
    for sez in sezioni_punti:
        anello = [bm.verts.new(pt) for pt in sez]
        anelli_v.append(anello)

    bm.verts.ensure_lookup_table()
    n_sez = len(anelli_v)
    n_pts = len(anelli_v[0])

    for i in range(n_sez - 1):
        a1 = anelli_v[i]
        a2 = anelli_v[i + 1]
        limite = n_pts if ciclico_profilo else (n_pts - 1)
        for j in range(limite):
            jn = (j + 1) % n_pts
            try:
                bm.faces.new((a1[j], a1[jn], a2[jn], a2[j]))
            except ValueError:
                pass

    if chiudi_capi and ciclico_profilo and n_pts >= 3:
        try:
            bm.faces.new(list(reversed(anelli_v[0])))
        except ValueError:
            pass
        try:
            bm.faces.new(anelli_v[-1])
        except ValueError:
            pass

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()

    o = bpy.data.objects.new(nome, me)
    link_obj(o, col)
    o.data.materials.append(mat)

    if bevel_w > 0:
        bv = o.modifiers.new("Bevel", 'BEVEL')
        bv.width = bevel_w
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(35)

    if subsurf > 0:
        sd = o.modifiers.new("Subsurf", 'SUBSURF')
        sd.levels = subsurf
        sd.render_levels = subsurf

    applica_smooth(o, 42.0)
    if parent is not None:
        o.parent = parent
    return o


def profilo_superellisse(x, y_c, z_min, z_max, w_sotto, w_sopra, exp_sotto=2.4, exp_sopra=2.0, n=28):
    z_mid = 0.5 * (z_min + z_max)
    hz = max(0.001, 0.5 * (z_max - z_min))
    pts = []
    for i in range(n):
        theta = 2.0 * math.pi * i / n
        ct = math.cos(theta)
        st = math.sin(theta)
        if st >= 0:
            esponente = exp_sopra
            w = w_sotto + (w_sopra - w_sotto) * (st ** 0.75)
        else:
            esponente = exp_sotto
            w = w_sotto
        sy = math.copysign(abs(ct) ** (2.0 / esponente), ct)
        sz = math.copysign(abs(st) ** (2.0 / esponente), st)
        y = y_c + w * sy
        z = z_mid + hz * sz
        pts.append((x, y, z))
    return pts


def crea_profilo_alare(nome, sezioni_alari, mat, col="Ali_Fondo_Diffusore", subsurf=2, parent=None):
    """
    Costruisce un profilo alare NACA autentico e affilato!
    Nota: spessore e camber sono frazioni della corda (es. spess=0.11 = 11% della corda).
    """
    n_punti_lato = 12
    sezioni_3d = []
    for (y_p, x_le, z_le, corda, spess_rel, alpha_deg, camber_rel) in sezioni_alari:
        alpha = math.radians(alpha_deg)
        ca, sa = math.cos(alpha), math.sin(alpha)
        anello = []
        for i in range(2 * n_punti_lato):
            if i <= n_punti_lato:
                t = i / n_punti_lato
                lato = 1.0
            else:
                t = (2 * n_punti_lato - i) / n_punti_lato
                lato = -1.0
            # Spessore e curvatura proporzionali alla corda!
            yt = 5.0 * (spess_rel * corda) * (
                0.2969 * math.sqrt(max(0.0, t)) - 0.1260 * t - 0.3516 * (t**2) + 0.2843 * (t**3) - 0.1015 * (t**4)
            )
            yc = (camber_rel * corda) * 4.0 * t * (1.0 - t)
            dx_loc = -t * corda
            dz_loc = yc + lato * yt
            rx = dx_loc * ca - dz_loc * sa
            rz = dx_loc * sa + dz_loc * ca
            anello.append((x_le + rx, y_p, z_le + rz))
        sezioni_3d.append(anello)

    return crea_mesh_loft(nome, sezioni_3d, mat, col=col, chiudi_capi=True, ciclico_profilo=True, subsurf=subsurf, parent=parent)


def tubo_curvo_bezier(nome, punti_3d, raggio, mat, col="Carrozzeria_Aero", bevel_res=8, res_u=24, parent=None):
    cu = bpy.data.curves.new(nome + "_Cu", 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = raggio
    cu.bevel_resolution = bevel_res
    cu.resolution_u = res_u
    cu.use_fill_caps = True

    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(punti_3d) - 1)
    for i, pt in enumerate(punti_3d):
        bp = sp.bezier_points[i]
        bp.co = pt
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'

    o = bpy.data.objects.new(nome, cu)
    link_obj(o, col)
    o.data.materials.append(mat)
    if parent is not None:
        o.parent = parent
    return o


def asta_alare_tra(nome, p1, p2, corda, spessore, mat, col="Ruote_Freni_Sospensioni", parent=None):
    v1, v2 = Vector(p1), Vector(p2)
    diff = v2 - v1
    lung = diff.length
    mid = (v1 + v2) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=lung, location=(0, 0, 0))
    o = bpy.context.object
    o.name = nome
    o.scale = (corda * 0.5, spessore * 0.5, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    quat = diff.normalized().to_track_quat('Z', 'X')
    o.rotation_euler = quat.to_euler()
    o.location = mid
    o.data.materials.append(mat)
    applica_smooth(o, 40.0)
    link_obj(o, col)
    if parent is not None:
        o.parent = parent
    return o


def cilindro(nome, pos, r, h, mat, asse='Z', vert=36, rot_extra=None, scala=None, bevel_w=0.003, col="Carrozzeria_Aero", parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vert, radius=r, depth=h, location=(0, 0, 0))
    o = bpy.context.object
    o.name = nome
    if scala is not None:
        o.scale = scala
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot_extra is not None:
        o.rotation_euler = rot_extra
    elif asse == 'X':
        o.rotation_euler = (0, math.radians(90), 0)
    elif asse == 'Y':
        o.rotation_euler = (math.radians(90), 0, 0)
    o.location = pos
    o.data.materials.append(mat)
    if bevel_w > 0:
        bv = o.modifiers.new("Bevel", 'BEVEL')
        bv.width = bevel_w
        bv.segments = 2
        bv.limit_method = 'ANGLE'
    applica_smooth(o, 36.0)
    link_obj(o, col)
    if parent is not None:
        o.parent = parent
    return o


def scatola_smussata(nome, pos, dim, mat, rot=(0, 0, 0), bevel_w=0.006, subsurf=0, col="Carrozzeria_Aero", parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
    o = bpy.context.object
    o.name = nome
    o.scale = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = pos
    o.rotation_euler = rot
    o.data.materials.append(mat)
    if bevel_w > 0:
        bv = o.modifiers.new("Bevel", 'BEVEL')
        bv.width = bevel_w
        bv.segments = 3
        bv.limit_method = 'ANGLE'
    if subsurf > 0:
        sd = o.modifiers.new("Subsurf", 'SUBSURF')
        sd.levels = subsurf
        sd.render_levels = subsurf
    applica_smooth(o, 36.0)
    link_obj(o, col)
    if parent is not None:
        o.parent = parent
    return o


# ============================ 4. COSTRUZIONE MONOSCOCCA, MUSO, PANCE & COFANO ============================
def costruisci_carrozzeria_sinuosa():
    # --- A. MUSO E SCOCCA ANTERIORE (da X=+2.92 a X=+0.66) ---
    dati_muso = [
        # (x,     z_min, z_max, w_sotto, w_sopra, exp_sotto, exp_sopra)
        (2.94,    0.160, 0.198, 0.042,   0.034,   2.2,       1.9),  # Punta del muso affilata
        (2.75,    0.158, 0.242, 0.080,   0.068,   2.5,       2.0),
        (2.42,    0.172, 0.312, 0.118,   0.105,   2.8,       2.1),
        (2.05,    0.190, 0.422, 0.162,   0.150,   3.0,       2.2),
        (1.75,    0.195, 0.515, 0.205,   0.195,   3.2,       2.3),  # Bulkhead sospensione anteriore
        (1.30,    0.150, 0.575, 0.248,   0.238,   3.4,       2.2),
        (0.92,    0.130, 0.608, 0.288,   0.275,   3.5,       2.2),
        (0.76,    0.125, 0.615, 0.305,   0.290,   3.5,       2.2),  # Si ferma alla paratia pedaliera!
    ]
    sezioni_muso = [profilo_superellisse(x, 0.0, z0, z1, ws, wt, es, et, n=28) for (x, z0, z1, ws, wt, es, et) in dati_muso]
    crea_mesh_loft("Monoscocca_Muso_Anteriore", sezioni_muso, M_ROSSO, col="Carrozzeria_Aero", subsurf=2)

    # Striscia bianca racing sottile sul dorso del muso
    dati_striscia = [
        (2.68, 0.238, 0.244, 0.036, 0.036, 3.0, 2.2),
        (2.15, 0.382, 0.390, 0.068, 0.068, 3.0, 2.2),
        (1.65, 0.522, 0.530, 0.095, 0.095, 3.0, 2.2),
        (1.10, 0.588, 0.596, 0.110, 0.110, 3.0, 2.2),
        (0.72, 0.612, 0.620, 0.120, 0.120, 3.0, 2.2),
    ]
    sezioni_striscia = [profilo_superellisse(x, 0.0, z0, z1, ws, wt, es, et, n=20) for (x, z0, z1, ws, wt, es, et) in dati_striscia]
    crea_mesh_loft("Livrea_Bianca_Muso", sezioni_striscia, M_BIANCO, col="Carrozzeria_Aero", subsurf=2)

    # --- B. VASCA ABITACOLO SCAVATA E FIANCHI COCKPIT (da X=+0.72 a X=-0.28) ---
    for lato, suff in ((-1, "SX"), (1, "DX")):
        dati_sponda = [
            # (x,    y_int, y_est, z_min, z_max)
            ( 0.76,  0.15,  0.31,  0.13,  0.615),
            ( 0.52,  0.20,  0.34,  0.13,  0.585),
            ( 0.20,  0.21,  0.35,  0.13,  0.565),
            (-0.06,  0.19,  0.34,  0.13,  0.625),
            (-0.28,  0.13,  0.31,  0.14,  0.720),
        ]
        sez_sponda = []
        for (x, yi, ye, z0, z1) in dati_sponda:
            yc = lato * 0.5 * (yi + ye)
            hw = 0.5 * (ye - yi)
            sez_sponda.append(profilo_superellisse(x, yc, z0, z1, hw, hw * 0.90, 3.0, 2.2, n=22))
        crea_mesh_loft(f"Scocca_Fianco_Cockpit_{suff}", sez_sponda, M_ROSSO, col="Carrozzeria_Aero", subsurf=2)

        # Protezione laterale testa pilota (Headrest FIA in carbonio/alcantara nera)
        dati_pad = [
            ( 0.44, 0.180, 0.220, 0.48, 0.572),
            ( 0.15, 0.185, 0.225, 0.46, 0.560),
            (-0.08, 0.165, 0.212, 0.48, 0.620),
            (-0.22, 0.120, 0.180, 0.52, 0.685),
        ]
        sez_pad = []
        for (x, yi, ye, z0, z1) in dati_pad:
            yc = lato * 0.5 * (yi + ye)
            hw = 0.5 * (ye - yi)
            sez_pad.append(profilo_superellisse(x, yc, z0, z1, hw, hw, 2.5, 2.5, n=16))
        crea_mesh_loft(f"Cockpit_Padding_FIA_{suff}", sez_pad, M_CARBON_OP, col="Interni_Cockpit", subsurf=2)

    # Pavimento interno e pareti interne scure in fibra di carbonio
    scatola_smussata("Vasca_Cockpit_Fondo", (0.28, 0.0, 0.135), (1.10, 0.46, 0.035), M_CARBON, bevel_w=0.008, col="Interni_Cockpit")
    scatola_smussata("Paratia_Post_Cockpit", (-0.19, 0.0, 0.40), (0.05, 0.42, 0.52), M_CARBON, rot=(0, math.radians(-22), 0), bevel_w=0.01, col="Interni_Cockpit")
    scatola_smussata("Paratia_Front_Cruscotto", (0.64, 0.0, 0.42), (0.06, 0.42, 0.42), M_CARBON_OP, rot=(0, math.radians(18), 0), bevel_w=0.01, col="Interni_Cockpit")
    # Rivestimento interno in carbonio sulle pareti laterali del cockpit (così dentro non è rosso ma vero telaio monoscocca in carbonio!)
    for lato, suff in ((-1, "SX"), (1, "DX")):
        scatola_smussata(
            f"Parete_Interna_Carbon_{suff}",
            (0.24, lato * 0.192, 0.34),
            (0.88, 0.016, 0.34),
            M_CARBON_OP, bevel_w=0.004, col="Interni_Cockpit"
        )

    # Palpebra cruscotto anteriore compatta (così non impalla la visuale dall'alto sul volante!)
    dati_palpebra = [
        (0.74, 0.55, 0.625, 0.26, 0.23, 2.5, 2.2),
        (0.64, 0.55, 0.635, 0.23, 0.19, 2.5, 2.2),
        (0.57, 0.54, 0.610, 0.20, 0.16, 2.5, 2.2),
    ]
    sez_palp = [profilo_superellisse(x, 0.0, z0, z1, ws, wt, es, et, n=20) for (x, z0, z1, ws, wt, es, et) in dati_palpebra]
    crea_mesh_loft("Cruscotto_Windscreen_Carbon", sez_palp, M_CARBON, col="Interni_Cockpit", subsurf=2)

    # --- C. ROLL-HOOP CON AIRBOX INTEGRATO & COFANO MOTORE SINUOSO (da X=-0.12 a X=-2.08) ---
    # Il cofano parte già con la forma dell'Airbox in alto e si fonde in basso con i fianchi cockpit e le pance!
    dati_cofano = [
        # (x,     z_min, z_max, w_sotto, w_sopra, exp_sotto, exp_sopra)
        (-0.14,   0.52,  0.945, 0.220,   0.088,   2.4,       2.0),  # Bocca Airbox integrata nel Roll-Hoop!
        (-0.26,   0.26,  0.965, 0.310,   0.095,   2.5,       1.9),  # Culmine Roll-Hoop e raccordo fianchi
        (-0.58,   0.20,  0.890, 0.300,   0.082,   2.4,       1.8),  # Discesa cofano motore
        (-0.96,   0.18,  0.795, 0.250,   0.066,   2.3,       1.7),  # V6 Turbo cover
        (-1.36,   0.18,  0.690, 0.190,   0.050,   2.2,       1.7),  # Coca-Cola rastremazione
        (-1.75,   0.20,  0.575, 0.130,   0.040,   2.2,       1.8),  # Zona sospensione posteriore
        (-2.06,   0.25,  0.475, 0.082,   0.036,   2.2,       2.0),  # Coda scarico
    ]
    sezioni_cofano = [profilo_superellisse(x, 0.0, z0, z1, ws, wt, es, et, n=28) for (x, z0, z1, ws, wt, es, et) in dati_cofano]
    crea_mesh_loft("Cofano_Motore_Airbox", sezioni_cofano, M_ROSSO, col="Carrozzeria_Aero", subsurf=2)

    # Condotto Airbox scavato (anello in carbonio annegato nel fronte del Roll-Hoop + cavità nera assoluta senza riflessi!)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.072, minor_radius=0.016,
        major_segments=36, minor_segments=16,
        location=(-0.155, 0.0, 0.840),
        rotation=(0, math.radians(82), 0)
    )
    o_ab_lip = bpy.context.object
    o_ab_lip.name = "Airbox_Lip_Carbon"
    o_ab_lip.scale = (1.15, 0.88, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o_ab_lip.data.materials.append(M_CARBON)
    applica_smooth(o_ab_lip, 42.0)
    link_obj(o_ab_lip, "Carrozzeria_Aero")

    cilindro("Airbox_Cavita_Nera", (-0.150, 0.0, 0.840), 0.066, 0.03, M_CAVITA_NERA, asse='X', scala=(1.0, 0.85, 1.12), bevel_w=0.0, col="Carrozzeria_Aero")
    scatola_smussata("Airbox_Splitter_RollHoop", (-0.145, 0.0, 0.840), (0.04, 0.012, 0.12), M_CARBON, bevel_w=0.002, col="Carrozzeria_Aero")

    # SHARK FIN (Pinna dorsale aerodinamica sul cofano motore)
    punti_fin = [
        (-0.34, 0.0, 0.945),
        (-0.75, 0.0, 0.910),
        (-1.25, 0.0, 0.850),
        (-1.68, 0.0, 0.780),
        (-1.68, 0.0, 0.550),
        (-1.25, 0.0, 0.640),
        (-0.75, 0.0, 0.740),
        (-0.34, 0.0, 0.840),
    ]
    me_fin = bpy.data.meshes.new("Shark_Fin")
    bm = bmesh.new()
    v_sx = [bm.verts.new((x, -0.008, z)) for (x, _, z) in punti_fin]
    v_dx = [bm.verts.new((x,  0.008, z)) for (x, _, z) in punti_fin]
    bm.faces.new(list(reversed(v_sx)))
    bm.faces.new(v_dx)
    for i in range(len(punti_fin)):
        inext = (i + 1) % len(punti_fin)
        bm.faces.new((v_sx[i], v_sx[inext], v_dx[inext], v_dx[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me_fin)
    bm.free()
    o_fin = bpy.data.objects.new("Shark_Fin", me_fin)
    link_obj(o_fin, "Carrozzeria_Aero")
    o_fin.data.materials.append(M_ROSSO)
    bv_f = o_fin.modifiers.new("Bevel", 'BEVEL')
    bv_f.width = 0.003
    bv_f.segments = 2
    applica_smooth(o_fin, 35.0)

    scatola_smussata("Shark_Fin_Top_Stripe", (-1.01, 0.0, 0.865), (1.30, 0.019, 0.042), M_BIANCO, rot=(0, math.radians(-7.1), 0), bevel_w=0.003, col="Carrozzeria_Aero")
    scatola_smussata("Shark_Fin_Gold_Stripe", (-1.01, 0.0, 0.838), (1.28, 0.020, 0.018), M_GIALLO, rot=(0, math.radians(-7.1), 0), bevel_w=0.002, col="Carrozzeria_Aero")

    # T-CAM Ufficiale FIA sopra il Roll-Hoop
    scatola_smussata("TCam_Stelo", (-0.25, 0.0, 1.000), (0.065, 0.016, 0.085), M_CARBON, bevel_w=0.004, col="Carrozzeria_Aero")
    scatola_smussata("TCam_Barra", (-0.24, 0.0, 1.048), (0.105, 0.23, 0.024), M_CARBON, bevel_w=0.005, col="Carrozzeria_Aero")
    scatola_smussata("TCam_Accent_Giallo", (-0.24, 0.0, 1.061), (0.085, 0.20, 0.007), M_GIALLO, bevel_w=0.002, col="Carrozzeria_Aero")

    # --- D. PANCE LATERALI (SIDEPODS) SCOLPITE CON BOCCA INTEGRATA E UNDERCUT ---
    for lato, suff in ((-1, "SX"), (1, "DX")):
        # Sezioni morbide che partono dal labbro anteriore della bocca radiatore fino alla coda Coca-Cola
        dati_pancia = [
            # (x,     y_int, y_est, z_min, z_max, wf)
            ( 0.82,   0.24,  0.60,  0.31,  0.55,  0.70),  # Ingresso bocca radiatore raccordata!
            ( 0.66,   0.20,  0.70,  0.20,  0.57,  0.58),  # Espansione spalla sidepod + undercut profondo sotto
            ( 0.30,   0.18,  0.73,  0.14,  0.56,  0.64),  # Massima larghezza sidepod
            (-0.15,   0.17,  0.68,  0.14,  0.52,  0.72),  # Inizio scivolo downwash
            (-0.65,   0.15,  0.55,  0.14,  0.45,  0.78),  # Rastremazione Coca-Cola
            (-1.18,   0.12,  0.38,  0.15,  0.39,  0.82),  # Verso gli scarichi
            (-1.68,   0.09,  0.21,  0.19,  0.34,  0.86),  # Coda sul cambio
        ]
        sez_pancia = []
        for (x, yi, ye, z0, z1, wf) in dati_pancia:
            yc = lato * 0.5 * (yi + ye)
            hw_top = 0.5 * (ye - yi)
            hw_bot = hw_top * wf
            pts = profilo_superellisse(x, yc, z0, z1, hw_bot, hw_top, 2.3, 2.4, n=28)
            sez_pancia.append(pts)
        crea_mesh_loft(f"Pancia_Sidepod_{suff}", sez_pancia, M_ROSSO, col="Carrozzeria_Aero", subsurf=2)

        # Bocca Radiatore Curva Integrata (cavità nera profonda + labbro in carbonio sottile + lamelle radiatore interne)
        sez_inlet = [
            profilo_superellisse(0.835, lato * 0.42, 0.33, 0.53, 0.13, 0.15, 2.4, 2.4, n=22),
            profilo_superellisse(0.760, lato * 0.42, 0.32, 0.53, 0.14, 0.16, 2.4, 2.4, n=22),
        ]
        crea_mesh_loft(f"Sidepod_Inlet_Lip_{suff}", sez_inlet, M_CARBON, col="Carrozzeria_Aero", chiudi_capi=False, subsurf=2)
        # Fondale oscuro della presa d'aria
        sez_cav = [
            profilo_superellisse(0.815, lato * 0.42, 0.34, 0.52, 0.12, 0.14, 2.4, 2.4, n=20),
            profilo_superellisse(0.780, lato * 0.42, 0.34, 0.52, 0.12, 0.14, 2.4, 2.4, n=20),
        ]
        crea_mesh_loft(f"Sidepod_Inlet_Cavity_{suff}", sez_cav, M_CAVITA_NERA, col="Carrozzeria_Aero", chiudi_capi=True, subsurf=1)

        # Lamelle radiatore in alluminio dentro la bocca scavata
        for k in range(5):
            zk = 0.365 + k * 0.032
            scatola_smussata(
                f"Lamella_Radiatore_{suff}_{k}",
                (0.818, lato * 0.42, zk),
                (0.018, 0.22, 0.004),
                M_ALLUMINIO,
                rot=(0, math.radians(24), math.radians(lato * -6)),
                bevel_w=0.001, col="Carrozzeria_Aero"
            )

        # Branchie di sfogo aria calda (Cooling Louvers) sul dorso della pancia
        for i in range(8):
            lx = 0.15 - i * 0.11
            ly = lato * (0.41 - i * 0.018)
            lz = 0.525 - i * 0.013
            scatola_smussata(
                f"Branchia_Sidepod_{suff}_{i}",
                (lx, ly, lz),
                (0.032, 0.14, 0.010),
                M_CARBON,
                rot=(math.radians(lato * 14), math.radians(-28), math.radians(lato * -10)),
                bevel_w=0.002, col="Carrozzeria_Aero"
            )

        # Specchietti Retrovisori Aerodinamici
        asta_alare_tra(
            f"Supporto_Specchietto_1_{suff}",
            (0.62, lato * 0.30, 0.55),
            (0.58, lato * 0.54, 0.635),
            0.042, 0.009, M_CARBON, col="Carrozzeria_Aero"
        )
        asta_alare_tra(
            f"Supporto_Specchietto_2_{suff}",
            (0.68, lato * 0.45, 0.53),
            (0.58, lato * 0.54, 0.625),
            0.035, 0.008, M_CARBON, col="Carrozzeria_Aero"
        )
        scatola_smussata(
            f"Calotta_Specchietto_{suff}",
            (0.57, lato * 0.56, 0.640),
            (0.105, 0.145, 0.048),
            M_ROSSO,
            rot=(0, math.radians(-4), math.radians(lato * -12)),
            bevel_w=0.014, subsurf=1, col="Carrozzeria_Aero"
        )
        scatola_smussata(
            f"Vetro_Specchietto_{suff}",
            (0.528, lato * 0.56, 0.640),
            (0.022, 0.120, 0.036),
            M_SPECCHIO,
            rot=(0, math.radians(-4), math.radians(lato * -12)),
            bevel_w=0.003, col="Carrozzeria_Aero"
        )

    # --- E. HALO IN TITANIO E FIBRA DI CARBONIO ---
    for lato, suff in ((-1, "SX"), (1, "DX")):
        punti_halo_arco = [
            ( 0.56, 0.0,          0.685),
            ( 0.42, lato * 0.185, 0.755),
            ( 0.12, lato * 0.280, 0.775),
            (-0.18, lato * 0.210, 0.725),
        ]
        tubo_curvo_bezier(f"Halo_Arco_{suff}", punti_halo_arco, 0.024, M_CARBON, col="Carrozzeria_Aero")
        tubo_curvo_bezier(
            f"Halo_Fairing_Rosso_{suff}",
            [(x, y, z + 0.015) for (x, y, z) in punti_halo_arco],
            0.010, M_ROSSO, col="Carrozzeria_Aero"
        )

    asta_alare_tra("Halo_Pilone_Centrale", (0.65, 0.0, 0.585), (0.55, 0.0, 0.695), 0.062, 0.025, M_CARBON, col="Carrozzeria_Aero")
    cilindro("Tubo_Pitot_Base", (1.62, 0.0, 0.555), 0.005, 0.08, M_TITANIO, asse='Z', col="Carrozzeria_Aero")
    cilindro("Tubo_Pitot_Punta", (1.66, 0.0, 0.592), 0.0035, 0.08, M_ALLUMINIO, asse='X', col="Carrozzeria_Aero")


# ============================ 5. INTERNI COCKPIT ULTRA-DETTAGLIATI ============================
def costruisci_interni_cockpit():
    # --- 1. SEDILE ANATOMICO SCOLPITO IN CARBONIO E ALCANTARA ---
    dati_sedile = [
        (-0.15, 0.40, 0.58, 0.14, 0.16),
        (-0.05, 0.24, 0.45, 0.17, 0.18),
        ( 0.12, 0.14, 0.28, 0.18, 0.18),
        ( 0.28, 0.14, 0.26, 0.17, 0.17),
        ( 0.42, 0.18, 0.28, 0.15, 0.15),
    ]
    sez_sedile = [profilo_superellisse(x, 0.0, z0, z1, ws, wt, 2.6, 2.2, n=22) for (x, z0, z1, ws, wt) in dati_sedile]
    crea_mesh_loft("Sedile_Guscio_Carbonio", sez_sedile, M_CARBON, col="Interni_Cockpit", subsurf=2)

    # Cuscini anatomici in Alcantara antracite (posizionati in modo da lasciare le cinture rosse in primo piano sopra di essi!)
    scatola_smussata("Sedile_Cuscino_Schiena", (-0.04, 0.0, 0.34), (0.032, 0.26, 0.32), M_ALCANTARA, rot=(0, math.radians(-32), 0), bevel_w=0.012, subsurf=1, col="Interni_Cockpit")
    scatola_smussata("Sedile_Cuscino_Seduta",  ( 0.17, 0.0, 0.19), (0.26,  0.28, 0.04), M_ALCANTARA, rot=(0, math.radians(14), 0),  bevel_w=0.012, subsurf=1, col="Interni_Cockpit")
    scatola_smussata("Sedile_Poggiatesta_FIA", (-0.13, 0.0, 0.54), (0.05,  0.21, 0.12), M_ALCANTARA, rot=(0, math.radians(-18), 0), bevel_w=0.018, subsurf=1, col="Interni_Cockpit")
    for lato, suff in ((-1, "SX"), (1, "DX")):
        scatola_smussata(
            f"Sedile_Sponda_Lat_{suff}",
            (0.08, lato * 0.155, 0.29),
            (0.36, 0.038, 0.14),
            M_ALCANTARA,
            rot=(math.radians(lato * -12), math.radians(-24), 0),
            bevel_w=0.012, subsurf=1, col="Interni_Cockpit"
        )

    # --- 2. CINTURE DI SICUREZZA A 6 PUNTI SABELT (BEN SOPRA IL CUSCINO!) ---
    pos_fibbia = (0.09, 0.0, 0.285)
    cilindro("Cinture_Fibbia_Centrale", pos_fibbia, 0.030, 0.018, M_ALLUMINIO, rot_extra=(0, math.radians(55), 0), col="Interni_Cockpit")
    cilindro("Cinture_Manopola_Sgancio", (0.102, 0.0, 0.295), 0.019, 0.014, M_GIALLO, rot_extra=(0, math.radians(55), 0), col="Interni_Cockpit")

    for lato, suff in ((-1, "SX"), (1, "DX")):
        # Bretelle spalle rosse ben appoggiate SOPRA il cuscino dello schienale
        punti_spalla = [
            (-0.12, lato * 0.082, 0.49),
            (-0.02, lato * 0.075, 0.41),
            ( 0.04, lato * 0.052, 0.335),
            ( 0.085, lato * 0.022, 0.288),
        ]
        tubo_curvo_bezier(f"Cintura_Spalla_{suff}", punti_spalla, 0.016, M_CINTURA_R, col="Interni_Cockpit")
        scatola_smussata(
            f"Cintura_Patch_{suff}",
            (0.00, lato * 0.068, 0.388),
            (0.068, 0.038, 0.012),
            M_GIALLO,
            rot=(0, math.radians(48), math.radians(lato * -8)),
            bevel_w=0.002, col="Interni_Cockpit"
        )
        punti_addome = [
            (0.08, lato * 0.145, 0.23),
            (0.085, lato * 0.085, 0.268),
            (0.09, lato * 0.025, 0.286),
        ]
        tubo_curvo_bezier(f"Cintura_Addominale_{suff}", punti_addome, 0.014, M_CINTURA_R, col="Interni_Cockpit")
        punti_inguine = [
            (0.24, lato * 0.045, 0.215),
            (0.16, lato * 0.035, 0.252),
            (0.095, lato * 0.018, 0.284),
        ]
        tubo_curvo_bezier(f"Cintura_Inguinale_{suff}", punti_inguine, 0.012, M_CINTURA_R, col="Interni_Cockpit")

    # --- 3. VOLANTE F1 MULTI-FUNZIONE CON DISPLAY OLED, 15 LED RPM E MANETTINI ---
    # Inclinato a 62° così si vede benissimo sia da dietro-alto che di tre-quarti!
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.43, 0.0, 0.510), rotation=(0, math.radians(62), 0))
    grp_volante = link_obj(bpy.context.object, "Interni_Cockpit")
    grp_volante.name = "GRP_Volante_Sterzo"

    cilindro("Piantone_Sterzo", (0.0, 0.0, 0.14), 0.020, 0.28, M_CARBON, asse='Z', col="Interni_Cockpit", parent=grp_volante)
    cilindro("Mozzo_QuickRelease", (0.0, 0.0, 0.026), 0.030, 0.042, M_ORO, asse='Z', col="Interni_Cockpit", parent=grp_volante)

    # Piastra frontale sagomata in fibra di carbonio
    scatola_smussata("Volante_Corpo_Centrale", (0.0, 0.0, 0.0), (0.150, 0.280, 0.024), M_CARBON, bevel_w=0.012, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("Volante_Archetto_Top", (0.072, 0.0, 0.002), (0.026, 0.200, 0.024), M_CARBON, bevel_w=0.006, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("Volante_Ponte_Basso", (-0.070, 0.0, 0.0), (0.028, 0.170, 0.024), M_CARBON, bevel_w=0.006, col="Interni_Cockpit", parent=grp_volante)

    for lato, suff in ((-1, "SX"), (1, "DX")):
        punti_grip = [
            ( 0.070, lato * 0.108, 0.0),
            ( 0.035, lato * 0.140, 0.003),
            ( 0.000, lato * 0.145, 0.005),
            (-0.042, lato * 0.138, 0.003),
            (-0.072, lato * 0.108, 0.0),
        ]
        tubo_curvo_bezier(f"Volante_Impugnatura_{suff}", punti_grip, 0.021, M_ALCANTARA, col="Interni_Cockpit", parent=grp_volante)

        scatola_smussata(
            f"Volante_Paletta_Cambio_{suff}",
            (0.015, lato * 0.108, 0.030),
            (0.078, 0.036, 0.006),
            M_CARBON, rot=(math.radians(lato * -12), 0, 0), bevel_w=0.002, col="Interni_Cockpit", parent=grp_volante
        )
        scatola_smussata(
            f"Volante_Paletta_Frizione_{suff}",
            (-0.036, lato * 0.090, 0.032),
            (0.052, 0.032, 0.005),
            M_ORO, rot=(math.radians(lato * -10), 0, 0), bevel_w=0.002, col="Interni_Cockpit", parent=grp_volante
        )

    # Schermo Display OLED Centrale (faccia rivolta verso il pilota = -Z locale)
    scatola_smussata("Volante_Cornice_OLED", (0.020, 0.0, -0.013), (0.072, 0.124, 0.006), M_ALLUMINIO, bevel_w=0.002, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("Volante_Schermo_OLED", (0.020, 0.0, -0.015), (0.064, 0.116, 0.004), M_OLED_BG, bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)

    # Grafica Telemetrica OLED ad alto contrasto
    scatola_smussata("OLED_Barra_RPM_Verde", (0.042, -0.030, -0.018), (0.007, 0.044, 0.002), M_LED_VERDE, bevel_w=0.0005, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("OLED_Barra_RPM_Rossa", (0.042,  0.012, -0.018), (0.007, 0.034, 0.002), M_LED_ROSSO, bevel_w=0.0005, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("OLED_Barra_RPM_Blu",   (0.042,  0.042, -0.018), (0.007, 0.022, 0.002), M_LED_BLU,   bevel_w=0.0005, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("OLED_Gear_Digit",      (0.016,  0.000, -0.018), (0.030, 0.024, 0.002), M_LED_GIALLO, bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("OLED_Box_SX",          (0.014, -0.038, -0.018), (0.024, 0.028, 0.002), M_LED_CIANO,  bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)
    scatola_smussata("OLED_Box_DX",          (0.014,  0.038, -0.018), (0.024, 0.028, 0.002), M_LED_VERDE,  bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)

    # 15 Shift-LEDs sopra il display
    for i in range(15):
        ly = -0.063 + i * 0.009
        m_led = M_LED_VERDE if i < 5 else (M_LED_ROSSO if i < 10 else M_LED_BLU)
        cilindro(f"Volante_ShiftLED_{i}", (0.072, ly, -0.012), 0.0035, 0.005, m_led, asse='Z', vert=16, bevel_w=0.0005, col="Interni_Cockpit", parent=grp_volante)

    # 5 Manettini rotativi
    manettini = [
        (-0.032,  0.000, M_ROSSO,     "Manettino_Engine_Mode"),
        (-0.046, -0.044, M_GIALLO,    "Manettino_SOC_Hybrid"),
        (-0.046,  0.044, M_LED_BLU,   "Manettino_Diff_Entry"),
        (-0.018, -0.080, M_LED_VERDE, "Manettino_Brake_Mig"),
        (-0.018,  0.080, M_ORO,       "Manettino_Torque_Map"),
    ]
    for (mx, my, m_col, m_nome) in manettini:
        cilindro(m_nome + "_Base", (mx, my, -0.013), 0.014, 0.008, M_ALLUMINIO, asse='Z', vert=20, bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)
        cilindro(m_nome + "_Cap",  (mx, my, -0.018), 0.011, 0.008, m_col,       asse='Z', vert=12, bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)
        scatola_smussata(m_nome + "_Pointer", (mx + 0.004, my, -0.023), (0.013, 0.004, 0.004), M_BIANCO, bevel_w=0.0005, col="Interni_Cockpit", parent=grp_volante)

    # 10 Pulsanti Tattili Colorati
    bottoni = [
        ( 0.054, -0.084, M_LED_VERDE),
        ( 0.028, -0.096, M_ROSSO),
        ( 0.002, -0.100, M_GIALLO),
        (-0.046, -0.090, M_LED_BLU),
        (-0.065, -0.064, M_BIANCO),
        ( 0.054,  0.084, M_LED_BLU),
        ( 0.028,  0.096, M_LED_ROSSO),
        ( 0.002,  0.100, M_LED_VERDE),
        (-0.046,  0.090, M_GIALLO),
        (-0.065,  0.064, M_ORO),
    ]
    for idx, (bx, by, bmat) in enumerate(bottoni):
        cilindro(f"Volante_Guard_{idx}", (bx, by, -0.013), 0.009, 0.007, M_CARBON, asse='Z', vert=20, bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)
        cilindro(f"Volante_Btn_{idx}",   (bx, by, -0.018), 0.0065, 0.007, bmat,    asse='Z', vert=20, bevel_w=0.001, col="Interni_Cockpit", parent=grp_volante)

    # --- 4. PEDALIERA F1 E PANNELLI INTERNI ABITACOLO ---
    scatola_smussata("Pedaliera_Base_Carbon", (0.76, 0.0, 0.165), (0.22, 0.28, 0.018), M_CARBON, bevel_w=0.004, col="Interni_Cockpit")
    scatola_smussata("Pedale_Acceleratore_Asta", (0.78,  0.065, 0.25), (0.022, 0.016, 0.15), M_ALLUMINIO, rot=(0, math.radians(-16), 0), bevel_w=0.003, col="Interni_Cockpit")
    scatola_smussata("Pedale_Acceleratore_Piastra", (0.75, 0.065, 0.29), (0.012, 0.052, 0.11), M_ALLUMINIO, rot=(0, math.radians(-16), 0), bevel_w=0.003, col="Interni_Cockpit")

    scatola_smussata("Pedale_Freno_Asta", (0.78, -0.065, 0.25), (0.026, 0.020, 0.15), M_CARBON, rot=(0, math.radians(-16), 0), bevel_w=0.003, col="Interni_Cockpit")
    scatola_smussata("Pedale_Freno_Piastra", (0.75, -0.065, 0.29), (0.014, 0.064, 0.11), M_CARBON, rot=(0, math.radians(-16), 0), bevel_w=0.003, col="Interni_Cockpit")
    for py in (-0.065, 0.065):
        cilindro(f"Pompa_Idraulica_{py}", (0.83, py, 0.20), 0.016, 0.09, M_ORO, asse='X', col="Interni_Cockpit")

    # Pannelli elettronici ausiliari sulle pareti interne in carbonio dell'abitacolo
    for lato, suff in ((-1, "SX"), (1, "DX")):
        scatola_smussata(f"Cockpit_Pannello_ECU_{suff}", (0.30, lato * 0.180, 0.38), (0.20, 0.014, 0.085), M_CARBON, bevel_w=0.003, col="Interni_Cockpit")
        for k in range(4):
            m_sw = M_LED_VERDE if k == 0 else (M_LED_GIALLO if k == 1 else (M_LED_BLU if k == 2 else M_LED_ROSSO))
            cilindro(f"Cockpit_Switch_{suff}_{k}", (0.23 + k * 0.042, lato * 0.170, 0.38), 0.006, 0.010, m_sw, asse='Y', col="Interni_Cockpit")

    cilindro("Estintore_Bordo_FIA", (0.28, 0.145, 0.18), 0.030, 0.20, M_ROSSO, asse='X', col="Interni_Cockpit")

    return grp_volante


# ============================ 6. ALA ANTERIORE, ALA POSTERIORE DRS & FONDO VENTURI ============================
def costruisci_ali_e_fondo():
    # --- A. ALA ANTERIORE MULTI-ELEMENTO CURVA (Lame NACA Affilatissime!) ---
    sezioni_mainplane = [
        # (y_pos, x_le, z_le,  corda, spess_rel, alpha_deg, camber_rel)
        (-0.96,   2.78, 0.095, 0.25,  0.09,      -5.0,      -0.05),
        (-0.65,   2.85, 0.082, 0.27,  0.09,      -7.0,      -0.06),
        (-0.28,   2.96, 0.068, 0.28,  0.10,      -8.0,      -0.06),
        ( 0.00,   3.02, 0.058, 0.29,  0.10,      -6.0,      -0.05),
        ( 0.28,   2.96, 0.068, 0.28,  0.10,      -8.0,      -0.06),
        ( 0.65,   2.85, 0.082, 0.27,  0.09,      -7.0,      -0.06),
        ( 0.96,   2.78, 0.095, 0.25,  0.09,      -5.0,      -0.05),
    ]
    crea_profilo_alare("AlaAnt_Mainplane", sezioni_mainplane, M_CARBON, col="Ali_Fondo_Diffusore", subsurf=2)

    for lato, suff in ((-1, "SX"), (1, "DX")):
        for idx_flap, (dx_off, dz_off, corda_f, alpha_f, mat_f) in enumerate([
            (-0.18, 0.028, 0.16, -14.0, M_ROSSO),
            (-0.31, 0.060, 0.13, -22.0, M_ROSSO),
            (-0.42, 0.096, 0.11, -30.0, M_BIANCO),
        ]):
            y_list = [0.08, 0.28, 0.52, 0.76, 0.95]
            if lato < 0:
                y_list = [-y for y in reversed(y_list)]
            sez_flap = []
            for yp in y_list:
                ay = abs(yp)
                x_le = 2.94 + dx_off - 0.14 * ((ay - 0.08) / 0.87) ** 1.3
                z_le = 0.065 + dz_off + 0.032 * math.sin(math.pi * (ay - 0.08) / 0.87)
                c_loc = corda_f * (1.0 - 0.20 * ((ay - 0.08) / 0.87))
                sez_flap.append((yp, x_le, z_le, c_loc, 0.09, alpha_f, -0.06))
            crea_profilo_alare(f"AlaAnt_Flap_{idx_flap+1}_{suff}", sez_flap, mat_f, col="Ali_Fondo_Diffusore", subsurf=2)

        asta_alare_tra(
            f"Pilone_Muso_Ala_{suff}",
            (2.68, lato * 0.072, 0.180),
            (2.74, lato * 0.082, 0.072),
            0.14, 0.015, M_CARBON, col="Ali_Fondo_Diffusore"
        )

        dati_ep = [
            (2.82, lato * 0.965, 0.065, 0.19, 0.010, 0.010),
            (2.62, lato * 0.972, 0.065, 0.27, 0.012, 0.010),
            (2.40, lato * 0.960, 0.070, 0.30, 0.010, 0.008),
        ]
        sez_ep = [profilo_superellisse(x, yc, z0, z1, ws, wt, 3.0, 2.5, n=18) for (x, yc, z0, z1, ws, wt) in dati_ep]
        crea_mesh_loft(f"AlaAnt_Endplate_{suff}", sez_ep, M_CARBON, col="Ali_Fondo_Diffusore", subsurf=2)
        scatola_smussata(
            f"AlaAnt_Diveplane_{suff}",
            (2.62, lato * 0.990, 0.195),
            (0.26, 0.036, 0.010),
            M_ROSSO,
            rot=(math.radians(lato * 12), math.radians(-18), 0),
            bevel_w=0.003, col="Ali_Fondo_Diffusore"
        )

    # --- B. FONDO VENTURI, FLOOR FENCES & DIFFUSORE POSTERIORE ---
    dati_fondo = [
        ( 1.25, 0.035, 0.062, 0.62, 0.64),
        ( 0.85, 0.032, 0.058, 0.78, 0.79),
        ( 0.20, 0.030, 0.055, 0.79, 0.80),
        (-0.65, 0.030, 0.055, 0.77, 0.78),
        (-1.42, 0.032, 0.058, 0.68, 0.69),
        (-1.95, 0.055, 0.140, 0.52, 0.54),
        (-2.28, 0.120, 0.290, 0.48, 0.50),
    ]
    sez_fondo = [profilo_superellisse(x, 0.0, z0, z1, ws, wt, 4.5, 4.0, n=24) for (x, z0, z1, ws, wt) in dati_fondo]
    crea_mesh_loft("Fondo_Venturi_Diffusore", sez_fondo, M_CARBON, col="Ali_Fondo_Diffusore", subsurf=2)

    for lato, suff in ((-1, "SX"), (1, "DX")):
        scatola_smussata(
            f"Fondo_Edge_Stripe_{suff}",
            (-0.15, lato * 0.788, 0.050),
            (1.95, 0.024, 0.014),
            M_ROSSO, bevel_w=0.003, col="Ali_Fondo_Diffusore"
        )
        for k, y_ch in enumerate((0.14, 0.28, 0.42)):
            scatola_smussata(
                f"Diffusore_Chiglia_{suff}_{k}",
                (-2.08, lato * y_ch, 0.14),
                (0.38, 0.009, 0.15),
                M_CARBON, rot=(0, math.radians(16), 0), bevel_w=0.002, col="Ali_Fondo_Diffusore"
            )

    # --- C. ALA POSTERIORE CON DRS ANIMABILE, SWAN-NECK & SCARICO ---
    sez_rw_main = [
        (-0.50, -2.14, 0.815, 0.24, 0.11, -12.0, -0.07),
        (-0.26, -2.13, 0.790, 0.26, 0.11, -14.0, -0.08),
        ( 0.00, -2.12, 0.780, 0.27, 0.12, -15.0, -0.08),
        ( 0.26, -2.13, 0.790, 0.26, 0.11, -14.0, -0.08),
        ( 0.50, -2.14, 0.815, 0.24, 0.11, -12.0, -0.07),
    ]
    crea_profilo_alare("AlaPost_Mainplane", sez_rw_main, M_CARBON, col="Ali_Fondo_Diffusore", subsurf=2)

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(-2.35, 0.0, 0.895))
    grp_drs = link_obj(bpy.context.object, "Ali_Fondo_Diffusore")
    grp_drs.name = "GRP_Flap_DRS"

    sez_rw_drs = [
        (-0.49, 0.09, -0.010, 0.16, 0.10, -28.0, -0.06),
        (-0.25, 0.09, -0.018, 0.17, 0.10, -30.0, -0.06),
        ( 0.00, 0.09, -0.022, 0.17, 0.10, -31.0, -0.06),
        ( 0.25, 0.09, -0.018, 0.17, 0.10, -30.0, -0.06),
        ( 0.49, 0.09, -0.010, 0.16, 0.10, -28.0, -0.06),
    ]
    crea_profilo_alare("AlaPost_Flap_DRS", sez_rw_drs, M_BIANCO, col="Ali_Fondo_Diffusore", subsurf=2, parent=grp_drs)

    scatola_smussata("DRS_Pod_Centrale", (-2.22, 0.0, 0.895), (0.19, 0.032, 0.068), M_ROSSO, bevel_w=0.009, col="Ali_Fondo_Diffusore")
    for lato in (-1, 1):
        punti_swan = [
            (-1.90, lato * 0.055, 0.45),
            (-2.02, lato * 0.055, 0.68),
            (-2.10, lato * 0.055, 0.85),
            (-2.18, lato * 0.055, 0.81),
        ]
        tubo_curvo_bezier(f"Pilone_SwanNeck_{lato}", punti_swan, 0.015, M_CARBON, col="Ali_Fondo_Diffusore")

    sez_beam = [
        (-0.48, -2.12, 0.42, 0.18, 0.10, -16.0, -0.06),
        ( 0.00, -2.10, 0.40, 0.20, 0.11, -18.0, -0.07),
        ( 0.48, -2.12, 0.42, 0.18, 0.10, -16.0, -0.06),
    ]
    crea_profilo_alare("AlaPost_BeamWing", sez_beam, M_CARBON, col="Ali_Fondo_Diffusore", subsurf=2)

    for lato, suff in ((-1, "SX"), (1, "DX")):
        dati_rw_ep = [
            (-2.10, lato * 0.505, 0.40, 0.94, 0.010, 0.010),
            (-2.28, lato * 0.512, 0.38, 0.96, 0.012, 0.010),
            (-2.46, lato * 0.502, 0.42, 0.95, 0.010, 0.008),
        ]
        sez_rw_ep = [profilo_superellisse(x, yc, z0, z1, ws, wt, 3.5, 2.5, n=18) for (x, yc, z0, z1, ws, wt) in dati_rw_ep]
        crea_mesh_loft(f"AlaPost_Endplate_{suff}", sez_rw_ep, M_ROSSO, col="Ali_Fondo_Diffusore", subsurf=2)

    # --- D. TERMINALE DI SCARICO INCONEL, WASTEGATE & LUCE PIOGGIA FIA ---
    cilindro("Scarico_Centrale_Inconel", (-2.12, 0.0, 0.485), 0.056, 0.22, M_INCONEL, asse='X', rot_extra=(0, math.radians(84), 0), col="Ali_Fondo_Diffusore")
    cilindro("Scarico_Interno_Nero",     (-2.15, 0.0, 0.488), 0.046, 0.18, M_CAVITA_NERA, asse='X', rot_extra=(0, math.radians(84), 0), col="Ali_Fondo_Diffusore")
    for lato in (-1, 1):
        cilindro(f"Wastegate_Pipe_{lato}", (-2.11, lato * 0.070, 0.455), 0.020, 0.18, M_INCONEL, asse='X', rot_extra=(0, math.radians(84), 0), col="Ali_Fondo_Diffusore")

    scatola_smussata("Crash_Structure_Rear", (-2.16, 0.0, 0.28), (0.28, 0.065, 0.15), M_CARBON, bevel_w=0.008, col="Ali_Fondo_Diffusore")
    scatola_smussata("Luce_Pioggia_FIA_LED", (-2.302, 0.0, 0.28), (0.016, 0.034, 0.115), M_LED_ROSSO, bevel_w=0.003, col="Ali_Fondo_Diffusore")

    return grp_drs


# ============================ 7. RUOTE PIRELLI 18", CERCHI CON RAZZE IN VISTA, FRENI E SOSPENSIONI ============================
def costruisci_ruote_freni_sospensioni():
    gruppi_sterzo_ant = []

    config_assi = [
        ("Ant",  1.75, 0.82, 0.360, 0.325),
        ("Post", -1.85, 0.80, 0.365, 0.415),
    ]

    for nome_asse, x_ax, y_track, r_gomma, w_gomma in config_assi:
        for lato, suff in ((-1, "SX"), (1, "DX")):
            yc = lato * y_track
            zc = r_gomma

            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(x_ax, yc, zc))
            grp_ruota = link_obj(bpy.context.object, "Ruote_Freni_Sospensioni")
            grp_ruota.name = f"GRP_Ruota_{nome_asse}_{suff}"
            if nome_asse == "Ant":
                gruppi_sterzo_ant.append(grp_ruota)

            # 1. PNEUMATICO PIRELLI P-ZERO 18" SLICK
            r_cerchio = 0.232
            hw = w_gomma * 0.5
            profilo_y_r = [
                (-hw * 0.80, r_cerchio),
                (-hw * 0.96, r_cerchio + 0.045),
                (-hw * 1.00, r_cerchio + 0.088),
                (-hw * 0.95, r_gomma - 0.014),
                (-hw * 0.78, r_gomma),
                ( 0.00,      r_gomma + 0.003),
                ( hw * 0.78, r_gomma),
                ( hw * 0.95, r_gomma - 0.014),
                ( hw * 1.00, r_cerchio + 0.088),
                ( hw * 0.96, r_cerchio + 0.045),
                ( hw * 0.80, r_cerchio),
            ]
            n_seg_ruota = 56
            sezioni_pneumatico = []
            for (yloc, rloc) in profilo_y_r:
                anello = []
                for k in range(n_seg_ruota):
                    ang = 2.0 * math.pi * k / n_seg_ruota
                    anello.append((rloc * math.cos(ang), yloc, rloc * math.sin(ang)))
                sezioni_pneumatico.append(anello)
            crea_mesh_loft(
                f"Pneumatico_Pirelli_{nome_asse}_{suff}",
                sezioni_pneumatico, M_GOMMA,
                col="Ruote_Freni_Sospensioni",
                chiudi_capi=False, ciclico_profilo=True, subsurf=1, parent=grp_ruota
            )

            # Striscia Rossa Pirelli P-Zero Soft
            for s_dir in (-1, 1):
                bpy.ops.mesh.primitive_torus_add(
                    major_radius=0.295, minor_radius=0.0085,
                    major_segments=56, minor_segments=16,
                    location=(0.0, s_dir * (hw * 0.985), 0.0),
                    rotation=(math.radians(90), 0, 0)
                )
                o_str = bpy.context.object
                o_str.name = f"Pirelli_Stripe_Soft_{nome_asse}_{suff}_{s_dir}"
                o_str.data.materials.append(M_ROSSO)
                applica_smooth(o_str, 45.0)
                link_obj(o_str, "Ruote_Freni_Sospensioni")
                o_str.parent = grp_ruota

            # 2. CERCHIO FORGIATO 18" CON CAVITA' ESTERNA E 10 RAZZE SDOPPIATE BEN VISIBILI!
            # Fondo interno scuro del canale così attraverso le razze si vedono il disco freno incandescente e la pinza Brembo!
            cilindro(
                f"Cerchio_Fondo_Interno_{nome_asse}_{suff}",
                (0, -lato * (hw * 0.18), 0), r_cerchio - 0.005, w_gomma * 0.35, M_CAVITA_NERA,
                asse='Y', vert=48, col="Ruote_Freni_Sospensioni", parent=grp_ruota
            )
            # Flangia esterna metallica del cerchio
            bpy.ops.mesh.primitive_torus_add(
                major_radius=r_cerchio, minor_radius=0.015,
                major_segments=48, minor_segments=16,
                location=(0, lato * (hw * 0.80), 0),
                rotation=(math.radians(90), 0, 0)
            )
            o_fl = bpy.context.object
            o_fl.name = f"Cerchio_Flangia_{nome_asse}_{suff}"
            o_fl.data.materials.append(M_ALLUMINIO)
            applica_smooth(o_fl, 45.0)
            link_obj(o_fl, "Ruote_Freni_Sospensioni")
            o_fl.parent = grp_ruota

            # 10 Razze Sdoppiate a Y in alluminio forgiato sul lato esterno (completamente visibili!)
            y_in_razza  = lato * (hw * 0.62)
            y_out_razza = lato * (hw * 0.78)
            for ir in range(10):
                ang = math.radians(ir * 36.0)
                p_in = (0.062 * math.cos(ang), y_in_razza, 0.062 * math.sin(ang))
                for s_fork in (-0.11, 0.11):
                    p_out = ((r_cerchio - 0.012) * math.cos(ang + s_fork), y_out_razza, (r_cerchio - 0.012) * math.sin(ang + s_fork))
                    asta_alare_tra(
                        f"Cerchio_Razza_{nome_asse}_{suff}_{ir}_{s_fork}",
                        p_in, p_out, 0.018, 0.011, M_ALLUMINIO,
                        col="Ruote_Freni_Sospensioni", parent=grp_ruota
                    )

            # Mozzo centrale in carbonio + Dado Centerlock anodizzato
            cilindro(
                f"Mozzo_Centrale_{nome_asse}_{suff}",
                (0, lato * (hw * 0.62), 0), 0.068, 0.05, M_CARBON,
                asse='Y', vert=32, col="Ruote_Freni_Sospensioni", parent=grp_ruota
            )
            cilindro(
                f"Dado_Ruota_Centerlock_{nome_asse}_{suff}",
                (0, lato * (hw * 0.72), 0), 0.036, 0.048, M_ROSSO if lato < 0 else M_ALLUMINIO,
                asse='Y', vert=6, bevel_w=0.003, col="Ruote_Freni_Sospensioni", parent=grp_ruota
            )

            # 3. DISCO FRENO CARBOCERAMICO INCANDESCENTE E PINZA BREMBO ROSSA (Visibili dietro le razze!)
            y_freno = lato * (hw * 0.35)
            cilindro(
                f"Disco_Freno_{nome_asse}_{suff}",
                (0, y_freno, 0), 0.175, 0.032, M_DISCO_CARB,
                asse='Y', vert=48, col="Ruote_Freni_Sospensioni", parent=grp_ruota
            )
            bpy.ops.mesh.primitive_torus_add(
                major_radius=0.138, minor_radius=0.022,
                major_segments=48, minor_segments=12,
                location=(0, y_freno + lato * 0.012, 0), rotation=(math.radians(90), 0, 0)
            )
            o_gl = bpy.context.object
            o_gl.name = f"Disco_Glow_{nome_asse}_{suff}"
            o_gl.data.materials.append(M_FRENO_GLOW)
            applica_smooth(o_gl, 40.0)
            link_obj(o_gl, "Ruote_Freni_Sospensioni")
            o_gl.parent = grp_ruota

            # Pinza Freno Brembo a 6 pistoncini visibile attraverso i raggi del cerchio!
            scatola_smussata(
                f"Pinza_Brembo_{nome_asse}_{suff}",
                (0.118 if nome_asse == "Ant" else -0.118, y_freno + lato * 0.015, 0.025),
                (0.082, 0.068, 0.145),
                M_PINZA_BREMBO, bevel_w=0.008, col="Ruote_Freni_Sospensioni", parent=grp_ruota
            )
            scatola_smussata(
                f"Brake_Duct_Scoop_{nome_asse}_{suff}",
                (0.08, -lato * (hw * 0.62), 0.04),
                (0.18, 0.045, 0.22),
                M_CARBON, bevel_w=0.008, col="Ruote_Freni_Sospensioni", parent=grp_ruota
            )

            # 4. BRACCI SOSPENSIONE A PROFILO ALARE
            y_scocca = lato * (0.20 if nome_asse == "Ant" else 0.12)
            y_mozzo  = lato * (y_track - hw * 0.58)
            z_up_in, z_up_out = (0.48, 0.46) if nome_asse == "Ant" else (0.44, 0.45)
            z_lo_in, z_lo_out = (0.22, 0.24) if nome_asse == "Ant" else (0.21, 0.24)

            asta_alare_tra(
                f"Wishbone_Up_Front_{nome_asse}_{suff}",
                (x_ax + 0.24, y_scocca, z_up_in), (x_ax, y_mozzo, z_up_out),
                0.052, 0.011, M_CARBON, col="Ruote_Freni_Sospensioni"
            )
            asta_alare_tra(
                f"Wishbone_Up_Rear_{nome_asse}_{suff}",
                (x_ax - 0.24, y_scocca, z_up_in - 0.02), (x_ax, y_mozzo, z_up_out),
                0.052, 0.011, M_CARBON, col="Ruote_Freni_Sospensioni"
            )
            asta_alare_tra(
                f"Wishbone_Lo_Front_{nome_asse}_{suff}",
                (x_ax + 0.22, y_scocca, z_lo_in), (x_ax, y_mozzo, z_lo_out),
                0.055, 0.012, M_CARBON, col="Ruote_Freni_Sospensioni"
            )
            asta_alare_tra(
                f"Wishbone_Lo_Rear_{nome_asse}_{suff}",
                (x_ax - 0.26, y_scocca, z_lo_in), (x_ax, y_mozzo, z_lo_out),
                0.055, 0.012, M_CARBON, col="Ruote_Freni_Sospensioni"
            )
            asta_alare_tra(
                f"PushRod_{nome_asse}_{suff}",
                (x_ax + 0.08, y_scocca, 0.54 if nome_asse == "Ant" else 0.50),
                (x_ax, y_mozzo, z_lo_out + 0.02),
                0.032, 0.014, M_CARBON, col="Ruote_Freni_Sospensioni"
            )
            asta_alare_tra(
                f"TrackRod_Driveshaft_{nome_asse}_{suff}",
                (x_ax + (0.12 if nome_asse == "Ant" else 0.0), y_scocca, 0.36),
                (x_ax + (0.08 if nome_asse == "Ant" else 0.0), y_mozzo, 0.36),
                0.038, 0.024 if nome_asse == "Post" else 0.011, M_CARBON, col="Ruote_Freni_Sospensioni"
            )

    return gruppi_sterzo_ant


# ============================ 8. AMBIENTAZIONE SHOWROOM / PIT-LANE E LUCI CINEMATOGRAFICHE ============================
def costruisci_studio_e_luci():
    world = bpy.data.worlds.new("Showroom_F1_World")
    S.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.006, 0.008, 0.014, 1.0)
        bg.inputs["Strength"].default_value = 0.70

    scatola_smussata("Pavimento_Showroom", (0.0, 0.0, -0.04), (24.0, 24.0, 0.08), M_ASFALTO, bevel_w=0.01, col="Studio_Pista_Luci")

    scatola_smussata("Griglia_Start_Front", (3.25, 0.0, 0.001), (0.09, 2.35, 0.003), M_BIANCO, bevel_w=0.0, col="Studio_Pista_Luci")
    for lato in (-1, 1):
        scatola_smussata(f"Griglia_Start_Lat_{lato}", (2.40, lato * 1.15, 0.001), (1.75, 0.09, 0.003), M_BIANCO, bevel_w=0.0, col="Studio_Pista_Luci")

    for lato in (-1, 1):
        for i in range(18):
            kx = -5.5 + i * 0.65
            m_k = M_ROSSO if i % 2 == 0 else M_BIANCO
            scatola_smussata(
                f"Cordolo_F1_{lato}_{i}",
                (kx, lato * 3.85, 0.018),
                (0.64, 0.48, 0.045),
                m_k, rot=(math.radians(lato * -5), 0, 0), bevel_w=0.006, col="Studio_Pista_Luci"
            )

    # Barre LED Showroom sopra l'auto per riflessi automobilistici nitidi
    scatola_smussata("LightBar_Centrale_Top", (0.2, 0.0, 3.85), (6.8, 0.28, 0.04), M_LUCE_STUDIO, bevel_w=0.005, col="Studio_Pista_Luci")
    for lato in (-1, 1):
        scatola_smussata(
            f"LightBar_Lat_{lato}",
            (0.2, lato * 2.35, 2.85),
            (6.5, 0.20, 0.04),
            M_LUCE_STUDIO, rot=(math.radians(lato * 32), 0, 0), bevel_w=0.005, col="Studio_Pista_Luci"
        )

    def crea_area_light(nome, pos, rot_deg, energia, sx, sy, col_rgb):
        bpy.ops.object.light_add(type='AREA', location=pos, rotation=tuple(math.radians(a) for a in rot_deg))
        l = link_obj(bpy.context.object, "Studio_Pista_Luci")
        l.name = nome
        l.data.shape = 'RECTANGLE'
        l.data.size = sx
        l.data.size_y = sy
        l.data.energy = energia
        l.data.color = col_rgb
        return l

    # Luci calibrate per non bruciare il Rosso Corsa e far risaltare le curve e il cockpit!
    crea_area_light("Key_Overhead_Main",   ( 0.3,  0.0, 3.70), (0, 0, 0),       580.0, 6.2, 1.4, (1.00, 0.97, 0.93))
    crea_area_light("Rim_Side_SX",         ( 0.2, -3.6, 2.10), (-58, 0, 0),      420.0, 5.8, 1.1, (0.85, 0.92, 1.00))
    crea_area_light("Rim_Side_DX",         ( 0.2,  3.6, 2.10), ( 58, 0, 0),      420.0, 5.8, 1.1, (1.00, 0.94, 0.88))
    crea_area_light("Front_Hero_Light",    ( 5.2, -1.8, 1.80), (62, 0, -110),    340.0, 3.2, 1.5, (0.92, 0.96, 1.00))
    crea_area_light("Rear_Diffuser_Light", (-5.0,  1.6, 1.75), (62, 0, 70),      390.0, 3.2, 1.5, (1.00, 0.90, 0.82))
    crea_area_light("Cockpit_Interior_Spot", (0.15, -0.45, 1.35), (-18, 12, 0),  110.0, 0.70, 0.70, (1.00, 0.98, 0.95))


# ============================ 9. ANIMAZIONE 10 SECONDI (300 FRAME: ORBITA + ZOOM COCKPIT + DRS) ============================
def imposta_animazione_10_secondi(grp_volante, gruppi_sterzo_ant, grp_drs):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.45, 0.0, 0.45))
    target = link_obj(bpy.context.object, "Studio_Pista_Luci")
    target.name = "Camera_Target_F1"

    bpy.ops.object.camera_add(location=(4.2, -3.2, 1.25))
    cam = link_obj(bpy.context.object, "Studio_Pista_Luci")
    cam.name = "Camera_Showcase_F1"
    cam.data.lens = 38.0
    cam.data.clip_start = 0.03
    cam.data.clip_end = 150.0

    ct = cam.constraints.new(type='TRACK_TO')
    ct.target = target
    ct.track_axis = 'TRACK_NEGATIVE_Z'
    ct.up_axis = 'UP_Y'
    S.camera = cam

    kf_target = [
        (1,   ( 0.55,  0.00, 0.38)),  # Hero Shot anteriore
        (45,  ( 1.35, -0.15, 0.36)),  # Zoom muso, ala anteriore e sospensione push-rod
        (85,  ( 0.35,  0.00, 0.45)),  # Avvicinamento al cockpit
        (120, ( 0.34,  0.02, 0.44)),  # ZOOM DRITTO SUL FRONTALE DEL VOLANTE OLED + MANETTINI + SEDILE!
        (155, ( 0.08,  0.00, 0.36)),  # ZOOM SUL SEDILE IN ALCANTARA E CINTURE ROSSI SABELT A 6 PUNTI!
        (195, (-0.85,  0.00, 0.46)),  # Scorre sulle pance sidepods e cofano motore
        (235, (-1.85,  0.00, 0.52)),  # Zoom retrotreno (Ala DRS aperta, scarico Inconel, diffusore, luce FIA)
        (275, ( 0.25,  0.00, 0.42)),  # Orbita ampia lato destro
        (300, ( 0.45,  0.00, 0.40)),  # Chiusura Hero Shot 3/4
    ]

    kf_cam = [
        # (frame, pos_camera,                 lens_mm)
        (1,      ( 4.35, -3.25, 1.18),        36.0),  # Hero Shot 3/4 Anteriore SX
        (45,     ( 3.15, -2.55, 0.85),        45.0),  # Orbita bassa ravvicinata su muso e ruota anteriore
        (85,     ( 0.85, -1.65, 1.18),        40.0),  # Sale verso l'abitacolo
        (120,    (-0.08, -0.44, 0.69),        34.0),  # Sotto l'arco dell'Halo: inquadra in pieno il Display OLED del volante e i comandi!
        (155,    ( 0.48, -0.52, 0.72),        35.0),  # Inquadra il sedile anatomico, le cinture a 6 punti con fibbia e il cockpit!
        (195,    (-2.45, -2.85, 1.30),        40.0),  # Orbita verso il 3/4 posteriore SX
        (235,    (-4.15,  1.65, 1.02),        46.0),  # Vista posteriore DX ravvicinata su Diffusore, Scarico e Ala DRS aperta!
        (275,    ( 0.85,  4.25, 1.32),        38.0),  # Orbita ampia sul lato destro
        (300,    ( 4.15,  3.10, 1.22),        38.0),  # Chiusura 3/4 Anteriore DX maestosa
    ]

    for fr, tpos in kf_target:
        target.location = tpos
        target.keyframe_insert(data_path="location", frame=fr)

    for fr, cpos, l_mm in kf_cam:
        cam.location = cpos
        cam.keyframe_insert(data_path="location", frame=fr)
        cam.data.lens = l_mm
        cam.data.keyframe_insert(data_path="lens", frame=fr)

    # Animazione Volante + Ruote Anteriori
    base_rot_vol = Euler((0, math.radians(62), 0), 'XYZ')
    kf_sterzo = [
        (1,   0.0),
        (85,  0.0),
        (115, 16.0),
        (145, -16.0),
        (170, 0.0),
        (300, 0.0),
    ]
    for fr, ang_deg in kf_sterzo:
        mat_rot = base_rot_vol.to_matrix().to_4x4() @ Matrix.Rotation(math.radians(ang_deg * 2.0), 4, 'Z')
        grp_volante.rotation_euler = mat_rot.to_euler()
        grp_volante.keyframe_insert(data_path="rotation_euler", frame=fr)
        for gr in gruppi_sterzo_ant:
            gr.rotation_euler = (0, 0, math.radians(-ang_deg * 0.65))
            gr.keyframe_insert(data_path="rotation_euler", frame=fr)

    # Animazione Apertura Flap DRS (Frame 195..255)
    kf_drs = [
        (1,   0.0),
        (195, 0.0),
        (215, 22.0),
        (245, 22.0),
        (265, 0.0),
        (300, 0.0),
    ]
    for fr, drs_deg in kf_drs:
        grp_drs.rotation_euler = (0, math.radians(drs_deg), 0)
        grp_drs.keyframe_insert(data_path="rotation_euler", frame=fr)

    for obj in (target, cam, cam.data, grp_volante, grp_drs, *gruppi_sterzo_ant):
        ad = getattr(obj, "animation_data", None)
        if ad and ad.action:
            try:
                for fc in ad.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'BEZIER'
                        kp.handle_left_type = 'AUTO_CLAMPED'
                        kp.handle_right_type = 'AUTO_CLAMPED'
            except Exception:
                pass


# ============================ 10. ESECUZIONE, SALVATAGGIO BLEND E RENDER ============================
costruisci_carrozzeria_sinuosa()
grp_volante = costruisci_interni_cockpit()
grp_drs = costruisci_ali_e_fondo()
gruppi_sterzo_ant = costruisci_ruote_freni_sospensioni()
costruisci_studio_e_luci()
imposta_animazione_10_secondi(grp_volante, gruppi_sterzo_ant, grp_drs)

S.render.engine = 'BLENDER_EEVEE'
S.render.resolution_x = 1280
S.render.resolution_y = 720
S.render.resolution_percentage = 100
S.render.image_settings.file_format = 'PNG'

try:
    S.eevee.taa_render_samples = 16
except Exception:
    pass

try:
    S.view_settings.view_transform = 'AgX'
    S.view_settings.look = 'AgX - High Contrast'
except Exception:
    pass

blend_path = os.path.join(CARTELLA, "f1_macchina_bella.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("FILE BLEND SALVATO IN:", blend_path)

if SOLO_PREVIEW:
    for fr, nome_img in [
        (1,   "preview_1_anteriore.png"),
        (120, "preview_2_zoom_interni_cockpit.png"),
        (155, "preview_2b_sedile_cinture.png"),
        (235, "preview_3_posteriore_drs.png"),
        (285, "preview_4_panoramica_3_4.png"),
    ]:
        S.frame_set(fr)
        S.render.filepath = os.path.join(CARTELLA, nome_img)
        bpy.ops.render.render(write_still=True)
    print("RENDER ANTEPRIME COMPLETATO")
else:
    frames_dir = os.path.join(CARTELLA, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    S.render.filepath = os.path.join(frames_dir, "frame_")
    bpy.ops.render.render(animation=True)
    print("RENDER ANIMAZIONE 300 FRAME COMPLETATO")
