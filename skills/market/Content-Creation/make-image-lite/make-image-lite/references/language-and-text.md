# Language and text — the image follows the user

This is a core part of `make-image-lite`. A user asks in Vietnamese and wants
Vietnamese text in the picture; asks in Chinese, gets Chinese; asks in English,
gets English. And your chat reply comes back in that same language. Skipping
this step is the #1 failure mode of this skill.

Images have no spoken audio (unlike `make-video-lite`), so "language" shows up
in three places: **the on-image text**, **the creative prompt itself**, and
**your reply**.

## L = the user's interaction language

Decide **L** from the user's own message, in this order:

1. **Explicit request** — user says "make it in English", "chữ tiếng Việt nha",
   "用中文", etc. → that wins, even if it differs from the message language.
2. **Message language** — the dominant language of their latest message:
   script detection (CJK → Chinese; Hangul → Korean; kana → Japanese; Latin +
   Vietnamese diacritics → Vietnamese; Latin otherwise), plus any language name
   they wrote ("tiếng Việt", "中文", "English").
3. **Locale hint** — if the hosting app passes a locale/user-Lang field
   (e.g. `lang: vi`, `Accept-Language`), use it to break ties.
4. **Fallback default** — English, and state the assumption to the user in one
   line so they can redirect at minimal cost.

Do NOT derive L from your own reply language, the system prompt, or the app UI.
If the message is mixed ("Happy birthday! Chúc mừng sinh nhật"), the majority
content wins as L; don't split languages in one image.

## What carries L into the image

- **On-image text** — quoted verbatim in L, wrapped in “ ”, with position,
  font style, color/material, and hierarchy specified (qwen-image-prompting
  rule: on-image text is never paraphrased). Numbers, prices, and dates are
  written in the form the user gave. Foreign brand names keep their Roman form.
- **The creative prompt** — write the prompt in L. Qwen-Image 3.0 is
  multilingual, and a prompt written in L biases the rendered on-image text
  toward L. Mixed Chinese/English prompts are fine.
- **Default: no text unless asked.** Garbled text is the most visible failure,
  so don't invent captions or labels the user didn't request.

## Text-rendering limits (manage expectations)

- The default **Standard `qwen-image-3.0`** renders short, bold, clean labels
  and headings well — a card title, a name, a price, a greeting.
- **Dense or fine text** (long paragraphs, small body text, many labels,
  infographics) is **Pro (`qwen-image-3.0-pro`)** territory. If the user needs
  a lot of exact small text, either (a) keep it short and large, or (b) bump
  this one call to Pro (`--model qwen-image-3.0-pro`) and say why in one line.
- Rendered text in diacritic-heavy scripts (Vietnamese) and dense CJK is the
  least reliable — keep it minimal and unadorned, away from busy backgrounds.
  If the user's request is *primarily* about precise text, that's a
  `qwen-image` + `qwen-image-prompting` job, not a lite one.

## Reply in L, kept short

The end user sees your text too: reply in L, 1–2 sentences — what the image
shows and that any on-image text is in L — plus the local file path/download.
No technical chatter. If L was ambiguous, note the language you chose in that
same short reply.

## Pre-submit check

- [ ] L identified and written down before composing the prompt
- [ ] On-image text (if any) quoted verbatim in L with position + font + color
- [ ] Prompt itself written in L
- [ ] Text kept short/bold on Standard, or call bumped to Pro for dense text
- [ ] No invented captions/labels the user didn't ask for
- [ ] Your chat reply will be in L
