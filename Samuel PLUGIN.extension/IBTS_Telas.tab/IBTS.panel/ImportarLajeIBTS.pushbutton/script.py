# -*- coding: utf-8 -*-
"""Importar Laje IBTS
Abre dialogo de arquivo para selecionar DWGs, importa, explode
e cria Laje Estrutural com parametros da tela soldada IBTS.
"""
__title__ = 'Importar\nLaje IBTS'
__author__ = 'Plugin IBTS'

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
import System.Windows.Forms as WinForms
import System.Drawing as Drawing

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# ─────────────────────────────────────────────────────────────────
# CATÁLOGO IBTS  CA-60  —  painéis 2,45 × 6,00 m
# ─────────────────────────────────────────────────────────────────
CATALOGO = [
    ("Q61",   15,15, 3.4, 3.4, 0.61,0.61, 0.97, "61"),
    ("Q75",   15,15, 3.8, 3.8, 0.75,0.75, 1.27, "75"),
    ("Q92",   15,15, 4.2, 4.2, 0.92,0.92, 1.48, "92"),
    ("L92",   30,15, 4.2, 4.2, 0.46,0.92, 1.12, "92"),
    ("Q113",  10,10, 3.8, 3.8, 1.13,1.13, 1.80, "113"),
    ("L113",  10,30, 3.8, 3.8, 1.13,0.38, 1.21, "113"),
    ("T113",  30,10, 3.8, 3.8, 0.38,1.13, 1.22, "113"),
    ("Q138",  10,10, 4.2, 4.2, 1.38,1.38, 2.20, "138"),
    ("R138",  10,15, 4.2, 4.2, 1.38,0.92, 1.83, "138"),
    ("M138",  10,20, 4.2, 4.2, 1.38,0.69, 1.65, "138"),
    ("L138",  10,30, 4.2, 4.2, 1.38,0.46, 1.47, "138"),
    ("T138",  30,10, 4.2, 4.2, 0.46,1.38, 1.49, "138"),
    ("Q159",  10,10, 4.5, 4.5, 1.59,1.59, 2.52, "159"),
    ("R159",  10,15, 4.5, 4.5, 1.59,1.06, 2.11, "159"),
    ("M159",  10,20, 4.5, 4.5, 1.59,0.79, 1.90, "159"),
    ("L159",  10,30, 4.5, 4.5, 1.59,0.53, 1.69, "159"),
    ("Q196",  10,10, 5.0, 5.0, 1.96,1.96, 3.11, "196"),
    ("R196",  10,15, 5.0, 5.0, 1.96,1.30, 2.60, "196"),
    ("M196",  10,20, 5.0, 5.0, 1.96,0.98, 2.34, "196"),
    ("L196",  10,30, 5.0, 5.0, 1.96,0.65, 2.09, "196"),
    ("T196",  30,10, 5.0, 5.0, 0.65,1.96, 2.11, "196"),
    ("Q246",  10,10, 5.6, 5.6, 2.46,2.46, 3.91, "246"),
    ("R246",  10,15, 5.6, 5.6, 2.46,1.64, 3.26, "246"),
    ("M246",  10,20, 5.6, 5.6, 2.46,1.23, 2.94, "246"),
    ("L246",  10,30, 5.6, 5.6, 2.46,0.82, 2.62, "246"),
    ("T246",  30,10, 5.6, 5.6, 0.82,2.46, 2.64, "246"),
    ("Q283",  10,10, 6.0, 6.0, 2.83,2.83, 4.48, "283"),
    ("R283",  10,15, 6.0, 6.0, 2.83,1.88, 3.74, "283"),
    ("M283",  10,20, 6.0, 6.0, 2.83,1.41, 3.37, "283"),
    ("L283",  10,30, 6.0, 6.0, 2.83,0.94, 3.00, "283"),
    ("T283",  30,10, 6.0, 6.0, 0.94,2.83, 3.03, "283"),
    ("Q335",  15,15, 8.0, 8.0, 3.35,3.35, 5.37, "335"),
    ("L335",  15,30, 8.0, 6.0, 3.35,0.94, 3.48, "335"),
    ("T335",  30,15, 6.0, 8.0, 0.94,3.35, 3.45, "335"),
    ("Q396",  10,10, 7.1, 7.1, 3.96,3.96, 6.28, "396"),
    ("R396",  10,15, 7.1, 7.1, 3.96,2.64, 5.24, "396"),
    ("M396",  10,20, 7.1, 7.1, 3.96,1.98, 4.73, "396"),
    ("L396",  10,30, 7.1, 6.0, 3.96,0.94, 3.91, "396"),
    ("T396",  30,10, 6.0, 7.1, 0.94,3.96, 3.92, "396"),
    ("Q503",  10,10, 8.0, 8.0, 5.03,5.03, 7.97, "503"),
    ("R503",  10,15, 8.0, 8.0, 5.03,3.35, 6.66, "503"),
    ("M503",  10,20, 8.0, 8.0, 5.03,2.51, 6.00, "503"),
    ("L503",  10,30, 8.0, 6.0, 5.03,0.94, 4.77, "503"),
    ("T503",  30,10, 6.0, 8.0, 0.94,5.03, 4.76, "503"),
    ("Q636",  10,10, 9.0, 9.0, 6.36,6.36,10.09, "636"),
    ("L636",  10,30, 9.0, 6.0, 6.36,0.94, 5.84, "636"),
    ("Q785",  10,10,10.0,10.0, 7.85,7.85,12.46, "785"),
    ("L785",  10,30,10.0, 6.0, 7.85,0.94, 7.03, "785"),
]

RELACOES = ["Positiva", "Negativa", "Positiva + Negativa"]

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def get_floor_types():
    col = FilteredElementCollector(doc).OfClass(FloorType).ToElements()
    result = []
    for ft in col:
        p = ft.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p:
            result.append((p.AsString(), ft.Id))
    return result


def get_levels():
    col = FilteredElementCollector(doc).OfClass(Level).ToElements()
    return sorted(col, key=lambda l: l.Elevation)


def import_and_explode_dwg(filepath, level):
    """Importa o DWG em metros e explode parcialmente. Retorna o ElementId do import."""
    opts = DWGImportOptions()
    opts.Unit        = ImportUnit.Meter
    opts.Placement   = ImportPlacement.Origin
    opts.ColorMode   = ImportColorMode.BlackAndWhite

    imp_id = ElementId.InvalidElementId
    with Transaction(doc, "IBTS - Importar DWG") as t:
        t.Start()
        try:
            success, imp_id = doc.Import(filepath, opts, doc.ActiveView, imp_id)
            t.Commit()
        except Exception as ex:
            t.RollBack()
            return None, str(ex)

    if imp_id == ElementId.InvalidElementId:
        return None, "Falha ao importar: " + filepath

    # Explodir parcialmente
    with Transaction(doc, "IBTS - Explodir DWG") as t:
        t.Start()
        try:
            imp_elem = doc.GetElement(imp_id)
            # PartialExplode retorna ids dos elementos gerados
            new_ids = imp_elem.ExplodeToMany(False)  # False = parcial
            t.Commit()
            # Retorna os ids gerados pela explosão
            return list(new_ids), None
        except Exception:
            # Se ExplodeToMany não existir nesta versão, mantém o import
            t.RollBack()
            return [imp_id], None


def get_boundary_from_ids(elem_ids):
    """Extrai CurveArray do conjunto de elementos (linhas do DWG explodido)."""
    curves = []
    for eid in elem_ids:
        elem = doc.GetElement(eid)
        if elem is None:
            continue
        # Elementos de detalhe (DetailCurve, DetailLine, etc.)
        if hasattr(elem, 'GeometryCurve'):
            try:
                curves.append(elem.GeometryCurve)
                continue
            except Exception:
                pass
        # Fallback: geometria bruta
        try:
            opts = Options()
            geom = elem.get_Geometry(opts)
            for obj in geom:
                if isinstance(obj, GeometryInstance):
                    for sub in obj.GetInstanceGeometry():
                        if isinstance(sub, Curve):
                            curves.append(sub)
                elif isinstance(obj, Curve):
                    curves.append(obj)
        except Exception:
            pass

    if not curves:
        return None

    ca = CurveArray()
    for c in curves[:200]:
        ca.Append(c)
    return ca


def get_boundary_from_import(imp_id):
    """Fallback: BoundingBox do ImportInstance."""
    imp = doc.GetElement(imp_id)
    if imp is None:
        return None
    bb = imp.get_BoundingBox(None)
    if not bb:
        return None
    mn, mx = bb.Min, bb.Max
    ca = CurveArray()
    ca.Append(Line.CreateBound(XYZ(mn.X,mn.Y,mn.Z), XYZ(mx.X,mn.Y,mn.Z)))
    ca.Append(Line.CreateBound(XYZ(mx.X,mn.Y,mn.Z), XYZ(mx.X,mx.Y,mn.Z)))
    ca.Append(Line.CreateBound(XYZ(mx.X,mx.Y,mn.Z), XYZ(mn.X,mx.Y,mn.Z)))
    ca.Append(Line.CreateBound(XYZ(mn.X,mx.Y,mn.Z), XYZ(mn.X,mn.Y,mn.Z)))
    return ca


def set_params(floor, row, relacao, invertida):
    desig, el, et, dl, dt, sl, st, kg, serie = row
    p = floor.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if p and not p.IsReadOnly:
        p.Set("IBTS {} | {} | L:{}cm ø{}mm {:.2f}cm²/m | T:{}cm ø{}mm {:.2f}cm²/m | {}kg/m²{}".format(
            desig, relacao, el, dl, sl, et, dt, st, kg,
            " [INV]" if invertida else ""))
    mapa = {
        "IBTS_Designacao"   : desig,
        "IBTS_Serie"        : serie,
        "IBTS_Relacao"      : relacao,
        "IBTS_Espacamento_L": "{} cm".format(el),
        "IBTS_Espacamento_T": "{} cm".format(et),
        "IBTS_Diametro_L"   : "{} mm".format(dl),
        "IBTS_Diametro_T"   : "{} mm".format(dt),
        "IBTS_Secao_L"      : "{} cm2/m".format(sl),
        "IBTS_Secao_T"      : "{} cm2/m".format(st),
        "IBTS_Peso"         : "{} kg/m2".format(kg),
    }
    for nome, val in mapa.items():
        p2 = floor.LookupParameter(nome)
        if p2 and not p2.IsReadOnly:
            p2.Set(val)


# ─────────────────────────────────────────────────────────────────
# JANELA
# ─────────────────────────────────────────────────────────────────

class ImportarLajeForm(WinForms.Form):

    AZUL  = Drawing.Color.FromArgb(24, 80, 150)
    CINZA = Drawing.Color.FromArgb(245, 245, 248)

    def __init__(self, floor_types, levels):
        self._floor_types  = floor_types
        self._levels       = levels
        self._dwg_paths    = []   # caminhos selecionados pelo usuário
        self.resultado     = None

        self.Text            = "ADAP.PC — Inserir telas de laje (IBTS)"
        self.Width           = 460
        self.Height          = 100   # ajustado ao final
        self.FormBorderStyle = WinForms.FormBorderStyle.FixedDialog
        self.MaximizeBox     = False
        self.StartPosition   = WinForms.FormStartPosition.CenterScreen
        self.BackColor       = self.CINZA
        self.Font            = Drawing.Font("Segoe UI", 9)

        y = 16
        # Cabeçalho
        lbl = WinForms.Label()
        lbl.Text      = "IBTS — Inserir Telas de Laje"
        lbl.Font      = Drawing.Font("Segoe UI", 12, Drawing.FontStyle.Bold)
        lbl.ForeColor = self.AZUL
        lbl.Location  = Drawing.Point(20, y)
        lbl.Size      = Drawing.Size(410, 26)
        self.Controls.Add(lbl)
        y += 26

        sub = WinForms.Label()
        sub.Text      = "CA-60  |  Painel 2,45 × 6,00 m  |  Modelo Estrutural"
        sub.ForeColor = Drawing.Color.Gray
        sub.Location  = Drawing.Point(20, y)
        sub.Size      = Drawing.Size(410, 16)
        self.Controls.Add(sub)
        y += 22

        sep = WinForms.Label()
        sep.BorderStyle = WinForms.BorderStyle.Fixed3D
        sep.Location    = Drawing.Point(20, y)
        sep.Size        = Drawing.Size(410, 2)
        self.Controls.Add(sep)
        y += 12

        # Tipo de tela
        y = self._lbl("Tipo de tela:", y)
        self.cb_tela = self._combo([r[0] for r in CATALOGO], y)
        self.cb_tela.SelectedIndexChanged += self._refresh_info
        y += 28

        # Relação + Inverter
        y = self._lbl("Relação:", y)
        self.cb_rel = self._combo(RELACOES, y, width=180)
        self.chk_inv = WinForms.CheckBox()
        self.chk_inv.Text     = "Inverter  (L ↔ T)"
        self.chk_inv.Location = Drawing.Point(215, y + 2)
        self.chk_inv.Size     = Drawing.Size(150, 20)
        self.chk_inv.CheckedChanged += self._refresh_info
        self.Controls.Add(self.chk_inv)
        y += 28

        # Info card
        self.pnl = WinForms.Panel()
        self.pnl.Location    = Drawing.Point(20, y)
        self.pnl.Size        = Drawing.Size(410, 90)
        self.pnl.BackColor   = Drawing.Color.White
        self.pnl.BorderStyle = WinForms.BorderStyle.FixedSingle
        self.Controls.Add(self.pnl)
        self.lbl_info = WinForms.Label()
        self.lbl_info.Font     = Drawing.Font("Consolas", 8.5)
        self.lbl_info.Location = Drawing.Point(8, 6)
        self.lbl_info.Size     = Drawing.Size(394, 80)
        self.pnl.Controls.Add(self.lbl_info)
        y += 98

        # Selecionar DWGs — botão que abre o explorador
        y = self._lbl("Selecionar DWGs:", y)

        self.lst_dwg = WinForms.ListBox()
        self.lst_dwg.Location = Drawing.Point(20, y)
        self.lst_dwg.Size     = Drawing.Size(310, 64)
        self.Controls.Add(self.lst_dwg)

        btn_browse = WinForms.Button()
        btn_browse.Text      = "Abrir\narquivos..."
        btn_browse.Location  = Drawing.Point(338, y)
        btn_browse.Size      = Drawing.Size(92, 64)
        btn_browse.BackColor = Drawing.Color.FromArgb(220, 235, 255)
        btn_browse.FlatStyle = WinForms.FlatStyle.Flat
        btn_browse.Click    += self._browse_dwg
        self.Controls.Add(btn_browse)

        btn_limpar = WinForms.Button()
        btn_limpar.Text      = "✕ Limpar"
        btn_limpar.Location  = Drawing.Point(20, y + 66)
        btn_limpar.Size      = Drawing.Size(80, 22)
        btn_limpar.FlatStyle = WinForms.FlatStyle.Flat
        btn_limpar.Click    += self._limpar_dwg
        self.Controls.Add(btn_limpar)
        y += 96

        # Tipo de Piso
        y = self._lbl("Selecionar Piso (Floor Type):", y)
        self.cb_floor = self._combo([n for n, _ in floor_types], y)
        y += 28

        # Nível
        y = self._lbl("Nível:", y)
        self.cb_nivel = self._combo([lv.Name for lv in levels], y)
        y += 36

        # Botões OK / Cancelar
        btn_ok = WinForms.Button()
        btn_ok.Text      = "OK"
        btn_ok.Location  = Drawing.Point(250, y)
        btn_ok.Size      = Drawing.Size(88, 30)
        btn_ok.BackColor = self.AZUL
        btn_ok.ForeColor = Drawing.Color.White
        btn_ok.FlatStyle = WinForms.FlatStyle.Flat
        btn_ok.Click    += self._on_ok
        self.Controls.Add(btn_ok)

        btn_cancel = WinForms.Button()
        btn_cancel.Text     = "Cancelar"
        btn_cancel.Location = Drawing.Point(348, y)
        btn_cancel.Size     = Drawing.Size(82, 30)
        btn_cancel.Click   += lambda s, e: self.Close()
        self.Controls.Add(btn_cancel)

        self.Height = y + 72
        self._refresh_info(None, None)

    # ── UI helpers ────────────────────────────────────

    def _lbl(self, text, y):
        lbl = WinForms.Label()
        lbl.Text     = text
        lbl.Font     = Drawing.Font("Segoe UI", 9, Drawing.FontStyle.Bold)
        lbl.Location = Drawing.Point(20, y)
        lbl.Size     = Drawing.Size(410, 17)
        self.Controls.Add(lbl)
        return y + 18

    def _combo(self, items, y, width=410):
        cb = WinForms.ComboBox()
        cb.Location      = Drawing.Point(20, y)
        cb.Size          = Drawing.Size(width, 24)
        cb.DropDownStyle = WinForms.ComboBoxStyle.DropDownList
        for it in items:
            cb.Items.Add(it)
        if items:
            cb.SelectedIndex = 0
        self.Controls.Add(cb)
        return cb

    # ── Lógica ────────────────────────────────────────

    def _get_row(self):
        idx = self.cb_tela.SelectedIndex
        if idx < 0:
            return None
        row = list(CATALOGO[idx])
        if self.chk_inv.Checked:
            row[1],row[2] = row[2],row[1]
            row[3],row[4] = row[4],row[3]
            row[5],row[6] = row[6],row[5]
        return row

    def _refresh_info(self, s, e):
        row = self._get_row()
        if not row:
            return
        desig, el, et, dl, dt, sl, st, kg, serie = row
        inv = "  ← INVERTIDA" if self.chk_inv.Checked else ""
        self.lbl_info.Text = (
            "Designação : {}{}\n"
            "Série      : {}    Painel : 2,45 × 6,00 m\n"
            "Espaç. L/T : {} / {} cm    Diâm. L/T : {} / {} mm\n"
            "Seção  L   : {} cm²/m      Seção T   : {} cm²/m\n"
            "Peso       : {} kg/m²"
        ).format(desig, inv, serie, el, et, dl, dt, sl, st, kg)

    def _browse_dwg(self, s, e):
        dlg = WinForms.OpenFileDialog()
        dlg.Title       = "Selecionar DWG(s) do IBTS"
        dlg.Filter      = "Arquivos DWG (*.dwg)|*.dwg"
        dlg.Multiselect = True
        if dlg.ShowDialog() == WinForms.DialogResult.OK:
            for path in dlg.FileNames:
                if path not in self._dwg_paths:
                    self._dwg_paths.append(path)
                    import System.IO as IO
                    self.lst_dwg.Items.Add(IO.Path.GetFileName(path))

    def _limpar_dwg(self, s, e):
        self._dwg_paths = []
        self.lst_dwg.Items.Clear()

    def _on_ok(self, s, e):
        if not self._dwg_paths:
            WinForms.MessageBox.Show(
                "Clique em 'Abrir arquivos...' e selecione ao menos um DWG.",
                "Atenção")
            return
        if self.cb_floor.SelectedIndex < 0:
            WinForms.MessageBox.Show("Selecione um Tipo de Piso.", "Atenção")
            return
        self.resultado = {
            "tela"      : self._get_row(),
            "invertida" : self.chk_inv.Checked,
            "relacao"   : self.cb_rel.SelectedItem,
            "dwg_paths" : list(self._dwg_paths),
            "floor_id"  : self._floor_types[self.cb_floor.SelectedIndex][1],
            "level"     : self._levels[self.cb_nivel.SelectedIndex],
        }
        self.DialogResult = WinForms.DialogResult.OK
        self.Close()


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

floor_types = get_floor_types()
levels      = get_levels()

if not floor_types:
    TaskDialog.Show("Aviso", "Nenhum Tipo de Piso encontrado no modelo.")
else:
    form = ImportarLajeForm(floor_types, levels)
    form.ShowDialog()

    if form.resultado:
        res     = form.resultado
        tela    = res["tela"]
        relacao = res["relacao"]
        inv     = res["invertida"]
        level   = res["level"]
        ft      = doc.GetElement(res["floor_id"])
        criados = 0
        erros   = []

        for path in res["dwg_paths"]:
            # 1. Importar + explodir
            elem_ids, err = import_and_explode_dwg(path, level)
            if err or not elem_ids:
                erros.append("{}: {}".format(path, err or "sem elementos"))
                continue

            # 2. Extrair contorno
            curves = get_boundary_from_ids(elem_ids)
            if not curves:
                # tenta fallback no ImportInstance (se não explodiu)
                imp_col = FilteredElementCollector(doc)\
                          .OfClass(ImportInstance).ToElements()
                for imp in imp_col:
                    curves = get_boundary_from_import(imp.Id)
                    if curves:
                        break
            if not curves:
                erros.append("{}: contorno não encontrado".format(path))
                continue

            # 3. Criar piso
            with Transaction(doc, "IBTS - Laje {} ({})".format(tela[0], relacao)) as t:
                t.Start()
                try:
                    new_floor = doc.Create.NewFloor(curves, ft, level, False)
                    set_params(new_floor, tela, relacao, inv)
                    t.Commit()
                    criados += 1
                except Exception as ex:
                    t.RollBack()
                    erros.append("{}: {}".format(path, str(ex)))

        msg = "{} piso(s) criado(s) com tela {}  [{}]{}.".format(
            criados, tela[0], relacao,
            "  ← Invertida" if inv else "")
        if erros:
            msg += "\n\nErros:\n" + "\n".join(erros)
        TaskDialog.Show("IBTS — Concluído", msg)
