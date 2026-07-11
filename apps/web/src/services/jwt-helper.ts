function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

async function signHmacSha256(message: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();
  const secretKeyData = encoder.encode(secret);
  const key = await window.crypto.subtle.importKey(
    "raw",
    secretKeyData,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await window.crypto.subtle.sign(
    "HMAC",
    key,
    encoder.encode(message)
  );
  return bytesToBase64Url(new Uint8Array(signature));
}

export async function generateToken(userId: string, role: string, department: string): Promise<string> {
  const header = { alg: "HS256", typ: "JWT" };
  const payload = {
    sub: userId,
    roles: [role],
    departments: [department],
    exp: Math.floor(Date.now() / 1000) + 86400, // 24 hours TTL
    iat: Math.floor(Date.now() / 1000)
  };
  
  const encoder = new TextEncoder();
  const headerStr = bytesToBase64Url(encoder.encode(JSON.stringify(header)));
  const payloadStr = bytesToBase64Url(encoder.encode(JSON.stringify(payload)));
  const unsignedToken = `${headerStr}.${payloadStr}`;
  
  const signatureStr = await signHmacSha256(unsignedToken, "change-me-in-production-32-bytes-minimum");
  return `${unsignedToken}.${signatureStr}`;
}
