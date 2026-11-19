#!/usr/bin/env bash
# ============================================================
#   ARASAKA // Tema completo para Zorin OS (17 / 18)
#   Boot (GRUB + Plymouth) -> Login (GDM) -> Desktop (GTK,
#   Shell, icones, cursores, sons, wallpapers) -> Terminal.
#
#   Uso:  ./install.sh [opcoes]      (NAO rode com sudo)
#     --sem-grub        nao mexe no GRUB
#     --sem-plymouth    nao troca a tela de carregamento
#     --sem-login       nao mexe na tela de login (GDM)
#     --sem-terminal    nao mexe no bash / perfil do terminal
#     --sem-sons        nao troca o tema de sons
#     --sem-download    nao baixa as fontes Rajdhani / Share Tech Mono
#     --sem-efeitos     nao instala a extensao Arasaka FX (glitch nas janelas, feixe no fundo, CRT)
#     --grub-oculto     mantem o menu do GRUB escondido
#     -y                nao pede confirmacao
# ============================================================

set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="$DIR/theme"

DO_GRUB=1 DO_PLY=1 DO_GDM=1 DO_TERM=1 DO_SND=1 DO_DL=1 DO_FX=1 GRUB_SHOW=1 ASSUME_YES=0
for a in "$@"; do
  case "$a" in
    --sem-grub) DO_GRUB=0 ;;
    --sem-plymouth) DO_PLY=0 ;;
    --sem-login) DO_GDM=0 ;;
    --sem-terminal) DO_TERM=0 ;;
    --sem-sons) DO_SND=0 ;;
    --sem-download) DO_DL=0 ;;
    --sem-efeitos) DO_FX=0 ;;
    --grub-oculto) GRUB_SHOW=0 ;;
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Opcao desconhecida: $a"; exit 1 ;;
  esac
done

R=$'\e[38;2;227;18;31m'; RH=$'\e[38;2;255;59;71m'; W=$'\e[38;2;236;236;240m'
G=$'\e[38;2;120;120;130m'; B=$'\e[1m'; N=$'\e[0m'

STEP=0
step()  { STEP=$((STEP + 1)); printf '\n%s%s[%02d]%s %s%s%s\n' "$R" "$B" "$STEP" "$N" "$W$B" "$*" "$N"; }
info()  { printf '     %s›%s %s\n' "$R" "$N" "$*"; }
ok()    { printf '     %s■%s %s\n' "$R" "$N" "$*"; }
warn()  { printf '     %s!! %s%s\n' "$RH" "$*" "$N"; }
die()   { printf '\n%s!! %s%s\n' "$RH" "$*" "$N"; exit 1; }

SYS_BK=/var/lib/arasaka-theme          # backups do sistema
USR_BK="$HOME/.config/arasaka"          # backups do usuario
GS_BK="$USR_BK/gsettings.bak"
SHARE=/usr/share/arasaka
FONT_DIR=/usr/local/share/fonts/arasaka
HAVE_RAJ=0 HAVE_STM=0

banner() {
  printf '%s' "$R"
  if [ -r "$T/terminal/logo.txt" ]; then sed 's/^/   /' "$T/terminal/logo.txt"; fi
  printf '%s\n   %sA R A S A K A%s  %s// INSTALADOR DE TEMA PARA ZORIN OS%s\n' "$N" "$W$B" "$N" "$G" "$N"
  printf '   %sSECURITY · TECHNOLOGY · ORDER%s\n' "$G" "$N"
}

# ---------------------------------------------------------------- utilitarios
gs_set() {  # schema key valor  (faz backup do valor antigo uma vez)
  local schema=$1 key=$2 val=$3
  gsettings list-keys "$schema" 2>/dev/null | grep -qx "$key" || return 0
  mkdir -p "$USR_BK"
  if ! grep -q "^$schema $key " "$GS_BK" 2>/dev/null; then
    printf '%s %s %s\n' "$schema" "$key" "$(gsettings get "$schema" "$key")" >> "$GS_BK"
  fi
  gsettings set "$schema" "$key" "$val" 2>/dev/null || warn "nao consegui definir $schema $key"
}

set_kv() {  # arquivo CHAVE valor  (para /etc/default/grub)
  local f=$1 k=$2 v=$3
  if sudo grep -qE "^#?[[:space:]]*$k=" "$f"; then
    sudo sed -i -E "s|^#?[[:space:]]*$k=.*|$k=$v|" "$f"
  else
    echo "$k=$v" | sudo tee -a "$f" >/dev/null
  fi
}

backup_sys() {  # arquivo -> /var/lib/arasaka-theme/<nome> (so na primeira vez)
  local src=$1 name=$2
  [ -e "$src" ] || return 0
  sudo mkdir -p "$SYS_BK"
  [ -e "$SYS_BK/$name" ] || sudo cp -a "$src" "$SYS_BK/$name"
}

pf2_name() {  # le o nome interno de uma fonte .pf2 do GRUB
  python3 - "$1" <<'PY'
import struct, sys
d = open(sys.argv[1], 'rb').read()
i = d.find(b'NAME')
n = struct.unpack('>I', d[i + 4:i + 8])[0]
print(d[i + 8:i + 8 + n].rstrip(b'\0').decode())
PY
}

# ---------------------------------------------------------------- verificacoes
preflight() {
  [ "$EUID" -eq 0 ] && die "Rode como seu usuario normal (sem sudo): ./install.sh"
  [ -f "$T/backgrounds/arasaka-core.png" ] || die "Assets nao encontrados em $T. Rode antes: python3 build/build_assets.py"
  command -v gsettings >/dev/null || die "gsettings nao encontrado. Este tema e para Zorin OS / GNOME."
  local os
  os=$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-?}")
  info "Sistema: $os"
  case "$os" in *Zorin*) ;; *) warn "Nao parece ser Zorin OS. Deve funcionar em Ubuntu/GNOME, mas nao foi feito para isso." ;; esac
  if [ "$ASSUME_YES" -eq 0 ]; then
    printf '\n   O instalador vai pedir sua senha (sudo) para os arquivos do sistema.\n'
    printf '   Backups ficam em %s e %s.\n' "$SYS_BK" "$USR_BK"
    printf '   %sContinuar? [s/N] %s' "$W" "$N"
    local r; read -r r
    case "$r" in s|S|y|Y|sim|SIM) ;; *) echo "Cancelado."; exit 0 ;; esac
  fi
  sudo -v || die "sudo necessario."
  # mantem o sudo vivo durante a instalacao
  ( while true; do sudo -n true; sleep 50; kill -0 "$$" 2>/dev/null || exit; done ) 2>/dev/null &
  SUDO_KEEPER=$!
  trap 'kill $SUDO_KEEPER 2>/dev/null' EXIT
  sudo mkdir -p "$SYS_BK" "$SHARE"
  mkdir -p "$USR_BK"
}

deps() {
  step "Dependencias"
  local pkgs=(gnome-shell-extensions papirus-icon-theme libglib2.0-bin libglib2.0-dev-bin dconf-cli curl python3 fontconfig)
  [ "$DO_PLY" -eq 1 ] && pkgs+=(plymouth plymouth-themes plymouth-label)
  [ "$DO_GRUB" -eq 1 ] && pkgs+=(grub-common)
  [ "$DO_SND" -eq 1 ] && pkgs+=(gnome-session-canberra)
  local missing=()
  for p in "${pkgs[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
  if [ ${#missing[@]} -eq 0 ]; then ok "tudo ja instalado"; return; fi
  info "instalando: ${missing[*]}"
  sudo apt-get update -qq || warn "apt update falhou (sem internet?)"
  for p in "${missing[@]}"; do
    sudo apt-get install -y -qq --no-install-recommends "$p" >/dev/null 2>&1 && ok "$p" || warn "nao foi possivel instalar $p"
  done
}

fonts() {
  step "Fontes"
  sudo mkdir -p "$FONT_DIR"
  sudo install -m644 "$T/fonts/cedge1.ttf" "$FONT_DIR/"
  ok "cedge1 (titulos e logos)"
  if [ "$DO_DL" -eq 1 ]; then
    local base="https://github.com/google/fonts/raw/main/ofl"
    local f
    for f in rajdhani/Rajdhani-Regular.ttf rajdhani/Rajdhani-Medium.ttf rajdhani/Rajdhani-SemiBold.ttf \
             rajdhani/Rajdhani-Bold.ttf sharetechmono/ShareTechMono-Regular.ttf; do
      local name=${f##*/}
      [ -s "$FONT_DIR/$name" ] && continue
      if curl -fsSL --max-time 30 "$base/$f" -o "/tmp/$name"; then
        sudo install -m644 "/tmp/$name" "$FONT_DIR/$name"; rm -f "/tmp/$name"
      else
        warn "falha ao baixar $name"
      fi
    done
  fi
  [ -s "$FONT_DIR/Rajdhani-SemiBold.ttf" ] && HAVE_RAJ=1 && ok "Rajdhani (interface)"
  [ -s "$FONT_DIR/ShareTechMono-Regular.ttf" ] && HAVE_STM=1 && ok "Share Tech Mono (terminal)"
  sudo fc-cache -f "$FONT_DIR" >/dev/null 2>&1
  fc-cache -f >/dev/null 2>&1
}

wallpapers() {
  step "Wallpapers"
  sudo mkdir -p /usr/share/backgrounds/arasaka /usr/share/gnome-background-properties
  sudo install -m644 "$T"/backgrounds/*.png /usr/share/backgrounds/arasaka/
  sudo install -m644 "$T/backgrounds/arasaka-backgrounds.xml" /usr/share/gnome-background-properties/arasaka.xml
  sudo install -m644 "$T/logo/arasaka-gdm.png" /usr/share/pixmaps/arasaka-gdm.png
  sudo install -m644 "$T/logo/arasaka-512.png" /usr/share/pixmaps/arasaka.png
  sudo install -m644 "$T/logo/arasaka.svg" /usr/share/pixmaps/arasaka.svg
  ok "5 wallpapers em /usr/share/backgrounds/arasaka (aparecem em Configuracoes > Fundo)"
}

# Escolhe o tema base do Zorin para herdar (vermelho escuro de preferencia).
base_theme() {  # subdir (gtk-3.0 | gtk-4.0 | gnome-shell)
  local sub=$1 t cur
  cur=$(gsettings get org.gnome.desktop.interface gtk-theme 2>/dev/null | tr -d "'")
  for t in ZorinRed-Dark "$cur" ZorinGrey-Dark ZorinBlue-Dark; do
    [ -n "$t" ] && [ "$t" != "Arasaka" ] && [ -d "/usr/share/themes/$t/$sub" ] && { echo "$t"; return; }
  done
}

gtk_theme() {
  step "Tema de janelas (GTK 3 / GTK 4 / libadwaita)"
  local dst=/usr/share/themes/Arasaka tmp
  tmp=$(mktemp -d)
  mkdir -p "$tmp/Arasaka"
  cp "$T/gtk/Arasaka/index.theme" "$tmp/Arasaka/"

  # GTK 3: copia o tema base inteiro (assets relativos continuam funcionando)
  local b3; b3=$(base_theme gtk-3.0)
  if [ -n "$b3" ]; then
    cp -r "/usr/share/themes/$b3/gtk-3.0" "$tmp/Arasaka/gtk-3.0"
    [ -f "$tmp/Arasaka/gtk-3.0/gtk-dark.css" ] && mv "$tmp/Arasaka/gtk-3.0/gtk-dark.css" "$tmp/Arasaka/gtk-3.0/base-dark.css"
    mv "$tmp/Arasaka/gtk-3.0/gtk.css" "$tmp/Arasaka/gtk-3.0/base.css"
    local basecss=base.css
    [ -f "$tmp/Arasaka/gtk-3.0/base-dark.css" ] && basecss=base-dark.css
    printf '@import url("%s");\n@import url("arasaka.css");\n' "$basecss" > "$tmp/Arasaka/gtk-3.0/gtk.css"
    info "GTK 3 baseado em $b3"
  else
    mkdir -p "$tmp/Arasaka/gtk-3.0"
    printf '@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css");\n@import url("arasaka.css");\n' \
      > "$tmp/Arasaka/gtk-3.0/gtk.css"
    info "GTK 3 baseado em Adwaita-dark"
  fi
  cp "$T/gtk/Arasaka/gtk-3.0/arasaka.css" "$tmp/Arasaka/gtk-3.0/"
  cp "$tmp/Arasaka/gtk-3.0/gtk.css" "$tmp/Arasaka/gtk-3.0/gtk-dark.css"

  # GTK 4 (apps GTK4 sem libadwaita)
  local b4; b4=$(base_theme gtk-4.0)
  if [ -n "$b4" ]; then
    cp -r "/usr/share/themes/$b4/gtk-4.0" "$tmp/Arasaka/gtk-4.0"
    [ -f "$tmp/Arasaka/gtk-4.0/gtk-dark.css" ] && mv "$tmp/Arasaka/gtk-4.0/gtk-dark.css" "$tmp/Arasaka/gtk-4.0/base-dark.css"
    [ -f "$tmp/Arasaka/gtk-4.0/gtk.css" ] && mv "$tmp/Arasaka/gtk-4.0/gtk.css" "$tmp/Arasaka/gtk-4.0/base.css"
    local b4css=base.css
    [ -f "$tmp/Arasaka/gtk-4.0/base-dark.css" ] && b4css=base-dark.css
    printf '@import url("%s");\n@import url("arasaka.css");\n' "$b4css" > "$tmp/Arasaka/gtk-4.0/gtk.css"
  else
    mkdir -p "$tmp/Arasaka/gtk-4.0"
    printf '@import url("arasaka.css");\n' > "$tmp/Arasaka/gtk-4.0/gtk.css"
  fi
  cp "$T/gtk/Arasaka/gtk-4.0/gtk.css" "$tmp/Arasaka/gtk-4.0/arasaka.css"
  cp "$tmp/Arasaka/gtk-4.0/gtk.css" "$tmp/Arasaka/gtk-4.0/gtk-dark.css"

  # GNOME Shell
  local bs; bs=$(base_theme gnome-shell)
  mkdir -p "$tmp/Arasaka/gnome-shell"
  if [ -n "$bs" ] && [ -f "/usr/share/themes/$bs/gnome-shell/gnome-shell.css" ]; then
    cp -r "/usr/share/themes/$bs/gnome-shell/." "$tmp/Arasaka/gnome-shell/"
    mv "$tmp/Arasaka/gnome-shell/gnome-shell.css" "$tmp/Arasaka/gnome-shell/base.css"
    printf '@import url("base.css");\n' > "$tmp/Arasaka/gnome-shell/gnome-shell.css"
    info "Shell baseado em $bs"
  else
    local gres=/usr/share/gnome-shell/gnome-shell-theme.gresource n css=""
    for n in gnome-shell-dark.css gnome-shell.css; do
      gresource list "$gres" 2>/dev/null | grep -qx "/org/gnome/shell/theme/$n" && { css=$n; break; }
    done
    [ -n "$css" ] && printf '@import url("resource:///org/gnome/shell/theme/%s");\n' "$css" > "$tmp/Arasaka/gnome-shell/gnome-shell.css"
    info "Shell baseado no tema padrao do GNOME"
  fi
  cat "$T/shell/arasaka-shell.css" >> "$tmp/Arasaka/gnome-shell/gnome-shell.css"
  # imagens usadas pelo CSS do shell (grade de neon da visão geral)
  [ -d "$T/shell/assets" ] && cp "$T/shell/assets/"* "$tmp/Arasaka/gnome-shell/"

  sudo rm -rf "$dst"
  sudo cp -r "$tmp/Arasaka" "$dst"
  sudo chmod -R a+rX "$dst"
  rm -rf "$tmp"
  ok "tema instalado em $dst"

  # libadwaita (Configuracoes, Arquivos, etc.)
  mkdir -p "$HOME/.config/gtk-4.0"
  local u4="$HOME/.config/gtk-4.0/gtk.css"
  if [ -e "$u4" ] && ! grep -q "ARASAKA" "$u4" 2>/dev/null; then
    [ -e "$USR_BK/gtk-4.0.css.bak" ] || cp -a "$u4" "$USR_BK/gtk-4.0.css.bak"
  fi
  rm -f "$u4"
  cp "$T/gtk/Arasaka/gtk-4.0/gtk.css" "$u4"
  ok "libadwaita: ~/.config/gtk-4.0/gtk.css"

  if command -v flatpak >/dev/null 2>&1; then
    flatpak override --user --filesystem=xdg-config/gtk-4.0:ro >/dev/null 2>&1 && ok "apps Flatpak (libadwaita) tambem tematizados"
  fi
}

icons() {
  step "Icones"
  local dst=/usr/share/icons/Arasaka tmp cur
  cur=$(gsettings get org.gnome.desktop.interface icon-theme 2>/dev/null | tr -d "'")
  tmp=$(mktemp -d)
  cp -r "$T/icons/Arasaka" "$tmp/"
  local dirs=("scalable/apps" "symbolic/apps")
  local pap=""
  for p in /usr/share/icons/Papirus /usr/share/icons/Papirus-Dark; do [ -d "$p" ] && { pap=/usr/share/icons/Papirus; break; }; done
  if [ -n "$pap" ]; then
    local sz f n c=0
    for sz in 16x16 22x22 24x24 32x32 48x48 64x64; do
      [ -d "$pap/$sz/places" ] || continue
      mkdir -p "$tmp/Arasaka/$sz/places"
      for f in "$pap/$sz/places"/folder-red*.svg "$pap/$sz/places"/user-red-*.svg; do
        [ -e "$f" ] || continue
        n=$(basename "$f"); n=${n/folder-red/folder}; n=${n/user-red-/user-}
        ln -sf "$f" "$tmp/Arasaka/$sz/places/$n"; c=$((c + 1))
      done
      dirs+=("$sz/places")
    done
    ok "pastas vermelhas ($c icones do Papirus)"
  else
    warn "Papirus nao encontrado: pastas ficam no estilo atual"
  fi
  local inherits=""
  [ -d /usr/share/icons/Papirus-Dark ] && inherits="Papirus-Dark,"
  [ -n "$cur" ] && [ "$cur" != "Arasaka" ] && [ "$cur" != "Papirus-Dark" ] && inherits+="$cur,"
  inherits+="Adwaita,hicolor"
  {
    printf '[Icon Theme]\nName=Arasaka\nComment=Arasaka Corporation icons\nInherits=%s\n' "$inherits"
    printf 'Directories=%s\n\n' "$(IFS=,; echo "${dirs[*]}")"
    printf '[scalable/apps]\nContext=Applications\nSize=128\nMinSize=8\nMaxSize=512\nType=Scalable\n\n'
    printf '[symbolic/apps]\nContext=Applications\nSize=16\nMinSize=8\nMaxSize=512\nType=Scalable\n\n'
    local d
    for d in "${dirs[@]:2}"; do
      printf '[%s]\nContext=Places\nSize=%s\nType=Fixed\n\n' "$d" "${d%%x*}"
    done
  } > "$tmp/Arasaka/index.theme"
  sudo rm -rf "$dst"
  sudo cp -a "$tmp/Arasaka" "$dst"
  sudo chmod -R a+rX "$dst"
  rm -rf "$tmp"
  sudo gtk-update-icon-cache -f -q "$dst" 2>/dev/null
  ok "icones em $dst (herda: $inherits)"
}

cursors() {
  step "Cursores"
  local dst=/usr/share/icons/Arasaka-Cursors
  sudo rm -rf "$dst"
  sudo cp -r "$T/cursors/Arasaka-Cursors" "$dst"
  local a b n=0
  while read -r a b; do
    [ -n "$a" ] || continue
    [ -e "$dst/cursors/$a" ] && continue
    sudo ln -s "$b" "$dst/cursors/$a" && n=$((n + 1))
  done < "$T/cursors/Arasaka-Cursors/links.txt"
  sudo rm -f "$dst/links.txt"
  sudo chmod -R a+rX "$dst"
  ok "cursores instalados ($n apelidos)"
}

sounds() {
  [ "$DO_SND" -eq 1 ] || return 0
  step "Sons"
  sudo rm -rf /usr/share/sounds/Arasaka
  sudo cp -r "$T/sounds/Arasaka" /usr/share/sounds/Arasaka
  sudo chmod -R a+rX /usr/share/sounds/Arasaka
  sudo install -m755 "$T/bin/arasaka-login-sound" "$SHARE/arasaka-login-sound"
  mkdir -p "$HOME/.config/autostart"
  cat > "$HOME/.config/autostart/arasaka-login-sound.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Arasaka login sound
Exec=$SHARE/arasaka-login-sound
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Phase=Application
EOF
  ok "tema de sons + som de entrada na sessao"
}

apply_settings() {
  step "Aplicando configuracoes do usuario"
  gs_set org.gnome.desktop.interface gtk-theme "'Arasaka'"
  gs_set org.gnome.desktop.interface icon-theme "'Arasaka'"
  gs_set org.gnome.desktop.interface cursor-theme "'Arasaka-Cursors'"
  gs_set org.gnome.desktop.interface color-scheme "'prefer-dark'"
  if [ "$HAVE_RAJ" -eq 1 ]; then
    gs_set org.gnome.desktop.interface font-name "'Rajdhani SemiBold 12'"
    gs_set org.gnome.desktop.wm.preferences titlebar-font "'Rajdhani Bold 12'"
  fi
  [ "$HAVE_STM" -eq 1 ] && gs_set org.gnome.desktop.interface monospace-font-name "'Share Tech Mono 12'"
  gs_set org.gnome.desktop.wm.preferences theme "'Arasaka'"
  local bg="file:///usr/share/backgrounds/arasaka/arasaka-core.png"
  gs_set org.gnome.desktop.background picture-uri "'$bg'"
  gs_set org.gnome.desktop.background picture-uri-dark "'$bg'"
  gs_set org.gnome.desktop.background picture-options "'zoom'"
  gs_set org.gnome.desktop.background primary-color "'#000000'"
  gs_set org.gnome.desktop.screensaver picture-uri "'file:///usr/share/backgrounds/arasaka/arasaka-login.png'"
  gs_set org.gnome.desktop.screensaver picture-options "'zoom'"
  if [ "$DO_SND" -eq 1 ]; then
    gs_set org.gnome.desktop.sound theme-name "'Arasaka'"
    gs_set org.gnome.desktop.sound event-sounds "true"
  fi
  # painel do Zorin (Zorin Taskbar, baseado no Dash to Panel)
  gs_set org.gnome.shell.extensions.zorin-taskbar trans-use-custom-bg "true"
  gs_set org.gnome.shell.extensions.zorin-taskbar trans-bg-color "'#050506'"
  gs_set org.gnome.shell.extensions.zorin-taskbar trans-use-custom-opacity "true"
  gs_set org.gnome.shell.extensions.zorin-taskbar trans-panel-opacity "0.94"
  ok "tema, icones, cursor, fontes, fundo e sons aplicados"

  # tema do shell via extensao User Themes
  local uuid=user-theme@gnome-shell-extensions.gcampax.github.com cur
  cur=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null)
  if [[ "$cur" != *"$uuid"* ]]; then
    if [[ "$cur" == "@as []" || "$cur" == "[]" || -z "$cur" ]]; then
      gs_set org.gnome.shell enabled-extensions "['$uuid']"
    else
      gs_set org.gnome.shell enabled-extensions "${cur%]}, '$uuid']"
    fi
  fi
  gnome-extensions enable "$uuid" >/dev/null 2>&1 || true
  if gsettings list-schemas | grep -qx org.gnome.shell.extensions.user-theme; then
    gs_set org.gnome.shell.extensions.user-theme name "'Arasaka'"
    ok "tema do GNOME Shell: Arasaka"
  else
    local sd=/usr/share/gnome-shell/extensions/$uuid/schemas
    if [ -d "$sd" ]; then
      gsettings --schemadir "$sd" set org.gnome.shell.extensions.user-theme name "'Arasaka'" && ok "tema do GNOME Shell: Arasaka"
    else
      warn "extensao User Themes nao encontrada; o painel/menus usarao o tema padrao do Zorin"
    fi
  fi
}

terminal() {
  [ "$DO_TERM" -eq 1 ] || return 0
  step "Terminal"
  sudo mkdir -p "$SHARE/terminal"
  sudo install -m644 "$T/terminal/logo.txt" "$T/terminal/arasaka-bashrc.sh" "$SHARE/terminal/"
  if ! grep -q ">>> arasaka-theme >>>" "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" <<'EOF'

# >>> arasaka-theme >>>
[ -r /usr/share/arasaka/terminal/arasaka-bashrc.sh ] && . /usr/share/arasaka/terminal/arasaka-bashrc.sh
# <<< arasaka-theme <<<
EOF
  fi
  ok "prompt + banner de acesso no bash (comando: arasaka)"

  # GNOME Terminal
  if command -v dconf >/dev/null 2>&1; then
    local P=/org/gnome/terminal/legacy/profiles: U=7a5a5a20-2077-4a7a-a5a5-a5a5a5a52077
    local list def
    list=$(dconf read "$P/list")
    def=$(dconf read "$P/default")
    [ -f "$USR_BK/terminal-default.bak" ] || printf '%s\n' "${def:-}" > "$USR_BK/terminal-default.bak"
    if [ -z "$list" ]; then
      list="['b1dcc9dd-5262-4d8d-a863-c897e6d979b9', '$U']"
    elif [[ "$list" != *"$U"* ]]; then
      list="${list%]}, '$U']"
    fi
    dconf write "$P/list" "$list"
    local K="$P/:$U"
    local font="'Monospace 12'"
    [ "$HAVE_STM" -eq 1 ] && font="'Share Tech Mono 13'"
    dconf write "$K/visible-name" "'Arasaka'"
    dconf write "$K/use-theme-colors" "false"
    dconf write "$K/foreground-color" "'#ECECF0'"
    dconf write "$K/background-color" "'#050506'"
    dconf write "$K/bold-color-same-as-fg" "false"
    dconf write "$K/bold-color" "'#FFFFFF'"
    dconf write "$K/cursor-colors-set" "true"
    dconf write "$K/cursor-background-color" "'#E3121F'"
    dconf write "$K/cursor-foreground-color" "'#050506'"
    dconf write "$K/highlight-colors-set" "true"
    dconf write "$K/highlight-background-color" "'#E3121F'"
    dconf write "$K/highlight-foreground-color" "'#FFFFFF'"
    dconf write "$K/palette" "['#0D0D10', '#E3121F', '#9FB4A8', '#FFB347', '#6B8CAE', '#C23B6E', '#8FC1C4', '#C9C9CF', '#3A3A42', '#FF3B47', '#C5DCCD', '#FFD08A', '#9DB8D6', '#FF6B9C', '#B8E3E5', '#F5F5F7']"
    dconf write "$K/bold-is-bright" "true"
    dconf write "$K/use-system-font" "false"
    dconf write "$K/font" "$font"
    dconf write "$K/cursor-shape" "'block'"
    dconf write "$K/cursor-blink-mode" "'on'"
    dconf write "$K/use-transparent-background" "true"
    dconf write "$K/background-transparency-percent" "6"
    dconf write "$K/scrollbar-policy" "'never'"
    dconf write "$K/default-size-columns" "110"
    dconf write "$K/default-size-rows" "30"
    dconf write "$P/default" "'$U'"
    gs_set org.gnome.Terminal.Legacy.Settings theme-variant "'dark'"
    ok "perfil 'Arasaka' no GNOME Terminal (definido como padrao)"
  fi
  # Ptyxis (terminal novo do GNOME, se existir)
  if command -v ptyxis >/dev/null 2>&1 || flatpak info app.devsuite.Ptyxis >/dev/null 2>&1; then
    mkdir -p "$HOME/.local/share/org.gnome.Ptyxis/palettes"
    cp "$T/terminal/Arasaka.palette" "$HOME/.local/share/org.gnome.Ptyxis/palettes/"
    ok "paleta 'Arasaka' disponivel no Ptyxis (Preferencias > Perfil > Paleta)"
  fi
}

gdm() {
  [ "$DO_GDM" -eq 1 ] || return 0
  step "Tela de login (GDM)"
  if ! command -v glib-compile-resources >/dev/null 2>&1 || ! command -v gresource >/dev/null 2>&1; then
    warn "glib-compile-resources/gresource ausentes; pulando a tela de login"; return 0
  fi
  local mode src out=/usr/share/gnome-shell/theme/Arasaka/gnome-shell-theme.gresource
  local def=/usr/share/gnome-shell/gnome-shell-theme.gresource
  if update-alternatives --query gdm-theme.gresource >/dev/null 2>&1; then
    mode=alt
    src=$(readlink -f /usr/share/gnome-shell/gdm-theme.gresource)
    if [ "$src" = "$out" ]; then
      src=$(sudo cat "$SYS_BK/gdm-alt-prev" 2>/dev/null || echo "$def")
    else
      echo "$src" | sudo tee "$SYS_BK/gdm-alt-prev" >/dev/null
    fi
  else
    mode=replace
    backup_sys "$def" gnome-shell-theme.gresource.orig
    src="$SYS_BK/gnome-shell-theme.gresource.orig"
  fi
  [ -f "$src" ] || { warn "gresource do GDM nao encontrado ($src)"; return 0; }

  local work r
  work=$(mktemp -d)
  sudo cp "$src" "$work/src.gresource"; sudo chown "$USER" "$work/src.gresource"
  {
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<gresources><gresource prefix="/">'
    for r in $(gresource list "$work/src.gresource"); do
      mkdir -p "$work/root$(dirname "$r")"
      gresource extract "$work/src.gresource" "$r" > "$work/root$r"
      echo "<file>${r#/}</file>"
    done
    echo '</gresource></gresources>'
  } > "$work/arasaka.gresource.xml"
  local css n=0
  for css in "$work"/root/org/gnome/shell/theme/*.css; do
    [ -f "$css" ] || continue
    case "$css" in *high-contrast*) continue ;; esac
    printf '\n/* ARASAKA */\n' >> "$css"
    cat "$T/shell/arasaka-shell.css" >> "$css"
    n=$((n + 1))
  done
  if [ "$n" -eq 0 ] || ! glib-compile-resources --sourcedir="$work/root" --target="$work/out.gresource" "$work/arasaka.gresource.xml"; then
    warn "falha ao gerar o tema do GDM"; rm -rf "$work"; return 0
  fi
  sudo mkdir -p "$(dirname "$out")"
  sudo install -m644 "$work/out.gresource" "$out"
  rm -rf "$work"
  if [ "$mode" = alt ]; then
    sudo update-alternatives --quiet --install /usr/share/gnome-shell/gdm-theme.gresource gdm-theme.gresource "$out" 200
    sudo update-alternatives --quiet --set gdm-theme.gresource "$out"
  else
    sudo install -m644 "$out" "$def"
  fi
  echo "$mode" | sudo tee "$SYS_BK/gdm-mode" >/dev/null
  ok "fundo e estilo da tela de login ($mode)"

  if [ -f /etc/dconf/profile/gdm ] && grep -q "system-db:gdm" /etc/dconf/profile/gdm; then
    sudo mkdir -p /etc/dconf/db/gdm.d
    {
      echo "[org/gnome/login-screen]"
      echo "logo='/usr/share/pixmaps/arasaka-gdm.png'"
      echo
      echo "[org/gnome/desktop/interface]"
      echo "cursor-theme='Arasaka-Cursors'"
      echo "icon-theme='Arasaka'"
      echo "color-scheme='prefer-dark'"
      [ "$HAVE_RAJ" -eq 1 ] && echo "font-name='Rajdhani SemiBold 12'"
      if [ "$DO_SND" -eq 1 ]; then
        echo
        echo "[org/gnome/desktop/sound]"
        echo "theme-name='Arasaka'"
      fi
    } | sudo tee /etc/dconf/db/gdm.d/95-arasaka >/dev/null
    sudo dconf update && ok "logo, cursor e fonte na tela de login"
  fi
}

grub() {
  [ "$DO_GRUB" -eq 1 ] || return 0
  step "GRUB (menu de boot)"
  command -v grub-mkfont >/dev/null || { warn "grub-mkfont ausente; pulando GRUB"; return 0; }
  local gdir=/boot/grub
  [ -d /boot/grub ] || { [ -d /boot/grub2 ] && gdir=/boot/grub2; }
  local dst="$gdir/themes/arasaka"
  sudo mkdir -p "$dst"
  sudo cp "$T"/grub/arasaka/*.png "$dst/"

  local dv=/usr/share/fonts/truetype/dejavu
  local f_item="$dv/DejaVuSans.ttf" f_bold="$dv/DejaVuSans-Bold.ttf" f_small="$dv/DejaVuSansMono.ttf" f_mono="$dv/DejaVuSansMono.ttf"
  [ -s "$FONT_DIR/Rajdhani-SemiBold.ttf" ] && f_item="$FONT_DIR/Rajdhani-SemiBold.ttf"
  [ -s "$FONT_DIR/Rajdhani-Bold.ttf" ] && f_bold="$FONT_DIR/Rajdhani-Bold.ttf"
  [ -s "$FONT_DIR/ShareTechMono-Regular.ttf" ] && f_small="$FONT_DIR/ShareTechMono-Regular.ttf"
  local tmp; tmp=$(mktemp -d)
  grub-mkfont -s 26 -o "$tmp/item.pf2"  "$f_item"  &&
  grub-mkfont -s 26 -o "$tmp/bold.pf2"  "$f_bold"  &&
  grub-mkfont -s 16 -o "$tmp/small.pf2" "$f_small" &&
  grub-mkfont -s 16 -o "$tmp/mono.pf2"  "$f_mono"  || { warn "grub-mkfont falhou"; rm -rf "$tmp"; return 0; }
  sed -e "s|@FONT_ITEM@|$(pf2_name "$tmp/item.pf2")|" \
      -e "s|@FONT_ITEM_BOLD@|$(pf2_name "$tmp/bold.pf2")|" \
      -e "s|@FONT_SMALL@|$(pf2_name "$tmp/small.pf2")|" \
      -e "s|@FONT_MONO@|$(pf2_name "$tmp/mono.pf2")|" \
      "$T/grub/arasaka/theme.txt.in" > "$tmp/theme.txt"
  sudo install -m644 "$tmp"/*.pf2 "$tmp/theme.txt" "$dst/"
  rm -rf "$tmp"

  local cfg=/etc/default/grub
  backup_sys "$cfg" grub.default
  set_kv "$cfg" GRUB_THEME "\"$dst/theme.txt\""
  if [ "$GRUB_SHOW" -eq 1 ]; then
    set_kv "$cfg" GRUB_TIMEOUT_STYLE menu
    local to; to=$(sudo sed -n -E 's/^GRUB_TIMEOUT=//p' "$cfg" | tr -d '"')
    { [ -z "$to" ] || [ "$to" = "0" ]; } && set_kv "$cfg" GRUB_TIMEOUT 5
  fi
  sudo sed -i -E 's|^(GRUB_TERMINAL=console)|#\1|' "$cfg"
  # garante "splash" para o Plymouth aparecer
  if [ "$DO_PLY" -eq 1 ] && ! sudo grep -qE '^GRUB_CMDLINE_LINUX_DEFAULT=.*splash' "$cfg"; then
    sudo sed -i -E 's|^GRUB_CMDLINE_LINUX_DEFAULT="([^"]*)"|GRUB_CMDLINE_LINUX_DEFAULT="\1 quiet splash"|' "$cfg"
  fi
  info "atualizando o GRUB..."
  if command -v update-grub >/dev/null; then sudo update-grub >/dev/null 2>&1
  else sudo grub-mkconfig -o "$gdir/grub.cfg" >/dev/null 2>&1; fi && ok "tema do GRUB ativo" || warn "update-grub falhou"
}

plymouth_theme() {
  [ "$DO_PLY" -eq 1 ] || return 0
  step "Plymouth (tela de carregamento)"
  local dst=/usr/share/plymouth/themes/arasaka
  [ -d /usr/share/plymouth/themes ] || { warn "Plymouth nao instalado"; return 0; }
  sudo rm -rf "$dst"
  sudo cp -r "$T/plymouth/arasaka" "$dst"
  sudo chmod -R a+rX "$dst"
  if update-alternatives --query default.plymouth >/dev/null 2>&1; then
    local prev
    prev=$(update-alternatives --query default.plymouth | sed -n 's/^Value: //p')
    [ -n "$prev" ] && [ "$prev" != "$dst/arasaka.plymouth" ] && echo "$prev" | sudo tee "$SYS_BK/plymouth-prev" >/dev/null
    sudo update-alternatives --quiet --install /usr/share/plymouth/themes/default.plymouth default.plymouth "$dst/arasaka.plymouth" 200
    sudo update-alternatives --quiet --set default.plymouth "$dst/arasaka.plymouth"
  elif command -v plymouth-set-default-theme >/dev/null; then
    plymouth-set-default-theme 2>/dev/null | sudo tee "$SYS_BK/plymouth-prev-name" >/dev/null
    sudo plymouth-set-default-theme arasaka
  else
    warn "nao achei como definir o tema padrao do Plymouth"; return 0
  fi
  info "recriando o initramfs (pode levar 1-2 minutos)..."
  sudo update-initramfs -u >/dev/null 2>&1 && ok "tela de carregamento Arasaka ativa" || warn "update-initramfs falhou"
}

# Extensão Arasaka FX (efeitos visuais) e o comando arasaka-fx; tudo na pasta do usuário, sem senha
fx() {
  [ "$DO_FX" -eq 1 ] || return 0
  step "Efeitos visuais (extensao Arasaka FX)"
  local uuid=arasaka-fx@arasaka.local cur dst="$HOME/.local/share/gnome-shell/extensions/arasaka-fx@arasaka.local"
  rm -rf "$dst"; mkdir -p "$(dirname "$dst")"
  cp -r "$T/extension/$uuid" "$dst"
  mkdir -p "$HOME/.local/bin" "$HOME/.config/arasaka"
  install -m755 "$T/bin/arasaka-fx" "$HOME/.local/bin/arasaka-fx"
  [ -f "$HOME/.config/arasaka/fx.json" ] || printf '{"windows": true, "overview": true, "background": true, "crt": true}\n' > "$HOME/.config/arasaka/fx.json"
  cur=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null)
  if [[ "$cur" != *"$uuid"* ]]; then
    if [[ "$cur" == "@as []" || "$cur" == "[]" || -z "$cur" ]]; then gsettings set org.gnome.shell enabled-extensions "['$uuid']"
    else gsettings set org.gnome.shell enabled-extensions "${cur%]}, '$uuid']"; fi
  fi
  gnome-extensions enable "$uuid" >/dev/null 2>&1 || true
  ok "Arasaka FX instalada (aparece no proximo login); comando: arasaka-fx"
}

finish() {
  printf '\n%s%s ■ INSTALACAO CONCLUIDA%s\n' "$R" "$B" "$N"
  printf '   %sEncerre a sessao e entre de novo (ou reinicie) para ver tudo:%s\n' "$W" "$N"
  printf '   %s· boot (GRUB + Plymouth) e tela de login aparecem no proximo reinicio%s\n' "$G" "$N"
  printf '   %s· o painel/menus do Shell precisam de novo login%s\n' "$G" "$N"
  printf '   %s· para desfazer: ./uninstall.sh%s\n\n' "$G" "$N"
}

banner
preflight
deps
fonts
wallpapers
gtk_theme
icons
cursors
sounds
apply_settings
terminal
gdm
grub
plymouth_theme
fx
finish
