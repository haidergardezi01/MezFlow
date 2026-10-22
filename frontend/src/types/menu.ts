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

// -----------------------------------------------------------------------------
// Module 3: Collaborative Dining Session, Cart & Order Types
// -----------------------------------------------------------------------------

export interface Diner {
  id: string;
  session_id: string;
  user_id?: string | null;
  display_name: string;
  avatar_color: string;
  client_session_id: string;
  is_host: boolean;
  is_active: boolean;
  joined_at: string;
}

export interface CartItemModifier {
  id: string;
  modifier_option_id: string;
  option_name: string;
  price_delta: number | string;
}

export interface CartItem {
  id: string;
  session_id: string;
  item_id: string;
  item_name: string;
  item_name_ur?: string | null;
  base_price: number | string;
  diner_id: string;
  diner_name: string;
  avatar_color: string;
  quantity: number;
  special_instructions?: string | null;
  modifiers: CartItemModifier[];
  unit_price: number | string;
  line_total: number | string;
  created_at: string;
}

export interface CartResponse {
  session_id: string;
  restaurant_id: string;
  table_id: string;
  table_number: number;
  status: string;
  items: CartItem[];
  diners: Diner[];
  subtotal: number | string;
  tax_amount: number | string;
  total_amount: number | string;
  currency: string;
  item_count: number;
}

export interface TableSession {
  id: string;
  restaurant_id: string;
  table_id: string;
  table_number: number;
  session_token: string;
  status: string;
  host_diner_id?: string | null;
  opened_at: string;
  total_amount: number | string;
  current_diner?: Diner | null;
  diners: Diner[];
  cart?: CartResponse | null;
}

export interface OrderItemModifier {
  id: string;
  modifier_option_id?: string | null;
  option_name: string;
  price_delta: number | string;
}

export interface OrderItem {
  id: string;
  item_id?: string | null;
  diner_id?: string | null;
  diner_name?: string | null;
  item_name: string;
  kitchen_station: string;
  quantity: number;
  unit_price: number | string;
  total_price: number | string;
  special_instructions?: string | null;
  status: string;
  modifiers: OrderItemModifier[];
  created_at: string;
}

export type OrderStatus =
  | "NEW"
  | "CONFIRMED"
  | "PREPARING"
  | "READY"
  | "DISPATCHED"
  | "CANCELLED";

export interface Order {
  id: string;
  restaurant_id: string;
  table_id: string;
  table_number: number;
  session_id?: string | null;
  order_number: number;
  display_number: string;
  status: OrderStatus;
  subtotal: number | string;
  tax_amount: number | string;
  total_amount: number | string;
  placed_by_diner_name?: string | null;
  notes?: string | null;
  placed_at: string;
  items: OrderItem[];
  currency: string;
}
