# Hats for Claude Code: zsh integration (macOS default shell, also Linux).
# All logic is in hat.py; this file only hooks it into the prompt and the `claude` command.

HAT_HOME=${HAT_HOME:-$HOME/.config/hats}
# The installer records which Python to use; if that one is gone, use any.
[[ -n ${HAT_PYTHON:-} && -x ${HAT_PYTHON:-} ]] || HAT_PYTHON=${commands[python3]:-$commands[python]}

hat__core() { "$HAT_PYTHON" "$HAT_HOME/hat.py" "$@" }
hat__ready() { [[ -n $HAT_PYTHON && -f $HAT_HOME/hat.py ]] }

# `claude` starts on the account shown in the prompt. If Hats has been removed,
# it is the normal claude again.
claude() {
  if hat__ready; then hat__core claude "$@"; else command claude "$@"; fi
}

hat() {
  case ${1:-} in
    (''|pick|use|auto)
      # These change this terminal's environment: hat.py prints the shell code to run.
      local code
      code=$(hat__core --shell zsh --eval "$@") || return
      eval "$code"
      ;;
    (*) hat__core "$@" ;;
  esac
}

hat__precmd() {
  local out title
  HAT__SEG=
  hat__ready || return 0
  out=$(hat__core --shell zsh prompt 2> /dev/null)
  HAT__SEG=${out%%$'\x1f'*}
  title=${out#*$'\x1f'}
  [[ $out == *$'\x1f'* ]] && print -rn -- $'\e]0;'"$title"$'\a'
  # Themes (oh-my-zsh, powerlevel10k...) may rebuild PROMPT; put the marker back.
  [[ $PROMPT == *'${HAT__SEG}'* ]] || PROMPT='${HAT__SEG}'"$PROMPT"
}

_hat() {
  if (( CURRENT == 2 )); then
    compadd pick status use auto add remove login map unmap default style run exec code doctor update export import edit which version help
  elif (( CURRENT == 3 )); then
    case $words[2] in
      (style) compadd clean badge minimal ;;
      (use|remove|map|default|login|run|exec|code) compadd ${(f)"$(hat__core names 2> /dev/null)"} ;;
    esac
  fi
}

if [[ -o interactive ]]; then
  export HAT_HOOK=zsh  # lets `hat doctor` see that this terminal is hooked
  # Needed to show the marker; most zsh themes turn it on anyway.
  setopt PROMPT_SUBST
  autoload -Uz add-zsh-hook
  add-zsh-hook precmd hat__precmd
  (( $+functions[compdef] )) && compdef _hat hat
  # F2 opens the account menu.
  hat__menu_widget() { BUFFER=hat; zle accept-line }
  zle -N hat__menu_widget
  bindkey '^[OQ' hat__menu_widget
  bindkey '^[[12~' hat__menu_widget
fi
