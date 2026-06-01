# -*- coding: utf-8 -*-

__title__   = "Filtrar Paredes"
__author__  = "Samuel"
__version__ = "Versao 1.2"

"""
Plugin: Grupos de Paredes Espelhadas
Versao: 1.2.0
Autor: Samuel

CORRECOES v1.2:
    
        SOLUCAO: Substituir .ToElements() por iteracao direta no
        collector (ele ja e iteravel), eliminando a conversao .NET.
        Adicionar python_list = list como alias ANTES de qualquer
        import .NET, garantindo referencia segura ao builtin.

    PROBLEMA 2: Fragilidade geral do escopo em IronPython.
        SOLUCAO: Salvar referencia ao builtin list() logo no
        inicio do modulo, antes de qualquer import clr/.NET.
"""

# ─────────────────────────────────────────────
#  
# ─────────────────────────────────────────────
_python_list = list  

# ─────────────────────────────────────────────
#  IMPORTS
# ─────────────────────────────────────────────
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

import System
from datetime import datetime

# NetList = .NET List<T> — alias evita sobrescrever builtin list
from System.Collections.Generic import List as NetList

import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI.Selection as Sel
from Autodesk.Revit.DB.ExtensibleStorage import (
    Schema, SchemaBuilder, Entity,
    DataStorage, AccessLevel
)

from pyrevit import forms

# ─────────────────────────────────────────────
#  CONFIGURACOES GLOBAIS
# ─────────────────────────────────────────────
SCHEMA_GUID      = System.Guid("C7E3A912-4F5B-4D8E-9A1C-2B6D0F3E8C5A")
SCHEMA_NAME      = "GruposParedesEspelhadas"
DATASTORAGE_NAME = "SamuelPlugin_GruposEspelhados"

FIELD_GRUPO_ID = "grupo_id"
FIELD_WALL_IDS = "wall_ids"
FIELD_DATA     = "data_criacao"
FIELD_NOME     = "nome_grupo"
FIELD_VERSAO   = "versao_schema"
VERSAO_SCHEMA  = "1.0.0"


# ─────────────────────────────────────────────
#  SCHEMA
# ─────────────────────────────────────────────
def obter_ou_criar_schema():
    schema_existente = Schema.Lookup(SCHEMA_GUID)
    if schema_existente:
        return schema_existente

    builder = SchemaBuilder(SCHEMA_GUID)
    builder.SetSchemaName(SCHEMA_NAME)
    builder.SetReadAccessLevel(AccessLevel.Public)
    builder.SetWriteAccessLevel(AccessLevel.Public)
    builder.SetDocumentation("Grupos logicos de paredes espelhadas. Samuel PLUGIN v1.2")
    builder.AddSimpleField(FIELD_GRUPO_ID, System.String)
    builder.AddSimpleField(FIELD_WALL_IDS, System.String)
    builder.AddSimpleField(FIELD_DATA,     System.String)
    builder.AddSimpleField(FIELD_NOME,     System.String)
    builder.AddSimpleField(FIELD_VERSAO,   System.String)
    return builder.Finish()


# ─────────────────────────────────────────────
#  SERIALIZACAO
# ─────────────────────────────────────────────
def serializar_wall_ids(wall_ids):
    """Converte list[ElementId] para string CSV."""
    return ",".join([str(wid.IntegerValue) for wid in wall_ids])


def deserializar_wall_ids(wall_ids_str):
    """
    Converte string CSV para list[ElementId].
    Usa _python_list para garantir o builtin mesmo se
    o escopo estiver contaminado.
    """
    if not wall_ids_str:
        return _python_list()
    return _python_list(
        DB.ElementId(int(id_str))
        for id_str in wall_ids_str.split(",")
        if id_str.strip()
    )


# ─────────────────────────────────────────────
#  CARREGAR GRUPOS
# ─────────────────────────────────────────────
def carregar_grupos(doc):
    """
    Le todos os grupos do Extensible Storage.

    CORRECAO: Itera diretamente no FilteredElementCollector
    sem chamar .ToElements() — elimina a conversao para
    IList<Element> do .NET que causava o conflito com list().
    """
    schema = Schema.Lookup(SCHEMA_GUID)
    if not schema:
        return _python_list()

    grupos = _python_list()

    # CORRIGIDO: iteracao direta no collector, sem .ToElements()
    for ds in DB.FilteredElementCollector(doc).OfClass(DataStorage):
        if not ds.Name.startswith(DATASTORAGE_NAME + "__"):
            continue
        entity = ds.GetEntity(schema)
        if not entity.IsValid():
            continue
        grupos.append({
            "grupo_id":      entity.Get[System.String](FIELD_GRUPO_ID),
            "wall_ids":      deserializar_wall_ids(entity.Get[System.String](FIELD_WALL_IDS)),
            "data_criacao":  entity.Get[System.String](FIELD_DATA),
            "nome_grupo":    entity.Get[System.String](FIELD_NOME),
            "versao_schema": entity.Get[System.String](FIELD_VERSAO),
        })
    return grupos


# ─────────────────────────────────────────────
#  SALVAR GRUPO
# ─────────────────────────────────────────────
def salvar_grupo(doc, wall_ids, nome_grupo=""):
    """Persiste novo grupo no Extensible Storage."""
    schema       = obter_ou_criar_schema()
    grupo_id     = str(System.Guid.NewGuid())
    data_criacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not nome_grupo:
        nome_grupo = "Grupo_" + grupo_id[:8]

    t = DB.Transaction(doc, "Salvar Grupo Espelhado")
    t.Start()
    try:
        ds      = DataStorage.Create(doc)
        ds.Name = DATASTORAGE_NAME + "__" + grupo_id

        entity = Entity(schema)
        entity.Set[System.String](FIELD_GRUPO_ID, grupo_id)
        entity.Set[System.String](FIELD_WALL_IDS, serializar_wall_ids(wall_ids))
        entity.Set[System.String](FIELD_DATA,     data_criacao)
        entity.Set[System.String](FIELD_NOME,     nome_grupo)
        entity.Set[System.String](FIELD_VERSAO,   VERSAO_SCHEMA)

        ds.SetEntity(entity)
        t.Commit()
        return grupo_id
    except Exception as ex:
        if t.HasStarted() and not t.HasEnded():
            t.RollBack()
        raise ex


# ─────────────────────────────────────────────
#  SELECAO DE PAREDES
# ─────────────────────────────────────────────
class FiltroParedes(Sel.ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, DB.Wall)
    def AllowReference(self, reference, point):
        return False


def solicitar_selecao_paredes(uidoc):
    """

    """
    try:
        referencias = uidoc.Selection.PickObjects(
            Sel.ObjectType.Element,
            FiltroParedes(),
            "Selecione as paredes do grupo espelhado. [ESC para cancelar]"
        )
    except Exception:
        return None

    if not referencias:
        return None

    # _python_list garante uso do builtin mesmo apos imports .NET
    return _python_list(ref.ElementId for ref in referencias)


# ─────────────────────────────────────────────
#  VALIDACAO
# ─────────────────────────────────────────────
def validar_selecao(doc, wall_ids):
    """
    Valida selecao: minimo 2 paredes, existencia no modelo,
    sem conflito com grupos existentes.
    Retorna (bool, str_erro).
    """
    if len(wall_ids) < 2:
        return False, "Selecione pelo menos 2 paredes para formar um grupo."

    for wid in wall_ids:
        el = doc.GetElement(wid)
        if el is None or not isinstance(el, DB.Wall):
            return False, "Uma ou mais paredes nao foram encontradas no modelo."

    grupos_existentes = carregar_grupos(doc)
    ids_em_uso = set()
    for grupo in grupos_existentes:
        for wid in grupo["wall_ids"]:
            ids_em_uso.add(wid.IntegerValue)

    conflitos = _python_list(wid for wid in wall_ids if wid.IntegerValue in ids_em_uso)
    if conflitos:
        return False, (
            "{} parede(s) ja pertencem a um grupo existente.\n"
            "Cada parede pode pertencer a apenas um grupo."
        ).format(len(conflitos))

    return True, ""


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    doc   = __revit__.ActiveUIDocument.Document
    uidoc = __revit__.ActiveUIDocument

    wall_ids = solicitar_selecao_paredes(uidoc)
    if wall_ids is None:
        forms.alert("Operacao cancelada.", title="Grupos Espelhados", warn_icon=False)
        return

    valido, erro = validar_selecao(doc, wall_ids)
    if not valido:
        forms.alert(erro, title="Grupos Espelhados - Erro de Validacao")
        return

    nome_grupo = forms.ask_for_string(
        default="",
        prompt="Nome do grupo (deixe em branco para gerar automaticamente):",
        title="Grupos Espelhados"
    )
    if nome_grupo is None:
        forms.alert("Operacao cancelada.", title="Grupos Espelhados", warn_icon=False)
        return

    try:
        grupo_id = salvar_grupo(doc, wall_ids, nome_grupo=nome_grupo)
    except Exception as ex:
        forms.alert(
            "Erro ao salvar o grupo:\n\n{}".format(str(ex)),
            title="Grupos Espelhados - Erro"
        )
        return

    forms.alert(
        "Grupo criado com sucesso!\n\n"
        "ID:      {}\n"
        "Paredes: {}\n"
        "Nome:    {}".format(
            grupo_id[:18] + "...",
            len(wall_ids),
            nome_grupo if nome_grupo else "Grupo_" + grupo_id[:8]
        ),
        title="Grupos Espelhados",
        warn_icon=False
    )


if __name__ == '__main__':
    main()
