export type PbRecordBase = {
  id: string;
  created: string;
  updated: string;
};

export type MemberRecord = PbRecordBase & {
  telegram_id: number;
  username?: string;
  display_name?: string;
  verified?: boolean;
};

export type DealRecord = PbRecordBase & {
  description?: string;
  status?: string;
};

export type ReviewRecord = PbRecordBase & {
  deal_id: string;
  reviewer_id: string;
  reviewee_id: string;
  rating: number;
  comment?: string;
  response?: string;
  response_at?: string;
  outcome?: "positive" | "neutral" | "negative";
  reviewer_username?: string;
  reviewee_username?: string;
  expand?: {
    reviewer_id?: MemberRecord;
    reviewee_id?: MemberRecord;
    deal_id?: DealRecord;
  };
};

export type ReputationRecord = PbRecordBase & {
  member_id: string;
  verified_deals?: number;
  avg_rating?: number;
};
