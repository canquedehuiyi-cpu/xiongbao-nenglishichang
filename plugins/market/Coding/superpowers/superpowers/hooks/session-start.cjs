#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
// Resolve from this file, not cwd or inherited variables from another harness.
const root = path.resolve(__dirname, '..');
try {
  const bootstrap = fs.readFileSync(path.join(root, 'skills/using-superpowers/SKILL.md'), 'utf8');
  const mapping = fs.readFileSync(path.join(root, 'skills/using-superpowers/references/qodercli-tools.md'), 'utf8');
  const additionalContext = '<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\n' +
    'Below is the full superpowers:using-superpowers skill. For other skills use the native Skill tool when available.\n\n' +
    bootstrap + '\n\n' + mapping + '\n</EXTREMELY_IMPORTANT>';
  process.stdout.write(JSON.stringify({hookSpecificOutput: {hookEventName: 'SessionStart', additionalContext}}) + '\n');
} catch (error) {
  process.stderr.write('Superpowers bootstrap could not load: ' + error.message + '\n');
  process.exitCode = 1;
}
