#!/usr/bin/env bash
# Testa a extensão Arasaka FX num GNOME Shell sem tela, isolado da sessão (config/dados/cache/runtime próprios).
# Uso: build/test_fx_headless.sh <pasta de saída>   -> prints em <pasta>/out e o log do shell em <pasta>/shell.log
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; T="$(realpath -m "${1:?pasta}")"
rm -rf -- "$T"; mkdir -p "$T"/{config,data/gnome-shell/extensions,cache,out}
# o socket do Wayland tem limite de 108 caracteres no caminho: pasta de execução curta, apagada no fim
RUN="$(mktemp -d "/run/user/$(id -u)/afx.XXXXXX")"; # no fim: desmonta o FUSE do portal de documentos (RUN/doc) e apaga a pasta
trap 'sleep 1; fusermount3 -u "$RUN/doc" 2>/dev/null || fusermount -u "$RUN/doc" 2>/dev/null; rm -rf -- "$RUN"' EXIT
cp -r "$ROOT/theme/extension/arasaka-fx@arasaka.local" "$T/data/gnome-shell/extensions/"
# tema do shell com o CSS do repositório (o user-theme procura primeiro em XDG_DATA_HOME/themes)
SH="$T/data/themes/Arasaka/gnome-shell"; mkdir -p "$SH"
cp -r /usr/share/themes/Arasaka/gnome-shell/. "$SH/"
printf '@import url("base.css");\n' > "$SH/gnome-shell.css"; cat "$ROOT/theme/shell/arasaka-shell.css" >> "$SH/gnome-shell.css"
cp "$ROOT/theme/shell/assets/"* "$SH/"
export XDG_CONFIG_HOME="$T/config" XDG_DATA_HOME="$T/data" XDG_CACHE_HOME="$T/cache" XDG_RUNTIME_DIR="$RUN" ARASAKA_FX_SELFTEST="$T/out"
unset WAYLAND_DISPLAY DISPLAY DBUS_SESSION_BUS_ADDRESS
dbus-run-session -- bash -c '
  gsettings set org.gnome.shell disable-user-extensions false
  gsettings set org.gnome.shell enabled-extensions "[\"user-theme@gnome-shell-extensions.gcampax.github.com\", \"zorin-taskbar@zorinos.com\", \"zorin-menu@zorinos.com\", \"arasaka-fx@arasaka.local\"]"
  gsettings set org.gnome.shell.extensions.user-theme name "Arasaka"
  gsettings set org.gnome.desktop.interface color-scheme prefer-dark
  gsettings set org.gnome.desktop.background picture-uri "file:///usr/share/backgrounds/arasaka/arasaka-core.png"
  gsettings set org.gnome.desktop.background picture-uri-dark "file:///usr/share/backgrounds/arasaka/arasaka-core.png"
  timeout 40 gnome-shell --headless --virtual-monitor 1920x1080 > "'"$T"'/shell.log" 2>&1
  true'
ls "$T/out"; cat "$T/out/log.txt" 2>/dev/null
grep -iE "arasaka|JS ERROR|error.*extension|GLSL|shader" "$T/shell.log" | head -20
