declare global {
  interface Window {
    toast: (message: string) => void;
    copyListToClipboard: (list: HTMLUListElement) => void;
  }
}

export function toast(message: string) {
  const template = document.querySelector(
    "#toast-template"
  ) as HTMLTemplateElement;
  const clone = template.content.cloneNode(true) as HTMLDivElement;
  const textElement = clone.querySelector(".toast-text") as HTMLDivElement;
  textElement.innerHTML = message;
  const toastElement = clone.querySelector(".toast") as HTMLDivElement;
  const container = document.querySelector(
    "#toast-container"
  ) as HTMLDivElement;
  container.appendChild(toastElement);
  window.bootstrap.Toast.getOrCreateInstance(toastElement).show();
  toastElement.addEventListener("hidden.bs.toast", () => {
    container.removeChild(toastElement);
  });
}

export function copyListToClipboard(list: HTMLUListElement) {
  navigator.clipboard.write([
    new ClipboardItem({
      "text/html": list.outerHTML,
      "text/plain": Array.from(list.children)
        .map((item) => item.textContent!.trim())
        .join("\n"),
    }),
  ]);
}

window.toast = toast;
window.copyListToClipboard = copyListToClipboard;
