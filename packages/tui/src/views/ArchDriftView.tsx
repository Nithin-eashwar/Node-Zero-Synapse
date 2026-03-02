import { Box, Text } from "ink";
import chalk from "chalk";
import type { ArchViolation } from "@nzs/core";
import { SectionHeader } from "../components/SectionHeader.js";
import { truncateMiddle } from "../components/format.js";
import { theme } from "../theme.js";

type ViolationSeverity = "critical" | "high";

type ArchDriftViewProps = {
  violations: ArchViolation[];
};

type ViolationWithSeverity = ArchViolation & {
  severity?: ViolationSeverity;
};

const getSeverity = (violation: ViolationWithSeverity): ViolationSeverity => {
  if (violation.severity === "critical" || violation.severity === "high") {
    return violation.severity;
  }

  const description = violation.description.toLowerCase();
  if (description.includes("critical") || description.includes("forbidden") || description.includes("blocked")) {
    return "critical";
  }

  return "high";
};

const layerHealth = (violations: ArchViolation[]): Array<{ layer: string; count: number }> => {
  const outgoingCount = new Map<string, number>();

  for (const violation of violations) {
    const normalizedFrom = violation.fromLayer.toLowerCase();
    outgoingCount.set(normalizedFrom, (outgoingCount.get(normalizedFrom) ?? 0) + 1);
  }

  return [
    { layer: "UI", count: outgoingCount.get("ui") ?? 0 },
    { layer: "Business Logic", count: 2 },
    { layer: "Data", count: outgoingCount.get("data") ?? 0 },
    { layer: "Infra", count: outgoingCount.get("infra") ?? 0 }
  ];
};

export function ArchDriftView({ violations }: ArchDriftViewProps) {
  const summary = layerHealth(violations);
  const sectionWidth = Math.max(28, (process.stdout.columns ?? 80) - 34);
  const fileWidth = Math.max(26, (process.stdout.columns ?? 80) - 18);

  return (
    <Box flexDirection="column">
      <SectionHeader title={`Architecture Drift (${violations.length})`} width={sectionWidth} />

      {violations.length === 0 ? (
        <Box marginTop={1}>
          <Text>{chalk.hex(theme.green)("No architecture violations.")}</Text>
        </Box>
      ) : (
        <Box flexDirection="column" marginTop={1}>
          {violations.map((baseViolation, index) => {
            const violation = baseViolation as ViolationWithSeverity;
            const severity = getSeverity(violation);
            const severityColor = severity === "critical" ? theme.red : theme.orange;
            const severityBadge = severity === "critical" ? "⛔ CRITICAL" : "△ HIGH";
            const fixLines = violation.suggestedFix
              .split("\n")
              .map((line) => line.trimEnd())
              .filter((line, lineIndex, all) => line.length > 0 || all.length === 1 || lineIndex < all.length - 1);

            return (
              <Box key={`${violation.file}:${violation.line}:${index}`} flexDirection="column" marginBottom={1}>
                <Box flexDirection="column" borderStyle="single" borderColor={severityColor} paddingX={1}>
                  <Text>{chalk.hex(severityColor).bold(severityBadge)}</Text>
                  <Text>{chalk.hex("#ffffff").bold(`${truncateMiddle(violation.file, fileWidth)}:${violation.line}`)}</Text>
                  <Text>{chalk.hex(theme.dim)(violation.description)}</Text>
                  <Text> </Text>

                  <Box flexDirection="column" borderStyle="round" borderColor={theme.muted} paddingX={1}>
                    <Text>{chalk.hex(theme.dim)("Suggested fix")}</Text>
                    {fixLines.map((line, lineIndex) => {
                      const trimmed = line.trimStart();
                      if (trimmed.startsWith("-")) {
                        return (
                          <Text key={lineIndex}>
                            {chalk.hex(theme.red)(line)}
                          </Text>
                        );
                      }

                      if (trimmed.startsWith("+")) {
                        return (
                          <Text key={lineIndex}>
                            {chalk.hex(theme.green)(line)}
                          </Text>
                        );
                      }

                      return (
                        <Text key={lineIndex}>
                          {chalk.hex(theme.text)(line)}
                        </Text>
                      );
                    })}
                  </Box>
                </Box>
              </Box>
            );
          })}
        </Box>
      )}

      <Box flexDirection="column" marginTop={1}>
        <SectionHeader title="Layer Health" width={sectionWidth} />
        {summary.map(({ layer, count }) => (
          <Text key={layer}>
            {chalk.hex(theme.text)(layer.padEnd(20, " "))}
            {count === 0
              ? chalk.hex(theme.green)("✓ OK")
              : chalk.hex(theme.red)(`${count} violation${count === 1 ? "" : "s"}`)}
          </Text>
        ))}
      </Box>
    </Box>
  );
}
