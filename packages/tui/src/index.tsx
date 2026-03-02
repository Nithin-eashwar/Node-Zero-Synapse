import React, { useCallback, useEffect, useRef, useState } from "react";
import { Box, Text, render, useInput, useStdout } from "ink";
import TextInput from "ink-text-input";
import chalk from "chalk";
import type { ArchViolation, BlastRadiusResult, MentorMessage, SmartBlameResult } from "@nzs/core";
import { ArchDriftView } from "./views/ArchDriftView.js";
import { BlastRadiusView } from "./views/BlastRadiusView.js";
import { MentorView } from "./views/MentorView.js";
import { SmartBlameView } from "./views/SmartBlameView.js";
import { theme } from "./theme.js";
import { fitLine, repeatChar, truncateEnd } from "./components/format.js";
import { riskColor, riskLabel, type UiRiskLevel } from "./components/visual.js";
import {
  fetchBlastRadius,
  fetchSmartBlame,
  fetchArchDrift,
  fetchMentorAsk,
  isTuiError,
} from "./services/api.js";

type View = "blast-radius" | "smart-blame" | "mentor" | "arch-drift";
type RiskLevel = "low" | "medium" | "high" | "critical";

/** Per-view async state: loading flag, last error, last successful data. */
interface ViewState<T> {
  loading: boolean;
  error: string | null;
  data: T | null;
}

const NAV_ITEMS: Array<{ key: View; label: string }> = [
  { key: "blast-radius", label: "Blast Radius" },
  { key: "smart-blame", label: "Smart Blame" },
  { key: "mentor", label: "Mentor" },
  { key: "arch-drift", label: "Arch Drift" }
];

const MENTOR_WELCOME: MentorMessage[] = [
  {
    role: "assistant",
    content: "I can help with this repo. Ask anything about architecture, refactors, or risk.",
    timestamp: new Date().toISOString(),
  },
];

const getRiskLevelForView = (view: View): RiskLevel => {
  switch (view) {
    case "blast-radius":
      return "high";
    case "smart-blame":
      return "medium";
    case "mentor":
      return "low";
    case "arch-drift":
      return "critical";
  }
};

const formatViewLabel = (view: View): string =>
  view
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

const getCommandHint = (view: View): string => {
  switch (view) {
    case "blast-radius":
      return "<function_name> · blast radius target";
    case "smart-blame":
      return "<file_path> · file to analyse";
    case "mentor":
      return ":patterns · :notes";
    case "arch-drift":
      return "--scan · :override";
  }
};

const getViewGlyph = (view: View): string => {
  switch (view) {
    case "blast-radius":
      return "◈";
    case "smart-blame":
      return "◎";
    case "mentor":
      return "⊕";
    case "arch-drift":
      return "⬡";
  }
};

const statusBackground = (risk: RiskLevel): string => {
  if (risk === "high" || risk === "critical") {
    return "#2d0a0f";
  }

  if (risk === "medium") {
    return "#1a1000";
  }

  return "#001a0d";
};

// ---------------------------------------------------------------------------
// Inline error banner shown when a fetch fails
// ---------------------------------------------------------------------------

function ErrorBanner({ message }: { message: string }) {
  return (
    <Box marginBottom={1}>
      <Text>
        {chalk.bgHex("#2d0a0f").hex(theme.red).bold(" ERROR ")}
        {chalk.hex(theme.dim)(` ${message}`)}
        {chalk.hex(theme.dim)("  (data below may be stale — retry with Enter)")}
      </Text>
    </Box>
  );
}

function EmptyState({ view }: { view: View }) {
  return (
    <Box flexDirection="column">
      <Text>{chalk.hex(theme.dim)(`No data loaded for ${formatViewLabel(view)}.`)}</Text>
      <Text>{chalk.hex(theme.dim)("Enter a query in the command bar or press Enter to fetch.")}</Text>
    </Box>
  );
}

function LoadingIndicator() {
  return <Text>{chalk.hex(theme.accent)("Loading...")}</Text>;
}

// ---------------------------------------------------------------------------
// Presentational components (unchanged from original)
// ---------------------------------------------------------------------------

function StatusBar({ currentView, width }: { currentView: View; width: number }) {
  const riskLevel = getRiskLevelForView(currentView);
  const bg = chalk.bgHex(statusBackground(riskLevel));
  const versionText = "synapse v0.1.0";
  const riskText = ` ⬤ ${riskLabel(riskLevel as UiRiskLevel)} `;
  const contextWidth = Math.max(0, width - 2 - versionText.length - riskText.length - 1);
  const leftContext = truncateEnd(`${formatViewLabel(currentView)} view`, contextWidth);

  return (
    <Box height={1} width={width} flexDirection="row" paddingX={1}>
      <Text>
        {bg.hex(riskColor(riskLevel as UiRiskLevel)).bold(riskText)}
        {chalk.hex(theme.dim)(` ${leftContext}`)}
      </Text>
      <Box flexGrow={1} />
      <Text>{chalk.hex(theme.dim)(versionText)}</Text>
    </Box>
  );
}

function Sidebar({
  items,
  selectedIndex,
  currentView,
  width,
  archViolationCount
}: {
  items: Array<{ key: View; label: string }>;
  selectedIndex: number;
  currentView: View;
  width: number;
  archViolationCount: number;
}) {
  const contentWidth = Math.max(0, width - 2);
  const badgeSlotWidth = 6;

  return (
    <Box borderStyle="single" borderColor={theme.muted} flexDirection="column" width={width}>
      <Text>{chalk.hex(theme.accent).bold(fitLine(" ◈ SYNAPSE", contentWidth))}</Text>
      <Text>{chalk.hex(theme.dim)(fitLine(` ${repeatChar("─", Math.max(0, width - 3))}`, contentWidth))}</Text>

      {items.map((item, index) => {
        const isCursor = index === selectedIndex;
        const isActive = item.key === currentView;
        const glyph = getViewGlyph(item.key);
        const showBadge = item.key === "arch-drift" && archViolationCount > 0;
        const badgeText = showBadge ? `[${archViolationCount}]` : "";
        const labelWidth = Math.max(0, contentWidth - (showBadge ? badgeSlotWidth : 0));
        const rowText = fitLine(`${isActive ? "▶" : " "} ${glyph} ${item.label}`, labelWidth);

        const baseColor = isActive ? theme.accent : isCursor ? theme.text : theme.dim;
        const labelStyled = isActive
          ? chalk.bgHex("#0d2137")(chalk.hex(baseColor)(rowText))
          : chalk.hex(baseColor)(rowText);

        return (
          <Box key={item.key} width={contentWidth} flexDirection="row">
            <Box width={labelWidth}>
              <Text>{labelStyled}</Text>
            </Box>
            {showBadge ? (
              <Box width={badgeSlotWidth} justifyContent="flex-end">
                <Text>{chalk.bgHex(theme.red).hex("#000000").bold(badgeText)}</Text>
              </Box>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );
}

function MainPanel({
  currentView,
  blastState,
  blameState,
  driftState,
  mentorMessages,
  onMentorSend,
}: {
  currentView: View;
  blastState: ViewState<BlastRadiusResult>;
  blameState: ViewState<SmartBlameResult>;
  driftState: ViewState<ArchViolation[]>;
  mentorMessages: MentorMessage[];
  onMentorSend: (text: string) => void;
}) {
  const panelTitle = formatViewLabel(currentView);
  let content: React.ReactNode;

  if (currentView === "blast-radius") {
    const s = blastState;
    content = (
      <>
        {s.error ? <ErrorBanner message={s.error} /> : null}
        {s.loading && !s.data ? <LoadingIndicator /> : null}
        {s.data ? <BlastRadiusView result={s.data} /> : !s.loading ? <EmptyState view={currentView} /> : null}
      </>
    );
  } else if (currentView === "smart-blame") {
    const s = blameState;
    content = (
      <>
        {s.error ? <ErrorBanner message={s.error} /> : null}
        {s.loading && !s.data ? <LoadingIndicator /> : null}
        {s.data ? <SmartBlameView result={s.data} /> : !s.loading ? <EmptyState view={currentView} /> : null}
      </>
    );
  } else if (currentView === "mentor") {
    content = <MentorView messages={mentorMessages} onSend={onMentorSend} />;
  } else if (currentView === "arch-drift") {
    const s = driftState;
    content = (
      <>
        {s.error ? <ErrorBanner message={s.error} /> : null}
        {s.loading && !s.data ? <LoadingIndicator /> : null}
        {s.data ? <ArchDriftView violations={s.data} /> : !s.loading ? <EmptyState view={currentView} /> : null}
      </>
    );
  } else {
    content = (
      <>
        <Text>{chalk.hex(theme.text)("Content area")}</Text>
        <Text>{chalk.hex(theme.text)("Select nav with Up/Down")}</Text>
        <Text>{chalk.hex(theme.text)("Press Enter to switch view")}</Text>
      </>
    );
  }

  return (
    <Box flexDirection="column" flexGrow={1} paddingLeft={1}>
      <Box
        flexDirection="column"
        borderStyle="single"
        borderColor={theme.muted}
        flexGrow={1}
        paddingX={1}
        overflow="hidden"
      >
        <Text>{chalk.hex(theme.dim)(panelTitle)}</Text>
        <Box flexDirection="column" flexGrow={1} overflow="hidden">
          {content}
        </Box>
      </Box>
    </Box>
  );
}

function CommandLine({
  currentView,
  value,
  onChange,
  onSubmit
}: {
  currentView: View;
  value: string;
  onChange: (next: string) => void;
  onSubmit: (next: string) => void;
}) {
  const prompt = chalk.hex(theme.accent).bold("synapse ›");
  const hint = value.length === 0 ? getCommandHint(currentView) : "";

  return (
    <Box paddingX={1}>
      <Text>{`${prompt} `}</Text>
      <TextInput value={value} onChange={onChange} onSubmit={onSubmit} />
      {hint ? <Text dimColor wrap="truncate-end">{` ${hint}`}</Text> : null}
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Layout — wires view state and fetch lifecycle
// ---------------------------------------------------------------------------

function Layout() {
  const [currentView, setCurrentView] = useState<View>("blast-radius");
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [command, setCommand] = useState<string>("");

  // Per-view async state
  const [blastState, setBlastState] = useState<ViewState<BlastRadiusResult>>({ loading: false, error: null, data: null });
  const [blameState, setBlameState] = useState<ViewState<SmartBlameResult>>({ loading: false, error: null, data: null });
  const [driftState, setDriftState] = useState<ViewState<ArchViolation[]>>({ loading: false, error: null, data: null });
  const [mentorMessages, setMentorMessages] = useState<MentorMessage[]>(MENTOR_WELCOME);

  // Track last query per view so command bar refetches with context
  const lastBlastTarget = useRef<string>("");
  const lastBlameFile = useRef<string>("");

  const { stdout } = useStdout();
  const stdoutWidth = stdout?.columns ?? 80;
  const stdoutHeight = stdout?.rows ?? 24;
  const layoutWidth = Math.max(40, stdoutWidth);
  const layoutHeight = Math.max(16, stdoutHeight);

  // --- Fetch helpers (no-throw, update view state) ---

  const doFetchBlastRadius = useCallback(async (target: string) => {
    if (!target) return;
    lastBlastTarget.current = target;
    setBlastState((prev) => ({ ...prev, loading: true, error: null }));
    const res = await fetchBlastRadius(target);
    if (isTuiError(res)) {
      setBlastState((prev) => ({ ...prev, loading: false, error: res.error.message }));
    } else {
      setBlastState({ loading: false, error: null, data: res });
    }
  }, []);

  const doFetchSmartBlame = useCallback(async (filePath: string) => {
    if (!filePath) return;
    lastBlameFile.current = filePath;
    setBlameState((prev) => ({ ...prev, loading: true, error: null }));
    const res = await fetchSmartBlame(filePath);
    if (isTuiError(res)) {
      setBlameState((prev) => ({ ...prev, loading: false, error: res.error.message }));
    } else {
      setBlameState({ loading: false, error: null, data: res });
    }
  }, []);

  const doFetchArchDrift = useCallback(async () => {
    setDriftState((prev) => ({ ...prev, loading: true, error: null }));
    const res = await fetchArchDrift();
    if (isTuiError(res)) {
      setDriftState((prev) => ({ ...prev, loading: false, error: res.error.message }));
    } else {
      // The endpoint returns ArchViolation[] directly (or error envelope)
      const violations = Array.isArray(res) ? res : [];
      setDriftState({ loading: false, error: null, data: violations });
    }
  }, []);

  const doMentorAsk = useCallback(async (query: string) => {
    const userMessage: MentorMessage = {
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };
    setMentorMessages((prev) => [...prev, userMessage]);

    const res = await fetchMentorAsk(query);
    let answer: string;
    if (isTuiError(res)) {
      answer = `[Backend unavailable] ${res.error.message}`;
    } else {
      answer = res.answer;
    }

    const assistantReply: MentorMessage = {
      role: "assistant",
      content: answer,
      timestamp: new Date().toISOString(),
    };
    setMentorMessages((prev) => [...prev, assistantReply]);
  }, []);

  // --- Fetch on initial mount for arch-drift (no params needed) ---
  useEffect(() => {
    void doFetchArchDrift();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Fetch on view switch ---
  const handleViewChange = useCallback(
    (view: View) => {
      setCurrentView(view);
      // Trigger fetch for the newly active view
      switch (view) {
        case "blast-radius":
          if (lastBlastTarget.current) {
            void doFetchBlastRadius(lastBlastTarget.current);
          }
          break;
        case "smart-blame":
          if (lastBlameFile.current) {
            void doFetchSmartBlame(lastBlameFile.current);
          }
          break;
        case "arch-drift":
          void doFetchArchDrift();
          break;
        // mentor: no auto-fetch
      }
    },
    [doFetchBlastRadius, doFetchSmartBlame, doFetchArchDrift],
  );

  // --- Command submit: parse target for active view and fetch ---
  const handleCommandSubmit = useCallback(
    (raw: string) => {
      const text = raw.trim();
      setCommand("");
      if (!text) {
        // Re-fetch current view with last known params
        handleViewChange(currentView);
        return;
      }

      switch (currentView) {
        case "blast-radius":
          void doFetchBlastRadius(text);
          break;
        case "smart-blame":
          void doFetchSmartBlame(text);
          break;
        case "arch-drift":
          void doFetchArchDrift();
          break;
        case "mentor":
          void doMentorAsk(text);
          break;
      }
    },
    [currentView, handleViewChange, doFetchBlastRadius, doFetchSmartBlame, doFetchArchDrift, doMentorAsk],
  );

  useInput((_input, key) => {
    if (key.upArrow) {
      const nextIndex = (selectedIndex - 1 + NAV_ITEMS.length) % NAV_ITEMS.length;
      setSelectedIndex(nextIndex);
      handleViewChange(NAV_ITEMS[nextIndex]?.key ?? "blast-radius");
      return;
    }

    if (key.downArrow) {
      const nextIndex = (selectedIndex + 1) % NAV_ITEMS.length;
      setSelectedIndex(nextIndex);
      handleViewChange(NAV_ITEMS[nextIndex]?.key ?? "blast-radius");
      return;
    }

    if (key.return) {
      handleViewChange(NAV_ITEMS[selectedIndex]?.key ?? "blast-radius");
    }
  });

  const archViolationCount = driftState.data?.length ?? 0;

  return (
    <Box flexDirection="column" width={layoutWidth} height={layoutHeight} overflow="hidden">
      <StatusBar currentView={currentView} width={layoutWidth} />
      <Text>{chalk.hex(theme.muted)(`├${repeatChar("─", layoutWidth - 1)}`)}</Text>

      <Box flexDirection="row" flexGrow={1} overflow="hidden">
        <Sidebar
          items={NAV_ITEMS}
          selectedIndex={selectedIndex}
          currentView={currentView}
          width={26}
          archViolationCount={archViolationCount}
        />
        <MainPanel
          currentView={currentView}
          blastState={blastState}
          blameState={blameState}
          driftState={driftState}
          mentorMessages={mentorMessages}
          onMentorSend={doMentorAsk}
        />
      </Box>

      <Text>{chalk.hex(theme.muted)(`├${repeatChar("─", layoutWidth - 1)}`)}</Text>
      {/* Hide bottom command line on Mentor view — MentorView has its own composer */}
      {currentView !== "mentor" ? (
        <CommandLine
          currentView={currentView}
          value={command}
          onChange={setCommand}
          onSubmit={handleCommandSubmit}
        />
      ) : (
        <Box paddingX={1}>
          <Text>{chalk.hex(theme.dim)("synapse ›   :patterns · :notes")}</Text>
        </Box>
      )}
    </Box>
  );
}

render(<Layout />);
