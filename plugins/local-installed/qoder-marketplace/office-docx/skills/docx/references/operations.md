# Qoder Word standalone tool contract

- The authoritative tool set is this server's `tools/list`. If a desktop tool is absent, do not call it; use listed operations through apply_ops where supported. load_guide(name=operations) returns a compact index. Add operations=[1..8 exact names] to read only their definitions, without the full guide; omitted definitions do not mean unsupported operations. The catalog remains the source of truth. This contract takes precedence over the upstream reference.
- Published tools: load_guide, create_document, read_context, read_blocks, insert_content, replace_blocks, apply_ops, check_document, save_document. Call only these tools on this server; do not invent aliases or additional parameters.
- Document context is not automatically attached to messages. Use read_context instead of upstream get_document_context; paginate its block and feature lists. Read complete affected blocks with read_blocks before rewriting; truncated summaries are not full content. read_blocks supports up to 100 blocks; paginate large HTML using htmlOffset and nextHtmlOffset. Assemble all HTML pages from offset zero at the same revision before rewriting; restart reading if the revision changes.
- create_document creates and saves an empty DOCX only; it does not accept content, a plan or a template. For a new document, create_document, then insert_content or replace_blocks, then save_document. There is no write_document or nested writer: the current model writes the requested content, using multiple content calls for long documents and refreshing block indexes as needed.
- apply_ops accepts ops and optional trackAuthor, plus path, expectedRevision and operationId. There is no dryRun parameter or validation-only mutation tool. Inspect the catalog and current context before applying; an invalid batch is rejected atomically. check_document inspects the committed draft and does not simulate proposed operations.
- Formatting, tables, images, text boxes, charts, page setup, headers/footers, comments, revisions and notes are available through the operations actually listed in the catalog. For example, insert_chart/edit_chart, add_comment/reply_comment/resolve_comment/delete_comment, accept_changes/reject_changes and note operations belong inside apply_ops.ops, not separate tool calls. Use each operation's exact schema; do not copy a desktop tool's arguments.
- findReplace searches direct text runs of top-level paragraph, heading or list blocks; it does not descend into table cells, text boxes or notes. For table text, read the complete affected table with read_blocks, preserve its structure, unrelated cells and markup, then use replace_blocks on that table block. Do not rewrite from a truncated summary. Use the published table operations for table structure or formatting, and edit_note for a note; do not invent a cell-text tool.
- Use read_context(include=[comments]), read_context(include=[revisions]) or read_context(include=[notes]) instead of upstream read_comments, read_revisions or read_notes. Headers, sections, styles, tableStyles and fields are also read_context include options. Read comment anchors before editing; accept/reject revisions or remove comments only when the user asks.
- Feature lists and check_document return ordinary entries in items. A single oversized entry returns itemJson fragments instead: keep its item offset (itemJsonIndex), continue with nextItemJsonOffset as itemJsonOffset until null, concatenate and parse the complete JSON. Empty items with itemJson is not empty content. read_context continuation requires exactly one include category; oversized headers use offset zero. Combine only identical revision and version, otherwise restart. Once the item is complete, nextOffset advances to the next list entry; never overwrite content from a fragment.
- There is no UI selection or replace_selection. Address known blocks or matching text from read_context/read_blocks; target.scope may only be document and is not itself a selector: also supply blockIndexes, nodeType, headingLevel (1..6), or containsText. Use current explicit block indexes for all-document formatting. If the requested selected span cannot be identified from the user's description, ask for its text instead of guessing a range. Desktop docnav links are not a published navigation contract; cite section names or quoted text instead.
- This server does not provide web search, image search, image generation or remote image downloads. If another authorized tool supplies an image, insert it through the catalog's image operation using an authorized local PNG/JPEG/GIF path; never use imageUrl or invent a local file. Lack of a search tool does not mean native images or charts are unsupported.
- Every write requires the current expectedRevision and a unique operationId. Retry the same request with the same ID only when replaying identical parameters. Edits are private drafts until save_document, which also requires the current file version as expectedVersion. Saving checks disk conflicts; preserve the draft on conflict and read context before deciding what to do. The preview editor and this plugin exchange only saved files, not each other's drafts.
- check_document validates document structure and references, not rendered pagination. Report completion only after successful save_document and verify the saved content; do not claim visual verification from structural checks alone. Clean documents may be unloaded and reopened automatically; unsaved documents are retained. If all document slots contain unsaved work, save that work before opening more files.

## Upstream reference (subject to the contract above)

apply_ops runs a list of ops as ONE atomic transaction: every op is validated first and any invalid op rejects the whole batch (the error quotes the op's usage line). Each op is a flat object { op, target?, ...fields }. Fields are patches: a present field is set, null clears it, an absent field is left untouched — never repeat properties the user did not ask to change. Colors are "#RRGGBB", font sizes are points, lengths are twips (1 pt = 20 twips). Pass dryRun: true to validate and see the plan without changing the document.

Target (all conditions are ANDed; provide at least one):
```
interface Target {
  nodeType?: 'docHeading' | 'docParagraph' | 'docListItem' | 'image' | 'table'  // image = image block, table = editable table (row/column/merge/format ops)
  headingLevel?: number        // only together with nodeType: 'docHeading'
  containsText?: string        // block plain text contains this substring
  matchCase?: boolean          // defaults to true
  blockIndexes?: number[]      // indexes from the "document block list"
  scope?: 'selection' | 'document'  // selection = only blocks covered by the current selection; when part of a block is selected, setFont / setMatchedFont / findReplace act only on the selected characters (paragraph-level ops still apply to the whole block)
}
```
Ops:
```
{ op: "setFont", target, bold?, italic?, underline?, strike?, color?: "#RRGGBB"|null, highlight?, fontSize?: pt|null, fontFamily?: string|null, baseline?: "superscript"|"subscript"|"none"|null, link?: {url}|null }  // run-level style of the targeted blocks (only the selected characters when the target is a partial selection); a present field is set, null clears it, absent fields stay; fontFamily applies to its own script slot (an East Asian font keeps the run's Latin font and vice versa)
{ op: "setMatchedFont", text, matchCase?, target?, bold?, italic?, underline?, strike?, color?: "#RRGGBB"|null, highlight?, fontSize?: pt|null, fontFamily?: string|null, baseline?: "superscript"|"subscript"|"none"|null, link?: {url}|null }  // character-level: styles only the occurrences of text (not the whole block); target narrows the scanned blocks, omitted = whole document
{ op: "setParagraphFormat", target, align?: "left"|"center"|"right"|"justify"|null, lineSpacing?, indentLeft?, indentRight?, indentFirstLine?, spaceBefore?, spaceAfter?, pageBreakBefore?: boolean, shadingFill?: "#RRGGBB"|null, borders?: subset of "tblr"|null }  // paragraph format of the targeted blocks (whole blocks, even for a partial selection); lengths in twips, lineSpacing as a multiple; indentFirstLine positive = first-line indent, negative = hanging; a two-character CJK indent ≈ font size in pt × 40 twips
{ op: "setHeadingLevel", target, level: 0-6 }  // 0 = demote to body paragraph
{ op: "findReplace", find, replace, matchCase?, target? }  // plain-text find & replace inside runs (no cross-block matching); the replacement keeps the matched text's formatting — the right op for small in-place fixes; target narrows the scanned blocks (blockIndexes / scope:"selection" / nodeType), omitted = whole document
{ op: "deleteBlocks", target }
{ op: "moveBlocks", blockIndexes: number[], afterBlockIndex }  // move the blocks (relative order kept) after afterBlockIndex; -1 = start of document
{ op: "setList", target, kind?: "bullet"|"number" }  // paragraphs to list items (default bullet); heading blocks are not converted
{ op: "clearList", target }  // list items back to body paragraphs
{ op: "setImageProperties", target, widthPx?, heightPx?, align?: "left"|"center"|"right"|null }  // image blocks only (target nodeType "image"); giving one dimension scales the other proportionally
{ op: "insertToc", afterBlockIndex }  // insert a TOC field after that block (-1 = start of document); entries come from the current headings, Word computes page numbers on open; fails if the document has no headings
{ op: "insertField", target, type: "SEQ"|"REF"|"PAGEREF"|"DATE"|"TIME"|"MERGEFIELD"|"IF"|"PAGE"|"NUMPAGES"|"AUTHOR"|..., args?: string, result?: string, position?: "start"|"end", afterText?: string }  // insert a Word field into exactly one paragraph, at its end unless position or afterText says otherwise; args is the instruction after the keyword ({ SEQ Figure \* ARABIC } = type "SEQ", args "Figure \* ARABIC"). Computed here: SEQ (visible fields with that identifier so far + 1), REF/PAGEREF (the bookmarked paragraph; insertBookmark creates one), DATE/TIME (now, \@ picture), MERGEFIELD («Name»), IF with literal operands; PAGE/NUMPAGES show "1"; anything else needs result, the text shown until Word updates it. Fields only Word can compute are marked dirty and refresh when the file opens in Word
{ op: "insertBookmark", target, name }  // bookmark exactly one paragraph (name: letters, digits, underscore, up to 40 characters, unique) so REF / PAGEREF fields can point at it
{ op: "updateFields", scope?: "all"|"SEQ"|"REF"|"DATE" }  // recompute the inline fields the editor can: SEQ numbering in document order, REF results from their bookmarks, DATE/TIME to now; with scope "all" every other field (PAGE, NUMPAGES, AUTHOR...) is marked dirty so Word recomputes it on open. Table-of-contents blocks are untouched (insertToc rebuilds one)
{ op: "insertTableRow", target, row, position?: "before"|"after", count? }  // target must match one native table (nodeType "table" and/or blockIndexes); row is 0-based; new rows copy the neighbouring row's cell shading/borders (default: after)
{ op: "deleteTableRow", target, row, count? }  // target must match one native table (nodeType "table" and/or blockIndexes); row is 0-based; cells merged across the row shrink
{ op: "insertTableColumn", target, col, position?: "before"|"after", count? }  // target must match one native table; col is a 0-based grid column; the new column takes the neighbouring column's width and cell formatting (default: after)
{ op: "deleteTableColumn", target, col, count? }  // target must match one native table; col is a 0-based grid column; cells merged across the column shrink
{ op: "mergeTableCells", target, range: { row, col, rowEnd?, colEnd? } }  // merge the rectangle (0-based grid coordinates, ends inclusive) into one cell; refused when an existing merged cell crosses the rectangle edge; the texts are kept as separate paragraphs
{ op: "splitTableCell", target, cell: { row, col } }  // undo a merge: the cell becomes one cell per grid slot it covered; the text stays in the top-left one
{ op: "setTableCellFormat", target, range?: { row, col, rowEnd?, colEnd? }, fill?: "#RRGGBB"|null, vAlign?: "top"|"center"|"bottom"|null, width?: twips|"2.5cm"|"1in"|"72pt"|"96px", borders?: { all?, top?, left?, bottom?, right?: { style?: "single"|"dashed"|"double"|"none", width?: pt, color?: "#RRGGBB" }|null }|null }  // cells in the range (omitted = whole table); width sets the grid columns the range covers; borders: null = no borders on the cell, a side null = that side off
{ op: "setTableStyle", target, styleId?: string|null, look?: { firstRow?, lastRow?, firstColumn?, lastColumn?, bandedRows?, bandedColumns?: boolean } }  // styleId must be a table style defined in this document (docs read lists them as tableStyles); null removes the style; look toggles Word's Table Style Options
{ op: "applyStyle", target, styleId }  // paragraph style by id (or name) from styles.xml / define_style; a heading style turns the block into a heading of its level, another paragraph style turns a heading back into a paragraph; list items keep their numbering
```

Common recipes:
- "Make all headings red" → ops: [{"op":"setFont","target":{"nodeType":"docHeading"},"color":"#FF0000"}]
- "1.5 line spacing for the whole document" → one setParagraphFormat each for docParagraph / docHeading / docListItem with "lineSpacing":1.5
- "Demote the 'Risk Notice' level-2 heading to level 3" → ops: [{"op":"setHeadingLevel","target":{"nodeType":"docHeading","headingLevel":2,"containsText":"Risk Notice"},"level":3}]
- "Delete blocks 3 to 5" → ops: [{"op":"deleteBlocks","target":{"blockIndexes":[3,4,5]}}]
- "Turn blocks 2 to 4 into a numbered list" → ops: [{"op":"setList","target":{"blockIndexes":[2,3,4]},"kind":"number"}]
- "Center all images" → ops: [{"op":"setImageProperties","target":{"nodeType":"image"},"align":"center"}]
- "In block 5, change 8% to 9%" → ops: [{"op":"findReplace","find":"8%","replace":"9%","target":{"blockIndexes":[5]}}]
- "Bold every TODO:" → ops: [{"op":"setMatchedFont","text":"TODO:","bold":true}]
- "Make the selected words 14 pt blue" (partial selection) → ops: [{"op":"setFont","target":{"scope":"selection"},"fontSize":14,"color":"#1A73E8"}]
- "Two-character first-line indent for the whole document" (11 pt font) → one setParagraphFormat for docParagraph with "indentFirstLine":440
- "Insert a table of contents at the beginning" → ops: [{"op":"insertToc","afterBlockIndex":-1}]; if the user wants the TOC on its own page, also setParagraphFormat the first body block after the TOC with "pageBreakBefore":true
- "Number the figures" → one insertField {"type":"SEQ","args":"Figure \* ARABIC"} per caption paragraph (afterText places the number after the label); "refresh the numbering / the date" → [{"op":"updateFields"}]; a cross-reference is insertBookmark on the target paragraph, then insertField {"type":"REF","args":"Name \h"} where it is cited
- Cover page recipe: use insert_content to insert one paragraph each for title/subtitle/date at the start of the document, then setFont to enlarge the title (e.g. "fontSize":36), setParagraphFormat to center everything and give the title "spaceBefore":4800, and finally set "pageBreakBefore":true on the first body block after the cover

Discipline:
- Read the "document block list" before issuing ops; anything like "paragraph N / a certain section" must be addressed with block indexes from the list — never guess;
- Only give the fields the user explicitly asked to change;
- Protected blocks such as images cannot be modified with style ops (they are skipped); to change table content, use read_blocks to get the <table> and rewrite it wholesale with replace_blocks (the table keeps its column widths, borders, shading and cell formatting; cells whose text you leave unchanged keep their content untouched).

Known error cases (must avoid):
BC-1 Giving fields the user did not ask for, wiping existing formatting by mistake;
BC-2 A "whole document" formatting operation only changed docParagraph and missed docHeading/docListItem;
BC-3 Addressing by word/character position (no such addressing exists); use block indexes, text containment or the selection instead;
BC-4 Using findReplace sentence by sentence for rewrites such as translation/abbreviation; use replace_blocks (or replace_selection for a selected span) instead;
