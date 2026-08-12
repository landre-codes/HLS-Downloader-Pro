#!/usr/bin/env bash
# Instala o binário Linux do HLS Downloader Pro no ~/.local/bin e cria o
# atalho clicável no menu de aplicativos (plus: instala as libs do Qt/xcb).
# Uso (dentro da pasta onde o binário foi extraído):
#     ./install-desktop.sh
# Para apontar para outro diretório:
#     APP_DIR=/caminho/do/binario ./install-desktop.sh

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")" && pwd)}"
BIN_TARGET="$HOME/.local/bin/HLS-Downloader-Pro"
ICON_DIR="$HOME/.local/share/icons"
APPS_DIR="$HOME/.local/share/applications"

if [[ ! -x "$APP_DIR/HLS-Downloader-Pro" ]]; then
    echo "ERRO: $APP_DIR/HLS-Downloader-Pro não encontrado." >&2
    echo "      Rode este script de dentro da pasta do binário." >&2
    exit 1
fi

# ----------------------------------------------------------------- libs Qt
if command -v apt-get >/dev/null 2>&1; then
    echo "==> Instalando bibliotecas do Qt (xcb)..."
    sudo apt-get install -y -qq \
        libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 \
        libxcb-xfixes0 libxcb-render-util0 libxkbcommon-x11-0 libx11-xcb1
elif command -v dnf >/dev/null 2>&1; then
    echo "==> Instalando bibliotecas do Qt (xcb)..."
    sudo dnf install -y qt6-qtbase xcb-util-cursor xcb-util-wm xcb-util-keysyms \
        xcb-util-renderutil xkbcomp libxkbcommon-x11
fi

# ------------------------------------------------------- copia binário+ícone
BIN_TARGET_DIR="$(dirname "$BIN_TARGET")"
mkdir -p "$BIN_TARGET_DIR" "$ICON_DIR" "$APPS_DIR"
cp -f "$APP_DIR/HLS-Downloader-Pro" "$BIN_TARGET"
chmod +x "$BIN_TARGET"
if [[ -f "$APP_DIR/icon.svg" ]]; then
    cp -f "$APP_DIR/icon.svg" "$ICON_DIR/hls-downloader-pro.svg"
fi

# ------------------------------------------------------------- menu clicável
cat > "$APPS_DIR/hls-downloader-pro.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=HLS Downloader Pro
Comment=Downloader de vídeos HLS/m3u8
Exec=$BIN_TARGET
Icon=hls-downloader-pro
Terminal=false
Categories=AudioVideo;Network;Utility;
StartupWMClass=HLS Downloader Pro
EOF

# GNOME/Unity cacheiam o menu; atualiza o índice se disponível
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

echo ""
echo "==> Pronto!"
echo "    Binário:   $BIN_TARGET"
echo "    Atalho:    HLS Downloader Pro (menu de aplicativos)"
echo "    Para rodar pelo terminal:  hls-downloader-pro (adicione ~/.local/bin ao PATH)"
