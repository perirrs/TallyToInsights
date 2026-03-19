/**
 * Product key generation and validation (offline, HMAC-SHA256)
 * KEEP THIS FILE'S MASTER_SECRET PRIVATE — it is the root of trust.
 *
 * Key format: TALLY-XXXXX-XXXXX-XXXXX-XXXXX
 *             prefix + 4 groups of 5 base32 chars = 20 payload chars
 *             encodes serial 1..9999 + HMAC checksum
 */

const crypto = require('crypto');
const os = require('os');
const { execSync } = require('child_process');

// ---------- CHANGE THIS SECRET BEFORE DISTRIBUTING ----------
const MASTER_SECRET = 'PERIRRS-TALLY-INSIGHTS-OFFLINE-KEY-2024-XK9M7N2P';
// ------------------------------------------------------------

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

function base32Encode(buffer) {
  let result = '';
  let bits = 0;
  let value = 0;
  for (const byte of buffer) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      result += BASE32_ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) result += BASE32_ALPHABET[(value << (5 - bits)) & 31];
  return result;
}

/**
 * Generate a product key for a given serial number (1–9999).
 * This is the developer tool function — not exposed to end users.
 */
function generateKey(serial) {
  const buf = Buffer.alloc(4);
  buf.writeUInt32BE(serial);
  const sig = crypto.createHmac('sha256', MASTER_SECRET).update(buf).digest();
  const code = base32Encode(sig.slice(0, 15)); // 24 base32 chars
  return `TALLY-${code.slice(0, 5)}-${code.slice(5, 10)}-${code.slice(10, 15)}-${code.slice(15, 20)}`;
}

/**
 * Validate a product key offline.
 * Returns serial number (1–9999) if valid, or null if invalid.
 * ~9999 HMAC operations ≈ 3–5 ms on modern hardware.
 */
function validateKey(key) {
  if (!key || typeof key !== 'string') return null;
  const clean = key.toUpperCase().trim();
  const parts = clean.split('-');
  if (parts.length !== 5 || parts[0] !== 'TALLY') return null;
  if (!parts.slice(1).every((p) => p.length === 5)) return null;

  const encoded = parts.slice(1).join('');

  for (let serial = 1; serial <= 9999; serial++) {
    const expected = generateKey(serial);
    const expectedEncoded = expected.split('-').slice(1).join('');
    if (expectedEncoded === encoded) return serial;
  }
  return null;
}

/**
 * Get a stable machine identifier.
 * Uses Windows UUID via wmic; falls back to hashed hostname+username.
 */
function getMachineId() {
  try {
    const out = execSync('wmic csproduct get uuid', { encoding: 'utf8', timeout: 5000 });
    const match = out.match(/[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}/i);
    if (match) return match[0].toUpperCase();
  } catch (_) {}

  // Fallback: hash of hostname + username
  const raw = `${os.hostname()}::${os.userInfo().username}`;
  return crypto.createHash('sha256').update(raw).digest('hex').slice(0, 36).toUpperCase();
}

module.exports = { generateKey, validateKey, getMachineId };
