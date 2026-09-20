#!/usr/bin/env node
/**
 * jev-use CLI.
 *
 *   jev-use serve             stdio MCP server (Claude Code, Codex, Cursor, ...)
 *   jev-use hook gate         PreToolUse hook adapter (Claude Code & Codex hooks)
 *   jev-use judge [json]      one-shot judgment from argv or stdin (smoke/CI)
 *   jev-use doctor            resolve the backend and run one live round trip
 *
 * Flags: --backend typesafe|openrouter|vercel|mock, --threshold 0..1
 */
export {};
