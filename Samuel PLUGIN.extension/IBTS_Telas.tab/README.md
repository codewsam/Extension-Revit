# Plugin — Importar Laje IBTS (pyRevit)

Plugin para Revit 2025 via pyRevit que importa o contorno de um DWG do IBTS
e cria automaticamente um Piso com os parâmetros da tela soldada preenchidos.

---

## INSTALAÇÃO (passo a passo)

### 1. Copiar a pasta do plugin

Copie a pasta **`IBTS_Telas.tab`** para dentro do seu extension do pyRevit.
O caminho padrão é:

```
C:\Users\<SEU_USUARIO>\AppData\Roaming\pyRevit\Extensions\
```

A estrutura deve ficar assim:

```
Extensions\
└── IBTS_Telas.tab\
    └── IBTS.panel\
        └── ImportarLajeIBTS.pushbutton\
            ├── script.py
            └── bundle.yaml
```

### 2. Recarregar o pyRevit

No Revit, vá em:
**pyRevit → Reload**

Uma nova aba chamada **"IBTS Telas"** vai aparecer na faixa de opções.

---

## COMO USAR

1. **Inserir > Importar CAD** → selecione o DWG da laje IBTS
   - Unidades de importação: **Metros**
   - Clique em Abrir

2. Selecione o bloco importado → **Explodir > Explodir Parcial**

3. Clique em **"Importar Laje IBTS"** na aba IBTS Telas

4. Na janela do plugin:
   - Escolha o **Tipo de Tela** (ex: Q138, L196…)
   - Marque **"Inverter (L ↔ T)"** se necessário
   - Selecione o **DWG** que você importou
   - Selecione o **Tipo de Piso** do seu modelo
   - Selecione o **Nível**
   - Clique em **Criar Piso**

O plugin cria o piso com o contorno do DWG e preenche automaticamente
os parâmetros técnicos da tela nos "Comentários" do elemento.

---

## PARÂMETROS IBTS (opcionais — para schedules)

Para criar schedules com os dados da tela, adicione estes
**Parâmetros de Projeto** (texto) ao seu modelo Revit:

| Nome do Parâmetro    | Categoria  |
|----------------------|------------|
| IBTS_Designacao      | Pisos      |
| IBTS_Serie           | Pisos      |
| IBTS_Espacamento_L   | Pisos      |
| IBTS_Espacamento_T   | Pisos      |
| IBTS_Diametro_L      | Pisos      |
| IBTS_Diametro_T      | Pisos      |
| IBTS_Secao_L         | Pisos      |
| IBTS_Secao_T         | Pisos      |
| IBTS_Peso            | Pisos      |

Mesmo sem eles, o resumo é gravado no campo **Comentários** do piso.

---

## COMO OBTER O DWG DO IBTS

O IBTS disponibiliza o software **"Tela Laje IBTS"** gratuitamente:

1. Acesse: **www.ibts.org.br**
2. Vá em **Softwares** (ou Informações Técnicas → Tela Laje)
3. Baixe e instale o **Tela Laje IBTS**
4. Nele você desenha/dimensiona a laje e **exporta o DWG**
5. Use esse DWG no fluxo acima

Alternativamente, qualquer DWG com o contorno da laje funciona —
o plugin usa o perímetro do arquivo para criar o piso.
