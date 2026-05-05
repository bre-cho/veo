import { packs, type MarketplacePack } from "@/lib/marketplace/packs";

export const marketplaceCategories = ["All", ...new Set(packs.map((pack) => pack.category))];

export type MarketplaceTemplate = MarketplacePack & {
  id: string;
  recommendScore?: number;
  priceLabel: string;
};

export function getMarketplaceTemplates(): MarketplaceTemplate[] {
  return packs.map((pack) => ({
    ...pack,
    id: pack.slug,
    priceLabel: new Intl.NumberFormat("vi-VN").format(pack.price) + "đ"
  }));
}

export function recommendTemplates(input: string, goal: string) {
  const text = `${input} ${goal}`.toLowerCase();

  return getMarketplaceTemplates()
    .map((template) => {
      const keywordScore = template.bestFor.reduce((sum, keyword) => {
        return sum + (text.includes(keyword.toLowerCase()) ? 22 : 0);
      }, 0);

      const categoryScore = text.includes(template.category.toLowerCase()) ? 18 : 0;
      const goalScore =
        template.logic.toLowerCase().includes(goal.toLowerCase()) ||
        template.goal.toLowerCase().includes(goal.toLowerCase()) ||
        template.platform.toLowerCase().includes(goal.toLowerCase())
          ? 12
          : 0;

      return {
        ...template,
        recommendScore: Math.min(100, template.score + keywordScore + categoryScore + goalScore)
      };
    })
    .sort((left, right) => (right.recommendScore || 0) - (left.recommendScore || 0))
    .slice(0, 3);
}

export function getTemplateBySlug(slug: string) {
  return getMarketplaceTemplates().find((template) => template.slug === slug) || null;
}