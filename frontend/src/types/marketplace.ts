export interface MarketplaceItem {
  id: string;
  avatar_id: string;
  creator_id?: string | null;
  price_usd?: number | null;
  license_type?: string | null;
  is_free: boolean;
  is_active: boolean;
  download_count: number;
  view_count: number;
  rating_avg?: number | null;
  rating_count: number;
  tags?: string[] | null;
}

export interface AvatarListing {
  id: string;
  name: string;
  role_id?: string | null;
  niche_code?: string | null;
  market_code?: string | null;
  is_published: boolean;
  is_featured: boolean;
  marketplace_item?: MarketplaceItem | null;
}

export interface MarketplaceListResponse {
  items: AvatarListing[];
  total: number;
  page: number;
  page_size: number;
}
