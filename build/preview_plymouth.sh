#!/usr/bin/env bash
# Pré-visualiza o tema do Plymouth numa janela, sem reiniciar e sem senha.
# O plymouthd roda dentro de uma "bolha" (bwrap): a pasta do tema e a de renderizadores do sistema são
# trocadas pelas deste repositório + o renderizador X11 (baixado com apt download, sem instalar).
#
# Uso: build/preview_plymouth.sh <pasta de saída> [boot|shutdown] [segundos] [intervalo]
#   -> prints <pasta>/f-XXX.png a cada [intervalo] segundos (padrão 0.25) e o log em <pasta>/plymouthd.log
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$(realpath -m "${1:?pasta de saída}")"; MODE="${2:-boot}"; SECS="${3:-6}"; STEP="${4:-0.25}"
WORK="$OUT/.work"; rm -rf -- "$OUT"; mkdir -p "$WORK/rend" "$OUT"
cp /usr/lib/x86_64-linux-gnu/plymouth/renderers/*.so "$WORK/rend/" 2>/dev/null
if [ ! -f "$WORK/../x11.so" ]; then
  (cd "$WORK" && apt download plymouth-x11 >/dev/null 2>&1 && dpkg -x plymouth-x11_*.deb x11pkg) || { echo "não consegui baixar o plymouth-x11"; exit 1; }
fi
cp "$WORK"/x11pkg/usr/lib/x86_64-linux-gnu/plymouth/renderers/x11.so "$WORK/rend/"
rm -f "$WORK"/rend/drm.so "$WORK"/rend/frame-buffer.so   # só o X11: abre numa janela
export OUT MODE SECS STEP WORK
bwrap --dev-bind / / --unshare-user --uid 0 --gid 0 --unshare-net --unshare-ipc \
  --bind "$ROOT/theme/plymouth/arasaka" /usr/share/plymouth/themes/arasaka \
  --bind "$WORK/rend" /usr/lib/x86_64-linux-gnu/plymouth/renderers \
  --tmpfs /run/plymouth --tmpfs /var/lib/plymouth \
  bash -c '
    plymouthd --no-daemon --debug --debug-file="$OUT/plymouthd.log" --mode="$MODE" --pid-file=/run/plymouth/pid \
      --kernel-command-line="splash quiet plymouth.theme=arasaka" --no-boot-log &
    PD=$!
    for i in $(seq 1 40); do plymouth --ping 2>/dev/null && break; sleep 0.1; done
    plymouth show-splash
    t0=$(date +%s.%N); n=0
    while :; do
      now=$(date +%s.%N); el=$(echo "$now - $t0" | bc)
      [ "$(echo "$el > $SECS" | bc)" = 1 ] && break
      plymouth system-update --progress=$(echo "$el * 100 / $SECS" | bc) 2>/dev/null
      wid=$(xwininfo -root -tree | grep -i plymouth | head -1 | awk "{print \$1}")
      [ -n "$wid" ] && xwd -silent -id "$wid" -out "$OUT/f-$(printf %03d $n).xwd" && n=$((n+1))
      sleep "$STEP"
    done
    plymouth quit; sleep 0.3; kill $PD 2>/dev/null; wait $PD 2>/dev/null
    echo "quadros: $n"'
