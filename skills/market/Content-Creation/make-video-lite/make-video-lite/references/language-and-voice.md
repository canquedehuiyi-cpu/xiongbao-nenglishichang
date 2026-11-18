# Language and voice — the video always follows the user

This is the differentiator of `make-video-lite`. A user asks in Vietnamese,
they get a Vietnamese video; asks in Chinese, a Chinese video. Skipping this
step is the #1 failure mode of this skill.

## L = the user's interaction language

Decide **L** from the user's own message, in this order:

1. **Explicit request** — user says "make it in English", "giọng tiếng Việt
   nha", etc. → that wins, even if it differs from the message language.
2. **Message language** — the dominant language of their latest message:
   script detection (CJK → Chinese; Hangul → Korean; kana → Japanese; Latin
   + Vietnamese diacritics → Vietnamese; Latin otherwise), plus any language
   name they wrote ("tiếng Việt", "中文", "Tiếng Anh").
3. **Locale hint** — if the hosting app passes a locale/user-Lang field
   (e.g. `lang: vi`, `Accept-Language`), use it to break ties.
4. **Fallback default** — English, and state the assumption to the user in
   one line so they can redirect at minimal cost.

Do NOT derive L from your own reply language, the system prompt, or the
app UI. If the message is mixed ("Happy birthday! Chúc mừng sinh nhật"),
the majority content wins as L; never silently switch languages mid-video.

## What carries L into the video

- **Dialogue / VO** — quoted verbatim in L with speaker voice attributes
  (emotion, tone, pace, timbre), per the wan-video-prompting universal rules.
  Numbers, prices, and brand compounds are spelled for pronunciation in L
  (e.g. Vietnamese numeral tone rules, Chinese character readings). Foreign
  brand names keep their Roman form.
- **Music cues** — describe the music in L-appropriate genre words: "nhạc
  sôi động kiểu TikTok", "喜庆的过年音乐", "upbeat pop". If the user's L
  maps to a tasteful genre default (Vietnamese → pop/EDM, Chinese → festive
  or inspirational), use it.
- **Burned-in text** — zero by default (garble risk); VO carries the
  message. If the user explicitly asks for text, request it only as clean
  unadorned type in L, and warn once that rendered text in Wan output is
  unreliable for Latin-script diacritics and CJK alike.
- **The prompt itself** — write the creative prompt in L (wan-video-prompting
  rule 8: the prompt's language tracks the creative content). Mixed
  Chinese/English prompts are fine; asset references stay "Image 1"/"Video 1".

## Reply in L, kept short

The end user sees your text too: reply in L, 1–3 sentences — what the video
shows, that its speech is in L, and the local file path/download. No
technical chatter. If L is ambiguous, note the language you chose in that
same short reply.

## Pre-submit check

- [ ] L identified and written down before composing the prompt
- [ ] Dialogue quoted verbatim in L, with voice attributes
- [ ] BGM described in L-appropriate terms (or explicit silence)
- [ ] No rendered text unless asked; pronunciation of numbers/brands handled
- [ ] Your chat reply will be in L