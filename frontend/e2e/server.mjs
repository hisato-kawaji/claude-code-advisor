import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawn } from 'node:child_process';

const root = mkdtempSync(join(tmpdir(), 'claude-analytics-e2e-'));
const projects = join(root, 'claude', 'projects', 'example');
const childDir = join(projects, 'session-1', 'subagents');
mkdirSync(childDir, { recursive: true });
const start = Date.now() - 10000;
let sequence = 0;
const entry = (type, uuid, message, more = {}) => ({type, uuid, timestamp: new Date(start + sequence++ * 1000).toISOString(), sessionId: 'session-1', cwd: '/work/example', message, ...more});
const usage = { input_tokens: 1000, output_tokens: 200, cache_creation_input_tokens: 100, cache_read_input_tokens: 200, cache_creation: { ephemeral_5m_input_tokens: 100, ephemeral_1h_input_tokens: 0 } };
writeFileSync(join(projects, 'session-1.jsonl'), [entry('user', 'prompt-1', { content: 'Fix the example with email alice@example.com' }), entry('assistant', 'assistant-1', { model: 'claude-sonnet-4-6', content: [{type: 'text', text: 'Done'}], usage })].map(x => JSON.stringify(x)).join('\n') + '\n');
writeFileSync(join(childDir, 'agent-1.jsonl'), JSON.stringify(entry('assistant', 'child-1', { model: 'claude-sonnet-4-6', content: [], usage }, {isSidechain: true})) + '\n');
const env = { ...process.env, CLAUDE_DATA_PATH: join(root, 'claude'), DATABASE_PATH: join(root, 'analytics.db'), OTEL_RECEIVER_TOKEN: 'e2e-token', OPENAI_API_KEY: 'e2e-not-real', CORS_ORIGINS: 'http://localhost:18766', VITE_API_URL: 'http://localhost:18765' };
const backend = spawn(resolve('../backend/venv/bin/python'), ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18765'], { cwd: resolve('../backend'), env, stdio: 'inherit' });
const frontend = spawn(resolve('node_modules/.bin/vite'), ['--host', '127.0.0.1', '--port', '18766', '--strictPort'], { cwd: process.cwd(), env, stdio: 'inherit' });
let stopping = false;
function stop(code = 0) { if (stopping) return; stopping = true; backend.kill('SIGTERM'); frontend.kill('SIGTERM'); setTimeout(() => { rmSync(root, {recursive: true, force: true}); process.exit(code); }, 300); }
for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => stop());
backend.on('exit', code => { if (!stopping) stop(code || 1); });
frontend.on('exit', code => { if (!stopping) stop(code || 1); });
