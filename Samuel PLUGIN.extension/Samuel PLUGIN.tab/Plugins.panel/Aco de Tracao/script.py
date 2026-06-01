# -*- coding: utf-8 -*-
"""Aco de Tracao - Lanca vergalhoes verticais em paredes estruturais."""
__title__ = "Aco 3"
__author__ = "Samuel PLUGIN"

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import Rebar, RebarBarType, RebarStyle, RebarHookOrientation
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
import System
from System.Windows import Window, Thickness
from System.Windows.Controls import StackPanel, Label, ComboBox, ComboBoxItem
from System.Windows.Controls import TextBox, Button, CheckBox, Separator
from System.Windows import HorizontalAlignment, FontWeights
from System.Windows.Media import SolidColorBrush, Color
import System.Windows.Controls as WpfControls

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CM_TO_FT = 1.0 / 30.48


class WallFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, Wall)
    def AllowReference(self, ref, point):
        return False


class AcoTracaoWindow(Window):
    def __init__(self, bar_types):
        self.bar_types = bar_types
        self.result = None
        self._build_ui()

    def _bt_name(self, bt):
        try:
            return getattr(bt, 'Name', None) or bt.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString()
        except:
            return 'Desconhecido'

    def _label(self, text):
        lbl = Label()
        lbl.Content = text
        lbl.Padding = Thickness(0)
        lbl.Margin = Thickness(0, 4, 0, 0)
        lbl.FontSize = 12
        return lbl

    def _textbox(self, default=''):
        tb = TextBox()
        tb.Text = default
        tb.Margin = Thickness(0, 2, 0, 4)
        tb.Padding = Thickness(4, 3, 4, 3)
        return tb

    def _on_ref_changed(self, s, e):
        self.txt_offset.IsEnabled = not bool(self.chk_ref.IsChecked)

    def _on_transp_changed(self, s, e):
        self.txt_transp.IsEnabled = bool(self.chk_transp.IsChecked)

    def _cancel(self, s, e):
        self.DialogResult = False
        self.Close()

    def _start(self, s, e):
        try:
            sel = self.cb_type.SelectedItem
            bar_type = sel.Tag if sel else None
            self.result = {
                'bar_type eu preciso fazer outro prompt agr, a ideia é parecida com esse ultimo, porem agora eu vou poder selecionar as paredes e ele vai fazer aquele "paliteiro" eu mandarei a foto com as opções mas elas devem ter: tipo de vergalhao, lançar arranque? comprimento do arranque(cm), lançar embassamento? comprimento do embassamento (cm), comprimento da dobra etc, na foto vai ter certinho o exemplo, e tbm vai ter de como imagino que fique o resultado final'   : bar_type,
                'quantity'   : int(self.txt_qty.Text),
                'spacing_ft' : float(self.txt_spacing.Text.replace(',', '.')) * CM_TO_FT,
                'use_ref'    : bool(self.chk_ref.IsChecked),
                'offset_ft'  : float(self.txt_offset.Text.replace(',', '.')) * CM_TO_FT,
                'transpasse' : bool(self.chk_transp.IsChecked),
                'transp_ft'  : float(self.txt_transp.Text.replace(',', '.')) * CM_TO_FT,
                'base_ft'    : float(self.txt_base.Text.replace(',', '.')) * CM_TO_FT,
                'cover_ft'   : float(self.txt_cover.Text.replace(',', '.')) * CM_TO_FT,
            }
            self.DialogResult = True
            self.Close()
        except Exception as ex:
            TaskDialog.Show('Erro', 'Verifique os campos: ' + str(ex))

    def _build_ui(self):
        self.Title = 'Aco de Tracao'
        self.Width = 340
        self.SizeToContent = System.Windows.SizeToContent.Height
        self.ResizeMode = System.Windows.ResizeMode.NoResize
        self.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen
        self.Background = SolidColorBrush(Color.FromRgb(245, 245, 245))
        outer = StackPanel()
        outer.Margin = Thickness(12)

        hdr = Label()
        hdr.Content = 'Aco de Tracao'
        hdr.FontSize = 16
        hdr.FontWeight = FontWeights.Bold
        hdr.Foreground = SolidColorBrush(Color.FromRgb(40, 40, 40))
        hdr.Margin = Thickness(0, 0, 0, 8)
        outer.Children.Add(hdr)

        s1 = Separator()
        s1.Margin = Thickness(0, 0, 0, 10)
        outer.Children.Add(s1)

        outer.Children.Add(self._label('Tipo de vergalhao:'))
        self.cb_type = ComboBox()
        self.cb_type.Margin = Thickness(0, 2, 0, 8)
        for bt in self.bar_types:
            item = ComboBoxItem()
            item.Content = self._bt_name(bt)
            item.Tag = bt
            self.cb_type.Items.Add(item)
        if self.cb_type.Items.Count > 0:
            self.cb_type.SelectedIndex = 0
        outer.Children.Add(self.cb_type)

        outer.Children.Add(self._label('Quantidade de acos:'))
        self.txt_qty = self._textbox('1')
        outer.Children.Add(self.txt_qty)

        outer.Children.Add(self._label('Espacamento entre acos (cm):'))
        self.txt_spacing = self._textbox('15.00')
        outer.Children.Add(self.txt_spacing)

        self.chk_ref = CheckBox()
        self.chk_ref.Content = 'Iniciar exatamente na referencia da parede'
        self.chk_ref.Margin = Thickness(0, 4, 0, 4)
        self.chk_ref.IsChecked = True
        self.chk_ref.Checked += self._on_ref_changed
        self.chk_ref.Unchecked += self._on_ref_changed
        outer.Children.Add(self.chk_ref)

        outer.Children.Add(self._label('Offset inicial (cm):'))
        self.txt_offset = self._textbox('0.00')
        self.txt_offset.IsEnabled = False
        outer.Children.Add(self.txt_offset)

        self.chk_transp = CheckBox()
        self.chk_transp.Content = 'Adicionar transpasse no topo'
        self.chk_transp.Margin = Thickness(0, 6, 0, 4)
        self.chk_transp.IsChecked = False
        self.chk_transp.Checked += self._on_transp_changed
        self.chk_transp.Unchecked += self._on_transp_changed
        outer.Children.Add(self.chk_transp)

        outer.Children.Add(self._label('Comprimento do transpasse / topo (cm):'))
        self.txt_transp = self._textbox('40.00')
        self.txt_transp.IsEnabled = False
        outer.Children.Add(self.txt_transp)

        outer.Children.Add(self._label('Comprimento da base (cm):'))
        self.txt_base = self._textbox('0.00')
        outer.Children.Add(self.txt_base)

        outer.Children.Add(self._label('Cobrimento (cm):'))
        self.txt_cover = self._textbox('2.50')
        outer.Children.Add(self.txt_cover)

        s2 = Separator()
        s2.Margin = Thickness(0, 10, 0, 10)
        outer.Children.Add(s2)

        btn_row = StackPanel()
        btn_row.Orientation = WpfControls.Orientation.Horizontal
        btn_row.HorizontalAlignment = HorizontalAlignment.Right

        bc = Button()
        bc.Content = 'Cancelar'
        bc.Width = 90
        bc.Margin = Thickness(0, 0, 8, 0)
        bc.Click += self._cancel
        btn_row.Children.Add(bc)

        bo = Button()
        bo.Content = 'Iniciar PICK POINT'
        bo.Width = 130
        bo.Background = SolidColorBrush(Color.FromRgb(0, 120, 212))
        bo.Foreground = SolidColorBrush(Color.FromRgb(255, 255, 255))
        bo.FontWeight = FontWeights.Bold
        bo.Click += self._start
        btn_row.Children.Add(bo)

        outer.Children.Add(btn_row)
        self.Content = outer


def get_wall_dir(wall):
    loc = wall.Location
    if isinstance(loc, LocationCurve):
        d = loc.Curve.GetEndPoint(1) - loc.Curve.GetEndPoint(0)
        return d.Normalize()
    return None


def create_rebars(doc, wall, click_pt, p):
    bb = wall.get_BoundingBox(None)
    z_bot = bb.Min.Z + p['base_ft']
    z_top = bb.Max.Z + (p['transp_ft'] if p['transpasse'] else 0.0)
    wall_dir = get_wall_dir(wall)
    if wall_dir is None:
        return
    lc = wall.Location.Curve
    axis_pt = lc.Evaluate(lc.Project(click_pt).Parameter, False)
    start = p['cover_ft'] if p['use_ref'] else p['offset_ft']
    t = Transaction(doc, 'Aco de Tracao')
    t.Start()
    try:
        for i in range(p['quantity']):
            dist = start + i * p['spacing_ft']
            pb = XYZ(axis_pt.X + wall_dir.X * dist, axis_pt.Y + wall_dir.Y * dist, z_bot)
            pt = XYZ(pb.X, pb.Y, z_top)
            Rebar.CreateFromCurves(
                doc, RebarStyle.Standard, p['bar_type'], None, None,
                wall, XYZ.BasisZ, [Line.CreateBound(pb, pt)],
                RebarHookOrientation.Left, RebarHookOrientation.Left, True, False)
        t.Commit()
    except Exception as ex:
        t.RollBack()
        raise ex


def main():
    av = uidoc.ActiveView
    if av.ViewType not in [ViewType.FloorPlan, ViewType.EngineeringPlan]:
        TaskDialog.Show('Aviso', 'Use este plugin em uma vista de planta (planta baixa).')
        return
    bar_types = list(FilteredElementCollector(doc).OfClass(RebarBarType))
    if not bar_types:
        TaskDialog.Show('Erro', 'Nenhum RebarBarType encontrado no projeto.')
        return
    win = AcoTracaoWindow(bar_types)
    if not win.ShowDialog():
        return
    if win.result is None:
        return
    p = win.result
    while True:
        try:
            ref = uidoc.Selection.PickObject(
                ObjectType.Element, WallFilter(),
                'Clique em uma parede (ESC para sair)')
        except System.Exception:
            break
        wall = doc.GetElement(ref.ElementId)
        if not isinstance(wall, Wall):
            continue
        try:
            create_rebars(doc, wall, ref.GlobalPoint, p)
        except Exception as ex:
            TaskDialog.Show('Erro ao criar vergalhoes', str(ex))
            break


main()
