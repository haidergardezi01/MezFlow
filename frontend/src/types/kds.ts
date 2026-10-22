export type KitchenStation =
  | "all"
  | "grill"
  | "fry"
  | "hot_kitchen"
  | "beverage";

export type KDSStatusFilter = "ALL" | "NEW" | "PREPARING" | "READY";

export type ItemStatus = "PENDING" | "PREPARING" | "READY";

export type UrgencyLevel = "NORMAL" | "WARNING" | "DELAYED";

export interface KDSModifier {
  id: string;
  option_name: string;
  price_delta: number | string;
}

export interface KDSItem {
  id: string;
  item_id?: string | null;
  item_name: string;
  kitchen_station: string;
  quantity: number;
  special_instructions?: string | null;
  status: ItemStatus;
  prepared_at?: string | null;
  modifiers: KDSModifier[];
}

export interface KDSOrderCard {
  id: string;
  restaurant_id: string;
  table_id: string;
  table_number: number;
  table_name?: string | null;
  order_number: number;
  display_number: string;
  status: "NEW" | "CONFIRMED" | "PREPARING" | "READY" | "DISPATCHED" | "CANCELLED";
  placed_at: string;
  confirmed_at?: string | null;
  preparing_started_at?: string | null;
  ready_at?: string | null;
  dispatched_at?: string | null;
  target_prep_minutes: number;
  elapsed_seconds: number;
  urgency_level: UrgencyLevel;
  notes?: string | null;
  placed_by_diner_name?: string | null;
  items: KDSItem[];
}

export interface KDSSummary {
  total_active: number;
  new: number;
  preparing: number;
  ready: number;
  delayed: number;
  by_station: Record<string, number>;
}
