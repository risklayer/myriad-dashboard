function toast(text) {
  const template = document.querySelector("#toast-template");
  const clone = template.content.cloneNode(true);
  const textElement = clone.querySelector(".toast-text");
  textElement.innerHTML = text;
  const toastElement = clone.querySelector(".toast");
  const container = document.querySelector("#toast-container");
  container.appendChild(toastElement);
  bootstrap.Toast.getOrCreateInstance(toastElement).show();
  toastElement.addEventListener("hidden.bs.toast", () => {
    container.removeChild(toastElement);
  });
}
