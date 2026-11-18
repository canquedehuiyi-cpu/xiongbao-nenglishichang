# Vietnamese Office Document Conventions (NĐ 30/2020/NĐ-CP)

Reference for `assets/templates/` and for composing any Vietnamese administrative
document (`văn bản hành chính`). The bundled `reference-vn.docx` already encodes the
typography — this file covers the *structure* the model must reproduce in markdown.

## Typography (already baked into reference-vn.docx)

| Property | Value |
|---|---|
| Font | Times New Roman (Unicode, full Vietnamese diacritics) |
| Body size | 13 pt (NĐ30 allows 13–14) |
| Page | A4, portrait |
| Margins | left 30 mm, right 15 mm, top/bottom 20 mm |
| Alignment | justified (`both`) |
| Line spacing | 1.3, no space before/after paragraphs |

Do not override these per document. If a user asks for a different look, change the
reference doc via `scripts/make-reference.py`, not the markdown.

## Mandatory header block

Every `văn bản hành chính` opens with these five elements, in this order:

1. **Tên cơ quan chủ quản** and **tên tổ chức** — top-left, uppercase, bold.
   Under the organization name, a short rule line (`----------`).
2. **Quốc hiệu** — `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM`, centred, bold, uppercase.
3. **Tiêu ngữ** — `Độc lập - Tự do - Hạnh phúc`, centred, bold, lowercase after the
   first letter of each phrase, with a hyphen (not an en-dash) between phrases.
   Underlined in Word by the user; leave as plain text.
4. **Số và ký hiệu hiệu lực** — `Số: 12/NQ-UBND`, left column, below the org name.
5. **Địa danh và ngày tháng** — `Hà Nội, ngày 05 tháng 9 năm 2026`, right column,
   italic in Word. Use lowercase `ngày`/`tháng`/`năm`, no leading zeros on the day.

In markdown, produce 2–4 with `custom-style="Title"` / `custom-style="Subtitle"` divs
(both are centred and bold in the reference doc); 1 and 5 as plain paragraphs.

## Tên loại văn bản và trích yếu

- Tên loại văn bản: uppercase, bold, centred — `NGHỊ QUYẾT`, `BÁO CÁO`, `TỜ TRÌNH`.
- Trích yếu: below the type, bold, sentence case or uppercase, centred.
- For công văn, `V/v <nội dung>` sits under the số, left-aligned, lowercase `V/v`.

## Body structure by document type

**Nghị quyết / Quyết định** — `Căn cứ …` clauses (each its own `##` heading, ending in
`;`, the last one ending in `.`), then `Điều 1.`, `Điều 2.`, `Điều 3.` Each Điều states
who does what. Final Điều covers hiệu lực thi hành and ends `…./.`, followed by `Nơi nhận:`.

**Báo cáo** — roman-numeral top sections: `I. Tình hình và kết quả`, `II. Hạn chế, nguyên
nhân`, `III. Phương hướng, nhiệm vụ`, `IV. Kiến nghị, đề xuất`. Numbers, not prose, carry
section II.

**Tờ trình** — `Kính gửi:` line first, then `I. Sự cần thiết`, `II. Căn cứ pháp lý`,
`III. Nội dung đề xuất` (with a kinh phí table), `IV. Kiến nghị`. Ends with
`Tài liệu gửi kèm:`.

**Công văn** — `Kính gửi:` then 2–4 short paragraphs of purpose, request, and closing.
No numbered sections.

## Signature block

Position and wording are fixed by the signer's role:

| Signer | Wording |
|---|---|
| Tập thể lãnh đạo, thay mặt | `TM. {{CHỨC DANH TẬP THỂ}}` + `PHÓ {{CHỨC DANH}}` |
| Cá nhân giữ chức vụ | `KT. {{CHỨC DANH}}` + `PHÓ {{CHỨC DANH}}` (cấp phó ký thay) |
| Được ủy quyền | `TU. {{CHỨC DANH}}` or `TL. {{CHỨC DANH}}` |

Under the function line: `(Ký, ghi rõ họ tên, đóng dấu)` — `đóng dấu` only where a seal
is required. Signer's name is bold.

`Nơi nhận:` sits bottom-left, italic, listing recipients then `- Lưu: VT.` (or
`- Lưu: VT, <bộ phận>.`).

## Language rules

- Write the document entirely in the language the user wrote in. Do not translate
  section headings into English, and do not add an English summary.
- Use ``, `’` correctly for Vietnamese: prefer plain ASCII hyphens and straight quotes
  in numbers (`1.200.000.000 đ`), Vietnamese thousands separator is `.`, decimal is `,`.
- Currency: `đ` or `VNĐ` after the number, with a space.
- Formal register: `Kính gửi`, `Đề nghị`, `Căn cứ`, `Trên đây là`. Avoid conversational
  phrasing in administrative documents.
- Date format in prose: `ngày 05 tháng 9 năm 2026`. In tables: `05/09/2026`.

## What to ask the user for, if missing

Only these are worth blocking on, because inventing them produces a wrong document:
`tên cơ quan ban hành`, `số hiệu văn bản`, `chức vụ và họ tên người ký`, `đơn vị nhận`.
Everything else: fill with a plausible value and flag it, rather than stalling a chat turn.
