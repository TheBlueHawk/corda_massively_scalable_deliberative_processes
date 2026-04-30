import type React from "react";

type MarkdownSummaryProps = {
  content: string;
};

function renderInline(text: string): React.ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export function MarkdownSummary({ content }: MarkdownSummaryProps) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (listItems.length === 0) {
      return;
    }
    elements.push(
      <ul key={`list-${elements.length}`}>
        {listItems.map((item, index) => (
          <li key={`${item}-${index}`}>{renderInline(item)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushList();
      return;
    }
    if (trimmed.startsWith("- ")) {
      listItems.push(trimmed.slice(2));
      return;
    }

    flushList();
    if (trimmed.startsWith("## ")) {
      elements.push(<h3 key={`h3-${index}`}>{renderInline(trimmed.slice(3))}</h3>);
      return;
    }
    if (trimmed.startsWith("# ")) {
      elements.push(<h2 key={`h2-${index}`}>{renderInline(trimmed.slice(2))}</h2>);
      return;
    }
    elements.push(<p key={`p-${index}`}>{renderInline(trimmed)}</p>);
  });

  flushList();

  return <div className="markdown-summary">{elements}</div>;
}
