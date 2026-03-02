import { theme } from "../theme.js";

export type UiRiskLevel = "low" | "medium" | "high" | "critical";

export const riskColor = (risk: UiRiskLevel): string => {
  if (risk === "critical" || risk === "high") {
    return theme.red;
  }

  if (risk === "medium") {
    return theme.orange;
  }

  return theme.green;
};

export const riskLabel = (risk: UiRiskLevel): string => {
  if (risk === "critical") {
    return "CRITICAL";
  }

  if (risk === "high") {
    return "HIGH RISK";
  }

  if (risk === "medium") {
    return "MEDIUM RISK";
  }

  return "OK";
};

export const riskDot = (risk: UiRiskLevel): string => {
  if (risk === "low") {
    return "○";
  }

  return "⬤";
};

export const scoreColor = (score: number): string => {
  if (score >= 70) {
    return theme.red;
  }

  if (score >= 40) {
    return theme.orange;
  }

  return theme.green;
};

export const barFill = (score: number, width: number): string => {
  const clampedWidth = Math.max(1, width);
  const normalized = Math.max(0, Math.min(100, score));
  const filled = Math.round((normalized / 100) * clampedWidth);
  return `${"█".repeat(filled)}${"░".repeat(clampedWidth - filled)}`;
};
