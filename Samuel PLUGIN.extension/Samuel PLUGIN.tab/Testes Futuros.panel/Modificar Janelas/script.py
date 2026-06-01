# -*- coding: utf-8 -*-
__title__ = "Trocar Tipo\nde Janela"
__version__ = "2.0"
__doc__ = "Identifica todas as janelas do projeto (incluindo aberturas TQS), agrupa por tipo e permite trocar em lote."

from Autodesk.Revit.DB import (
    FilteredElementCollector, BuiltInCategory, BuiltInParameter,
    FamilyInstance, FamilySymbol, Transaction, ElementId
)
from pyrevit import forms, revit, script

doc   = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# =============================================================================
# ETAPA 1 — Coletar todas as janelas do projeto
# Estratégia: OST_Windows + OST_GenericModel com filtragem inteligente
# =============================================================================

def coletar_janelas():
    """
    Coleta todas as instâncias que provavelmente são janelas.
    Prioriza OST_Windows. Complementa com GenericModel que tenham
    parâmetros característicos de janela (Altura do peitoril, etc.)
    """
    janelas = []

    # --- Fonte 1: categoria oficial OST_Windows ---
    wins = (FilteredElementCollector(doc)
            .OfCategory(BuiltInCategory.OST_Windows)
            .WhereElementIsNotElementType()
            .ToElements())
    janelas.extend(list(wins))

    # --- Fonte 2: GenericModel que parecem janelas (ex: aberturas TQS) ---
    gms = (FilteredElementCollector(doc)
           .OfCategory(BuiltInCategory.OST_GenericModel)
           .WhereElementIsNotElementType()
           .ToElements())

    for elem in gms:
        if _parece_janela(elem):
            janelas.append(elem)

    # --- Fonte 3: FamilyInstance sem categoria clara hospedada em parede ---
    todos_fi = (FilteredElementCollector(doc)
                .OfClass(FamilyInstance)
                .WhereElementIsNotElementType()
                .ToElements())

    ids_ja = set(e.Id.IntegerValue for e in janelas)
    for fi in todos_fi:
        if fi.Id.IntegerValue in ids_ja:
            continue
        try:
            cat = fi.Category
            if cat and cat.Name in ("Janelas", "Windows"):
                janelas.append(fi)
                continue
        except:
            pass
        if _parece_janela(fi):
            janelas.append(fi)

    return janelas


def _parece_janela(elem):
    """
    Heurística para identificar janelas genéricas/TQS:
    - Tem parâmetro 'Altura do peitoril' ou 'Sill Height'
    - Tem host (está hospedado em parede)
    - Proporção Largura/Altura típica de janela (não é porta)
    - Elevação base > 20cm (portas normalmente começam no nível 0)
    """
    try:
        # Deve ter host (estar em parede)
        host = elem.Host
        if not host:
            return False

        # Checar parâmetros típicos de janela
        sill = (elem.LookupParameter("Altura do peitoril") or
                elem.LookupParameter("Sill Height") or
                elem.LookupParameter("Peitoril"))
        if sill:
            return True

        # Checar pelo nome da família
        sym = doc.GetElement(elem.GetTypeId())
        if sym:
            fname = ""
            try:
                fname = sym.get_Parameter(BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM).AsString().lower()
            except:
                pass
            tname = ""
            try:
                tname = sym.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString().lower()
            except:
                pass
            palavras_janela = ["janela", "window", "abertura de janela", "jnl", " j1", " j2", " j3"]
            for p in palavras_janela:
                if p in fname or p in tname:
                    return True

        # Checar elevação base > 20cm (0.656 ft) — portas começam em 0
        try:
            base_elev = elem.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
            if base_elev and base_elev.AsDouble() > 0.656:
                return True
        except:
            pass

    except:
        pass

    return False


# =============================================================================
# ETAPA 2 — Agrupar por tipo (FamilySymbol)
# =============================================================================

def agrupar_por_tipo(janelas):
    """
    Retorna dois dicionários:
      grupos:      { "J1": [inst, inst, ...], "J2": [...], ... }
      tipos_info:  { "J1": FamilySymbol, "J2": FamilySymbol, ... }
    """
    grupos     = {}
    tipos_info = {}

    for jan in janelas:
        try:
            sym = doc.GetElement(jan.GetTypeId())
            if not sym:
                continue
            nome_tipo = sym.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
            if not nome_tipo:
                nome_tipo = "Sem Nome"

            if nome_tipo not in grupos:
                grupos[nome_tipo]     = []
                tipos_info[nome_tipo] = sym
            grupos[nome_tipo].append(jan)
        except:
            continue

    return grupos, tipos_info


# =============================================================================
# ETAPA 3 — Coletar todos os tipos disponíveis no projeto
# =============================================================================

def coletar_tipos_disponiveis():
    """
    Retorna dict { "J1": FamilySymbol, "J2": FamilySymbol, ... }
    com todos os FamilySymbol de janela carregados no projeto.
    """
    tipos = {}
    syms = (FilteredElementCollector(doc)
            .OfCategory(BuiltInCategory.OST_Windows)
            .WhereElementIsElementType()
            .ToElements())
    for s in syms:
        try:
            nome = s.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
            if nome:
                tipos[nome] = s
        except:
            continue
    return tipos


# =============================================================================
# ETAPA 4 — Interface de seleção
# =============================================================================

def montar_label_tipo(nome, qtd):
    return "{} — {} instância(s)".format(nome, qtd)


# =============================================================================
# ETAPA 5 — Destacar elementos no modelo
# =============================================================================

def destacar_elementos(janelas):
    """Seleciona os elementos no Revit para que fiquem visualmente destacados."""
    try:
        ids = [j.Id for j in janelas]
        col = System.Collections.Generic.List[ElementId](ids)
        uidoc.Selection.SetElementIds(col)
    except:
        pass  # não critico se falhar, é só UX


# =============================================================================
# ETAPA 6 — Trocar o tipo das instâncias
# =============================================================================

def trocar_tipo(instancias, novo_symbol):
    """
    Troca o FamilySymbol de todas as instâncias passadas.
    Retorna (ok, erros, mensagens_erro).
    """
    ok     = 0
    erros  = 0
    logs   = []

    with Transaction(doc, "Trocar Tipo de Janela → {}".format(
            novo_symbol.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString())) as t:
        t.Start()
        try:
            for inst in instancias:
                try:
                    inst.ChangeTypeId(novo_symbol.Id)
                    ok += 1
                except Exception as e:
                    erros += 1
                    marca = ""
                    try:
                        marca = inst.get_Parameter(BuiltInParameter.ALL_MODEL_MARK).AsString()
                    except:
                        pass
                    logs.append("Id {} ({}): {}".format(inst.Id, marca, str(e)))
            t.Commit()
        except Exception as e_geral:
            t.RollBack()
            raise e_geral

    return ok, erros, logs


# =============================================================================
# FLUXO PRINCIPAL
# =============================================================================

# — 1. Coletar —
todas_janelas = coletar_janelas()

if not todas_janelas:
    forms.alert(
        "Nenhuma janela encontrada no projeto.\n\n"
        "Verifique se existem elementos nas categorias:\n"
        "• Janelas (OST_Windows)\n"
        "• Modelos Genéricos hospedados em parede",
        title="Sem Janelas", exitscript=True
    )

# — 2. Agrupar —
grupos, tipos_info = agrupar_por_tipo(todas_janelas)

if not grupos:
    forms.alert("Não foi possível agrupar as janelas por tipo.", exitscript=True)

# — 3. Tipos disponíveis para substituição —
tipos_disponiveis = coletar_tipos_disponiveis()

if not tipos_disponiveis:
    forms.alert("Nenhum tipo de janela (FamilySymbol) carregado no projeto.", exitscript=True)

# — 4. Mostrar resumo e pedir tipo ORIGEM —
resumo_tipos = sorted(grupos.keys())
labels_origem = [montar_label_tipo(n, len(grupos[n])) for n in resumo_tipos]

label_selecionado = forms.ask_for_one_item(
    labels_origem,
    default=labels_origem[0],
    prompt=(
        "Projeto: {}\n"
        "Total de janelas encontradas: {}\n\n"
        "Selecione o TIPO DE ORIGEM (que será substituído):"
    ).format(doc.Title, len(todas_janelas)),
    title="[1/2] Selecionar Tipo de Origem"
)

if not label_selecionado:
    script.exit()

# Recuperar nome limpo do tipo selecionado
tipo_origem_nome = label_selecionado.split(" — ")[0]
instancias_para_trocar = grupos[tipo_origem_nome]
qtd = len(instancias_para_trocar)

# — 5. Pedir tipo DESTINO —
# Excluir o próprio tipo origem da lista de destino
nomes_destino = sorted([n for n in tipos_disponiveis.keys() if n != tipo_origem_nome])

if not nomes_destino:
    forms.alert(
        "Não há outros tipos disponíveis para substituição.\n"
        "Carregue outros tipos de janela no projeto primeiro.",
        exitscript=True
    )

tipo_destino_nome = forms.ask_for_one_item(
    nomes_destino,
    default=nomes_destino[0],
    prompt=(
        "Tipo de origem selecionado: {}\n"
        "Instâncias que serão afetadas: {}\n\n"
        "Selecione o TIPO DE DESTINO (novo tipo):"
    ).format(tipo_origem_nome, qtd),
    title="[2/2] Selecionar Tipo de Destino"
)

if not tipo_destino_nome:
    script.exit()

novo_symbol = tipos_disponiveis[tipo_destino_nome]

# — 6. Confirmar —
separador = u"\u2500" * 35  # ─────────────────────────────────────

confirmar = forms.alert(
    u"RESUMO DA OPERAÇÃO\n"
    u"{}\n\n"
    u"  Tipo ORIGEM:   {}\n"
    u"  Tipo DESTINO:  {}\n"
    u"  Instâncias:    {}\n\n"
    u"Deseja continuar?".format(separador, tipo_origem_nome, tipo_destino_nome, qtd),
    title="Confirmar Troca",
    yes=True, no=True
)

if not confirmar:
    script.exit()

# — 7. Destacar no modelo antes de modificar —
destacar_elementos(instancias_para_trocar)

# — 8. Executar troca —
try:
    ok, erros, logs = trocar_tipo(instancias_para_trocar, novo_symbol)
except Exception as e:
    forms.alert(
        "Erro crítico durante a transação:\n\n{}".format(str(e)),
        title="Erro Fatal", exitscript=True
    )

# — 9. Relatório final —
linhas_log = "\n".join(logs) if logs else "Nenhum erro registrado."

output.print_md("## ✅ Troca de Tipo Concluída")
output.print_md("---")
output.print_md("**Projeto:** {}".format(doc.Title))
output.print_md("**Origem:** `{}` → **Destino:** `{}`".format(tipo_origem_nome, tipo_destino_nome))
output.print_md("**✔ Sucesso:** {}  |  **✘ Erros:** {}".format(ok, erros))
if logs:
    output.print_md("### Erros detalhados")
    output.print_md("```\n{}\n```".format(linhas_log))

forms.alert(
    "Troca Concluída!\n\n"
    "  {} → {}\n\n"
    "  ✔ Modificadas com sucesso:  {}\n"
    "  ✘ Com erro:                 {}\n\n"
    "{}".format(
        tipo_origem_nome,
        tipo_destino_nome,
        ok,
        erros,
        "Verifique o Output Window para detalhes dos erros." if erros else ""
    ),
    title="Resultado Final",
    warn_icon=(erros > 0)
)