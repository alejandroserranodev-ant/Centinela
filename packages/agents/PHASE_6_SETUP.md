# Masking and prompt hygiene

This page covers `centinela_agents/security.py`. The file keeps its historical name and sits
beside [`AGENTS.md`](./AGENTS.md) because the team keeps the file structure; `AGENTS.md` is the
level page and links here.

**No leaf, orchestrator or API path calls this module**; only its tests import it. A prompt
reaches the model unmasked and unchecked. Masking personal data is decided for `packages/tools`
([`../tools/AGENTS.md`](../tools/AGENTS.md)), and `apps/api` holds its own unwired masking
([`../../apps/api/AGENTS.md`](../../apps/api/AGENTS.md)).

## What it holds

- `SENSITIVE_PATTERNS` and `SECRET_PATTERNS`: regular expressions for emails, phones, capitalised
  names, identity numbers, card numbers, passwords, and OpenAI, Anthropic, GitHub and AWS keys.
- `centinela_agents/security.py:mask_data(text, placeholder_prefix)` replaces each sensitive match
  with a placeholder; `restore_data(masked_text, replacements)` puts the originals back.
- `centinela_agents/security.py:DataMasker(action_id)` keeps one placeholder per value for one
  action, so the same value masks the same way twice; `mask(text, data_type)` and
  `unmask(text)`.
- `centinela_agents/security.py:detect_secrets(text)` lists the secret patterns a text contains.
- `centinela_agents/security.py:check_prompt_injection(user_input, instructions)` lists phrases
  that try to override instructions, change role or break context.
- `centinela_agents/security.py:SecurePrompt(system_instruction)` builds a prompt in trust layers:
  instructions, policies, data, and untrusted content such as a rejection reason, each added by its
  own method, and `build()` returns the system and user prompts.

## Tests

`uv run pytest tests/test_security.py` checks the patterns.
