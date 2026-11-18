# ============================================================
#  ARASAKA // bash: prompt + banner de acesso
#  Carregado pelo ~/.bashrc (linha adicionada pelo install.sh).
#  Para desligar o banner: export ARASAKA_BANNER=0 antes desta linha.
# ============================================================

case $- in *i*) ;; *) return ;; esac

__ara_r=$'\e[38;2;227;18;31m'
__ara_rh=$'\e[38;2;255;59;71m'
__ara_w=$'\e[38;2;236;236;240m'
__ara_g=$'\e[38;2;110;110;120m'
__ara_b=$'\e[1m'
__ara_n=$'\e[0m'

arasaka_banner() {
  local logo_file="/usr/share/arasaka/terminal/logo.txt"
  [ -r "$logo_file" ] || return 0
  local -a logo info
  mapfile -t logo < "$logo_file"

  local os kernel up mem shell_name host
  os=$(. /etc/os-release 2>/dev/null && printf '%s' "$PRETTY_NAME")
  kernel=$(uname -r)
  up=$(uptime -p 2>/dev/null | sed 's/^up //')
  mem=$(free -h 2>/dev/null | awk '/^(Mem|Mem.):/ {print $3 " / " $2; exit}')
  shell_name=${SHELL##*/}
  host=$(hostname 2>/dev/null || cat /etc/hostname)

  info=(
    ""
    ""
    "${__ara_r}${__ara_b}A R A S A K A${__ara_n}  ${__ara_g}// 荒坂 CORPORATION${__ara_n}"
    "${__ara_g}──────────────────────────────────────${__ara_n}"
    "${__ara_r}OPERATOR  ${__ara_w}${USER}"
    "${__ara_r}NODE      ${__ara_w}${host}"
    "${__ara_r}SYSTEM    ${__ara_w}${os}"
    "${__ara_r}KERNEL    ${__ara_w}${kernel}"
    "${__ara_r}UPTIME    ${__ara_w}${up}"
    "${__ara_r}MEMORY    ${__ara_w}${mem}"
    "${__ara_r}SHELL     ${__ara_w}${shell_name}"
    "${__ara_g}──────────────────────────────────────${__ara_n}"
    "${__ara_g}CLEARANCE ${__ara_r}■ ${__ara_w}LEVEL 05 ${__ara_g}· ${__ara_r}■ ${__ara_w}ACCESS GRANTED"
    "${__ara_g}NETWATCH  ${__ara_w}LINK ESTABLISHED"
  )

  local cols=${COLUMNS:-$(tput cols 2>/dev/null || echo 80)}
  local i n=${#logo[@]}
  [ ${#info[@]} -gt "$n" ] && n=${#info[@]}
  printf '\n'
  for ((i = 0; i < n; i++)); do
    if [ "$cols" -ge 92 ]; then
      printf '  %s%s%s   %s%s\n' "$__ara_r" "${logo[i]:-$(printf '%*s' "${#logo[0]}" '')}" "$__ara_n" "${info[i]}" "$__ara_n"
    elif [ "$i" -lt "${#logo[@]}" ]; then
      printf '  %s%s%s\n' "$__ara_r" "${logo[i]}" "$__ara_n"
    fi
  done
  if [ "$cols" -lt 92 ]; then
    for ((i = 2; i < ${#info[@]}; i++)); do printf '  %s%s\n' "${info[i]}" "$__ara_n"; done
  fi
  printf '\n'
}

# versoes "invisiveis" (\001..\002) para usar dentro de $(...) no prompt
__ara_pr=$'\001'"${__ara_r}"$'\002'
__ara_prh=$'\001'"${__ara_rh}"$'\002'

__ara_git() {
  local b
  b=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null) || return 0
  printf '%s─[%s%s%s]' "$__ara_pr" "$__ara_prh" "$b" "$__ara_pr"
}

__ara_status() {
  local s=$?
  if [ "$s" -ne 0 ]; then __ARA_ST="${__ara_pr}─[${__ara_prh}✖ ${s}${__ara_pr}]"; else __ARA_ST=""; fi
}

case ";${PROMPT_COMMAND:-};" in
  *";__ara_status;"*) ;;
  *) PROMPT_COMMAND="__ara_status${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
esac

PS1='\[${__ara_r}\]┌─[\[${__ara_b}${__ara_w}\]\u\[${__ara_n}${__ara_r}\]@\[${__ara_w}\]\h\[${__ara_r}\]]─[\[${__ara_w}\]\w\[${__ara_r}\]]$(__ara_git)${__ARA_ST}\n\[${__ara_r}\]└──▶\[${__ara_n}\] '

alias arasaka='arasaka_banner'

if [ "${ARASAKA_BANNER:-1}" = "1" ] && [ -z "${ARASAKA_BANNER_SHOWN:-}" ]; then
  export ARASAKA_BANNER_SHOWN=1
  arasaka_banner
fi
