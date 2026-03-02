export const repeatChar = (char: string, length: number): string => {
  const safeLength = Math.max(0, length);
  return char.repeat(safeLength);
};

export const fitLine = (text: string, width: number): string => {
  const safeWidth = Math.max(0, width);
  return text.length >= safeWidth ? text.slice(0, safeWidth) : text.padEnd(safeWidth, " ");
};

export const truncateEnd = (text: string, width: number): string => {
  const safeWidth = Math.max(0, width);
  if (safeWidth === 0) {
    return "";
  }

  if (text.length <= safeWidth) {
    return text;
  }

  if (safeWidth === 1) {
    return "…";
  }

  return `${text.slice(0, safeWidth - 1)}…`;
};

export const truncateMiddle = (text: string, width: number): string => {
  const safeWidth = Math.max(0, width);
  if (safeWidth === 0) {
    return "";
  }

  if (text.length <= safeWidth) {
    return text;
  }

  if (safeWidth <= 2) {
    return truncateEnd(text, safeWidth);
  }

  const head = Math.ceil((safeWidth - 1) / 2);
  const tail = Math.floor((safeWidth - 1) / 2);
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
};

export const padCell = (text: string, width: number): string => {
  const value = truncateEnd(text, width);
  return value.padEnd(Math.max(0, width), " ");
};
