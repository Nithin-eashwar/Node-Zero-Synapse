import { useEffect, useMemo, useState } from "react";
import { Box, Text, useInput, useStdout } from "ink";
import TextInput from "ink-text-input";
import chalk from "chalk";
import type { MentorMessage } from "@nzs/core";
import { SectionHeader } from "../components/SectionHeader.js";
import { theme } from "../theme.js";

type MentorViewProps = {
  messages: MentorMessage[];
  onSend: (text: string) => void;
};

type Segment =
  | { type: "text"; value: string }
  | { type: "code"; value: string; language: string };

type RenderedEntry =
  | {
      id: string;
      type: "text";
      text: string;
    }
  | {
      id: string;
      type: "code";
      language: string;
      lines: string[];
    };

const PRIVACY_BANNER = "session private and encrypted";
const ASSISTANT_PREFIX = "synapse › ";
const USER_PREFIX = "    you › ";
const HANGING_INDENT = 10;
const CONTINUATION_PREFIX = " ".repeat(HANGING_INDENT);

const splitCodeBlocks = (content: string): Segment[] => {
  const segments: Segment[] = [];
  const blockPattern = /```([^\n`]*)\n?([\s\S]*?)```/g;
  let cursor = 0;

  for (const match of content.matchAll(blockPattern)) {
    const index = match.index ?? 0;
    if (index > cursor) {
      segments.push({ type: "text", value: content.slice(cursor, index) });
    }

    segments.push({
      type: "code",
      language: (match[1] ?? "").trim(),
      value: match[2] ?? ""
    });
    cursor = index + match[0].length;
  }

  if (cursor < content.length) {
    segments.push({ type: "text", value: content.slice(cursor) });
  }

  return segments.length > 0 ? segments : [{ type: "text", value: content }];
};

const wrapLine = (line: string, width: number): string[] => {
  if (width <= 0) {
    return [""];
  }

  if (line.length <= width) {
    return [line];
  }

  const chunks: string[] = [];
  let rest = line;

  while (rest.length > width) {
    const slice = rest.slice(0, width);
    const breakAt = slice.lastIndexOf(" ");

    if (breakAt <= 0) {
      chunks.push(slice);
      rest = rest.slice(width);
      continue;
    }

    chunks.push(rest.slice(0, breakAt));
    rest = rest.slice(breakAt + 1);
  }

  chunks.push(rest);
  return chunks;
};

const wrapText = (value: string, width: number): string[] =>
  value
    .split("\n")
    .flatMap((line) => wrapLine(line, width));

const toRenderableEntries = (messages: MentorMessage[], width: number): RenderedEntry[] => {
  const entries: RenderedEntry[] = [];

  messages.forEach((message, messageIndex) => {
    const prefix = message.role === "assistant" ? ASSISTANT_PREFIX : USER_PREFIX;
    const styledPrefix = message.role === "assistant" ? chalk.hex(theme.accent).bold(prefix) : chalk.hex(theme.dim)(prefix);
    const bodyWidth = Math.max(1, width - HANGING_INDENT);
    const codeWidth = Math.min(72, Math.max(16, width - HANGING_INDENT - 8));
    const segments = splitCodeBlocks(message.content);

    let hasRenderedFirstLine = false;

    segments.forEach((segment, segmentIndex) => {
      if (segment.type === "code") {
        if (!hasRenderedFirstLine) {
          entries.push({
            id: `${messageIndex}-${segmentIndex}-prefix`,
            type: "text",
            text: styledPrefix
          });
          hasRenderedFirstLine = true;
        }

        const wrappedCode = wrapText(segment.value, codeWidth);
        const codeLines = (wrappedCode.length > 0 ? wrappedCode : [""]).map((line) => line.padEnd(codeWidth, " "));

        entries.push({
          id: `${messageIndex}-${segmentIndex}-code`,
          type: "code",
          language: segment.language,
          lines: codeLines
        });
        return;
      }

      const wrapped = wrapText(segment.value, bodyWidth);
      const lineValues = wrapped.length > 0 ? wrapped : [""];

      lineValues.forEach((lineValue, lineIndex) => {
        const linePrefix = hasRenderedFirstLine ? CONTINUATION_PREFIX : styledPrefix;
        entries.push({
          id: `${messageIndex}-${segmentIndex}-${lineIndex}`,
          type: "text",
          text: `${linePrefix}${chalk.hex(theme.text)(lineValue)}`
        });
        hasRenderedFirstLine = true;
      });
    });
  });

  return entries;
};

const entryHeight = (entry: RenderedEntry): number => {
  if (entry.type === "text") {
    return 1;
  }

  const languageRows = entry.language.length > 0 ? 1 : 0;
  return 2 + languageRows + entry.lines.length;
};

const sliceVisibleEntries = (entries: RenderedEntry[], viewportHeight: number, offset: number): RenderedEntry[] => {
  const totalRows = entries.reduce((sum, entry) => sum + entryHeight(entry), 0);
  const startRow = Math.max(0, totalRows - viewportHeight - offset);
  const endRow = startRow + viewportHeight;

  const visible: RenderedEntry[] = [];
  let rowCursor = 0;

  for (const entry of entries) {
    const nextRow = rowCursor + entryHeight(entry);
    if (nextRow > startRow && rowCursor < endRow) {
      visible.push(entry);
    }

    rowCursor = nextRow;
    if (rowCursor >= endRow) {
      break;
    }
  }

  return visible;
};

export function MentorView({ messages, onSend }: MentorViewProps) {
  const [draft, setDraft] = useState<string>("");
  const [scrollOffset, setScrollOffset] = useState<number>(0);
  const { stdout } = useStdout();
  const width = Math.max(20, stdout?.columns ?? 80);
  const height = Math.max(8, stdout?.rows ?? 24);
  const sectionWidth = Math.max(24, width - 34);

  const renderedEntries = useMemo(() => toRenderableEntries(messages, width), [messages, width]);
  const viewportHeight = Math.max(3, height - 9);
  const totalRows = renderedEntries.reduce((sum, entry) => sum + entryHeight(entry), 0);
  const maxOffset = Math.max(0, totalRows - viewportHeight);
  const clampedOffset = Math.min(scrollOffset, maxOffset);

  useEffect(() => {
    if (scrollOffset !== clampedOffset) {
      setScrollOffset(clampedOffset);
    }
  }, [clampedOffset, scrollOffset]);

  useInput((_input, key) => {
    if (key.pageUp) {
      setScrollOffset((previous) => Math.min(maxOffset, previous + viewportHeight));
      return;
    }

    if (key.pageDown) {
      setScrollOffset((previous) => Math.max(0, previous - viewportHeight));
    }
  });

  const visibleEntries = sliceVisibleEntries(renderedEntries, viewportHeight, clampedOffset);

  return (
    <Box flexDirection="column" flexGrow={1}>
      <SectionHeader title="Mentor Session" width={sectionWidth} />
      <Text>{chalk.hex(theme.dim)(PRIVACY_BANNER)}</Text>

      <Box flexDirection="column" flexGrow={1} marginTop={1}>
        <SectionHeader title="Conversation" width={sectionWidth} />
        {visibleEntries.length > 0 ? (
          visibleEntries.map((entry) => {
            if (entry.type === "text") {
              return <Text key={entry.id}>{entry.text}</Text>;
            }

            return (
              <Box
                key={entry.id}
                marginLeft={HANGING_INDENT}
                marginBottom={1}
                borderStyle="round"
                borderColor={theme.green}
                flexDirection="column"
                paddingX={1}
              >
                {entry.language.length > 0 ? <Text>{chalk.hex(theme.dim)(`[${entry.language}]`)}</Text> : null}
                {entry.lines.map((line, lineIndex) => (
                  <Text key={`${entry.id}-${lineIndex}`}>{chalk.hex(theme.green)(line)}</Text>
                ))}
              </Box>
            );
          })
        ) : (
          <Text dimColor>No mentor messages yet.</Text>
        )}
      </Box>

      <Box marginTop={1}>
        <Text>{clampedOffset > 0 ? chalk.hex(theme.dim)(`scroll ${clampedOffset}/${maxOffset}`) : ""}</Text>
      </Box>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title="Composer" width={sectionWidth} />
        <Box>
          <Text>{chalk.hex(theme.dim)("› ")}</Text>
          <TextInput
            value={draft}
            onChange={setDraft}
            onSubmit={(text) => {
              const trimmed = text.trim();
              if (trimmed.length === 0) {
                setDraft("");
                return;
              }

              onSend(trimmed);
              setDraft("");
              setScrollOffset(0);
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}
