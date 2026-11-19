#!/usr/bin/env bash
# ============================================================
#   ARASAKA // Desinstalador
#   Restaura tudo a partir dos backups feitos pelo install.sh.
#   Uso: ./uninstall.sh   (NAO rode com sudo)
# ============================================================

set -uo pipefail

R=$'\e[38;2;227;18;31m'; W=$'\e[38;2;236;236;240m'; G=$'\e[38;2;120;120;130m'; B=$'\e[1m'; N=$'\e[0m'
ok()   { printf '   %s■%s %s\n' "$R" "$N" "$*"; }
warn() { printf '   %s!! %s%s\n' "$R" "$*" "$N"; }

SYS_BK=/var/lib/arasaka-theme
USR_BK="$HOME/.config/arasaka"
GS_BK="$USR_BK/gsettings.bak"

[ "$EUID" -eq 0 ] && { echo "Rode como seu usuario normal (sem sudo)."; exit 1; }
printf '%s%sARASAKA // DESINSTALAR TEMA%s\n' "$R" "$B" "$N"
printf '   %sIsso remove o tema e restaura suas configuracoes anteriores. Continuar? [s/N] %s' "$W" "$N"
read -r r
case "$r" in s|S|y|Y|sim|SIM) ;; *) echo "Cancelado."; exit 0 ;; esac
sudo -v || exit 1

# ---------------------------------------------------------------- gsettings
if [ -f "$GS_BK" ]; then
  while read -r schema key val; do
    [ -n "$schema" ] || continue
    gsettings set "$schema" "$key" "$val" 2>/dev/null || warn "nao restaurou $schema $key"
  done < "$GS_BK"
  ok "configuracoes do usuario restauradas"
fi

# ---------------------------------------------------------------- terminal
if command -v dconf >/dev/null 2>&1; then
  P=/org/gnome/terminal/legacy/profiles: U=7a5a5a20-2077-4a7a-a5a5-a5a5a5a52077
  list=$(dconf read "$P/list")
  if [[ "$list" == *"$U"* ]]; then
    list=${list//", '$U'"/}; list=${list//"'$U', "/}; list=${list//"'$U'"/}
    dconf write "$P/list" "$list"
  fi
  dconf reset -f "$P/:$U/"
  prev=$(cat "$USR_BK/terminal-default.bak" 2>/dev/null)
  if [ -n "$prev" ]; then dconf write "$P/default" "$prev"; else dconf reset "$P/default"; fi
  ok "perfil do GNOME Terminal removido"
fi
if [ -f "$HOME/.bashrc" ]; then
  sed -i '/# >>> arasaka-theme >>>/,/# <<< arasaka-theme <<</d' "$HOME/.bashrc"
  ok "bloco do ~/.bashrc removido"
fi
rm -f "$HOME/.local/share/org.gnome.Ptyxis/palettes/Arasaka.palette"
rm -f "$HOME/.config/autostart/arasaka-login-sound.desktop"

# ---------------------------------------------------------------- Arasaka FX
fxid=arasaka-fx@arasaka.local
gnome-extensions disable "$fxid" >/dev/null 2>&1 || true
cur=$(gsettings get org.gnome.shell enabled-extensions 2>/dev/null)
if [[ "$cur" == *"$fxid"* ]]; then
  gsettings set org.gnome.shell enabled-extensions "$(printf '%s' "$cur" | sed "s/, *'$fxid'//; s/'$fxid', *//; s/'$fxid'//")"
fi
rm -rf "$HOME/.local/share/gnome-shell/extensions/$fxid" "$HOME/.local/bin/arasaka-fx" "$HOME/.config/arasaka/fx.json"
ok "efeitos Arasaka FX removidos"

# ---------------------------------------------------------------- libadwaita
u4="$HOME/.config/gtk-4.0/gtk.css"
rm -f "$u4"
[ -f "$USR_BK/gtk-4.0.css.bak" ] && cp -a "$USR_BK/gtk-4.0.css.bak" "$u4"
command -v flatpak >/dev/null 2>&1 && flatpak override --user --nofilesystem=xdg-config/gtk-4.0 >/dev/null 2>&1
ok "estilo libadwaita restaurado"

# ---------------------------------------------------------------- GDM
mode=$(cat "$SYS_BK/gdm-mode" 2>/dev/null)
out=/usr/share/gnome-shell/theme/Arasaka/gnome-shell-theme.gresource
if [ "$mode" = alt ]; then
  sudo update-alternatives --quiet --remove gdm-theme.gresource "$out" 2>/dev/null
  prev=$(cat "$SYS_BK/gdm-alt-prev" 2>/dev/null)
  [ -n "$prev" ] && [ -f "$prev" ] && sudo update-alternatives --quiet --set gdm-theme.gresource "$prev" 2>/dev/null
  ok "tela de login restaurada"
elif [ "$mode" = replace ] && [ -f "$SYS_BK/gnome-shell-theme.gresource.orig" ]; then
  sudo install -m644 "$SYS_BK/gnome-shell-theme.gresource.orig" /usr/share/gnome-shell/gnome-shell-theme.gresource
  ok "tela de login restaurada"
fi
sudo rm -rf /usr/share/gnome-shell/theme/Arasaka
if [ -f /etc/dconf/db/gdm.d/95-arasaka ]; then
  sudo rm -f /etc/dconf/db/gdm.d/95-arasaka
  sudo dconf update
fi

# ---------------------------------------------------------------- GRUB
if [ -f "$SYS_BK/grub.default" ]; then
  sudo install -m644 "$SYS_BK/grub.default" /etc/default/grub
  sudo rm -rf /boot/grub/themes/arasaka /boot/grub2/themes/arasaka
  if command -v update-grub >/dev/null; then sudo update-grub >/dev/null 2>&1; fi
  ok "GRUB restaurado"
fi

# ---------------------------------------------------------------- Plymouth
ply=/usr/share/plymouth/themes/arasaka/arasaka.plymouth
if update-alternatives --query default.plymouth 2>/dev/null | grep -q "$ply"; then
  sudo update-alternatives --quiet --remove default.plymouth "$ply"
  prev=$(cat "$SYS_BK/plymouth-prev" 2>/dev/null)
  [ -n "$prev" ] && [ -f "$prev" ] && sudo update-alternatives --quiet --set default.plymouth "$prev"
elif [ -f "$SYS_BK/plymouth-prev-name" ] && command -v plymouth-set-default-theme >/dev/null; then
  sudo plymouth-set-default-theme "$(cat "$SYS_BK/plymouth-prev-name")"
fi
if [ -d /usr/share/plymouth/themes/arasaka ]; then
  sudo rm -rf /usr/share/plymouth/themes/arasaka
  echo "   ${G}recriando o initramfs...${N}"
  sudo update-initramfs -u >/dev/null 2>&1
  ok "tela de carregamento restaurada"
fi

# ---------------------------------------------------------------- arquivos
sudo rm -rf /usr/share/themes/Arasaka /usr/share/icons/Arasaka /usr/share/icons/Arasaka-Cursors \
            /usr/share/sounds/Arasaka /usr/share/backgrounds/arasaka /usr/share/arasaka \
            /usr/local/share/fonts/arasaka
sudo rm -f /usr/share/gnome-background-properties/arasaka.xml /usr/share/pixmaps/arasaka-gdm.png \
           /usr/share/pixmaps/arasaka.png /usr/share/pixmaps/arasaka.svg
sudo fc-cache -f >/dev/null 2>&1
sudo rm -rf "$SYS_BK"
rm -rf "$USR_BK"
ok "arquivos do tema removidos"

printf '\n%s%s ■ TEMA REMOVIDO.%s %sEncerre a sessao e entre de novo.%s\n\n' "$R" "$B" "$N" "$W" "$N"
