import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

const css = readFileSync(resolve(__dirname, "../app/globals.css"), "utf-8");

const longTitles = [
  "What do you think is needed to end the Russia/Ukraine war?",
  "Rent Caps: Solution or Barrier to Affordable Housing?",
  "Should cities restrict private cars in downtown areas?",
];

function renderHtml(): string {
  const slides = longTitles
    .map(
      (title, index) => `
        <a class="topic-slide ${index === 0 ? "topic-slide-featured" : ""}" href="#">
          <span class="topic-status">Results available</span>
          <h3>${title}</h3>
          <p>A structured public deliberation summarized after closure.</p>
          <span class="topic-date">Closed May 4, 2026, 11:00 AM</span>
        </a>
      `,
    )
    .join("");
  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>${css}</style>
  </head>
  <body>
    <main class="shell home-shell">
      <section class="topic-rail-section">
        <div class="topic-rail">${slides}</div>
      </section>
    </main>
  </body>
</html>`;
}

test("topic-slide titles never overflow horizontally", async ({ page }) => {
  await page.setContent(renderHtml());
  const overflows = await page.$$eval(".topic-slide h3", (nodes) =>
    nodes.map((node) => ({
      text: node.textContent ?? "",
      scrollWidth: node.scrollWidth,
      clientWidth: node.clientWidth,
    })),
  );
  expect(overflows.length).toBeGreaterThan(0);
  for (const item of overflows) {
    expect(item.scrollWidth, `"${item.text.slice(0, 40)}" overflows`).toBeLessThanOrEqual(
      item.clientWidth + 1,
    );
  }
});

test("first topic card stays within the viewport", async ({ page }) => {
  await page.setContent(renderHtml());
  const firstCardLeft = await page.$eval(".topic-slide:first-child", (node) => {
    return node.getBoundingClientRect().left;
  });
  expect(firstCardLeft).toBeGreaterThanOrEqual(0);
});
