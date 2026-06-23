export const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const formatCurrency = (value: any): string => {
  const num = typeof value === "number" ? value : parseFloat(value);
  if (Math.abs(num) > 1000) {
    return `${num.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} JPY`;
  }
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export const formatStatKey = (key: string): string => {
  const keyMap: Record<string, string> = {
    "Start Index": "Start Date",
    "End Index": "End Date",
    "Start Value": "Start Value",
    "End Value": "End Value",
  };
  return keyMap[key] || key;
};

export const formatStatValue = (key: string, value: any): string => {
  if (key === "Start Index" || key === "End Index") {
    return formatDate(value);
  }
  if (key === "Start Value" || key === "End Value") {
    return formatCurrency(value);
  }
  if (typeof value === "number") {
    return value.toFixed(2);
  }
  return String(value);
};