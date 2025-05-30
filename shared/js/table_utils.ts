import { uniq } from "lodash";

/**
 * Creates a button that will open a popup with a list of references.
 * @param references List of reference strings or null
 * @returns array containing a single Datatables.net button config if references
 *          are provided, otherwise an empty array. Use spread operator to add
 *          it to a list of buttons, i.e.:
 * ```ts
 * buttons: [
 *   "copy",
 *   {
 *     extend: "excel",
 *     filename: title,
 *     title: title,
 *   },
 *   {
 *     extend: "csv",
 *     filename: title,
 *   },
 *   ...createDataTableReferencesButtonArray(references),
 * ],
 *
 */
export function createDataTableReferencesButtonArray(references?: string[]) {
  if (!references?.length) {
    return [];
  }
  return [
    {
      text: "References",
      attr: {
        "data-bs-toggle": "popover",
      },
      action: async (event: MouseEvent) => {
        const referencesTemplate = (await import("./reference_list.jst"))
          .default;
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
    },
  ];
}
