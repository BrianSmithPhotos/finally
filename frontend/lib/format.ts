export function formatCurrency(value: number, options?: { decimals?: number }): string {
  const decimals = options?.decimals ?? 2;
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(value: number, decimals = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatSignedCurrency(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatCurrency(value)}`;
}

export function formatQuantity(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}
