"""CSS-темы приложения.

Нативная тема Streamlit — светлая (config.toml base="light").
ТЁМНАЯ ТЕМА не использует :has() (не поддерживается старыми браузерами):
app.py инжектирует DARK_CSS отдельным блоком только при выбранной тёмной теме.
"""

CUSTOM_CSS = """
<style>
/* ═══════════════ БАЗА / СВЕТЛАЯ ТЕМА ═══════════════ */
:root {
    --bg-app: #FFFFFF;
    --bg-sidebar: #F7F7FA;
    --bg-surface: #FFFFFF;
    --bg-input: #FFFFFF;
    --text-primary: #1F2328;
    --text-muted: #6B7280;
    --accent: #7C3AED;
    --accent-2: #4F46E5;
    --accent-hover: #6D28D9;
    --accent-soft: rgba(124, 58, 237, 0.08);
    --border: #EDEFF2;
    --ok: #2DA44E;
    --bad: #CF222E;
    --radius-block: 14px;
    --radius-control: 10px;
    --ghost-rest: 0.35;
    --ghost-hover: 1;
}

.st-dot { display:inline-block; width:10px; height:10px; border-radius:50%;
    margin-right:7px; vertical-align:middle; }
.st-dot.ok  { background: var(--ok);  box-shadow: 0 0 6px rgba(45,164,78,.5); }
.st-dot.bad { background: var(--bad); box-shadow: 0 0 6px rgba(207,34,46,.4); }
.st-dot-text { font-size:.8rem; opacity:.75; vertical-align:middle; }

.msg-meta { text-align:right; font-size:.75rem; opacity:.5; margin-top:-.6rem; }
.theme-slot { height: 1.1rem; }

[data-testid="stChatMessage"] {
    border-radius: var(--radius-block);
    margin-bottom: 8px;
    padding: .6rem .9rem;
}

.stButton > button,
.stDownloadButton > button {
    border-radius: var(--radius-control);
    font-weight: 600;
    font-size: .85rem;
    transition: all .15s ease;
}
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    border: none;
    color: #fff;
}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, var(--accent-hover), #4338CA);
    box-shadow: 0 4px 16px rgba(124,58,237,.3);
}

/* ghost-иконки: 1.65 — emoji внутри кнопки; legacy — title */
button:has([data-testid="stIconEmoji"]),
button[data-testid="stPopoverButton"]:has([data-testid="stIconEmoji"]),
[data-testid="stChatInputFileUploadButton"] button,
.stButton > button[title],
.stDownloadButton > button[title],
button[data-testid="stPopoverButton"][title] {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 2px 6px !important;
    min-width: 0 !important;
    height: auto !important;
    font-size: 1rem !important;
    line-height: 1.2;
    opacity: var(--ghost-rest);
    transition: opacity .15s ease, background-color .15s ease;
}
button:has([data-testid="stIconEmoji"]):hover,
button[data-testid="stPopoverButton"]:has([data-testid="stIconEmoji"]):hover,
[data-testid="stChatInputFileUploadButton"] button:hover,
.stButton > button[title]:hover,
.stDownloadButton > button[title]:hover,
button[data-testid="stPopoverButton"][title]:hover {
    opacity: var(--ghost-hover);
    background-color: var(--accent-soft) !important;
    border-radius: 8px;
}
[data-testid="stChatMessage"] button:has([data-testid="stIconEmoji"]),
[data-testid="stChatMessage"] .stButton > button[title],
[data-testid="stChatMessage"] button[data-testid="stPopoverButton"][title] {
    opacity: .25;
}
[data-testid="stChatMessage"] button:has([data-testid="stIconEmoji"]):hover,
[data-testid="stChatMessage"] .stButton > button[title]:hover,
[data-testid="stChatMessage"] button[data-testid="stPopoverButton"][title]:hover {
    opacity: 1;
}

/* табы: pill-блоки (baseweb + react-aria role=tab) */
[data-testid="stTabs"] [data-baseweb="tab-list"],
[data-testid="stTabs"] [role="tablist"] {
    gap: 8px !important;
    background: var(--accent-soft) !important;
    border-radius: 14px !important;
    padding: 5px !important;
    border-bottom: none !important;
    width: fit-content !important;
}
[data-testid="stTabs"] [data-baseweb="tab"],
[data-testid="stTabs"] [role="tab"] {
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 7px 22px !important;
    min-height: 0 !important;
    background: transparent !important;
    transition: background-color .15s ease, box-shadow .15s ease;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover,
[data-testid="stTabs"] [role="tab"]:hover {
    background: rgba(124, 58, 237, 0.12) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
    color: #fff !important;
    box-shadow: 0 2px 10px rgba(124, 58, 237, 0.35) !important;
}

[data-testid="stChatInput"] {
    border-radius: 16px !important;
    box-shadow: 0 -2px 16px rgba(0,0,0,.04);
}

[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: var(--radius-block); }
/* рамка у прокручиваемого блока истории не нужна */
div[overflow="auto"][data-testid="stLayoutWrapper"],
div[overflow="auto"][data-testid="stLayoutWrapper"] > .stVerticalBlock {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] details { border-radius: 12px; }
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important;
    border-radius: 8px !important;
}

[data-testid="stFileUploaderDropzone"] {
    border-radius: 12px !important;
    padding: 10px 14px !important;
    min-height: 0 !important;
}
[data-testid="stFileUploaderDropzone"] > div > div { font-size: .85rem !important; }

[data-testid="stMarkdownContainer"] { max-width: 100% !important; }
[data-testid="stMarkdownContainer"] table { width: 100% !important; table-layout: fixed !important; }
[data-testid="stMarkdownContainer"] table th,
[data-testid="stMarkdownContainer"] table td {
    white-space: pre-wrap !important;
    word-break: break-word !important;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(128,128,160,.3); border-radius: 3px; }

/* прокручиваемый контейнер истории чата */
[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
    background: rgba(128,128,160,.35); border-radius: 3px;
}

/* кнопка «стоп генерации»: плавно в правом нижнем углу, цвет не приглушать */
.st-key-chat_stop {
    position: fixed;
    right: 18px;
    bottom: 14px;
    z-index: 1050;
}
.st-key-chat_stop button {
    opacity: 1 !important;
    background: #E5484D !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(229, 72, 77, 0.45) !important;
    padding: 4px 10px !important;
    min-width: 0 !important;
}
.st-key-chat_stop button:hover { background: #C93A3F !important; opacity: 1 !important; }
</style>

"""

DARK_CSS = """
<style>
/* ═══════════ ТЁМНАЯ ТЕМА (инжектируется только когда ui_theme=dark) ═══════════ */
:root {
    --bg-app: #0F0A1E;
    --bg-sidebar: #1E1640;
    --bg-surface: rgba(30, 22, 64, 0.26);
    --bg-input: #191136;
    --text-primary: #E2D9F3;
    --text-muted: #9A8FB8;
    --accent-soft: rgba(124, 58, 237, 0.22);
    --border: rgba(124, 58, 237, 0.16);
    --ok: #3FB950;
    --bad: #F85149;
}

.stApp {
    background: linear-gradient(160deg, #0F0A1E 0%, #1A1145 55%, #0D1B3E 100%) !important;
    color: var(--text-primary) !important;
}

/* служебные обёртки: тушим любые фоны светлой темы */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stToolbar"],
[data-testid="stHeader"],
[data-testid="stAppDeployButton"],
[data-testid="stDecoration"],
[data-testid="stViewportSizes"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stElementContainer"],
[data-testid="stMarkdownContainer"],
header[data-testid="stHeader"] {
    background: transparent !important;
    background-color: transparent !important;
}

/* тулбар: иконки меню/прелом */
[data-testid="stToolbar"] * { color: #A78BFA !important; }
[data-testid="stToolbar"] button div { color: #A78BFA !important; }
[data-testid="stToolbar"] kbd { color: #9A8FB8 !important; }
.stApp p,
.stApp li,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp strong,
.stApp a,
.stApp label,
[data-testid="stWidgetLabel"] p,
.stButton > button,
.stDownloadButton > button {
    color: var(--text-primary) !important;
}
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] { color: #fff !important; }
[data-testid="stCaptionContainer"] { color: var(--text-muted) !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E1640 0%, #0F0A1E 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: #D9CEF0 !important; }

[data-testid="stChatMessage"] {
    background: rgba(124, 58, 237, 0.07) !important;
    border: 1px solid rgba(124, 58, 237, 0.12) !important;
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: var(--bg-surface) !important;
    border-color: var(--border) !important;
}

/* поля ввода */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-testid="stChatInput"] textarea {
    background-color: var(--bg-input) !important;
    color: var(--text-primary) !important;
}
.stTextInput > div,
.stTextArea > div,
.stNumberInput > div > div,
[data-baseweb="select"] > div {
    background-color: var(--bg-input) !important;
    border-color: var(--border) !important;
    color: var(--text-primary) !important;
}

/* контролы формы, включая новые React-Aria виджеты (data-rac, role=combobox) */
input,
textarea,
[data-rac][role="group"] {
    background-color: var(--bg-input) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
input[type="checkbox"],
input[type="radio"],
input[type="file"] {
    background: transparent !important;
}
[data-rac][role="group"] { border-radius: 10px; }
[data-rac][role="group"] input { background: transparent !important; }
[data-rac][role="group"] button { background: transparent !important; color: #A78BFA !important; }
[data-rac][role="group"] svg { fill: #A78BFA !important; }
::placeholder { color: #6E6390 !important; opacity: 1; }

/* выпадающий список React-Aria (портал, не baseweb) */
[role="listbox"],
[data-testid="stSelectboxPopover"] div[role="dialog"],
[data-testid="stPopoverBody"] {
    background-color: #1E1640 !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
}
[role="listbox"] * { color: var(--text-primary) !important; }
/* состояния React-Aria: серый дефолт светлой темы на hover/focus/selected */
[role="option"],
[role="option"][data-hovered="true"],
[role="option"][data-focused="true"] {
    background-color: transparent !important;
}
[role="option"]:hover,
[role="option"][data-hovered="true"]:hover,
[role="option"][data-focused="true"]:hover {
    background-color: var(--accent-soft) !important;
}
[role="option"][data-selected="true"],
[role="option"][aria-selected="true"] {
    background-color: var(--accent) !important;
}
[role="option"][data-selected="true"] *,
[role="option"][aria-selected="true"] * { color: #fff !important; }
[role="option"][data-selected="true"][data-hovered="true"],
[role="option"][data-selected="true"][data-focused="true"] {
    background-color: #6D28D9 !important;
}

/* сфокусированное поле combobox — без серого подсвета базовой темы */
[data-rac][role="group"][data-focus-within="true"],
[data-rac][role="group"][data-focus-within="true"] input,
input[data-focused="true"] {
    background-color: var(--bg-input) !important;
    border-color: var(--accent) !important;
    box-shadow: none !important;
}

/* кнопка отправки в поле чата */
[data-testid="stChatInput"] [data-rac] button,
[data-testid="stChatInputSubmitButton"] {
    background: transparent !important;
    border: none !important;
}
[data-testid="stChatInput"] svg { fill: #A78BFA !important; }

/* все внутренние обёртки поля чата прозрачные — тёмный только сам textarea */
[data-testid="stChatInput"] * { background-color: transparent !important; }
[data-testid="stChatInput"] textarea {
    background-color: rgba(25, 17, 54, 0.4) !important;
    color: var(--text-primary) !important;
}

/* загрузчик: тёмная зона дроппинга и карточка загруженного файла */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(30, 22, 64, 0.28) !important;
}
[data-testid="stFileUploaderFile"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px;
    color: var(--text-primary) !important;
}
[data-baseweb="select"] span { color: var(--text-primary) !important; }
[data-baseweb="select"] svg { fill: #A78BFA !important; }
.stTextInput ::placeholder,
.stTextArea ::placeholder,
.stNumberInput ::placeholder,
[data-testid="stChatInput"] ::placeholder { color: #6E6390 !important; }

[data-testid="stChatInput"] {
    background: rgba(20, 14, 44, 0.92) !important;
    border: 1px solid var(--border) !important;
    backdrop-filter: blur(8px);
    box-shadow: none !important;
}

/* portal-слои: меню, поповеры, тултипы, уведомления */
[data-baseweb="popover"],
[data-baseweb="menu"] {
    background-color: #1E1640 !important;
    border: 1px solid var(--border) !important;
}
[data-baseweb="popover"] *,
[data-baseweb="menu"] * { color: var(--text-primary) !important; }
[data-baseweb="menu"] li:hover { background-color: var(--accent-soft) !important; }
[data-baseweb="notification"] {
    background-color: rgba(25, 17, 54, 0.92) !important;
    color: var(--text-primary) !important;
}
[data-testid="stAlert"] p { color: var(--text-primary) !important; }

/* код */
[data-testid="stCode"] { background: #17102E !important; }
[data-testid="stCode"] code, code { color: #D9CEF0 !important; }
/* inline-code (`` `test` ``, `# test`) — светлая заливка базовой темы неуместна */
[data-testid="stMarkdownContainer"] code {
    background-color: rgba(124, 58, 237, 0.2) !important;
    color: #D9CEF0 !important;
}
[data-testid="stMarkdownContainer"] pre {
    background-color: rgba(25, 17, 54, 0.8) !important;
    color: #E2D9F3 !important;
}
[data-testid="stMarkdownContainer"] pre code { background: transparent !important; }
[data-testid="stCode"] [data-baseweb="button"] { color: #A78BFA !important; }

/* кнопки: Streamlit 1.65 рендерит <button kind=... data-testid="stBaseButton-*"> без
   обёртки .stButton — целимся напрямую по kind/testid; legacy .stButton оставлен */
button[kind="primary"] {
    background: linear-gradient(135deg, #7C3AED, #4F46E5) !important;
    border: none !important;
    color: #fff !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #6D28D9, #4338CA) !important;
}
button:not([kind="primary"]) {
    background: rgba(30, 22, 64, 0.3) !important;
    border: 1px solid rgba(124, 58, 237, 0.22) !important;
    color: var(--text-primary) !important;
}
button:not([kind="primary"]):hover { background: var(--accent-soft) !important; }

/* ghost-иконки: только emoji-иконки (label пустой) — ступ/повтор/тема/pdf/корзина/копировать */
button:has([data-testid="stIconEmoji"]),
.stButton > button[title]:not([kind="primary"]),
.stDownloadButton > button[title],
button[data-testid="stPopoverButton"][title],
button[data-testid="stPopoverButton"]:has([data-testid="stIconEmoji"]) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    opacity: .35;
}
button:has([data-testid="stIconEmoji"]):hover,
.stButton > button[title]:not([kind="primary"]):hover,
.stDownloadButton > button[title]:hover,
button[data-testid="stPopoverButton"][title]:hover,
button[data-testid="stPopoverButton"]:has([data-testid="stIconEmoji"]):hover {
    opacity: 1;
    background: var(--accent-soft) !important;
}
[data-testid="stChatMessage"] button:has([data-testid="stIconEmoji"]) { opacity: .25; }
[data-testid="stChatMessage"] button:has([data-testid="stIconEmoji"]):hover { opacity: 1; }

/* кнопка «прикрепить файл» в поле чата — тоже ghost */
[data-testid="stChatInputFileUploadButton"] button {
    background: transparent !important;
    border: none !important;
    color: #A78BFA !important;
}

/* табы */
[data-testid="stTabs"] [data-baseweb="tab-list"],
[data-testid="stTabs"] [role="tablist"] {
    background: rgba(30, 22, 64, 0.32) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"],
[data-testid="stTabs"] [role="tab"] { color: #C9B8F0 !important; }
[data-testid="stTabs"] [data-baseweb="tab"]:hover,
[data-testid="stTabs"] [role="tab"]:hover {
    background: rgba(124, 58, 237, 0.22) !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #fff !important;
    box-shadow: 0 2px 12px rgba(124, 58, 237, 0.5) !important;
}

/* expander: summary иначе остаётся серым (нативный светлый фон) */
[data-testid="stExpander"] details {
    background: rgba(30, 22, 64, 0.28) !important;
    border-color: rgba(124, 58, 237, 0.14) !important;
}
[data-testid="stExpander"] details > summary { background: transparent !important; }
[data-testid="stExpander"] details > summary:hover { background: var(--accent-soft) !important; }
[data-testid="stExpander"] summary * { color: #C9B8F0 !important; }
[data-testid="stExpander"] summary svg { fill: #A78BFA !important; }

/* сегментированный переключатель (тема) — серый трек нативной светлой темы */
[data-testid="stSegmentedControl"],
[data-testid="stSegmentedControl"] > div,
[data-baseweb="segmented-control"],
[data-rac][role="radiogroup"] {
    background: rgba(30, 22, 64, 0.32) !important;
    border-radius: 10px;
}
[data-testid="stSegmentedControl"] label > div,
[data-baseweb="segmented-control"] label > div,
[role="radio"] {
    background-color: transparent !important;
    color: #C9B8F0 !important;
}
[data-testid="stSegmentedControl"] input:checked ~ div,
[data-baseweb="segmented-control"] input:checked ~ div,
[role="radio"][aria-checked="true"] {
    background-color: var(--accent) !important;
    color: #fff !important;
}

/* слайдеры / чекбоксы */
[data-baseweb="slider"] [role="slider"] { background-color: #B9A6FF !important; }
[data-baseweb="slider"] > div > div:first-child > div { background-color: rgba(124,58,237,.3) !important; }
[data-baseweb="checkbox"] i { color: var(--bg-input) !important; }

[data-testid="stFileUploaderDropzone"] {
    border: 1px dashed var(--border) !important;
}
[data-testid="stFileUploaderDropzone"] span { color: #C9B8F0 !important; }

hr { background-color: rgba(124, 58, 237, 0.14) !important; }
[data-baseweb="tag"] { background-color: rgba(124,58,237,.3) !important; color: #E2D9F3 !important; }
::-webkit-scrollbar-thumb { background: rgba(124, 58, 237, 0.35); }

/* прогресс: фон-трек тоже светлый из темы */
[data-testid="stProgress"] > div > div { background-color: rgba(124, 58, 237, 0.2) !important; }
[data-testid="stProgress"] { color: var(--text-muted) !important; }

/* загрузчик: список файлов и подписи */
[data-testid="stFileUploaderFooter"] *,
[data-testid="stFileUploaderDropzoneInstructions"] { color: #9A8FB8 !important; }
[data-testid="stFileUploaderFileName"] { color: var(--text-primary) !important; }

/* степперы number_input */
[data-testid="stNumberInputStepper"] {
    background: var(--bg-input) !important;
    border-color: var(--border) !important;
}
[data-testid="stNumberInputStepper"] svg { fill: #A78BFA !important; }

/* прокручиваемый контейнер истории чата */
[data-testid="stVerticalBlock"] { scrollbar-color: rgba(124,58,237,.3) transparent; }

/* toast */
[data-testid="stToast"] {
    background-color: #1E1640 !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

/* glide-data-grid */
:root {
    --gdg-bg-cell: #191136;
    --gdg-bg-header: #1E1640;
    --gdg-fg-cell: #E2D9F3;
    --gdg-border-color: rgba(124, 58, 237, 0.14);
    --gdg-horizontal-line-color: rgba(124, 58, 237, 0.2);
    --gdg-vertical-line-color: rgba(124, 58, 237, 0.2);
    --gdg-accent-color: #7C3AED;
    --gdg-accent-fg: #FFFFFF;
}

/* кнопка «стоп генерации»: плавно в правом нижнем углу, цвет не приглушать */
.st-key-chat_stop {
    position: fixed;
    right: 18px;
    bottom: 14px;
    z-index: 1050;
}
.st-key-chat_stop button {
    opacity: 1 !important;
    background: #E5484D !important;
    color: #fff !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(229, 72, 77, 0.45) !important;
    padding: 4px 10px !important;
    min-width: 0 !important;
}
.st-key-chat_stop button:hover { background: #C93A3F !important; opacity: 1 !important; }
</style>

"""

DARK_SENTINEL = "ТЁМНАЯ ТЕМА (инжектируется"
