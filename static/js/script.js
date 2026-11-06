(() => {
  const form = document.getElementById("qr-form");
  const input = document.getElementById("url-input");
  const protocolSelect = document.getElementById("protocol-select");
  const generateButton = document.getElementById("generate-button");
  const clearButton = document.getElementById("clear-input");
  const errorMessage = document.getElementById("form-error");
  const resultPanel = document.getElementById("result-panel");
  const qrImage = document.getElementById("qr-image");
  const resultUrl = document.getElementById("result-url");
  const downloadButton = document.getElementById("download-button");
  const copyButton = document.getElementById("copy-button");
  const anotherButton = document.getElementById("another-link");

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.hidden = false;
    input.setAttribute("aria-invalid", "true");
  }

  function clearError() {
    errorMessage.textContent = "";
    errorMessage.hidden = true;
    input.removeAttribute("aria-invalid");
  }

  input.addEventListener("input", () => {
    clearButton.hidden = input.value.length === 0;
    if (!errorMessage.hidden) clearError();
  });

  clearButton.addEventListener("click", () => {
    input.value = "";
    clearButton.hidden = true;
    clearError();
    resultPanel.hidden = true;
    input.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearError();
    resultPanel.hidden = true;

    if (!input.value.trim()) {
      showError("Enter a website URL to get started.");
      input.focus();
      return;
    }

    generateButton.disabled = true;
    generateButton.classList.add("is-loading");
    generateButton.setAttribute("aria-busy", "true");

    try {
      const response = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ url: input.value, protocol: protocolSelect.value })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "We couldn’t create that QR code. Please try again.");

      resultUrl.textContent = result.url;
      resultUrl.href = result.url;
      qrImage.src = result.image;
      downloadButton.href = result.download_url;
      copyButton.classList.remove("is-copied");
      copyButton.querySelector("span").textContent = "Copy URL";
      resultPanel.hidden = false;
    } catch (error) {
      showError(error instanceof TypeError
        ? "We couldn’t reach the generator. Check your connection and try again."
        : error.message);
    } finally {
      generateButton.disabled = false;
      generateButton.classList.remove("is-loading");
      generateButton.removeAttribute("aria-busy");
    }
  });

  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(resultUrl.textContent);
      copyButton.classList.add("is-copied");
      copyButton.querySelector("span").textContent = "Copied!";
    } catch {
      showError("Your browser couldn’t copy the URL. Select and copy the link above instead.");
    }
  });

  anotherButton.addEventListener("click", () => {
    resultPanel.hidden = true;
    input.focus();
    input.select();
  });
})();
