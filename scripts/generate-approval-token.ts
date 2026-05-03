import { generateApprovalToken, getApprovalTokenWindowMs } from "@/lib/v7/approval-token";

try {
  const token = generateApprovalToken();
  const expiresAt = new Date(Date.now() + getApprovalTokenWindowMs()).toISOString();

  console.log(token);
  console.log(`expires_at=${expiresAt}`);
} catch (error: any) {
  console.error(error.message || "Cannot generate approval token");
  process.exit(1);
}