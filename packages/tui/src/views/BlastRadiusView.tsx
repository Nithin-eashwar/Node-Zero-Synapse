import { Box, Text } from "ink";
import chalk from "chalk";
import type { BlastRadiusResult, DependencyNode } from "@nzs/core";
import { SectionHeader } from "../components/SectionHeader.js";
import { padCell, truncateMiddle } from "../components/format.js";
import { barFill, riskColor, riskDot, scoreColor } from "../components/visual.js";
import { theme } from "../theme.js";

type BlastRadiusViewProps = {
  result: BlastRadiusResult;
};

/** Display limits to prevent OOM on large graphs */
const MAX_CHANGED_FILES = 20;
const MAX_NODES_PER_FILE = 8;
const MAX_TREE_DEPTH = 3;
const MAX_EDGES_DISPLAYED = 30;

type TreeNodeProps = {
  node: DependencyNode;
  isLast: boolean;
  depth: number;
  branchMask: boolean[];
  nodeNameWidth: number;
  lineWidth: number;
  childrenById: Map<string, DependencyNode[]>;
  ancestorIds: Set<string>;
};

type ScoreSignal = {
  label: string;
  score: number;
};

const SCORE_SIGNALS: ScoreSignal[] = [
  { label: "Test coverage gap", score: 85 },
  { label: "Dependency spread", score: 78 },
  { label: "Legacy coupling", score: 52 }
];

const riskText = (risk: DependencyNode["riskLevel"]): string => {
  if (risk === "high") {
    return "HIGH";
  }

  if (risk === "medium") {
    return "MED";
  }

  return "LOW";
};

const renderScoreLine = ({ label, score }: ScoreSignal): string => {
  const bar = barFill(score, 20);
  const labelText = padCell(label, 21);
  const scoreText = padCell(String(score), 3);
  const color = scoreColor(score);

  return `${chalk.hex(theme.text)(labelText)}${chalk.hex(color)(bar)}  ${chalk.hex(color)(scoreText)}`;
};

const renderNodeLine = (
  prefix: string,
  connector: "├──" | "└──",
  node: DependencyNode,
  nodeNameWidth: number,
): string => {
  const color = riskColor(node.riskLevel);
  const label = riskText(node.riskLevel);
  const name = truncateMiddle(node.name, nodeNameWidth);
  return `${prefix}${connector} ${chalk.hex(color)(riskDot(node.riskLevel))} ${chalk.hex(theme.text)(name)} ${chalk.hex(color)(label)} ${chalk.hex(theme.dim)(`(${node.refCount} refs)`)}`;
};

function TreeNode({
  node,
  isLast,
  depth,
  branchMask,
  nodeNameWidth,
  lineWidth,
  childrenById,
  ancestorIds
}: TreeNodeProps) {
  const prefix = branchMask.map((hasSibling) => (hasSibling ? "│   " : "    ")).join("");
  const connector = isLast ? "└──" : "├──";

  // Stop recursion at depth limit
  if (depth >= MAX_TREE_DEPTH) {
    const childCount = (childrenById.get(node.id) ?? []).length;
    const suffix = childCount > 0 ? chalk.hex(theme.dim)(` (+${childCount} more…)`) : "";
    return (
      <Box flexDirection="column">
        <Text wrap="truncate-end">{truncateMiddle(renderNodeLine(prefix, connector, node, nodeNameWidth), lineWidth)}{suffix}</Text>
      </Box>
    );
  }

  const childNodes = (childrenById.get(node.id) ?? []).filter((child) => !ancestorIds.has(child.id));
  const nextAncestorIds = new Set(ancestorIds);
  nextAncestorIds.add(node.id);

  return (
    <Box flexDirection="column">
      <Text wrap="truncate-end">{truncateMiddle(renderNodeLine(prefix, connector, node, nodeNameWidth), lineWidth)}</Text>
      {childNodes.map((childNode, index) => (
        <TreeNode
          key={`${node.id}-${childNode.id}-${index}`}
          node={childNode}
          isLast={index === childNodes.length - 1}
          depth={depth + 1}
          branchMask={[...branchMask, !isLast]}
          nodeNameWidth={nodeNameWidth}
          lineWidth={lineWidth}
          childrenById={childrenById}
          ancestorIds={nextAncestorIds}
        />
      ))}
    </Box>
  );
}

export function BlastRadiusView({ result }: BlastRadiusViewProps) {
  const nodesById = new Map(result.nodes.map((node) => [node.id, node]));
  const nodesByFilepath = new Map<string, DependencyNode[]>();
  const childrenById = new Map<string, DependencyNode[]>();
  const sectionWidth = Math.max(28, (process.stdout.columns ?? 80) - 34);
  const fileWidth = Math.max(24, (process.stdout.columns ?? 80) - 32);
  const nodeNameWidth = Math.max(16, Math.min(36, sectionWidth - 22));
  const lineWidth = Math.max(28, sectionWidth - 2);
  const edgeEntityWidth = Math.max(12, Math.floor((lineWidth - 14) / 2));

  for (const node of result.nodes) {
    const fileNodes = nodesByFilepath.get(node.filepath) ?? [];
    fileNodes.push(node);
    nodesByFilepath.set(node.filepath, fileNodes);
  }

  for (const edge of result.edges) {
    const sourceNode = nodesById.get(edge.sourceId);
    const targetNode = nodesById.get(edge.targetId);
    if (!sourceNode || !targetNode) {
      continue;
    }

    const childNodes = childrenById.get(sourceNode.id) ?? [];
    childNodes.push(targetNode);
    childrenById.set(sourceNode.id, childNodes);
  }

  const displayedFiles = result.changedFiles.slice(0, MAX_CHANGED_FILES);
  const hiddenFileCount = result.changedFiles.length - displayedFiles.length;
  const displayedEdges = result.edges.slice(0, MAX_EDGES_DISPLAYED);
  const hiddenEdgeCount = result.edges.length - displayedEdges.length;

  return (
    <Box flexDirection="column">
      <SectionHeader title={`Changed Files (${result.changedFiles.length})`} width={sectionWidth} />
      {displayedFiles.length > 0 ? (
        <>
          {displayedFiles.map((file) => (
            <Text key={file} wrap="truncate-end">{chalk.hex(theme.text)(`- ${truncateMiddle(file, fileWidth)}`)}</Text>
          ))}
          {hiddenFileCount > 0 ? (
            <Text dimColor wrap="truncate-end">{`  ... and ${hiddenFileCount} more files`}</Text>
          ) : null}
        </>
      ) : (
        <Text dimColor wrap="truncate-end">- none</Text>
      )}

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title={`Impacted Nodes (${result.nodes.length})`} width={sectionWidth} />
        {displayedFiles.length > 0 ? (
          displayedFiles.map((file) => {
            const allRootNodes = nodesByFilepath.get(file) ?? [];
            const rootNodes = allRootNodes.slice(0, MAX_NODES_PER_FILE);
            const hiddenNodeCount = allRootNodes.length - rootNodes.length;

            return (
              <Box key={file} flexDirection="column" marginBottom={1}>
                <Text wrap="truncate-end">{chalk.hex(theme.muted)(truncateMiddle(file, fileWidth))}</Text>
                {rootNodes.length > 0 ? (
                  <>
                    {rootNodes.map((node, index) => (
                      <TreeNode
                        key={`${file}-${node.id}-${index}`}
                        node={node}
                        isLast={index === rootNodes.length - 1 && hiddenNodeCount === 0}
                        depth={0}
                        branchMask={[]}
                        nodeNameWidth={nodeNameWidth}
                        lineWidth={lineWidth}
                        childrenById={childrenById}
                        ancestorIds={new Set<string>()}
                      />
                    ))}
                    {hiddenNodeCount > 0 ? (
                      <Text dimColor wrap="truncate-end">{`    ... and ${hiddenNodeCount} more nodes in this file`}</Text>
                    ) : null}
                  </>
                ) : (
                  <Text dimColor wrap="truncate-end">- none</Text>
                )}
              </Box>
            );
          })
        ) : (
          <Text dimColor wrap="truncate-end">- none</Text>
        )}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title="Risk Signals" width={sectionWidth} />
        {SCORE_SIGNALS.map((signal) => (
          <Text key={signal.label}>{renderScoreLine(signal)}</Text>
        ))}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title={`Edges (${result.edges.length})`} width={sectionWidth} />
        {displayedEdges.length > 0 ? (
          <>
            {displayedEdges.map((edge, index) => (
              <Text key={`${edge.sourceId}-${edge.targetId}-${index}`} wrap="truncate-end">
                {chalk.hex(theme.text)(`- ${truncateMiddle(edge.sourceId, edgeEntityWidth)} -> ${truncateMiddle(edge.targetId, edgeEntityWidth)} (${edge.degrees} hops)`)}
              </Text>
            ))}
            {hiddenEdgeCount > 0 ? (
              <Text dimColor wrap="truncate-end">{`  ... and ${hiddenEdgeCount} more edges`}</Text>
            ) : null}
          </>
        ) : (
          <Text dimColor wrap="truncate-end">- none</Text>
        )}
      </Box>

      <Box marginTop={1} flexDirection="column">
        <SectionHeader title={`Warnings (${result.warnings.length})`} width={sectionWidth} />
        {result.warnings.length > 0 ? (
          result.warnings.map((warning, index) => (
            <Text key={`${warning}-${index}`} wrap="truncate-end">{chalk.hex(theme.yellow)(`- ${warning}`)}</Text>
          ))
        ) : (
          <Text wrap="truncate-end">{chalk.hex(theme.green)("- no warnings")}</Text>
        )}
      </Box>
    </Box>
  );
}
