import { countBy, groupBy, isEqual, mapValues, memoize, uniq } from "lodash";
import $ from "jquery";
import "jquery-deserialize";
import { CountriesEnum } from "../../data/types/api";

/**
 * Returns immediate descendant nodes of the provided parentInput in a select-tree.
 * @param parentInput The node input for which you'd like descendents
 * @returns array of input elements
 */
export function getImmediateChildInputs(
  inputField: HTMLInputElement
): HTMLInputElement[] {
  const childListItems =
    inputField.closest("li")?.querySelector("ul")?.children ?? [];
  if (!childListItems?.length) {
    return [];
  }
  return Array.from(childListItems).map(
    (listItem) => listItem!.querySelector("input")!
  );
}

/**
 * Returns all descendant nodes of the provided parentInput in a select-tree.
 * @param parentInput The node input for which you'd like descendents
 * @returns array of input elements
 */
export function getAllChildInputs(
  parentInput: HTMLInputElement
): HTMLInputElement[] {
  return Array.from(
    (parentInput
      .closest("li")
      ?.querySelectorAll("ul input") as NodeListOf<HTMLInputElement>) ?? []
  ).filter((input) => input !== parentInput);
}

/**
 * Walk down through the select-tree starting with the provided field and update
 * all child nodes to the same value, and indeterminate=false.
 * @param inputField The field to start from (the one that's changed or known)
 * @returns void
 */
export function propagateCheckboxDown(inputField: HTMLInputElement) {
  const { checked } = inputField;
  getAllChildInputs(inputField).forEach((child) => {
    child.checked = checked;
    child.indeterminate = false;
  });
}

/**
 * Walk up through the select-tree starting with the provided field and update
 * the checked/indeterminate states of ancestor nodes based on the states of
 * their child nodes (checked if all children are checked, indeterminate if
 * some are).
 * @param inputField The field to start from (the one that's changed or known)
 * @param indeterminateOnly Don't modify the checked value of any fields
 * @returns void
 */
export function propagateCheckboxUp(
  inputField: HTMLInputElement,
  indeterminateOnly: boolean = false
) {
  const parentListItem = inputField.closest("li")?.parentElement?.closest("li");
  const parentInput = parentListItem?.querySelector("input");
  if (!parentInput) {
    return;
  }
  const cousinInputs = getAllChildInputs(parentInput);
  const { true: checked, false: unchecked } = countBy(cousinInputs, "checked");
  if (checked) {
    if (unchecked) {
      if (!indeterminateOnly) {
        parentInput.checked = false;
      }
      parentInput.indeterminate = true;
    } else {
      if (!indeterminateOnly) {
        parentInput.checked = true;
      }
      parentInput.indeterminate = false;
    }
  } else {
    if (!indeterminateOnly) {
      parentInput.checked = false;
    }
    parentInput.indeterminate = false;
  }
  propagateCheckboxUp(parentInput, indeterminateOnly);
}

/**
 * Given the root of a  tree of ul/li/[details/summary]/input, recursively find
 * all checked inputs that don't have a checked ancestor.
 * @returns an array of input elements
 */
export function getMinimalCheckedInputs(
  inputs: HTMLInputElement | HTMLInputElement[]
): HTMLInputElement[] {
  if (Array.isArray(inputs)) {
    return inputs.map(getMinimalCheckedInputs).flat();
  }
  if (inputs.checked) {
    return [inputs];
  }
  return getImmediateChildInputs(inputs)
    .map((child) => getMinimalCheckedInputs(child))
    .flat();
}

/**
 * Take values from the current URL and apply them to the provided list of forms
 * provided as IDs.
 * Propagates selected tree values down to all children and marks nodes as
 * indeterminate when they contain both selected and deselected nodes.
 * @param form the form to populate
 */
export function applyParamsToAllForms(formIds: string[]) {
  for (const id in formIds) {
    const form = document.getElementById(id) as HTMLFormElement;
    if (!form) {
      console.error(`Invalid form ID ${id} provided to applyParamsToAllForms`);
      return;
    }
    return applyParamsToForms(form);
  }
}

/**
 * Take values from the current URL and apply them to the provided form.
 * Propagates selected tree values down to all children and marks nodes as
 * indeterminate when they contain both selected and deselected nodes.
 * @param form the form to populate
 */
export function applyParamsToForms(form: HTMLFormElement) {
  const params = new URL(document.location.href).searchParams;

  const selectArrayMultipleElementsMap: Map<string, HTMLSelectElement> =
    new Map(
      (
        Array.from(
          form.querySelectorAll(".select-array-multiple")
        ) as HTMLSelectElement[]
      ).map((el) => [el.name, el])
    );

  // Regular fields use jQuery.deserialize plugin, tree-selects are done separate
  const allTreeInputs = Array.from(
    form.querySelectorAll(".select-tree-input")
  ) as HTMLInputElement[];

  // Reset all of the trees
  allTreeInputs.forEach((input) => {
    input.checked = false;
    input.indeterminate = false;
  });

  // Group the tree inputs for easy reference
  const treeInputsByNameAndCode: Record<
    string,
    Record<string, HTMLInputElement>
  > = {};

  for (const input of allTreeInputs) {
    const { name, value } = input;
    if (!treeInputsByNameAndCode[name]) {
      treeInputsByNameAndCode[name] = {
        [value]: input,
      };
    } else {
      treeInputsByNameAndCode[name][value] = input;
    }
  }

  // Apply all values from the search params to the form
  $(form).deserialize(location.search.slice(1), {
    filter: ":not(.select-tree-input,.select-array-multiple)",
  });

  // Propagating each selected node down to its children
  const checkedInputs = [];
  const arrayMultiples: Record<string, string[]> = {};
  for (const [key, val] of params.entries()) {
    const input = treeInputsByNameAndCode[key]?.[val];
    if (input) {
      input.checked = true;
      propagateCheckboxDown(input);
      checkedInputs.push(input);
    } else if (selectArrayMultipleElementsMap.has(key)) {
      if (!arrayMultiples[key]) {
        arrayMultiples[key] = [val];
      } else {
        arrayMultiples[key].push(val);
      }
    }
  }

  for (const key of selectArrayMultipleElementsMap.keys()) {
    const vals = arrayMultiples[key]! ?? [];
    updateSelectArray(selectArrayMultipleElementsMap.get(key)!, vals);
  }

  // Then set parent inputs (e.g. to indeterminate). Avoid repeating (expensive).
  const checkedParents = new Set();
  checkedInputs.forEach((input) => {
    if (!checkedParents.has(input.dataset.parent)) {
      propagateCheckboxUp(input);
      checkedParents.add(input.dataset.parent);
    }
  });
}

export function updateSelectArray(
  selectArrayElement: HTMLSelectElement,
  keys: string[]
) {
  const existing = getSelectArrayValues(selectArrayElement);
  if (isEqual(keys, existing)) {
    return;
  }
  const options = keys.map((key) => {
    const option = document.createElement("option");
    option.value = key;
    option.selected = true;
    option.innerText = key;
    return option;
  });

  selectArrayElement.innerHTML = "";
  selectArrayElement.append(...options);
}

export function reorderSelectArrayValues(
  selectArrayElementId: string,
  key: string,
  direction: "up" | "down"
) {
  const selectArrayElement = document.getElementById(
    selectArrayElementId
  ) as HTMLSelectElement;
  const selectArrayListElement = selectArrayElement.nextElementSibling!;
  const values = getSelectArrayValues(selectArrayElement);
  const index = values.indexOf(key);
  if (index === -1) {
    return;
  }
  const newValues = [...values];
  let newIndex: number;
  const clickedElement = Array.from(selectArrayListElement.children)[index]!;
  if (direction === "up") {
    newIndex = index - 1;
    if (newIndex < 0) {
      return;
    }
    const previousElement = clickedElement.previousElementSibling!;
    previousElement.remove();
    clickedElement.insertAdjacentElement("afterend", previousElement);
  } else {
    newIndex = index + 1;
    if (newValues.length <= newIndex) {
      return;
    }
    const nextElement = clickedElement.nextElementSibling!;
    nextElement.remove();
    clickedElement.insertAdjacentElement("beforebegin", nextElement);
  }
  const swapped = newValues[newIndex]!;
  newValues[index] = swapped;
  newValues[newIndex] = key;
  updateSelectArray(selectArrayElement, newValues);
}

function getSelectArrayValues(selectArrayElement: HTMLSelectElement) {
  return Array.from(selectArrayElement.options).map((opt) => opt.value);
}

export function toggleSelectArray(
  selectArrayElementId: string,
  key: string,
  listNode?: Node
): string[] {
  const selectArrayElement = document.getElementById(
    selectArrayElementId
  ) as HTMLSelectElement;
  const selectArrayListElement =
    selectArrayElement.nextElementSibling as HTMLUListElement;
  const existingIndex = Array.from(selectArrayElement.options).findIndex(
    (option) => option.value === key
  );
  if (existingIndex > -1) {
    selectArrayElement.remove(existingIndex);
    selectArrayListElement?.removeChild(
      selectArrayListElement.children[existingIndex]!
    );
  } else {
    const option = document.createElement("option");
    option.value = key;
    option.selected = true;
    option.innerText = key;
    selectArrayElement.options.add(option, selectArrayElement.options[0]);
    if (listNode) {
      selectArrayListElement?.prepend(listNode);
    }
  }
  const selectedKeys = Array.from(selectArrayElement.options).map(
    (opt) => opt.value
  );
  return selectedKeys;
}

/**
 * Take values from the provided forms (by ID) and serialize them into the URL.
 * Compresses selected tree-select values down to only the necessary nodes, i.e.
 * the highest nodes in the tree for which all children are selected.
 * @param filterFormIds The IDs of forms to serialize
 * @param clickedElement The clicked select (where relevant) from which to
 *                       propagate selections up and down the tree.
 */
export function applyAllFormValuesToParams(
  filterFormsIds: string[],
  clickedElement:
    | HTMLInputElement
    | HTMLSelectElement
    | HTMLButtonElement
    | undefined
) {
  const forms = [];
  for (const id of filterFormsIds) {
    const form = document.getElementById(id) as HTMLFormElement;
    if (!form) {
      console.error(`Invalid form ID ${id} provided to applyParamsToAllForms`);
    } else {
      forms.push(form);
    }
  }
  return applyFormValuesToParams(forms, clickedElement);
}

/**
 * Take values from the provided form and serialize them into the URL.
 * Compresses selected tree-select values down to only the necessary nodes, i.e.
 * the highest nodes in the tree for which all children are selected.
 * @param filterForms The form to serialize
 * @param clickedElement The clicked select (where relevant) from which to
 *                       propagate selections up and down the tree.
 */
export function applyFormValuesToParams(
  filterForms: HTMLFormElement | HTMLFormElement[],
  clickedElement:
    | HTMLInputElement
    | HTMLSelectElement
    | HTMLButtonElement
    | undefined
) {
  filterForms = Array.from(filterForms) as HTMLFormElement[];
  const url = new URL(document.location.href);
  url.search = "";

  for (const filterForm of filterForms) {
    const formData = new FormData(filterForm);

    const treeInputs = new Set(
      uniq(
        Array.from(
          filterForm.querySelectorAll(".select-tree-input")
        ) as HTMLInputElement[]
      ).map((input) => input.name)
    );

    // @ts-expect-error .entries() is in all browsers, but not in web standards yet (?)
    for (const [name, value] of formData.entries()) {
      if (treeInputs.has(name) || value === "" || value == null) {
        continue;
      }
      url.searchParams.append(name, value as string);
    }

    if (
      clickedElement?.type === "checkbox" &&
      clickedElement.classList.contains("select-tree-input")
    ) {
      propagateCheckboxDown(clickedElement);
      propagateCheckboxUp(clickedElement);
    }

    const rootFields = Array.from(
      filterForm.querySelectorAll(".select-tree-input-1")
    ) as HTMLInputElement[];
    const minimalChecked = getMinimalCheckedInputs(rootFields);
    const inputValuesByName = mapValues(
      groupBy(minimalChecked, (input) => input.name),
      (inputs) => inputs.map((input) => input.value)
    );
    for (const key in inputValuesByName) {
      for (const value of inputValuesByName[key]!) {
        url.searchParams.append(key, value);
      }
    }
  }

  // We could save the state but it's not used at the moment (the state is all
  // stored in the URL)
  history.pushState(null, "", url);
}

/**
 * Using the countries/areas tree (and data-parent metadata), create a
 * dictionary of area code -> country code. Needed because some areas' codes
 * start with different letters than their respective country's 2-letter code.
 * Memoized so it only happens once.
 */
export const getCountriesByAreaCode = memoize(
  function getCountriesByAreaCode(): Record<string, CountriesEnum> {
    const countriesByAreaCode: Record<string, CountriesEnum> = {};

    const regionsForm = document.getElementById(
      "regions-form"
    ) as HTMLFormElement;

    for (const input of regionsForm.areas ?? []) {
      const {
        value,
        dataset: { parent },
      } = input;
      countriesByAreaCode[value] = parent as CountriesEnum;
    }
    return countriesByAreaCode;
  }
);
export function getParamsGrouped() {
  const params = new URL(document.location.href).searchParams;
  const paramsGrouped = mapValues(groupBy([...params.entries()], 0), (pairs) =>
    pairs.map(([_, v]) => v)
  );
  return paramsGrouped;
}

export function deactivateButton(button: HTMLElement) {
  button.classList.remove("active");
  button.ariaPressed = "false";
}

export function activateButton(button: HTMLElement) {
  button.classList.add("active");
  button.ariaPressed = "true";
}
export function resetSelectTreeIndeterminate() {
  (
    document.querySelectorAll(
      ".select-tree-input[indeterminate]"
    ) as NodeListOf<HTMLInputElement>
  ).forEach((element) => {
    element.indeterminate = true;
  });
}
