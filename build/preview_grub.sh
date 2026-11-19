#!/usr/bin/env bash
# Pré-visualiza o tema do GRUB numa máquina virtual (QEMU + OVMF), sem reiniciar e sem senha.
# Monta um GRUB EFI com o tema, as fontes e o 09_arasaka; a entrada faz o mesmo que as do Linux
# (load_video) e depois espera, para dar tempo de capturar a caixa do terminal.
# Uso: build/preview_grub.sh <pasta de saída>   -> <pasta>/1-menu.png e <pasta>/2-boot.png
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; T="$ROOT/theme"
OUT="$(realpath -m "${1:?pasta de saída}")"; rm -rf -- "$OUT"; mkdir -p "$OUT"
W="$OUT/.work"; TH="$W/theme"; mkdir -p "$TH" "$W/esp/EFI/BOOT"
cp "$T"/grub/arasaka/*.png "$TH/"

# fontes como o install.sh faz (Rajdhani / Share Tech Mono se estiverem instaladas)
FD=/usr/local/share/fonts/arasaka dv=/usr/share/fonts/truetype/dejavu
fi="$dv/DejaVuSans.ttf"; fb="$dv/DejaVuSans-Bold.ttf"; fs="$dv/DejaVuSansMono.ttf"; fm="$dv/DejaVuSansMono.ttf"
[ -s "$FD/Rajdhani-SemiBold.ttf" ] && fi="$FD/Rajdhani-SemiBold.ttf"
[ -s "$FD/Rajdhani-Bold.ttf" ] && fb="$FD/Rajdhani-Bold.ttf"
[ -s "$FD/ShareTechMono-Regular.ttf" ] && fs="$FD/ShareTechMono-Regular.ttf"
grub-mkfont -s 26 -o "$TH/item.pf2" "$fi"; grub-mkfont -s 26 -o "$TH/bold.pf2" "$fb"
grub-mkfont -s 16 -o "$TH/small.pf2" "$fs"; grub-mkfont -s 16 -o "$TH/mono.pf2" "$fm"
name() { python3 -I -c 'import struct,sys;d=open(sys.argv[1],"rb").read();i=d.find(b"NAME");n=struct.unpack(">I",d[i+4:i+8])[0];print(d[i+8:i+8+n].rstrip(b"\0").decode())' "$1"; }
sed -e "s|@FONT_ITEM@|$(name "$TH/item.pf2")|" -e "s|@FONT_ITEM_BOLD@|$(name "$TH/bold.pf2")|" \
    -e "s|@FONT_SMALL@|$(name "$TH/small.pf2")|" -e "s|@FONT_MONO@|$(name "$TH/mono.pf2")|" \
    "$T/grub/arasaka/theme.txt.in" > "$TH/theme.txt"

P='(memdisk)/boot/grub/themes/arasaka'
{
  cat <<EOF
insmod all_video
insmod gfxterm
insmod png
set gfxmode=1920x1080,auto
for f in $P/*.pf2; do loadfont \$f; done
terminal_output gfxterm
set theme=$P/theme.txt
set timeout_style=menu
set timeout=7
set default=0
EOF
  sh "$T/grub/arasaka/09_arasaka"
  cat <<'EOF'
menuentry 'Arasaka OS' {
	load_video
	set gfxpayload=keep
	sleep 30
}
menuentry 'Advanced options for Arasaka OS' { true; }
menuentry 'Memory test (memtest86+x64.efi)' { true; }
menuentry 'UEFI Firmware Settings' { fwsetup; }
EOF
} > "$W/grub.cfg"

grub-mkstandalone -O x86_64-efi -o "$W/esp/EFI/BOOT/BOOTX64.EFI" \
  "boot/grub/grub.cfg=$W/grub.cfg" "boot/grub/themes/arasaka=$TH" >/dev/null

# socket do monitor numa pasta curta (limite de 108 caracteres no caminho)
SD="$(mktemp -d "/run/user/$(id -u)/agrub.XXXXXX")"; SOCK="$SD/mon"; trap 'rm -rf -- "$SD"' EXIT
qemu-system-x86_64 -machine q35 -m 512 -bios /usr/share/ovmf/OVMF.fd -vga std -display none \
  -drive "file=fat:rw:$W/esp,format=raw" -monitor "unix:$SOCK,server,nowait" -no-reboot &
QP=$!
shot() { sleep "$1"; echo "screendump $W/$2.ppm" | socat - "UNIX-CONNECT:$SOCK" >/dev/null; sleep 0.5
         python3 -I -c 'import sys;from PIL import Image;Image.open(sys.argv[1]).save(sys.argv[2])' "$W/$2.ppm" "$OUT/$2.png"; }
shot 5 1-menu     # menu (contagem regressiva de 7 s)
shot 7 2-boot     # entrada escolhida: caixa do terminal com o painel
kill $QP 2>/dev/null; wait $QP 2>/dev/null || true
ls "$OUT"
