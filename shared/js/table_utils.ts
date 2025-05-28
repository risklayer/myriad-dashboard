import { uniq } from "lodash";

export function createDataTableReferencesButton(references?: string[]) {
  if (!references?.length) {
    return null;
  }
  return {
    text: "References",
    attr: {
      "data-bs-toggle": "popover",
    },
    action: async (event: MouseEvent) => {
      const referencesTemplate = (await import("./reference_list.jst")).default;
      const button = event.currentTarget as HTMLButtonElement;
      const contentString = referencesTemplate({
        references: uniq(references).sort(),
      });
      const content = document.createElement("div");
      content.innerHTML = contentString;
      const popover = window.bootstrap.Popover.getOrCreateInstance(button, {
        title: "References",
        content,
        html: true,
      });
      popover.show();
    },
  };
}
