import { AdInput, Mechanism } from './types';

const includesAny = (text: string, words: string[]) => words.some((w) => text.includes(w));

export function detectSellingMechanism(input: AdInput): Mechanism {
  const text = `${input.product} ${input.industry || ''} ${input.audience || ''} ${input.goal || ''}`.toLowerCase();

  if (includesAny(text, ['mụn', 'nám', 'giảm cân', 'đau', 'rụng', 'hôi', 'sẹo', 'eo', 'corset', 'trị'])) return 'problem';
  if (includesAny(text, ['nước ép', 'cá', 'hải sản', 'sả', 'chanh', 'cam', 'dứa', 'tươi', 'organic', 'thiên nhiên'])) return 'ingredient';
  if (includesAny(text, ['luxury', 'cao cấp', 'nước hoa', 'xe', 'fashion', 'thời trang', 'iconic'])) return 'aspiration';
  if (includesAny(text, ['review', 'feedback', 'bằng chứng', 'trước sau', 'chứng minh'])) return 'proof';
  if (includesAny(text, ['sale', 'giảm giá', 'combo', 'mua 1', 'ưu đãi'])) return 'offer';
  return 'lifestyle';
}
