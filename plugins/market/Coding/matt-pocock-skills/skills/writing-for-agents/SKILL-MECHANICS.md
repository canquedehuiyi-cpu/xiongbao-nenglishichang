# Skill mechanics

The skill-specific branch of [`writing-for-agents`](SKILL.md): what changes when the document is a skill in Qoder (frontmatter, invocation, and router skills). Everything else about writing it is the universal reference in `SKILL.md`.

## Invocation

One mechanism, not two. Qoder has no `disable-model-invocation` flag: every skill is model-invoked, and every skill is also user-invoked by typing its name. Neither reach has an opt-out.

The `description` is the agent's only trigger surface and the skill's top-level context pointer, forced to stay loaded at all times: permanent context load in exchange for discoverability. In Qoder that trade is the cost of having a skill at all. There is no flag to strip the description from the agent's reach — only wording to shape it: trigger branches in the description get it fired autonomously; a plain one-line summary leaves the timing mostly to the human's name. (The pointer-writing rules in `SKILL.md` apply in full.)

Write the description bilingual: the full Chinese sentence, a space, then the full English sentence — no `/` separators. `descriptionZh` carries the Chinese alone.

A skill whose content is all reference is also one home for shared reference: any other skill can reach it by name, so reference needed by several skills lives in one place.

## Splitting by invocation

The invocation cut of splitting (the sequence cut lives in `SKILL.md`) narrows in Qoder: there is no separate user-invoked variant to split off. The only question left is whether a distinct leading word deserves its own always-loaded description — you pay context load for every new skill, so that independent reach has to be worth it.

## Router skills

When skills multiply past what you can remember, that piled-up cognitive load is cured by a **router skill**: one skill that names the others and when to reach for each, so the human has one skill to remember instead of many. A Qoder router can do more than hint: every skill is visible to the agent, so the router's instructions can name a skill for the agent to fire. One invocation can chain into the rest.
