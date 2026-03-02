import { Text } from "ink";
import { repeatChar, truncateEnd } from "./format.js";

export const SectionHeader = ({ title, width }: { title: string; width?: number }) => {
  const terminalCols = process.stdout.columns ?? 80;
  const cols = Math.max(20, Math.min(width ?? terminalCols - 4, terminalCols - 4));
  const safeTitle = truncateEnd(title, Math.max(4, cols - 2));
  const dashes = Math.max(1, Math.floor((cols - safeTitle.length - 2) / 2));
  const remainder = Math.max(0, cols - (dashes * 2 + safeTitle.length + 2));
  const line = repeatChar("─", dashes);
  return <Text dimColor>{line} {safeTitle} {line}{repeatChar("─", remainder)}</Text>;
};
