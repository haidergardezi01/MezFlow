export interface ModifierOption {
  id: string;
  group_id: string;
  name: string;
  name_ur?: string | null;
  price_delta: number | string;
  is_default: boolean;
  is_available: boolean;
  sort_order: number;
}

export interface ModifierGroup {
  id: string;
  restaurant_id: string;
  item_id: string;
  name: string;
  name_ur?: string | null;
  selection_type: "single" | "multiple";
  min_selections: number;
  max_selections: number;
  is_required: boolean;
  sort_order: number;
  options: ModifierOption[];
}

export interface StructuredAttributes {
  heat_level?: string;
  flavor?: string;
  texture?: string;
  portion_size?: string;
  ingredients?: string[];
}

export interface MenuItem {
  id: string;
  restaurant_id: string;
  category_id: string;
  name: string;
  name_ur?: string | null;
  description?: string | null;
  description_ur?: string | null;
  price: number | string;
  image_url?: string | null;
  is_available: boolean;
  expected_prep_minutes: number;
  kitchen_station: string;
  dietary_tags?: string[];
  sort_order: number;
  structured_attributes?: StructuredAttributes | null;
  modifier_groups: ModifierGroup[];
}

export interface MenuCategory {
  id: string;
  restaurant_id: string;
  name: string;
  name_ur?: string | null;
  description?: string | null;
  description_ur?: string | null;
  icon_name?: string | null;
  sort_order: number;
  is_active: boolean;
  items: MenuItem[];
}

export interface PublicMenuResponse {
  restaurant_id: string;
  restaurant_name: string;
  currency: string;
  categories: MenuCategory[];
}

export interface TableLookup {
  table_id: string;
  table_number: number;
  table_name?: string | null;
  capacity: number;
  status: string;
  restaurant_id: string;
  restaurant_name: string;
  restaurant_slug: string;
  currency: string;
  qr_code_token: string;
}

export interface TableItem {
  id: string;
  restaurant_id: string;
  table_number: number;
  name?: string | null;
  qr_code_token: string;
  capacity: number;
  status: "available" | "occupied" | "awaiting_cleanup";
  created_at: string;
}

export interface TableQRGraphic {
  table_id: string;
  table_number: number;
  table_name?: string | null;
  qr_code_token: string;
  diner_url: string;
  svg_data: string;
  png_data_url: string;
}

export interface SelectedModifier {
  group_id: string;
  group_name: string;
  option_id: string;
  option_name: string;
  price_delta: number;
}
