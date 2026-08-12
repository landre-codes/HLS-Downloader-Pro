#!/usr/bin/env bash
# Instalador do HLS Downloader Pro para Linux (Debian/Ubuntu, Fedora, Arch).
# Cria um ambiente virtual, instala as dependências e um atalho no PATH.

set -euo pipefail

echo "==> HLS Downloader Pro — instalação para Linux"
echo ""

# ---------------------------------------------------------------- ffmpeg + py
if command -v apt-get >/dev/null 2>&1; then
    echo "==> Instalando ffmpeg e python3 (apt)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq ffmpeg python3 python3-venv
elif command -v dnf >/dev/null 2>&1; then
    echo "==> Instalando ffmpeg e python3 (dnf)..."
    sudo dnf install -y ffmpeg python3 python3-pip
elif command -v pacman >/dev/null 2>&1; then
    echo "==> Instalando ffmpeg e python (pacman)..."
    sudo pacman -S --noconfirm ffmpeg python
else
    echo "!! Gerenciador de pacotes desconhecido."
    echo "   Instale manualmente: ffmpeg + python3 + pip."
fi

# ------------------------------------------------------------------ venv + pip
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERRO: python3 não encontrado. Instale o Python 3.10+." >&2
    exit 1
fi

echo "==> Criando ambiente virtual em .venv..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt

# --------------------------------------------------------------------- atalho
LAUNCHER="$HOME/.local/bin/hls-downloader-pro"
mkdir -p "$HOME/.local/bin"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
# Atalho gerado pelo install.sh
exec "$PWD/.venv/bin/python" "$PWD/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

echo ""
echo "==> Instalação concluída!"
echo "    Rode com:  hls-downloader-pro"
echo "    (ou adicione ~/.local/bin ao PATH se ainda não estiver:"
echo "     echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc)"
