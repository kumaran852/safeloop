export type Level = "Low" | "Moderate" | "High" | "Critical";
export interface Ward { id: number; code: string; name: string; active: boolean }
export interface Meta {
  tasks: string[]; body_regions: { key: string; label: string }[]; shift_types: string[]; levels: Level[]; statuses: string[];
  transitions: Record<string, string[]>; outcomes: string[]; wards: Ward[];
}
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface Rate { num: number; den: number; pct: number | null }
// Response shapes are documented by the API's OpenAPI schema (/docs); loosely typed here on purpose.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Json = any;
