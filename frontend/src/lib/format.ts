export function humanise(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** The API returns naive UTC timestamps; treat them as UTC, not local time. */
export function parseUtc(value: string): Date {
  return /[Z+]|-\d{2}:\d{2}$/.test(value.slice(10)) ? new Date(value) : new Date(`${value}Z`);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "";
  return parseUtc(value).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return "";
  return parseUtc(value).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/** The backend works in UTC; datetime-local inputs work in local time. */
export function toIsoUtc(localValue: string): string {
  return new Date(localValue).toISOString().replace("Z", "");
}

export function toLocalInput(date: Date): string {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function utcToLocalInput(value: string): string {
  return toLocalInput(parseUtc(value));
}

export const WEEKDAYS = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 7, label: "Sun" },
];
