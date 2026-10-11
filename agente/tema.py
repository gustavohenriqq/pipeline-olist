"""Tema do app: paleta escura (padrao) e clara, trocadas pelo botao de sol/lua.

O Streamlit nao deixa cada visitante trocar o tema por codigo, entao a troca e
feita aqui, com CSS. Os seletores usam data-testid do Streamlit (versao fixada em
agente/requirements.txt): se uma atualizacao mudar esses nomes, algum detalhe
visual pode quebrar, nunca a resposta.
"""
from __future__ import annotations

PALETAS = {
    "claro": {
        "fundo": "#F7FAF9",
        "superficie": "#FFFFFF",
        "superficie_2": "#F1F5F4",
        "borda": "#E3EBE8",
        "texto": "#0F172A",
        "texto_suave": "#64748B",
        "destaque": "#10B981",
        "destaque_suave": "#D1FAE5",
        "texto_no_destaque": "#04291D",
        "brilho": "rgba(16, 185, 129, 0.16)",
        "sombra": "rgba(15, 23, 42, 0.06)",
        "grade": "#E8EEF0",
        "azul": "#2563EB",
        "violeta": "#7C3AED",
        "ambar": "#D97706",
        "vermelho": "#DC2626",
    },
    "escuro": {
        "fundo": "#0B1220",
        "superficie": "#111A2C",
        "superficie_2": "#162033",
        "borda": "#1F2A40",
        "texto": "#E2E8F0",
        "texto_suave": "#94A3B8",
        "destaque": "#34D399",
        "destaque_suave": "rgba(52, 211, 153, 0.14)",
        "texto_no_destaque": "#04291D",
        "brilho": "rgba(52, 211, 153, 0.10)",
        "sombra": "rgba(0, 0, 0, 0.35)",
        "grade": "#1C263A",
        "azul": "#60A5FA",
        "violeta": "#A78BFA",
        "ambar": "#FBBF24",
        "vermelho": "#F87171",
    },
}


def tema_valido(nome: str | None) -> str:
    return nome if nome in PALETAS else "escuro"


_ESTILO = """
/* campos e listas (selectbox, date_input) seguem o tema, nao o base do config.toml */
html, body { background: var(--fundo); }
[data-testid="stDateInputField"], [data-testid="stSelectbox"] div:has(> input) {
  background: var(--superficie) !important; border: 1px solid var(--borda) !important; border-radius: 10px;
}
[data-testid="stDateInputField"] *, [data-testid="stDateInput"] input, [data-testid="stSelectbox"] input {
  color: var(--texto) !important; -webkit-text-fill-color: var(--texto);
}
[data-testid="stSelectbox"] svg { color: var(--texto_suave); }
[data-testid="stSelectboxVirtualDropdown"] {
  background: var(--superficie) !important; color: var(--texto) !important;
  border: 1px solid var(--borda); border-radius: 10px;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] { color: var(--texto); }
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
[data-testid="stSelectboxVirtualDropdown"] [aria-selected="true"] { background: var(--destaque_suave); }
.stApp [data-testid="stWidgetLabel"] p { color: var(--texto_suave); }

/* menu de paginas */
[data-testid="stSidebarNav"] a span, [data-testid="stSidebarNavLink"] span { color: var(--texto_suave); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: var(--destaque_suave); border-radius: 10px;
}
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: var(--destaque); font-weight: 600; }

/* cabecalho das paginas do painel */
.cabecalho h1 { font-size: 28px; font-weight: 700; padding: 0; margin: 0; }
.cabecalho p { color: var(--texto_suave); margin: 2px 0 0; }

/* cartoes de indicador */
.cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 6px 0 14px; }
.cartao {
  --cor: var(--destaque);
  display: flex; gap: 14px; align-items: flex-start; padding: 16px 18px; border-radius: 18px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--cor) 16%, var(--superficie)), var(--superficie) 70%);
  border: 1px solid color-mix(in srgb, var(--cor) 32%, var(--borda));
  box-shadow: 0 10px 30px var(--sombra);
}
.cor-menta { --cor: var(--destaque); }
.cor-azul { --cor: var(--azul); }
.cor-violeta { --cor: var(--violeta); }
.cor-ambar { --cor: var(--ambar); }
.cartao-icone {
  flex: none; width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center;
  background: color-mix(in srgb, var(--cor) 22%, transparent); color: var(--cor);
}
.cartao-icone span { font-family: "Material Symbols Rounded"; font-size: 24px; line-height: 1; }
.cartao-rotulo { color: var(--texto_suave); font-size: 13px; }
.cartao-valor { color: var(--texto); font-size: 24px; white-space: nowrap; font-weight: 700; letter-spacing: -.01em; line-height: 1.25; }
.cartao-delta { font-size: 12.5px; margin-top: 2px; color: var(--texto_suave); }
.cartao-delta b { font-weight: 600; }
.cartao-delta.melhora b { color: var(--destaque); }
.cartao-delta.piora b { color: var(--vermelho); }

/* blocos de grafico e tabela */
.bloco-titulo { font-weight: 600; font-size: 16px; color: var(--texto); margin: 4px 0 0; }
.bloco-sub { color: var(--texto_suave); font-size: 13px; margin: 0 0 6px; }
.risco-alto { background: color-mix(in srgb, var(--vermelho) 22%, transparent); }
.risco-medio { background: color-mix(in srgb, var(--ambar) 20%, transparent); }
.stApp {
  background:
    radial-gradient(circle at 0% 100%, var(--brilho), transparent 32%),
    radial-gradient(circle at 100% 0%, var(--brilho), transparent 28%),
    var(--fundo);
  color: var(--texto);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: transparent; }
.stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
.stApp summary, .stApp [data-testid="stMarkdownContainer"] { color: var(--texto); }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {
  color: var(--texto_suave);
}
.stApp a { color: var(--destaque); text-decoration: none; }
.stApp a:hover { text-decoration: underline; }

/* barra lateral */
[data-testid="stSidebar"] {
  background: var(--superficie);
  border-right: 1px solid var(--borda);
}
.rotulo-secao {
  font-size: 12px; letter-spacing: .04em; text-transform: uppercase;
  color: var(--texto_suave); margin: 18px 0 4px;
}

/* botoes: chips arredondados */
.stApp button[data-testid="stBaseButton-secondary"] {
  background: var(--superficie); color: var(--texto);
  border: 1px solid var(--borda); border-radius: 999px;
  box-shadow: 0 1px 2px var(--sombra);
  transition: border-color .2s, transform .2s;
}
.stApp button[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--destaque); color: var(--texto); transform: translateY(-1px);
}
.stApp button[data-testid="stBaseButton-secondary"] p { color: var(--texto); }
.stApp button[data-testid="stBaseButton-primary"] {
  background: var(--destaque); color: var(--texto_no_destaque);
  border: 0; border-radius: 12px; font-weight: 600;
}
.stApp button[data-testid="stBaseButton-primary"] p { color: var(--texto_no_destaque); }
.stApp button[data-testid="stBaseButton-tertiary"],
.stApp button[data-testid="stBaseButton-tertiary"] p { color: var(--texto_suave); }
.stApp button[data-testid="stBaseButton-tertiary"]:hover,
.stApp button[data-testid="stBaseButton-tertiary"]:hover p { color: var(--destaque); }

/* marca no topo */
.marca { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 18px; margin-bottom: 14px; }
.marca-icone {
  width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
  background: var(--destaque); color: var(--texto_no_destaque);
}

/* tela vazia */
.hero { text-align: center; margin: 6vh 0 18px; }
.hero-icone {
  width: 76px; height: 76px; margin: 0 auto 22px; border-radius: 50%;
  display: grid; place-items: center; color: var(--texto_no_destaque);
  background: radial-gradient(circle at 35% 30%, #A7F3D0, var(--destaque));
  box-shadow: 0 0 0 12px var(--brilho), 0 0 0 26px var(--brilho), 0 18px 40px var(--brilho);
}
.hero h1 { font-size: 30px; font-weight: 700; letter-spacing: -.01em; padding: 0; }
.hero h1 .destaque { color: var(--destaque); }
.st-key-chips { justify-content: center; }
.st-key-vazio [data-testid="stCaptionContainer"] { text-align: center; }
.pilha { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 26px; }
.pilha span {
  font-size: 12px; color: var(--texto_suave); background: var(--superficie);
  border: 1px solid var(--borda); border-radius: 8px; padding: 4px 10px;
}

/* mensagens em cartoes */
[data-testid="stChatMessage"] {
  background: var(--superficie); border: 1px solid var(--borda);
  border-radius: 18px; padding: 14px 18px; box-shadow: 0 6px 24px var(--sombra);
}
[data-testid^="stChatMessageAvatar"] {
  background: var(--destaque_suave); color: var(--destaque);
}

/* caixa de pergunta */
[data-testid="stChatInput"] {
  background: var(--superficie); border: 1px solid var(--borda); border-radius: 18px;
  box-shadow: 0 0 0 6px var(--brilho), 0 12px 32px var(--sombra);
}
[data-testid="stChatInput"] > div { background: transparent; border-color: transparent; }
[data-testid="stChatInput"] textarea { color: var(--texto); background: transparent; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--texto_suave); }
[data-testid="stChatInputSubmitButton"] {
  background: var(--destaque); color: var(--texto_no_destaque); border-radius: 10px;
}

/* SQL gerado, avisos */
[data-testid="stExpander"] details {
  background: var(--superficie); border: 1px solid var(--borda); border-radius: 12px;
}
[data-testid="stExpander"] summary:hover, [data-testid="stExpander"] summary:hover p { color: var(--destaque); }
[data-testid="stCode"] pre, [data-testid="stCode"] code {
  background: var(--superficie_2) !important; color: var(--texto) !important;
}
[data-testid="stCode"] code span { color: inherit !important; }
[data-testid="stAlertContainer"] p { color: var(--texto); }

/* tabela do resultado */
.tabela-resultado {
  max-height: 420px; overflow: auto; border: 1px solid var(--borda); border-radius: 14px;
  margin: 4px 0 8px;
}
.tabela-resultado table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 0; }
.tabela-resultado th {
  position: sticky; top: 0; background: var(--superficie_2); color: var(--texto_suave);
  font-weight: 600; text-align: left; padding: 9px 14px; border: 0;
}
.tabela-resultado td {
  color: var(--texto); padding: 8px 14px; border: 0; border-top: 1px solid var(--borda);
}
.tabela-resultado .num { text-align: right; font-variant-numeric: tabular-nums; }
.tabela-resultado tr:hover td { background: var(--destaque_suave); }
"""


def css(tema: str | None) -> str:
    paleta = PALETAS[tema_valido(tema)]
    variaveis = "\n".join(f"  --{nome}: {valor};" for nome, valor in paleta.items())
    # Icones dos cartoes (Material Symbols); @import precisa vir antes de qualquer regra.
    fonte = "@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded');"
    return f"{fonte}\n:root {{\n{variaveis}\n}}\n{_ESTILO}"
