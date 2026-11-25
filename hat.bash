# Hats for Claude Code: bash integration (bash 3.2+, so it also runs on macOS).
# All logic is in hat.py; this file only hooks it into the prompt and the `claude` command.

HAT_HOME=${HAT_HOME:-$HOME/.config/hats}
# The installer records which Python to use; if that one is gone, use any.
command -v "${HAT_PYTHON:-}" > /dev/null 2>&1 || HAT_PYTHON=$(command -v python3 || command -v python)

hat__core() { "$HAT_PYTHON" "$HAT_HOME/hat.py" "$@"; }
hat__ready() { [ -n "$HAT_PYTHON" ] && [ -f "$HAT_HOME/hat.py" ]; }

# `claude` starts on the account shown in the prompt. If Hats has been removed,
# it is the normal claude again.
claude() {
  if hat__ready; then hat__core claude "$@"; else command claude "$@"; fi
}

hat() {
  case ${1:-} in
    "" | pick | use | auto)
      # These change this terminal's environment: hat.py prints the shell code to run.
      local code
      code=$(hat__core --shell bash --eval "$@") || return
      eval "$code"
      ;;
    *) hat__core "$@" ;;
  esac
}

hat__prompt() {
  local rc=$?
  HAT__SEG=
  hat__ready && HAT__SEG=$(hat__core --shell bash prompt 2> /dev/null)
  HAT__SEG=${HAT__SEG%%$'\x1f'*}
  return $rc
}

hat__complete() {
  local cur=${COMP_WORDS[COMP_CWORD]}
  if ((COMP_CWORD == 1)); then
    COMPREPLY=($(compgen -W "pick status use auto add remove login map unmap default style run exec code doctor update export import edit which version help" -- "$cur"))
  elif ((COMP_CWORD == 2)) && [[ ${COMP_WORDS[1]} == style ]]; then
    COMPREPLY=($(compgen -W "clean badge minimal" -- "$cur"))
  elif ((COMP_CWORD == 2)) && [[ ${COMP_WORDS[1]} =~ ^(use|remove|map|default|login|run|exec|code)$ ]]; then
    COMPREPLY=($(compgen -W "$(hat__core names 2> /dev/null)" -- "$cur"))
  fi
}

if [[ $- == *i* ]]; then
  export HAT_HOOK=bash  # lets `hat doctor` see that this terminal is hooked
  complete -o default -F hat__complete hat
  # The marker (and the tab title) go at the start of the prompt. The stock
  # "user@host: dir" title that many distributions put at the start of PS1 is
  # dropped, since it would overwrite ours; nothing else in PS1 is changed.
  [[ $PROMPT_COMMAND == *hat__prompt* ]] || PROMPT_COMMAND="hat__prompt${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
  PS1=${PS1#'\[\e]0;'*'\a\]'}
  [[ $PS1 == *HAT__SEG* ]] || PS1='${HAT__SEG}'"$PS1"
  # F2 opens the account menu.
  bind '"\eOQ": "\C-a\C-khat\C-m"' 2> /dev/null
  bind '"\e[12~": "\C-a\C-khat\C-m"' 2> /dev/null
fi
