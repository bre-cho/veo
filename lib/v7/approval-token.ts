import { createHmac, timingSafeEqual } from "crypto";

const DEFAULT_WINDOW_MINUTES = 10;

function base64UrlEncode(value: string) {
  return Buffer.from(value, "utf8").toString("base64url");
}

function base64UrlDecode(value: string) {
  return Buffer.from(value, "base64url").toString("utf8");
}

function getSecret() {
  return process.env.DEPLOY_APPROVAL_TOKEN_SECRET || "";
}

export function getApprovalTokenWindowMs() {
  const minutes = Number(process.env.DEPLOY_APPROVAL_TOKEN_WINDOW_MINUTES || DEFAULT_WINDOW_MINUTES);
  return Math.max(1, minutes) * 60 * 1000;
}

export function generateApprovalToken(now = Date.now()) {
  const secret = getSecret();
  if (!secret) {
    throw new Error("Missing DEPLOY_APPROVAL_TOKEN_SECRET");
  }

  const issuedAt = String(now);
  const expiresAt = String(now + getApprovalTokenWindowMs());
  const payload = `${issuedAt}.${expiresAt}`;
  const signature = createHmac("sha256", secret).update(payload).digest("base64url");

  return `${base64UrlEncode(issuedAt)}.${base64UrlEncode(expiresAt)}.${signature}`;
}

export function validateRotatingApprovalToken(token: string, now = Date.now()) {
  const secret = getSecret();
  if (!secret) {
    return { ok: false, reason: "Missing DEPLOY_APPROVAL_TOKEN_SECRET" };
  }

  const parts = String(token || "").split(".");
  if (parts.length !== 3) {
    return { ok: false, reason: "Malformed rotating token" };
  }

  const [issuedAtEncoded, expiresAtEncoded, providedSignature] = parts;
  const issuedAt = base64UrlDecode(issuedAtEncoded);
  const expiresAt = base64UrlDecode(expiresAtEncoded);

  if (!/^\d+$/.test(issuedAt) || !/^\d+$/.test(expiresAt)) {
    return { ok: false, reason: "Invalid token timestamps" };
  }

  const payload = `${issuedAt}.${expiresAt}`;
  const expectedSignature = createHmac("sha256", secret).update(payload).digest();
  const actualSignature = Buffer.from(providedSignature, "base64url");

  if (expectedSignature.length !== actualSignature.length) {
    return { ok: false, reason: "Invalid rotating token signature" };
  }

  if (!timingSafeEqual(expectedSignature, actualSignature)) {
    return { ok: false, reason: "Invalid rotating token signature" };
  }

  const expiresAtNumber = Number(expiresAt);
  if (Number.isNaN(expiresAtNumber) || now > expiresAtNumber) {
    return { ok: false, reason: "Approval token expired" };
  }

  return {
    ok: true,
    reason: null,
    issuedAt: Number(issuedAt),
    expiresAt: expiresAtNumber
  };
}

export function validateApprovalToken(token: string) {
  const rotating = validateRotatingApprovalToken(token);
  if (rotating.ok) {
    return {
      ok: true,
      mode: "rotating" as const,
      expiresAt: rotating.expiresAt
    };
  }

  const legacy = process.env.DEPLOY_APPROVAL_TOKEN || "";
  if (legacy && token === legacy) {
    return {
      ok: true,
      mode: "static" as const,
      expiresAt: null
    };
  }

  return {
    ok: false,
    mode: null,
    expiresAt: null,
    reason: rotating.reason || "Invalid approval token"
  };
}