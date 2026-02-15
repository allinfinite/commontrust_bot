export type ExpandMap = Record<string, unknown>;

export type PbListResult<T> = {
  page: number;
  perPage: number;
  totalItems: number;
  totalPages: number;
  items: T[];
};

export type MemberRecord = {
  id: string;
  telegram_id?: number;
  username?: string;
  display_name?: string;
  joined_at?: string;
  verified?: boolean;
  profile_image_url?: string | null;
  photo_url?: string | null;
};

export type DealRecord = {
  id: string;
  description?: string;
  status?: string;
};

export type ReviewRecord = {
  id: string;
  created: string;
  created_at?: string;
  rating: number;
  comment?: string;
  outcome?: string;
  reviewer_id?: string;
  reviewee_id?: string;
  reviewer_username?: string;
  reviewee_username?: string;
  deal_id?: string;
  expand?: {
    reviewer_id?: MemberRecord;
    reviewee_id?: MemberRecord;
    deal_id?: DealRecord;
  };
};

export type ReputationRecord = {
  id: string;
  member_id?: string;
  verified_deals?: number;
  avg_rating?: number;
};
