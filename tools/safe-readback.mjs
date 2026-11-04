// Summarize private JSON without echoing values, keys, error messages, or paths.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
export function summarize(raw) {
  const bytes = Buffer.isBuffer(raw) ? raw : Buffer.from(raw);
  if (bytes.length > 8 * 1024 * 1024) throw new Error('readback_too_large');
  const data = JSON.parse(bytes.toString('utf8'));
  const object = data !== null && typeof data === 'object' && !Array.isArray(data);
  const result = { parsed: true, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'), rootType: data === null ? 'null' : Array.isArray(data) ? 'array' : typeof data };
  if (Array.isArray(data)) result.items = data.length;
  if (!object) return result;
  if (typeof data.ok === 'boolean') result.ok = data.ok;
  if (Number.isInteger(data.schemaVersion) && data.schemaVersion >= 0 && data.schemaVersion <= 1000) result.schemaVersion = data.schemaVersion;
  if (Number.isInteger(data.httpStatus) && data.httpStatus >= 100 && data.httpStatus <= 599) result.httpStatus = data.httpStatus;
  if (typeof data.revision === 'string' && /^[a-f0-9]{40,64}$/.test(data.revision)) result.revision = data.revision;
  if (data.contract === 'failsafe.shared-memory.v1') result.memoryContractVerified = true;
  if (data.access === 'read-only') result.readOnlyReported = true;
  if (['pass','partial','fail','blocked','not_verified'].includes(data.status)) result.status = data.status;
  if (typeof data.error === 'string' && /^(memory_http_[1-5][0-9]{2}|memory_network_secret_missing|memory_network_unavailable|memory_response_too_large|memory_query_invalid|memory_read_not_confirmed|memory_client_failed)$/.test(data.error)) result.memoryError = data.error;
  for (const key of ['records','events','tasks','errors','items','objects']) if (Array.isArray(data[key])) result[key + 'Count'] = data[key].length;
  return result;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    if (process.argv.length !== 3) throw new Error('invalid_arguments');
    process.stdout.write(JSON.stringify(summarize(readFileSync(process.argv[2]))) + '\n');
  } catch {
    process.stdout.write(JSON.stringify({ parsed: false, error: 'safe_readback_failed' }) + '\n');
    process.exitCode = 1;
  }
}
