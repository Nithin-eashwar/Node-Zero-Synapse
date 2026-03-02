import { Box, Text } from "ink";
import chalk from "chalk";
import type { Contributor, SmartBlameResult } from "@nzs/core";
import { SectionHeader } from "../components/SectionHeader.js";
import { barFill, scoreColor } from "../components/visual.js";
import { padCell, truncateMiddle } from "../components/format.js";
import { theme } from "../theme.js";

type SmartBlameViewProps = {
  result: SmartBlameResult;
};

const COLUMN_WIDTHS = {
  rank: 4,
  name: 20,
  scoreBar: 12,
  scorePct: 5,
  commits: 8,
  refactors: 10,
  lastActive: 12
} as const;

const normalizeScore = (score: number): number => {
  if (!Number.isFinite(score)) {
    return 0;
  }

  const base = score > 1 ? score / 100 : score;
  return Math.max(0, Math.min(1, base));
};

const formatLastActive = (lastActive: string): string => {
  const date = new Date(lastActive);
  if (Number.isNaN(date.getTime())) {
    return padCell(lastActive, COLUMN_WIDTHS.lastActive);
  }

  return padCell(date.toISOString().slice(0, 10), COLUMN_WIDTHS.lastActive);
};

const busFactorColor = (busFactor: number): string => {
  if (busFactor < 3) {
    return theme.red;
  }

  if (busFactor < 5) {
    return theme.orange;
  }

  return theme.green;
};

const recommendationReason = (expert: Contributor): string => {
  const score = Math.round(normalizeScore(expert.expertiseScore) * 100);
  return `Top expertise (${score}%), ${expert.commitCount} commits, ${expert.refactorCount} refactors, active ${formatLastActive(expert.lastActive).trim()}.`;
};

const scoreParts = (score: number): { bar: string; pct: string; color: string } => {
  const normalized = normalizeScore(score);
  const percent = Math.round(normalized * 100);

  return {
    bar: barFill(percent, COLUMN_WIDTHS.scoreBar),
    pct: padCell(`${percent}%`, COLUMN_WIDTHS.scorePct),
    color: scoreColor(percent)
  };
};

export function SmartBlameView({ result }: SmartBlameViewProps) {
  const topExpert = result.experts[0];
  const sectionWidth = Math.max(28, (process.stdout.columns ?? 80) - 34);
  const filepathWidth = Math.max(24, (process.stdout.columns ?? 80) - 18);

  const header = [
    padCell("Rank", COLUMN_WIDTHS.rank),
    padCell("Name", COLUMN_WIDTHS.name),
    padCell("Score", COLUMN_WIDTHS.scoreBar),
    padCell("%", COLUMN_WIDTHS.scorePct),
    padCell("Commits", COLUMN_WIDTHS.commits),
    padCell("Refactors", COLUMN_WIDTHS.refactors),
    padCell("Last active", COLUMN_WIDTHS.lastActive),
    "Status"
  ].join(" ");

  return (
    <Box flexDirection="column">
      <SectionHeader title="Smart Blame" width={sectionWidth} />
      <Text>{chalk.hex(theme.text)(truncateMiddle(result.filepath, filepathWidth))}</Text>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title="Contributors" width={sectionWidth} />
        <Text>{chalk.hex(theme.dim)(header)}</Text>

        {result.experts.map((expert, index) => {
          const rank = index + 1;
          const isTopRank = rank === 1;
          const { bar, pct, color } = scoreParts(expert.expertiseScore);
          const rankCell = padCell(String(rank), COLUMN_WIDTHS.rank);
          const nameCell = padCell(expert.name, COLUMN_WIDTHS.name);
          const commitsCell = padCell(String(expert.commitCount), COLUMN_WIDTHS.commits);
          const refactorsCell = padCell(String(expert.refactorCount), COLUMN_WIDTHS.refactors);
          const lastActiveCell = formatLastActive(expert.lastActive);
          const statusCell = expert.status.toUpperCase();

          const rankText = chalk.hex(theme.dim)(rankCell);
          const nameText = isTopRank ? chalk.hex(theme.text).bold(nameCell) : chalk.hex(theme.text)(nameCell);
          const scoreTint = isTopRank ? theme.accent : color;
          const scoreBarText = chalk.hex(scoreTint)(bar);
          const scorePctText = chalk.hex(scoreTint)(pct);
          const commitsText = chalk.hex(theme.dim)(commitsCell);
          const refactorsText = chalk.hex(theme.dim)(refactorsCell);
          const lastActiveText = chalk.hex(theme.dim)(lastActiveCell);
          const statusText = chalk.hex(theme.dim)(statusCell);

          return (
            <Text key={expert.id}>
              {rankText} {nameText} {scoreBarText} {scorePctText} {commitsText} {refactorsText} {lastActiveText} {statusText}
            </Text>
          );
        })}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title="Bus Factor" width={sectionWidth} />
        <Text>
          {chalk.hex(theme.text)("Bus Factor: ")}
          {chalk.hex(busFactorColor(result.busFactor))(String(result.busFactor))}
        </Text>
      </Box>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title="Recommendation" width={sectionWidth} />
        {topExpert ? (
          <>
            <Text>{chalk.hex(theme.accent)(`Ask ${topExpert.name}`)}</Text>
            <Text>{chalk.hex(theme.text)(recommendationReason(topExpert))}</Text>
          </>
        ) : (
          <Text dimColor>No experts found for this file.</Text>
        )}
      </Box>
    </Box>
  );
}
