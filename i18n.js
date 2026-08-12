// Dicionário PT/EN da interface. `getAll()` devolve o dicionário do idioma
// atual; o ui.qml expõe como `T` e REATRIBUI (retranslate()) quando o idioma
// muda — os bindings `T.chave` são reavaliados automaticamente.

.pragma library

var lang = "pt"

var dict = {
    "pt": {
        app_title: "HLS Downloader Pro",
        titlebar_sub: "yt-dlp + ffmpeg + fallback HTML",
        tab_downloads: "Downloads",
        tab_downloads_tip: "Aba de downloads: fila, progresso e ações",
        tab_settings: "Configurações",
        tab_settings_tip: "Aba de configurações: tema, downloads e cookies",

        entry_title: "Entrada em Lote",
        entry_placeholder: "Cole dezenas ou centenas de links aqui (um por linha)…\nLinks espalhados em textos longos também são detectados automaticamente.",
        btn_add: "Adicionar à Fila",
        btn_add_tip: "Adiciona os links do campo acima à fila de downloads",
        btn_paste: "Colar da Área de Transferência",
        btn_paste_tip: "Lê a área de transferência e adiciona todos os links encontrados",
        btn_import: "Importar .txt",
        btn_import_tip: "Importa uma lista de links de um arquivo .txt",
        btn_clear: "Limpar campo",
        btn_clear_tip: "Apaga o conteúdo do campo de entrada",
        entry_hint: "Dica: copie links de qualquer lugar, clique em “Colar da Área de Transferência” e o app separa tudo automaticamente.",

        warn_attention: "Atenção:",
        warn_ytdlp_missing: "yt-dlp não encontrado no PATH.",
        warn_ffmpeg_missing: "ffmpeg não encontrado no PATH.",
        warn_tools: "Sem essas ferramentas os downloads não funcionam.",

        queue_title: "Fila de Downloads",
        h_status: "Status",
        h_progress: "Progresso",
        h_speed_size: "Velocidade / Tamanho",
        empty_title: "Nenhum link na fila",
        empty_hint: "Cole links acima e clique em Adicionar à Fila",
        stat_waiting: "aguardando",
        stat_downloading: "baixando",
        stat_done: "concluídos",
        stat_errors: "erros",
        btn_start: "Iniciar Fila",
        btn_start_tip: "Inicia os downloads pendentes (respeita o limite de simultâneos)",
        btn_cancel_all: "Cancelar Tudo",
        btn_cancel_all_tip: "Cancela todos os downloads ativos e pendentes",
        btn_clear_finished: "Limpar Concluídos",
        btn_clear_finished_tip: "Remove da tabela os itens concluídos, com erro ou cancelados",

        cfg_appearance: "Aparência",
        cfg_dark: "Tema escuro",
        cfg_dark_tip: "Alterna entre tema escuro e claro",
        cfg_language: "Idioma / Language:",
        cfg_downloads: "Downloads",
        cfg_concurrency: "Downloads simultâneos:",
        cfg_concurrency_tip: "Quantos downloads rodam ao mesmo tempo (1–8)",
        cfg_outdir: "Pasta de Saída",
        cfg_outdir_tip: "Escolhe a pasta onde os vídeos serão salvos",
        cfg_cookies_title: "Cookies (sites com login)",
        cfg_cookies_use: "Usar cookies do navegador",
        cfg_cookies_use_tip: "Envia cookies para sites que exigem login (ou impõem paywall)",
        cfg_browser: "Navegador:",
        cfg_browser_tip: "Navegador de onde os cookies serão lidos (feche-o antes do download)",
        cfg_cookies_file: "Ou arquivo cookies.txt (formato Netscape):",
        cfg_cookies_placeholder: "caminho/para/cookies.txt",
        cfg_cookies_file_tip: "Caminho do arquivo cookies.txt no formato Netscape (substitui o navegador)",
        btn_choose: "Escolher…",
        btn_choose_tip: "Seleciona o arquivo cookies.txt",
        cfg_cookies_hint: "Dica: feche o navegador antes do download (bases de cookies ficam bloqueadas). O arquivo cookies.txt, se definido, substitui o navegador.",
        cfg_tools: "Ferramentas externas",
        tool_found: "encontrado no PATH",
        tool_ytdlp_missing: "NÃO encontrado — instale com: pip install yt-dlp",
        tool_ffmpeg_missing: "NÃO encontrado — necessário para merge de vídeo+áudio",

        tip_edit: "Editar link",
        tip_copy: "Copiar link",
        tip_cancel: "Cancelar este download",
        tip_open: "Abrir pasta do arquivo",
        btn_open: "Abrir",

        s_Aguardando: "Aguardando",
        s_Baixando: "Baixando",
        "s_Analisando HTML": "Analisando HTML",
        "s_Concluído": "Concluído",
        s_Erro: "Erro",
        s_Cancelado: "Cancelado"
    },

    "en": {
        app_title: "HLS Downloader Pro",
        titlebar_sub: "yt-dlp + ffmpeg + HTML fallback",
        tab_downloads: "Downloads",
        tab_downloads_tip: "Downloads tab: queue, progress and actions",
        tab_settings: "Settings",
        tab_settings_tip: "Settings tab: theme, downloads and cookies",

        entry_title: "Batch Entry",
        entry_placeholder: "Paste dozens or hundreds of links here (one per line)…\nLinks scattered in long texts are also detected automatically.",
        btn_add: "Add to Queue",
        btn_add_tip: "Adds the links above to the download queue",
        btn_paste: "Paste from Clipboard",
        btn_paste_tip: "Reads the clipboard and adds all links found",
        btn_import: "Import .txt",
        btn_import_tip: "Imports a link list from a .txt file",
        btn_clear: "Clear field",
        btn_clear_tip: "Clears the input field",
        entry_hint: "Tip: copy links from anywhere, click “Paste from Clipboard” and the app splits everything automatically.",

        warn_attention: "Warning:",
        warn_ytdlp_missing: "yt-dlp not found in PATH.",
        warn_ffmpeg_missing: "ffmpeg not found in PATH.",
        warn_tools: "Without these tools downloads will not work.",

        queue_title: "Download Queue",
        h_status: "Status",
        h_progress: "Progress",
        h_speed_size: "Speed / Size",
        empty_title: "No links in queue",
        empty_hint: "Paste links above and click Add to Queue",
        stat_waiting: "waiting",
        stat_downloading: "downloading",
        stat_done: "completed",
        stat_errors: "errors",
        btn_start: "Start Queue",
        btn_start_tip: "Starts pending downloads (respects the concurrency limit)",
        btn_cancel_all: "Cancel All",
        btn_cancel_all_tip: "Cancels all active and pending downloads",
        btn_clear_finished: "Clear Finished",
        btn_clear_finished_tip: "Removes completed, failed or cancelled items from the table",

        cfg_appearance: "Appearance",
        cfg_dark: "Dark theme",
        cfg_dark_tip: "Toggles dark and light theme",
        cfg_language: "Idioma / Language:",
        cfg_downloads: "Downloads",
        cfg_concurrency: "Concurrent downloads:",
        cfg_concurrency_tip: "How many downloads run at the same time (1–8)",
        cfg_outdir: "Output Folder",
        cfg_outdir_tip: "Choose the folder where videos are saved",
        cfg_cookies_title: "Cookies (login-protected sites)",
        cfg_cookies_use: "Use browser cookies",
        cfg_cookies_use_tip: "Sends cookies to sites that require login (or enforce a paywall)",
        cfg_browser: "Browser:",
        cfg_browser_tip: "Browser whose cookies will be read (close it before downloading)",
        cfg_cookies_file: "Or cookies.txt file (Netscape format):",
        cfg_cookies_placeholder: "path/to/cookies.txt",
        cfg_cookies_file_tip: "Path to a cookies.txt file in Netscape format (overrides the browser)",
        btn_choose: "Choose…",
        btn_choose_tip: "Selects the cookies.txt file",
        cfg_cookies_hint: "Tip: close the browser before downloading (cookie databases get locked). The cookies.txt file, if set, overrides the browser.",
        cfg_tools: "External tools",
        tool_found: "found in PATH",
        tool_ytdlp_missing: "NOT found — install with: pip install yt-dlp",
        tool_ffmpeg_missing: "NOT found — required for video+audio merge",

        tip_edit: "Edit link",
        tip_copy: "Copy link",
        tip_cancel: "Cancel this download",
        tip_open: "Open file folder",
        btn_open: "Open",

        s_Aguardando: "Waiting",
        s_Baixando: "Downloading",
        "s_Analisando HTML": "Analyzing HTML",
        "s_Concluído": "Completed",
        s_Erro: "Error",
        s_Cancelado: "Cancelled"
    }
}

function getAll() {
    var d = dict[lang] || dict["pt"]
    var out = {}
    for (var k in d)
        out[k] = d[k]
    return out
}

function setLang(l) {
    if (dict[l]) lang = l
}
