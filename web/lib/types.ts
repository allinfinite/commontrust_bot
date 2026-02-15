export type PbListResponse<T> = {
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
  verified?: boolean;
  joined_at?: string;
  created_at?: string;
  profile_image_url?: string;
  photo_url?: string;
};

export type ReputationRecord = {
  id: string;
  member_id: string;
  avg_rating?: number;
  verified_deals?: number;
};

export type DealRecord = {
  id: string;
  description?: string;
};

export type ReviewRecord = {
  id: string;
  created: string;
  reviewer_id?: string;
  reviewee_id?: string;
  reviewer_username?: string;
  reviewee_username?: string;
  rating: number;
  outcome?: string;
  comment?: string;
  expand?: {
    reviewer_id?: MemberRecord;
    reviewee_id?: MemberRecord;
    deal_id?: DealRecord;
  };
};
