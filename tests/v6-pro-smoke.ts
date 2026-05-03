import { runAdsFactoryV6Pro } from "@/lib/v6-pro/runtime";

async function main() {
  const result = await runAdsFactoryV6Pro({
    product_type: "giftset qua tang tri an doanh nghiep cao cap",
    goal: "conversion",
    brand: "Demo Brand",
    ratio: "4:5"
  });

  if (!result.industry) {
    throw new Error("Missing industry");
  }
  if (!result.winner) {
    throw new Error("Missing winner");
  }
  if (!result.scored_variants.conversion?.score.total) {
    throw new Error("Missing scoring");
  }

  console.log("SMOKE TEST PASSED");
  console.log(
    JSON.stringify(
      {
        industry: result.industry,
        winner: result.winner.type,
        score: result.winner.score.total
      },
      null,
      2
    )
  );
}

void main();