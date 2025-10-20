document.addEventListener('DOMContentLoaded', function () {
  // Find all pre code blocks
  const codeBlocks = document.querySelectorAll('pre');
  const PREVIEW_LINES = 15; // Number of lines to show in preview
  const MIN_LINES_TO_COLLAPSE = 15; // Minimum number of lines required to collapse

  const style = document.createElement('style');
  style.textContent = `
    .code-truncated {
      max-height: 375px; /* Approximately 15 lines */
      overflow: hidden;
    }
    .code-expand-button {
      width: 100%;
      background: #f5f5f5;
      border: none;
      border-top: 1px solid #ddd;
      padding: 8px;
      text-align: center;
      cursor: pointer;
      color: #666;
      font-size: 0.9em;
    }
    .code-expand-button:hover {
      background: #e5e5e5;
    }
    .code-expand-button span {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 4px;
    }
  `;
  document.head.appendChild(style);

  codeBlocks.forEach(function (block) {
    const codeLines = block.textContent.trim().split('\n');
    const totalLines = codeLines.length;

    if (totalLines >= MIN_LINES_TO_COLLAPSE) {
      // Add truncation class
      block.classList.add('code-truncated');

      // Create proper button element with accessibility attributes
      const expandButton = document.createElement('button');
      expandButton.className = 'code-expand-button';
      expandButton.setAttribute('aria-expanded', 'false');
      expandButton.setAttribute('aria-label', `Show ${totalLines - PREVIEW_LINES} more lines of code`);
      const spanElement = document.createElement('span');
      spanElement.textContent = `${totalLines - PREVIEW_LINES} more lines - Click to expand`;
      expandButton.appendChild(spanElement);

      // Add the button after the code block
      block.parentNode.insertBefore(expandButton, block.nextSibling);

      // Add click handler
      expandButton.addEventListener('click', function () {
        block.classList.remove('code-truncated');
        expandButton.setAttribute('aria-expanded', 'true');
        expandButton.style.display = 'none';
      });
    }
  });
});
