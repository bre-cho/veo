export async function GET() {
  const clientKey = process.env.TIKTOK_CLIENT_KEY;
  const redirectUri = process.env.TIKTOK_REDIRECT_URI;

  if (!clientKey || !redirectUri) {
    return Response.json(
      { error: "Missing TIKTOK_CLIENT_KEY or TIKTOK_REDIRECT_URI" },
      { status: 500 }
    );
  }

  const scope = encodeURIComponent("user.info.basic,video.publish");
  const url =
    `https://www.tiktok.com/v2/auth/authorize/?client_key=${encodeURIComponent(clientKey)}` +
    `&response_type=code&scope=${scope}&redirect_uri=${encodeURIComponent(redirectUri)}`;

  return Response.json({ url });
}
